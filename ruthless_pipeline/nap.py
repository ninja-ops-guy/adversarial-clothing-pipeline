from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Protocol, Sequence

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

from .common import atomic_json_dump, ensure_dir, get_logger, image_tensor_to_uint8, resolve_device, seed_everything, validate_image_tensor

log = get_logger(__name__)


class BlackBoxMode(str, Enum):
    PURE_TRANSFER = "pure_transfer"
    QUERY_EFFICIENT = "query_efficient"
    ACTIVE_LEARNING = "active_learning"


@dataclass
class BlackBoxNAPConfig:
    pattern_id: str = "ADV-NAP-001"
    version: str = "v3.0-prod"
    target_prompt: str = "abstract textile pattern"
    target_size: tuple[int, int] = (512, 512)
    black_box_mode: BlackBoxMode = BlackBoxMode.PURE_TRANSFER
    max_queries: int = 500
    surrogate_weights: Dict[str, float] = field(default_factory=dict)
    adv_loss_weight: float = 1.0
    aesthetic_loss_weight: float = 0.25
    nps_loss_weight: float = 0.10
    tv_loss_weight: float = 0.03
    learning_rate: float = 0.015
    num_iterations: int = 500
    query_interval: int = 25
    query_directions: int = 8
    query_sigma: float = 0.025
    diffusion_steps: int = 30
    diffusion_guidance_scale: float = 7.0
    diffusion_model_id: str = "runwayml/stable-diffusion-v1-5"
    diffusion_local_files_only: bool = True
    prior_backend: str = "procedural"  # procedural | diffusers
    aesthetic_backend: str = "disabled"  # disabled | open_clip
    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"
    seed: int = 1337
    device: str = "auto"
    checkpoint_every: int = 100

    def validate(self) -> None:
        h, w = self.target_size
        if h < 64 or w < 64:
            raise ValueError("target_size must be at least 64x64")
        if self.max_queries < 0:
            raise ValueError("max_queries must be non-negative")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if self.num_iterations <= 0:
            raise ValueError("num_iterations must be positive")
        if self.query_interval <= 0:
            raise ValueError("query_interval must be positive")
        if self.query_directions <= 0:
            raise ValueError("query_directions must be positive")


class TexturePrior(Protocol):
    def generate(self, prompt: str, num_samples: int = 1) -> torch.Tensor: ...


class AestheticController(Protocol):
    def loss(self, texture: torch.Tensor) -> torch.Tensor: ...


class ProceduralTexturePrior:
    """Deterministic, dependency-free natural texture prior for CI and offline runs."""

    def __init__(self, config: BlackBoxNAPConfig, device: torch.device):
        self.config = config
        self.device = device

    def generate(self, prompt: str, num_samples: int = 1) -> torch.Tensor:
        h, w = self.config.target_size
        textures = []
        for i in range(num_samples):
            g = torch.Generator(device=self.device).manual_seed(self.config.seed + i)
            base = torch.randn((1, 3, h, w), generator=g, device=self.device)
            # Odd kernels preserve HxW exactly; the old even-kernel path produced 513x513.
            low = F.avg_pool2d(base, kernel_size=63, stride=1, padding=31)
            mid = F.avg_pool2d(base, kernel_size=15, stride=1, padding=7)
            texture = 0.55 * low + 0.30 * mid + 0.15 * base
            texture = torch.sigmoid(texture)
            textures.append(texture)
        return torch.cat(textures, dim=0)


class DiffusersTexturePrior:
    """Lazy Stable Diffusion adapter. No silent fallback: missing deps/config fail loudly."""

    def __init__(self, config: BlackBoxNAPConfig, device: torch.device):
        self.config = config
        self.device = device
        try:
            from diffusers import AutoPipelineForText2Image
        except ImportError as exc:
            raise RuntimeError("diffusers backend selected but `diffusers` is not installed") from exc
        dtype = torch.float16 if device.type == "cuda" else torch.float32
        self.pipe = AutoPipelineForText2Image.from_pretrained(
            config.diffusion_model_id,
            torch_dtype=dtype,
            local_files_only=config.diffusion_local_files_only,
        )
        self.pipe = self.pipe.to(device)

    def generate(self, prompt: str, num_samples: int = 1) -> torch.Tensor:
        h, w = self.config.target_size
        generator = torch.Generator(device=self.device).manual_seed(self.config.seed)
        out = self.pipe(
            prompt=[prompt] * num_samples,
            num_inference_steps=self.config.diffusion_steps,
            guidance_scale=self.config.diffusion_guidance_scale,
            height=h,
            width=w,
            generator=generator,
        )
        tensors = []
        for img in out.images:
            arr = torch.from_numpy(np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0)
            tensors.append(arr.permute(2, 0, 1))
        return torch.stack(tensors).to(self.device)


class DisabledAestheticController:
    def __init__(self, device: torch.device):
        self.device = device

    def loss(self, texture: torch.Tensor) -> torch.Tensor:
        return texture.new_zeros(())


class OpenCLIPAestheticController:
    def __init__(self, config: BlackBoxNAPConfig, device: torch.device):
        try:
            import open_clip
        except ImportError as exc:
            raise RuntimeError("open_clip backend selected but `open_clip_torch` is not installed") from exc
        self.open_clip = open_clip
        self.device = device
        self.model, _, _ = open_clip.create_model_and_transforms(
            config.clip_model_name, pretrained=config.clip_pretrained, device=device
        )
        self.model.eval()
        for p in self.model.parameters():
            p.requires_grad_(False)
        self.tokenizer = open_clip.get_tokenizer(config.clip_model_name)
        with torch.no_grad():
            tokens = self.tokenizer([config.target_prompt]).to(device)
            target = self.model.encode_text(tokens)
            self.target = F.normalize(target.float(), dim=-1)
        # CLIP normalization constants.
        self.mean = torch.tensor([0.48145466, 0.4578275, 0.40821073], device=device).view(1, 3, 1, 1)
        self.std = torch.tensor([0.26862954, 0.26130258, 0.27577711], device=device).view(1, 3, 1, 1)

    def loss(self, texture: torch.Tensor) -> torch.Tensor:
        x = F.interpolate(texture, size=(224, 224), mode="bicubic", align_corners=False)
        x = (x - self.mean) / self.std
        emb = F.normalize(self.model.encode_image(x).float(), dim=-1)
        return 1.0 - (emb * self.target).sum(dim=-1).mean()


class NonPrintabilityScore(nn.Module):
    """Differentiable distance to an approximate printable RGB palette, chunked for memory safety."""

    def __init__(self, device: torch.device, palette_step: int = 51, pixel_stride: int = 32):
        super().__init__()
        colors = []
        vals = list(range(0, 256, palette_step))
        if vals[-1] != 255:
            vals.append(255)
        for c in vals:
            for m in vals:
                for y in vals:
                    for k in (0, 64, 128, 192):
                        r = (1 - c / 255.0) * (1 - k / 255.0)
                        g = (1 - m / 255.0) * (1 - k / 255.0)
                        b = (1 - y / 255.0) * (1 - k / 255.0)
                        colors.append((r, g, b))
        self.register_buffer("palette", torch.tensor(colors, dtype=torch.float32, device=device))
        self.pixel_stride = pixel_stride

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        validate_image_tensor(x)
        pixels = x.permute(0, 2, 3, 1).reshape(-1, 3)[:: self.pixel_stride]
        mins = []
        for chunk in pixels.split(2048):
            mins.append(torch.cdist(chunk, self.palette).min(dim=1).values)
        return torch.cat(mins).mean() if mins else x.new_zeros(())


class QueryBudgetExceeded(RuntimeError):
    pass


class QueryEfficientOptimizer:
    """Budget-aware antithetic random-direction optimizer for scalar black-box scores.

    The query function must return a scalar score to MINIMIZE. It is intentionally generic and
    intended for owned/authorized evaluation systems.
    """

    def __init__(self, config: BlackBoxNAPConfig, device: torch.device):
        self.config = config
        self.device = device
        self.query_count = 0

    @property
    def remaining(self) -> int:
        return max(0, self.config.max_queries - self.query_count)

    def _query(self, fn: Callable[[torch.Tensor], float], x: torch.Tensor) -> float:
        if self.remaining <= 0:
            raise QueryBudgetExceeded("query budget exhausted")
        score = float(fn(x.detach()))
        if not math.isfinite(score):
            raise ValueError("black-box query returned non-finite score")
        self.query_count += 1
        return score

    def step(self, texture: torch.Tensor, query_fn: Callable[[torch.Tensor], float]) -> tuple[torch.Tensor, dict]:
        sigma = self.config.query_sigma
        max_dirs = min(self.config.query_directions, self.remaining // 2)
        if max_dirs <= 0:
            return texture, {"queries": 0, "score": None}
        grad = torch.zeros_like(texture)
        scores = []
        for _ in range(max_dirs):
            direction = torch.randn_like(texture)
            direction = direction / (direction.norm() + 1e-12)
            pos = (texture + sigma * direction).clamp(0, 1)
            neg = (texture - sigma * direction).clamp(0, 1)
            s_pos = self._query(query_fn, pos)
            s_neg = self._query(query_fn, neg)
            grad = grad + ((s_pos - s_neg) / (2.0 * sigma)) * direction
            scores.extend((s_pos, s_neg))
        grad /= float(max_dirs)
        candidate = (texture - self.config.learning_rate * grad).clamp(0, 1)
        return candidate, {"queries": 2 * max_dirs, "score": float(np.mean(scores))}


class EnhancedBlackBoxNAP:
    """Production-oriented NAP optimizer with explicit backends, checkpointing, and query accounting."""

    def __init__(self, config: BlackBoxNAPConfig):
        config.validate()
        seed_everything(config.seed)
        self.config = config
        self.device = resolve_device(config.device)
        self.prior = self._build_prior()
        self.aesthetic = self._build_aesthetic()
        self.nps = NonPrintabilityScore(self.device)
        self.bb = QueryEfficientOptimizer(config, self.device)
        initial = self.prior.generate(config.target_prompt, 1)
        initial = initial.to(self.device, dtype=torch.float32)
        if initial.shape[-2:] != config.target_size:
            initial = F.interpolate(initial, size=config.target_size, mode="bilinear", align_corners=False)
        validate_image_tensor(initial)
        self.texture = nn.Parameter(initial.clamp(0, 1))
        self.optimizer = torch.optim.Adam([self.texture], lr=config.learning_rate)
        self.history: list[dict] = []
        self.query_log: list[dict] = []

    @property
    def query_count(self) -> int:
        return self.bb.query_count

    def _build_prior(self) -> TexturePrior:
        if self.config.prior_backend == "procedural":
            return ProceduralTexturePrior(self.config, self.device)
        if self.config.prior_backend == "diffusers":
            return DiffusersTexturePrior(self.config, self.device)
        raise ValueError(f"Unknown prior_backend: {self.config.prior_backend}")

    def _build_aesthetic(self) -> AestheticController:
        if self.config.aesthetic_backend == "disabled":
            return DisabledAestheticController(self.device)
        if self.config.aesthetic_backend == "open_clip":
            return OpenCLIPAestheticController(self.config, self.device)
        raise ValueError(f"Unknown aesthetic_backend: {self.config.aesthetic_backend}")

    @staticmethod
    def total_variation(x: torch.Tensor) -> torch.Tensor:
        return (x[:, :, 1:, :] - x[:, :, :-1, :]).abs().mean() + (x[:, :, :, 1:] - x[:, :, :, :-1]).abs().mean()

    def surrogate_loss(self, surrogate_fn: Callable[[torch.Tensor], Mapping[str, torch.Tensor | float]]) -> tuple[torch.Tensor, dict]:
        outputs = surrogate_fn(self.texture)
        if not outputs:
            raise ValueError("surrogate_fn returned no model scores")
        if self.config.surrogate_weights:
            weights = self.config.surrogate_weights
        else:
            weights = {name: 1.0 / len(outputs) for name in outputs}
        adv = self.texture.new_zeros(())
        used_weight = 0.0
        per_model: dict[str, float] = {}
        for name, raw in outputs.items():
            score = raw if isinstance(raw, torch.Tensor) else self.texture.new_tensor(float(raw))
            score = score.float().mean()
            if not torch.isfinite(score):
                raise ValueError(f"surrogate {name} returned non-finite score")
            w = float(weights.get(name, 0.0))
            if w <= 0:
                continue
            adv = adv + w * score
            used_weight += w
            per_model[name] = float(score.detach().cpu())
        if used_weight <= 0:
            raise ValueError("no positive surrogate weights matched returned models")
        adv = adv / used_weight
        aesthetic = self.aesthetic.loss(self.texture)
        nps = self.nps(self.texture)
        tv = self.total_variation(self.texture)
        total = (
            self.config.adv_loss_weight * adv
            + self.config.aesthetic_loss_weight * aesthetic
            + self.config.nps_loss_weight * nps
            + self.config.tv_loss_weight * tv
        )
        return total, {
            "adversarial": float(adv.detach().cpu()),
            "aesthetic": float(aesthetic.detach().cpu()),
            "nps": float(nps.detach().cpu()),
            "tv": float(tv.detach().cpu()),
            "per_model": per_model,
        }

    def optimize(
        self,
        surrogate_fn: Callable[[torch.Tensor], Mapping[str, torch.Tensor | float]],
        black_box_query_fn: Optional[Callable[[torch.Tensor], float]] = None,
        num_iterations: Optional[int] = None,
        checkpoint_dir: Optional[str | Path] = None,
    ) -> list[dict]:
        n = int(num_iterations or self.config.num_iterations)
        ckpt_dir = ensure_dir(checkpoint_dir) if checkpoint_dir else None
        for iteration in range(n):
            self.optimizer.zero_grad(set_to_none=True)
            loss, parts = self.surrogate_loss(surrogate_fn)
            loss.backward()
            torch.nn.utils.clip_grad_norm_([self.texture], max_norm=5.0)
            self.optimizer.step()
            with torch.no_grad():
                self.texture.clamp_(0, 1)

            query_meta = {"queries": 0, "score": None}
            if (
                black_box_query_fn is not None
                and self.config.black_box_mode != BlackBoxMode.PURE_TRANSFER
                and (iteration + 1) % self.config.query_interval == 0
                and self.bb.remaining >= 2
            ):
                candidate, query_meta = self.bb.step(self.texture.detach(), black_box_query_fn)
                with torch.no_grad():
                    self.texture.copy_(candidate)
                self.query_log.append({"iteration": iteration, "total_queries": self.query_count, **query_meta})

            row = {
                "iteration": iteration,
                "loss": float(loss.detach().cpu()),
                "query_count": self.query_count,
                **parts,
            }
            self.history.append(row)
            if ckpt_dir and self.config.checkpoint_every > 0 and (iteration + 1) % self.config.checkpoint_every == 0:
                self.save(ckpt_dir, suffix=f"iter{iteration+1:06d}")
        return self.history

    def save(self, output_dir: str | Path, suffix: str = "final") -> Path:
        output_dir = ensure_dir(output_dir)
        stem = f"{self.config.pattern_id}_{self.config.version}_{suffix}"
        png_path = output_dir / f"{stem}.png"
        Image.fromarray(image_tensor_to_uint8(self.texture)).save(png_path)
        torch.save({
            "texture": self.texture.detach().cpu(),
            "optimizer": self.optimizer.state_dict(),
            "history": self.history,
            "query_log": self.query_log,
            "query_count": self.query_count,
            "config": asdict(self.config),
        }, output_dir / f"{stem}.pt")
        atomic_json_dump(output_dir / f"{stem}.json", {
            "config": asdict(self.config),
            "query_count": self.query_count,
            "final": self.history[-1] if self.history else None,
            "saved_at_unix": time.time(),
        })
        return png_path

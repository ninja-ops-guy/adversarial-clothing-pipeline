from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .common import atomic_json_dump, ensure_dir, get_logger, resolve_device, seed_everything, validate_image_tensor

log = get_logger(__name__)


@dataclass
class NeuralDeformationConfig:
    hidden_dim: int = 192
    num_layers: int = 5
    positional_encoding_dim: int = 8
    include_time: bool = True
    fabric_type: str = "cotton"
    field_resolution: tuple[int, int] = (128, 128)
    learning_rate: float = 1e-3
    train_steps: int = 800
    batch_size: int = 2048
    smoothness_weight: float = 0.02
    magnitude_weight: float = 0.001
    seed: int = 1337
    device: str = "auto"

    def validate(self) -> None:
        if self.hidden_dim < 16:
            raise ValueError("hidden_dim too small")
        if self.num_layers < 2:
            raise ValueError("num_layers must be >=2")
        if self.positional_encoding_dim < 0:
            raise ValueError("positional_encoding_dim must be >=0")
        if self.batch_size <= 0 or self.train_steps <= 0:
            raise ValueError("batch_size/train_steps must be positive")


@dataclass
class DeformationObservation:
    """Observed 2D correspondences in normalized [0,1] UV coordinates."""
    source_uv: torch.Tensor       # [N,2]
    target_uv: torch.Tensor       # [N,2]
    time: Optional[torch.Tensor] = None  # [N,1]
    weight: Optional[torch.Tensor] = None  # [N,1]

    def validate(self) -> None:
        if self.source_uv.ndim != 2 or self.source_uv.shape[-1] != 2:
            raise ValueError("source_uv must be [N,2]")
        if self.target_uv.shape != self.source_uv.shape:
            raise ValueError("target_uv must match source_uv")
        if self.time is not None and (self.time.ndim != 2 or self.time.shape != (self.source_uv.shape[0], 1)):
            raise ValueError("time must be [N,1]")
        if self.weight is not None and self.weight.shape not in ((self.source_uv.shape[0],), (self.source_uv.shape[0], 1)):
            raise ValueError("weight must be [N] or [N,1]")


class PositionalEncoding(nn.Module):
    def __init__(self, num_freqs: int):
        super().__init__()
        self.num_freqs = num_freqs

    @property
    def multiplier(self) -> int:
        return 1 + 2 * self.num_freqs

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        outs = [x]
        for i in range(self.num_freqs):
            freq = (2.0 ** i) * np.pi
            outs.extend((torch.sin(freq * x), torch.cos(freq * x)))
        return torch.cat(outs, dim=-1)


class NeuralDeformationField(nn.Module):
    """Continuous deformation + uncertainty field."""

    def __init__(self, config: NeuralDeformationConfig):
        super().__init__()
        self.config = config
        self.pe = PositionalEncoding(config.positional_encoding_dim)
        base_dim = 2 * self.pe.multiplier
        if config.include_time:
            base_dim += 1 * self.pe.multiplier
        layers: list[nn.Module] = []
        d = base_dim
        for _ in range(config.num_layers - 1):
            layers += [nn.Linear(d, config.hidden_dim), nn.SiLU()]
            d = config.hidden_dim
        self.backbone = nn.Sequential(*layers)
        self.displacement_head = nn.Linear(d, 2)
        self.logvar_head = nn.Linear(d, 2)
        # Start close to identity instead of a random large warp.
        nn.init.zeros_(self.displacement_head.weight)
        nn.init.zeros_(self.displacement_head.bias)
        nn.init.constant_(self.logvar_head.bias, -4.0)

    def forward(self, coords: torch.Tensor, time: Optional[torch.Tensor] = None) -> tuple[torch.Tensor, torch.Tensor]:
        if coords.shape[-1] != 2:
            raise ValueError("coords must end in dimension 2")
        parts = [self.pe(coords)]
        if self.config.include_time:
            if time is None:
                time = torch.zeros((*coords.shape[:-1], 1), dtype=coords.dtype, device=coords.device)
            parts.append(self.pe(time))
        h = self.backbone(torch.cat(parts, dim=-1))
        disp = 0.35 * torch.tanh(self.displacement_head(h))
        logvar = self.logvar_head(h).clamp(-8.0, 3.0)
        return disp, logvar

    def predict(self, coords: torch.Tensor, time: Optional[torch.Tensor] = None) -> torch.Tensor:
        return self(coords, time)[0]

    def warp(self, image: torch.Tensor, displacement: torch.Tensor) -> torch.Tensor:
        validate_image_tensor(image)
        b, _, h, w = image.shape
        if displacement.shape != (b, h, w, 2):
            raise ValueError(f"displacement must be {(b,h,w,2)}, got {tuple(displacement.shape)}")
        yy, xx = torch.meshgrid(
            torch.linspace(-1, 1, h, device=image.device, dtype=image.dtype),
            torch.linspace(-1, 1, w, device=image.device, dtype=image.dtype),
            indexing="ij",
        )
        grid = torch.stack((xx, yy), dim=-1).unsqueeze(0).expand(b, -1, -1, -1)
        # Network displacement is normalized UV [0,1]; grid_sample needs [-1,1].
        grid = grid + 2.0 * displacement
        return F.grid_sample(image, grid, mode="bilinear", padding_mode="border", align_corners=True)


class FabricDeformationPrior:
    PARAMS = {
        "cotton": dict(stretch=(0.01, 0.08), wrinkle_amp=(0.005, 0.025), wrinkle_freq=(2.0, 6.0)),
        "polyester": dict(stretch=(0.02, 0.12), wrinkle_amp=(0.003, 0.015), wrinkle_freq=(2.0, 5.0)),
        "silk": dict(stretch=(0.01, 0.05), wrinkle_amp=(0.01, 0.035), wrinkle_freq=(3.0, 8.0)),
        "denim": dict(stretch=(0.005, 0.025), wrinkle_amp=(0.006, 0.02), wrinkle_freq=(1.0, 4.0)),
    }

    def __init__(self, config: NeuralDeformationConfig, device: torch.device):
        self.config = config
        self.device = device

    def sample_field(self, batch_size: int, h: int, w: int, generator: Optional[torch.Generator] = None) -> torch.Tensor:
        p = self.PARAMS.get(self.config.fabric_type, self.PARAMS["cotton"])
        yy, xx = torch.meshgrid(
            torch.linspace(0, 1, h, device=self.device),
            torch.linspace(0, 1, w, device=self.device),
            indexing="ij",
        )
        out = []
        for _ in range(batch_size):
            def rand(a: float, b: float) -> torch.Tensor:
                return a + (b-a) * torch.rand((), device=self.device, generator=generator)
            stretch = rand(*p["stretch"])
            amp = rand(*p["wrinkle_amp"])
            freq = rand(*p["wrinkle_freq"])
            phase = 2*np.pi*torch.rand((), device=self.device, generator=generator)
            dx = stretch * (xx - 0.5) + amp * torch.sin(2*np.pi*freq*yy + phase)
            dy = -0.5 * stretch * (yy - 0.5) + amp * torch.sin(2*np.pi*(freq*0.7)*xx - phase)
            out.append(torch.stack((dx, dy), dim=-1))
        return torch.stack(out)


class NeuralDeformationModule:
    def __init__(self, config: NeuralDeformationConfig):
        config.validate()
        seed_everything(config.seed)
        self.config = config
        self.device = resolve_device(config.device)
        self.field = NeuralDeformationField(config).to(self.device)
        self.fabric_prior = FabricDeformationPrior(config, self.device)
        self.history: list[dict] = []

    def fit(self, observation: DeformationObservation, steps: Optional[int] = None) -> list[dict]:
        observation.validate()
        src = observation.source_uv.to(self.device, dtype=torch.float32)
        tgt = observation.target_uv.to(self.device, dtype=torch.float32)
        time = observation.time.to(self.device, dtype=torch.float32) if observation.time is not None else None
        weight = observation.weight.to(self.device, dtype=torch.float32).reshape(-1, 1) if observation.weight is not None else None
        n = src.shape[0]
        opt = torch.optim.AdamW(self.field.parameters(), lr=self.config.learning_rate, weight_decay=1e-5)
        total_steps = int(steps or self.config.train_steps)
        for step in range(total_steps):
            idx = torch.randint(0, n, (min(self.config.batch_size, n),), device=self.device)
            s = src[idx]
            t = tgt[idx]
            ti = time[idx] if time is not None else None
            w = weight[idx] if weight is not None else None
            disp, logvar = self.field(s, ti)
            target_disp = t - s
            sq = (disp - target_disp).pow(2)
            nll = 0.5 * (torch.exp(-logvar) * sq + logvar)
            if w is not None:
                nll = nll * w
            data_loss = nll.mean()
            # Smoothness via nearby coordinate perturbation.
            eps = 1.0 / max(self.config.field_resolution)
            jitter = torch.randn_like(s) * eps
            disp2, _ = self.field((s + jitter).clamp(0, 1), ti)
            smooth = (disp2 - disp).pow(2).mean() / (eps * eps + 1e-12)
            magnitude = disp.pow(2).mean()
            loss = data_loss + self.config.smoothness_weight * smooth + self.config.magnitude_weight * magnitude
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.field.parameters(), 5.0)
            opt.step()
            if step % 50 == 0 or step == total_steps - 1:
                self.history.append({
                    "step": step,
                    "loss": float(loss.detach().cpu()),
                    "data_loss": float(data_loss.detach().cpu()),
                    "smoothness": float(smooth.detach().cpu()),
                })
        return self.history

    def predict_field(self, batch_size: int, h: int, w: int, time_value: float = 0.0) -> tuple[torch.Tensor, torch.Tensor]:
        yy, xx = torch.meshgrid(
            torch.linspace(0, 1, h, device=self.device),
            torch.linspace(0, 1, w, device=self.device),
            indexing="ij",
        )
        coords = torch.stack((xx, yy), dim=-1).reshape(-1, 2)
        ti = torch.full((coords.shape[0], 1), float(time_value), device=self.device) if self.config.include_time else None
        disp, logvar = self.field(coords, ti)
        disp = disp.reshape(1, h, w, 2).expand(batch_size, -1, -1, -1)
        unc = torch.exp(0.5 * logvar).reshape(1, h, w, 2).expand(batch_size, -1, -1, -1)
        return disp, unc

    def sample_warp(self, batch_size: int, h: int, w: int, learned_weight: float = 0.5) -> torch.Tensor:
        learned, _ = self.predict_field(batch_size, h, w)
        prior = self.fabric_prior.sample_field(batch_size, h, w)
        return learned_weight * learned + (1.0 - learned_weight) * prior

    def apply_warp(self, texture: torch.Tensor, displacement: Optional[torch.Tensor] = None) -> torch.Tensor:
        validate_image_tensor(texture)
        b, _, h, w = texture.shape
        if displacement is None:
            displacement = self.sample_warp(b, h, w)
        if displacement.shape[1:3] != (h, w):
            displacement = F.interpolate(displacement.permute(0,3,1,2), size=(h,w), mode="bilinear", align_corners=True).permute(0,2,3,1)
        return self.field.warp(texture, displacement.to(texture.device, texture.dtype))

    def save(self, output_dir: str | Path, name: str = "deformation_field") -> Path:
        output_dir = ensure_dir(output_dir)
        path = output_dir / f"{name}_{self.config.fabric_type}.pt"
        torch.save({"state_dict": self.field.state_dict(), "config": asdict(self.config), "history": self.history}, path)
        atomic_json_dump(output_dir / f"{name}_{self.config.fabric_type}.json", {"config": asdict(self.config), "history": self.history[-20:]})
        return path

    @classmethod
    def load(cls, path: str | Path, map_location: str = "cpu") -> "NeuralDeformationModule":
        payload = torch.load(path, map_location=map_location, weights_only=False)
        cfg = NeuralDeformationConfig(**payload["config"])
        cfg.device = map_location
        obj = cls(cfg)
        obj.field.load_state_dict(payload["state_dict"])
        obj.history = payload.get("history", [])
        return obj


def synthetic_observation(n: int = 5000, amplitude: float = 0.03, seed: int = 0) -> DeformationObservation:
    g = torch.Generator().manual_seed(seed)
    uv = torch.rand((n, 2), generator=g)
    x, y = uv[:, 0], uv[:, 1]
    dx = amplitude * torch.sin(2 * np.pi * 3 * y)
    dy = amplitude * torch.sin(2 * np.pi * 2 * x)
    target = (uv + torch.stack((dx, dy), dim=-1)).clamp(0, 1)
    return DeformationObservation(uv, target)

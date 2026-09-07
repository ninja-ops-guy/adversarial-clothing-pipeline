from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Callable, Mapping, Sequence

import torch
import torch.nn.functional as F

from .common import seed_everything, validate_image_tensor


@dataclass
class EnvironmentAdaptiveConfig:
    """RAC implementation inspired by CAPGen's pattern/color decomposition.

    This module is intentionally surrogate-only. Held-out models belong to the
    certification boundary and must never be passed to optimize().
    """

    num_base_colors: int = 3
    temperature: float = 0.10
    num_iterations: int = 100
    learning_rate: float = 0.05
    entropy_weight: float = 0.03
    tv_weight: float = 0.01
    eot_samples: int = 4
    brightness_range: tuple[float, float] = (0.75, 1.25)
    rotation_deg: float = 20.0
    scale_range: tuple[float, float] = (0.80, 1.20)
    max_palette_pixels: int = 50_000
    kmeans_iterations: int = 20
    seed: int = 1337

    def validate(self) -> None:
        if self.num_base_colors < 2:
            raise ValueError("num_base_colors must be >= 2")
        if self.temperature <= 0:
            raise ValueError("temperature must be positive")
        if self.num_iterations <= 0:
            raise ValueError("num_iterations must be positive")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if self.eot_samples <= 0:
            raise ValueError("eot_samples must be positive")
        if self.max_palette_pixels <= 0:
            raise ValueError("max_palette_pixels must be positive")
        if self.kmeans_iterations <= 0:
            raise ValueError("kmeans_iterations must be positive")
        lo, hi = self.brightness_range
        if not (0 < lo <= hi):
            raise ValueError("invalid brightness_range")
        lo, hi = self.scale_range
        if not (0 < lo <= hi):
            raise ValueError("invalid scale_range")


@dataclass
class EnvironmentAdaptiveResult:
    patch: torch.Tensor
    logits: torch.Tensor
    base_colors: torch.Tensor
    history: list[dict]
    config: dict


def _sample_pixels(images: Sequence[torch.Tensor], max_pixels: int) -> torch.Tensor:
    if not images:
        raise ValueError("at least one environment image is required")
    chunks: list[torch.Tensor] = []
    for image in images:
        validate_image_tensor(image)
        pixels = image.detach().float().clamp(0, 1).permute(0, 2, 3, 1).reshape(-1, 3)
        chunks.append(pixels)
    all_pixels = torch.cat(chunks, dim=0)
    if all_pixels.shape[0] > max_pixels:
        idx = torch.linspace(0, all_pixels.shape[0] - 1, max_pixels, device=all_pixels.device).long()
        all_pixels = all_pixels[idx]
    return all_pixels


def extract_base_colors(
    images: Sequence[torch.Tensor],
    num_colors: int = 3,
    max_pixels: int = 50_000,
    iterations: int = 20,
    seed: int = 1337,
) -> torch.Tensor:
    """Deterministic K-means palette extraction in RGB [0,1]."""
    if num_colors < 2:
        raise ValueError("num_colors must be >= 2")
    pixels = _sample_pixels(images, max_pixels)
    if pixels.shape[0] < num_colors:
        raise ValueError("not enough pixels for requested color count")

    g = torch.Generator(device=pixels.device).manual_seed(seed)
    first = torch.randint(0, pixels.shape[0], (1,), generator=g, device=pixels.device).item()
    centers = [pixels[first]]
    for _ in range(1, num_colors):
        stacked = torch.stack(centers)
        dist = torch.cdist(pixels, stacked).min(dim=1).values
        next_idx = int(dist.argmax().item())
        centers.append(pixels[next_idx])
    centers_t = torch.stack(centers)

    for _ in range(iterations):
        labels = torch.cdist(pixels, centers_t).argmin(dim=1)
        updated = []
        for k in range(num_colors):
            cluster = pixels[labels == k]
            updated.append(cluster.mean(dim=0) if cluster.numel() else centers_t[k])
        new_centers = torch.stack(updated)
        if torch.allclose(new_centers, centers_t, atol=1e-5, rtol=0):
            centers_t = new_centers
            break
        centers_t = new_centers

    # Stable ordering by luminance makes recoloring deterministic across environments.
    luminance = 0.2126 * centers_t[:, 0] + 0.7152 * centers_t[:, 1] + 0.0722 * centers_t[:, 2]
    return centers_t[luminance.argsort()]


def initialize_pattern_logits(texture: torch.Tensor, num_colors: int, strength: float = 8.0) -> torch.Tensor:
    """Encode color-agnostic local structure into categorical color-allocation logits.

    The initialization uses relative luminance ranks rather than absolute RGB, preserving
    edges/regions while allowing a completely different environment palette later.
    """
    validate_image_tensor(texture)
    if texture.shape[0] != 1:
        raise ValueError("pattern initialization currently expects a single texture")
    lum = 0.2126 * texture[:, 0:1] + 0.7152 * texture[:, 1:2] + 0.0722 * texture[:, 2:3]
    anchors = torch.linspace(0, 1, num_colors, device=texture.device, dtype=texture.dtype).view(1, num_colors, 1, 1)
    logits = -strength * (lum - anchors).abs()
    return logits


def render_palette_patch(logits: torch.Tensor, base_colors: torch.Tensor, temperature: float = 0.10) -> torch.Tensor:
    if logits.ndim != 4:
        raise ValueError("logits must be BCHW")
    if base_colors.ndim != 2 or base_colors.shape[1] != 3:
        raise ValueError("base_colors must have shape [K,3]")
    if logits.shape[1] != base_colors.shape[0]:
        raise ValueError("logit channel count must equal number of base colors")
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    probs = torch.softmax(logits / temperature, dim=1)
    colors = base_colors.to(logits.device, logits.dtype).view(1, -1, 3, 1, 1)
    patch = (probs.unsqueeze(2) * colors).sum(dim=1)
    return patch.clamp(0, 1)


def color_allocation_entropy(logits: torch.Tensor, temperature: float) -> torch.Tensor:
    probs = torch.softmax(logits / temperature, dim=1).clamp_min(1e-8)
    return -(probs * probs.log()).sum(dim=1).mean()


def allocation_tv(logits: torch.Tensor) -> torch.Tensor:
    probs = torch.softmax(logits, dim=1)
    return (
        (probs[:, :, 1:, :] - probs[:, :, :-1, :]).abs().mean()
        + (probs[:, :, :, 1:] - probs[:, :, :, :-1]).abs().mean()
    )


def _eot_transform(
    patch: torch.Tensor,
    brightness: float,
    rotation_deg: float,
    scale: float,
) -> torch.Tensor:
    validate_image_tensor(patch)
    x = (patch * brightness).clamp(0, 1)
    angle = math.radians(rotation_deg)
    c, s = math.cos(angle), math.sin(angle)
    theta = torch.tensor(
        [[[c / scale, -s / scale, 0.0], [s / scale, c / scale, 0.0]]],
        device=x.device,
        dtype=x.dtype,
    ).repeat(x.shape[0], 1, 1)
    grid = F.affine_grid(theta, x.shape, align_corners=False)
    return F.grid_sample(x, grid, mode="bilinear", padding_mode="border", align_corners=False)


class EnvironmentAdaptivePatchGenerator:
    """Environment-adaptive, palette-constrained surrogate optimizer.

    The generator receives a pre-existing seed texture (e.g. NAP or textile-generator
    output), extracts environment colors, preserves the texture's structural allocation,
    and optimizes only against explicitly supplied surrogate scoring functions.
    """

    def __init__(self, config: EnvironmentAdaptiveConfig | None = None):
        self.config = config or EnvironmentAdaptiveConfig()
        self.config.validate()
        seed_everything(self.config.seed)

    def extract_palette(self, environment_images: Sequence[torch.Tensor]) -> torch.Tensor:
        return extract_base_colors(
            environment_images,
            num_colors=self.config.num_base_colors,
            max_pixels=self.config.max_palette_pixels,
            iterations=self.config.kmeans_iterations,
            seed=self.config.seed,
        )

    def recolor(
        self,
        pattern_logits: torch.Tensor,
        environment_images: Sequence[torch.Tensor],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Rapid environment adaptation: preserve pattern logits, replace base colors only."""
        colors = self.extract_palette(environment_images).to(pattern_logits.device)
        patch = render_palette_patch(pattern_logits, colors, self.config.temperature)
        return patch, colors

    def _expected_surrogate_loss(
        self,
        patch: torch.Tensor,
        surrogate_fn: Callable[[torch.Tensor], Mapping[str, torch.Tensor | float]],
        generator: torch.Generator,
    ) -> tuple[torch.Tensor, dict[str, float]]:
        total = patch.new_zeros(())
        per_model_acc: dict[str, float] = {}

        for _ in range(self.config.eot_samples):
            br_lo, br_hi = self.config.brightness_range
            sc_lo, sc_hi = self.config.scale_range
            brightness = float(torch.empty((), device=patch.device).uniform_(br_lo, br_hi, generator=generator).item())
            scale = float(torch.empty((), device=patch.device).uniform_(sc_lo, sc_hi, generator=generator).item())
            rotation = float(
                torch.empty((), device=patch.device)
                .uniform_(-self.config.rotation_deg, self.config.rotation_deg, generator=generator)
                .item()
            )
            transformed = _eot_transform(patch, brightness, rotation, scale)
            outputs = surrogate_fn(transformed)
            if not outputs:
                raise ValueError("surrogate_fn returned no model scores")
            sample_loss = patch.new_zeros(())
            for name, raw in outputs.items():
                score = raw if isinstance(raw, torch.Tensor) else patch.new_tensor(float(raw))
                score = score.float().mean()
                if not torch.isfinite(score):
                    raise ValueError(f"surrogate {name} returned non-finite score")
                sample_loss = sample_loss + score
                per_model_acc[name] = per_model_acc.get(name, 0.0) + float(score.detach().cpu())
            sample_loss = sample_loss / len(outputs)
            total = total + sample_loss

        total = total / self.config.eot_samples
        per_model = {name: value / self.config.eot_samples for name, value in per_model_acc.items()}
        return total, per_model

    def optimize(
        self,
        seed_texture: torch.Tensor,
        environment_images: Sequence[torch.Tensor],
        surrogate_fn: Callable[[torch.Tensor], Mapping[str, torch.Tensor | float]],
        num_iterations: int | None = None,
    ) -> EnvironmentAdaptiveResult:
        validate_image_tensor(seed_texture)
        if seed_texture.shape[0] != 1:
            raise ValueError("optimize currently expects one seed texture")
        colors = self.extract_palette(environment_images).to(seed_texture.device, seed_texture.dtype)
        logits = torch.nn.Parameter(initialize_pattern_logits(seed_texture, self.config.num_base_colors))
        optimizer = torch.optim.Adam([logits], lr=self.config.learning_rate)
        steps = int(num_iterations or self.config.num_iterations)
        g = torch.Generator(device=seed_texture.device).manual_seed(self.config.seed)
        history: list[dict] = []

        for iteration in range(steps):
            optimizer.zero_grad(set_to_none=True)
            patch = render_palette_patch(logits, colors, self.config.temperature)
            adv, per_model = self._expected_surrogate_loss(patch, surrogate_fn, g)
            entropy = color_allocation_entropy(logits, self.config.temperature)
            tv = allocation_tv(logits)
            loss = adv + self.config.entropy_weight * entropy + self.config.tv_weight * tv
            loss.backward()
            torch.nn.utils.clip_grad_norm_([logits], max_norm=5.0)
            optimizer.step()

            history.append(
                {
                    "iteration": iteration,
                    "loss": float(loss.detach().cpu()),
                    "adversarial": float(adv.detach().cpu()),
                    "entropy": float(entropy.detach().cpu()),
                    "allocation_tv": float(tv.detach().cpu()),
                    "per_model": per_model,
                }
            )

        final_patch = render_palette_patch(logits.detach(), colors, self.config.temperature)
        return EnvironmentAdaptiveResult(
            patch=final_patch,
            logits=logits.detach(),
            base_colors=colors.detach(),
            history=history,
            config=asdict(self.config),
        )

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

import torch
from PIL import Image

from .capgen import EnvironmentAdaptiveConfig, EnvironmentAdaptivePatchGenerator
from .common import atomic_json_dump, ensure_dir, image_tensor_to_uint8, validate_image_tensor


@dataclass
class CandidateGenerationConfig:
    candidate_id: str = "RAC-CAP-001"
    generator_version: str = "1.0.0"
    optimizer: str = "EnvironmentAdaptivePatchGenerator"
    environment_profile: str = "unspecified"


@dataclass
class CandidateArtifact:
    candidate_id: str
    patch: torch.Tensor
    metadata: dict

    def save(self, output_dir: str | Path) -> tuple[Path, Path]:
        output_dir = ensure_dir(output_dir)
        png = output_dir / f"{self.candidate_id}.png"
        meta = output_dir / f"{self.candidate_id}.json"
        Image.fromarray(image_tensor_to_uint8(self.patch)).save(png)
        atomic_json_dump(meta, self.metadata)
        return png, meta


class DetectorDrivenCandidateOptimizer:
    """Upstream candidate generator that is intentionally blind to D2 held-out models."""

    def __init__(
        self,
        generation: CandidateGenerationConfig | None = None,
        adaptive: EnvironmentAdaptiveConfig | None = None,
    ):
        self.generation = generation or CandidateGenerationConfig()
        self.adaptive = EnvironmentAdaptivePatchGenerator(adaptive)

    def optimize(
        self,
        seed_texture: torch.Tensor,
        environment_images: Sequence[torch.Tensor],
        surrogate_fn: Callable[[torch.Tensor], Mapping[str, torch.Tensor | float]],
        surrogate_model_ids: Sequence[str],
    ) -> CandidateArtifact:
        validate_image_tensor(seed_texture)
        model_ids = tuple(str(x) for x in surrogate_model_ids)
        if not model_ids:
            raise ValueError("at least one surrogate_model_id is required")
        if len(set(model_ids)) != len(model_ids):
            raise ValueError("duplicate surrogate_model_id")
        result = self.adaptive.optimize(seed_texture, environment_images, surrogate_fn)
        metadata = {
            "candidate_id": self.generation.candidate_id,
            "evidence_class": "candidate_generation_only",
            "optimizer": self.generation.optimizer,
            "optimizer_version": self.generation.generator_version,
            "environment_profile": self.generation.environment_profile,
            "surrogate_model_ids": list(model_ids),
            "heldout_models_used": [],
            "base_colors_rgb01": result.base_colors.detach().cpu().tolist(),
            "adaptive_config": result.config,
            "final_training_metrics": result.history[-1] if result.history else None,
            "notes": [
                "This artifact is not D2 evidence.",
                "Held-out models must remain unused until the candidate is frozen.",
                "Re-optimization after held-out evaluation invalidates the D2 generation.",
            ],
        }
        return CandidateArtifact(self.generation.candidate_id, result.patch, metadata)

    def recolor(
        self,
        pattern_logits: torch.Tensor,
        environment_images: Sequence[torch.Tensor],
        source_candidate_id: str,
    ) -> CandidateArtifact:
        patch, colors = self.adaptive.recolor(pattern_logits, environment_images)
        metadata = {
            "candidate_id": self.generation.candidate_id,
            "evidence_class": "candidate_generation_only",
            "optimizer": "EnvironmentAdaptiveRecolor",
            "optimizer_version": self.generation.generator_version,
            "environment_profile": self.generation.environment_profile,
            "source_candidate_id": source_candidate_id,
            "heldout_models_used": [],
            "base_colors_rgb01": colors.detach().cpu().tolist(),
            "adaptive_config": asdict(self.adaptive.config),
            "notes": [
                "Pattern allocation preserved; environment colors replaced.",
                "This artifact is not D2 evidence.",
            ],
        }
        return CandidateArtifact(self.generation.candidate_id, patch, metadata)

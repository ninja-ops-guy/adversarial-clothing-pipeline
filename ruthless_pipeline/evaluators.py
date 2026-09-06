from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import torch
import torch.nn as nn

from .common import resolve_device, validate_image_tensor


@dataclass
class TorchvisionDetectionEvaluator:
    """Adapter around a torchvision-style detection model already loaded by the caller.

    The model is expected to return a list of dicts with `labels` and `scores`. This adapter does
    not download weights and therefore keeps model/version provenance under the experimenter's control.
    """
    name: str
    model: nn.Module
    class_label: int = 1
    device: str = "auto"

    def __post_init__(self):
        self._device = resolve_device(self.device)
        self.model = self.model.to(self._device).eval()
        for p in self.model.parameters():
            p.requires_grad_(False)

    def score(self, images: torch.Tensor) -> torch.Tensor:
        validate_image_tensor(images)
        imgs = images.to(self._device)
        outputs = self.model([img for img in imgs])
        scores = []
        for out in outputs:
            labels = out.get("labels")
            raw_scores = out.get("scores")
            if labels is None or raw_scores is None:
                raise ValueError("detector output must contain labels and scores")
            selected = raw_scores[labels == self.class_label]
            scores.append(selected.max() if selected.numel() else raw_scores.new_zeros(()))
        return torch.stack(scores)


@dataclass
class DifferentiableScoreEvaluator:
    """Simple adapter for models/callables that directly return differentiable scalar scores per image."""
    name: str
    fn: Callable[[torch.Tensor], torch.Tensor]

    def score(self, images: torch.Tensor) -> torch.Tensor:
        out = self.fn(images)
        if not isinstance(out, torch.Tensor):
            raise TypeError("DifferentiableScoreEvaluator requires a torch.Tensor output")
        return out.reshape(-1)

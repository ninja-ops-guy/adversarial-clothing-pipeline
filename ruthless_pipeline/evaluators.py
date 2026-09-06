from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import torch
import torch.nn as nn

from .common import resolve_device, validate_image_tensor


@dataclass
class DetectionBatch:
    boxes: list[torch.Tensor]
    labels: list[torch.Tensor]
    scores: list[torch.Tensor]
    target_scores: torch.Tensor


@dataclass
class TorchvisionDetectionEvaluator:
    """Adapter around a caller-supplied torchvision-style detector.

    Full predictions are retained for certification analysis while score() remains
    backward compatible with optimization and comparative benchmark callers.
    """

    name: str
    model: nn.Module
    class_label: int = 1
    device: str = "auto"

    def __post_init__(self):
        self._device = resolve_device(self.device)
        self.model = self.model.to(self._device).eval()
        for parameter in self.model.parameters():
            parameter.requires_grad_(False)

    def predict(self, images: torch.Tensor) -> DetectionBatch:
        validate_image_tensor(images)
        imgs = images.to(self._device)
        outputs = self.model([img for img in imgs])
        boxes: list[torch.Tensor] = []
        labels: list[torch.Tensor] = []
        raw_scores: list[torch.Tensor] = []
        target_scores: list[torch.Tensor] = []
        for out in outputs:
            out_boxes = out.get("boxes")
            out_labels = out.get("labels")
            out_scores = out.get("scores")
            if out_boxes is None or out_labels is None or out_scores is None:
                raise ValueError("detector output must contain boxes, labels, and scores")
            boxes.append(out_boxes.detach())
            labels.append(out_labels.detach())
            raw_scores.append(out_scores.detach())
            selected = out_scores[out_labels == self.class_label]
            target_scores.append(selected.max() if selected.numel() else out_scores.new_zeros(()))
        return DetectionBatch(boxes, labels, raw_scores, torch.stack(target_scores))

    def score(self, images: torch.Tensor) -> torch.Tensor:
        return self.predict(images).target_scores


@dataclass
class DifferentiableScoreEvaluator:
    name: str
    fn: Callable[[torch.Tensor], torch.Tensor]

    def score(self, images: torch.Tensor) -> torch.Tensor:
        out = self.fn(images)
        if not isinstance(out, torch.Tensor):
            raise TypeError("DifferentiableScoreEvaluator requires a torch.Tensor output")
        return out.reshape(-1)

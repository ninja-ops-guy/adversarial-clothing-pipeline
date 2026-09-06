from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn.functional as F

from .common import validate_image_tensor


@dataclass
class GarmentSceneBatch:
    """Owned/authorized lab scene with a garment region mask.

    images: BCHW RGB in [0,1]
    masks:  B1HW in [0,1], where 1 denotes the garment print region
    """
    images: torch.Tensor
    masks: torch.Tensor

    def validate(self) -> None:
        validate_image_tensor(self.images)
        if self.masks.ndim != 4 or self.masks.shape[1] != 1:
            raise ValueError("masks must be B1HW")
        if self.masks.shape[0] != self.images.shape[0] or self.masks.shape[-2:] != self.images.shape[-2:]:
            raise ValueError("mask batch/spatial shape must match images")
        if not torch.isfinite(self.masks).all():
            raise ValueError("masks contain NaN/Inf")


class GarmentTextureComposer:
    """Differentiable 2D garment texture compositor.

    This is the bridge between a generated texture and detector input images. For high-fidelity
    experiments, feed it masks/UV maps from the deformation or physics pipeline rather than
    evaluating a raw texture as if it were itself a surveillance-camera frame.
    """

    def __init__(self, tile: bool = True):
        self.tile = tile

    def _texture_to_frame(self, texture: torch.Tensor, h: int, w: int) -> torch.Tensor:
        validate_image_tensor(texture)
        if self.tile:
            th, tw = texture.shape[-2:]
            reps_h = max(1, (h + th - 1) // th)
            reps_w = max(1, (w + tw - 1) // tw)
            out = texture.repeat(1, 1, reps_h, reps_w)[..., :h, :w]
        else:
            out = F.interpolate(texture, size=(h,w), mode="bilinear", align_corners=False)
        return out

    def compose(
        self,
        scene: GarmentSceneBatch,
        texture: torch.Tensor,
        warped_texture: Optional[torch.Tensor] = None,
        opacity: float = 1.0,
    ) -> torch.Tensor:
        scene.validate()
        x = scene.images
        mask = scene.masks.clamp(0,1)
        tex = warped_texture if warped_texture is not None else texture
        if tex.shape[0] == 1 and x.shape[0] > 1:
            tex = tex.expand(x.shape[0], -1, -1, -1)
        if tex.shape[0] != x.shape[0]:
            raise ValueError("texture batch must be 1 or match scene batch")
        tex = self._texture_to_frame(tex, x.shape[-2], x.shape[-1])
        alpha = (mask * float(opacity)).clamp(0,1)
        return x * (1-alpha) + tex * alpha

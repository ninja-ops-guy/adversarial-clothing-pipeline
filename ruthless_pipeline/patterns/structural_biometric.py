"""Structural/biometric P0 generators (spec section 4.1-4.3).

Landmark- and sensor-targeted attacks. All rendering is deterministic
numpy/PIL on an RGB canvas of params.output_size.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
from PIL import Image, ImageDraw

from .base import (
    GeneratedPattern,
    GeneratorParams,
    PatternGenerator,
    base_param_schema,
    require_bboxes,
    require_landmarks,
)

_HIGH_CONTRAST = ["#000000", "#FFFFFF", "#FF0000"]


def _canvas(output_size: Tuple[int, int], background: str = "#808080") -> ImageDraw.ImageDraw:
    img = Image.new("RGB", (int(output_size[0]), int(output_size[1])), background)
    return ImageDraw.Draw(img), img


def _to_array(img: Image.Image) -> np.ndarray:
    return np.asarray(img, dtype=np.uint8).copy()


class HyperfaceLikeGenerator(PatternGenerator):
    """High-contrast geometric shapes over detected features.

    Based on Hyperface/CV Dazzle principles (spec section 4.1).
    """

    name = "hyperface_like"
    version = "1.0.0"
    category = "structural_biometric"
    priority = "P0"

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        self.validate_params(params)
        landmarks = require_landmarks(params, ["left_eye", "right_eye", "mouth_center"])
        rng = np.random.default_rng(params.seed)
        p = params.params
        concentric_count = int(p.get("concentric_count", 4))
        shape_count = int(p.get("shape_count", 10))
        scheme = p.get("color_scheme", "bwr")
        palette = {"bw": ["#000000", "#FFFFFF"],
                   "bwr": _HIGH_CONTRAST,
                   "full": ["#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF"]}[scheme]

        draw, img = _canvas(params.output_size)
        w, h = int(params.output_size[0]), int(params.output_size[1])

        # 1-2. Concentric circles at eye/mouth locations.
        for name, entry in sorted(landmarks.items()):
            if any(t in name for t in ("eye", "mouth")):
                cx, cy = float(entry["position"][0]), float(entry["position"][1])
                for i in range(concentric_count):
                    r = 10.0 * (i + 1)
                    color = palette[i % len(palette)]
                    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)

        # 3. Blocky geometric shapes.
        for _ in range(shape_count):
            shape = ["rectangle", "line", "triangle"][int(rng.integers(0, 3))]
            color = palette[int(rng.integers(0, len(palette)))]
            x0, y0 = float(rng.uniform(0, w)), float(rng.uniform(0, h))
            x1, y1 = float(rng.uniform(0, w)), float(rng.uniform(0, h))
            if shape == "rectangle":
                draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)],
                               fill=color)
            elif shape == "line":
                draw.line([x0, y0, x1, y1], fill=color, width=int(rng.integers(3, 9)))
            else:
                x2, y2 = float(rng.uniform(0, w)), float(rng.uniform(0, h))
                draw.polygon([(x0, y0), (x1, y1), (x2, y2)], fill=color)

        return self._finalize(params, _to_array(img))

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema({
            "concentric_count": {"type": "integer", "minimum": 3, "maximum": 10},
            "shape_count": {"type": "integer", "minimum": 5, "maximum": 30},
            "color_scheme": {"type": "string", "enum": ["bw", "bwr", "full"]},
        })


class DazzleSurgicalLinesGenerator(PatternGenerator):
    """Thick lines connecting facial landmarks to break feature continuity.

    Classic CV Dazzle approach (spec section 4.2).
    """

    name = "dazzle_surgical_lines"
    version = "1.0.0"
    category = "structural_biometric"
    priority = "P0"

    _EDGES = [
        ("left_eye", "right_eye"),
        ("left_eye", "nose_tip"),
        ("right_eye", "nose_tip"),
        ("nose_tip", "mouth_center"),
        ("left_brow", "right_brow"),
        ("left_cheek", "right_cheek"),
    ]

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        self.validate_params(params)
        landmarks = require_landmarks(
            params, ["left_eye", "right_eye", "nose_tip", "mouth_center"])
        rng = np.random.default_rng(params.seed)
        draw, img = _canvas(params.output_size, background="#FFFFFF")

        for a, b in self._EDGES:
            if a in landmarks and b in landmarks:
                pa, pb = landmarks[a]["position"], landmarks[b]["position"]
                thickness = int(rng.integers(10, 20))
                color = _HIGH_CONTRAST[int(rng.integers(0, len(_HIGH_CONTRAST)))]
                draw.line([float(pa[0]), float(pa[1]), float(pb[0]), float(pb[1])],
                          fill=color, width=thickness)
                # Asymmetric color break: offset secondary stroke.
                off = float(rng.uniform(-6, 6))
                color2 = _HIGH_CONTRAST[int(rng.integers(0, len(_HIGH_CONTRAST)))]
                draw.line([float(pa[0]) + off, float(pa[1]),
                           float(pb[0]) + off, float(pb[1])],
                          fill=color2, width=max(2, thickness // 3))

        return self._finalize(params, _to_array(img))

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema({
            "min_thickness": {"type": "integer", "minimum": 5, "maximum": 20},
        })


class KeyFeatureBlackoutGenerator(PatternGenerator):
    """Solid bars over eyes and mouth using detected bounding boxes.

    Simple, effective occlusion (spec section 4.3).
    """

    name = "key_feature_blackout"
    version = "1.0.0"
    category = "structural_biometric"
    priority = "P0"

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        self.validate_params(params)
        bboxes = require_bboxes(params, ["eyes", "mouth"])
        rng = np.random.default_rng(params.seed)
        draw, img = _canvas(params.output_size, background="#FFFFFF")

        for feature in ("eyes", "mouth"):
            x, y, bw, bh = [float(v) for v in bboxes[feature]]
            pad = float(rng.integers(5, 15))  # extend beyond feature
            color = "#000000" if feature == "eyes" else "#FFFFFF"
            outline = "#FFFFFF" if feature == "eyes" else "#000000"
            draw.rectangle([x - pad, y - pad, x + bw + pad, y + bh + pad],
                           fill=color, outline=outline, width=2)

        return self._finalize(params, _to_array(img))

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema({
            "padding_min": {"type": "integer", "minimum": 0, "maximum": 30},
        })

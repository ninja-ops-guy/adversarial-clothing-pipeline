"""Feature-disruption P0 generators (spec section 4.4-4.8).

Feature overload attacks. Eye/feature sprites are generated deterministically
in code (no network, no asset files): an eye sprite is a white ellipse with a
dark pupil; mouth and nose sprites are similarly primitive.

adversarial_patch: the spec's ``_generate_optimized_patch`` implies live
optimization against target models. That optimization bridges to the existing
RAC optimization pipeline (ruthless_pipeline.optimization); THIS generator
produces the candidate geometry only, as a deterministic structured
high-frequency noise patch. No live optimization is performed here.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw

from .base import (
    GeneratedPattern,
    GeneratorParams,
    MissingLandmarksError,
    PatternGenerator,
    base_param_schema,
    require_landmarks,
)


# ---------------------------------------------------------------------------
# Deterministic synthetic sprites
# ---------------------------------------------------------------------------

def eye_sprite(size: int = 32, pupil_ratio: float = 0.35) -> Image.Image:
    """White ellipse + dark pupil, RGBA."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, size // 4, size - 2, size - 1 - size // 4], fill=(255, 255, 255, 255),
              outline=(0, 0, 0, 255))
    r = size * pupil_ratio / 2
    cx, cy = size / 2, size / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(10, 10, 10, 255))
    return img


def mouth_sprite(size: int = 32) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, size // 3, size - 2, size - 1 - size // 3],
              fill=(120, 20, 20, 255), outline=(0, 0, 0, 255))
    return img


def nose_sprite(size: int = 32) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(size / 2, 2), (2, size - 2), (size - 2, size - 2)],
              fill=(200, 160, 140, 255), outline=(0, 0, 0, 255))
    return img


def _paste_sprite(canvas: Image.Image, sprite: Image.Image, position: Tuple[float, float],
                  scale: float, rotation: float, opacity: float = 1.0) -> None:
    s = max(1, int(round(sprite.width * scale)))
    spr = sprite.resize((s, s), Image.NEAREST).rotate(rotation, expand=True)
    if opacity < 1.0:
        alpha = spr.getchannel("A").point(lambda a: int(a * opacity))
        spr.putalpha(alpha)
    x = int(round(position[0])) - spr.width // 2
    y = int(round(position[1])) - spr.height // 2
    canvas.paste(spr, (x, y), spr)


def _blank(output_size: Tuple[int, int], bg=(128, 128, 128)) -> Image.Image:
    return Image.new("RGB", (int(output_size[0]), int(output_size[1])), bg)


def _arr(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB"), dtype=np.uint8).copy()


class SaliencyEyeAttackGenerator(PatternGenerator):
    """Dense eye feature tiling to overload saliency maps (spec section 4.4)."""

    name = "saliency_eye_attack"
    version = "1.0.0"
    category = "feature_disruption"
    priority = "P0"

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        self.validate_params(params)
        rng = np.random.default_rng(params.seed)
        coverage_target = float(params.params.get("coverage_target", 0.85))
        w, h = int(params.output_size[0]), int(params.output_size[1])
        sprites = [eye_sprite(32, 0.30), eye_sprite(40, 0.35), eye_sprite(48, 0.40)]

        canvas = _blank(params.output_size)
        # Deterministic stamp count derived from the coverage target (the spec's
        # while-loop with coverage recalculation is replaced by a closed-form
        # count to keep runtime bounded and deterministic).
        mean_sprite_area = sum(s.width * s.height for s in sprites) / len(sprites)
        count = int(math.ceil(coverage_target * w * h / mean_sprite_area))
        for _ in range(count):
            sprite = sprites[int(rng.integers(0, len(sprites)))]
            pos = (float(rng.uniform(0, w)), float(rng.uniform(0, h)))
            _paste_sprite(canvas, sprite, pos,
                          scale=float(rng.uniform(0.5, 1.5)),
                          rotation=float(rng.uniform(-15, 15)))
        return self._finalize(params, _arr(canvas))

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema({
            "coverage_target": {"type": "number", "minimum": 0.1, "maximum": 1.0},
        })


class AdversarialPatchGenerator(PatternGenerator):
    """Optimized adversarial patches at key anchor points (spec section 4.5).

    EVIDENCE-INTEGRITY NOTE: live patch optimization bridges to the existing
    RAC optimization pipeline (ruthless_pipeline.optimization). This generator
    produces the candidate GEOMETRY ONLY: a deterministic structured
    high-frequency noise patch. No target-model queries are made here and no
    efficacy is claimed.
    """

    name = "adversarial_patch"
    version = "1.0.0"
    category = "feature_disruption"
    priority = "P0"

    def __init__(self, mode: str = "single"):
        if mode not in ("single", "multi"):
            raise ValueError("mode must be 'single' or 'multi'")
        self.mode = mode

    def _generate_optimized_patch(self, size: int, rng: np.random.Generator) -> Image.Image:
        """Deterministic structured high-frequency noise patch (blocky 8x8
        macro-pixels upscaled with NEAREST). NOT a live optimization product."""
        blocks = 8
        arr = rng.integers(0, 256, size=(blocks, blocks, 3), dtype=np.uint8)
        img = Image.fromarray(arr, "RGB").resize((size, size), Image.NEAREST)
        return img

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        self.validate_params(params)
        if self.mode == "single":
            landmarks = require_landmarks(params, ["nose_tip"])
            anchors = [landmarks["nose_tip"]]
        else:
            landmarks = require_landmarks(
                params, ["left_eye", "right_eye", "nose_tip",
                         "left_cheek", "right_cheek"])
            anchors = [landmarks[k] for k in
                       ("left_eye", "right_eye", "nose_tip", "left_cheek", "right_cheek")]

        rng = np.random.default_rng(params.seed)
        canvas = _blank(params.output_size)
        for anchor in anchors:
            size = int(rng.integers(30, 60))
            patch = self._generate_optimized_patch(size, rng)
            offset = rng.integers(-10, 10, size=2)
            cx = int(round(float(anchor["position"][0]) + int(offset[0])))
            cy = int(round(float(anchor["position"][1]) + int(offset[1])))
            # Blend edges (deterministic linear alpha ramp) for physical
            # realizability.
            mask = Image.new("L", (size, size), 255)
            ramp = np.minimum(
                np.minimum(np.arange(size), np.arange(size)[::-1])[None, :],
                np.minimum(np.arange(size), np.arange(size)[::-1])[:, None])
            alpha = np.clip(ramp.astype(np.float64) / max(1.0, size / 6.0), 0, 1)
            mask = Image.fromarray((alpha * 255).astype(np.uint8), "L")
            canvas.paste(patch, (cx - size // 2, cy - size // 2), mask)
        return self._finalize(params, _arr(canvas))

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema({
            "mode": {"type": "string", "enum": ["single", "multi"]},
        })


class SwappedLandmarksGenerator(PatternGenerator):
    """Biologically impossible feature geometry (spec section 4.6).

    Feature "transplant" is realised with deterministic synthetic sprites
    (no base image exists at candidate-geometry stage).
    """

    name = "swapped_landmarks"
    version = "1.0.0"
    category = "feature_disruption"
    priority = "P0"

    _FEATURE_SPRITES = {"eye": eye_sprite, "mouth": mouth_sprite, "nose": nose_sprite}
    _SWAPS = [("mouth", "left_eye"), ("nose", "right_eye"), ("left_brow", "mouth")]

    def _sprite_for(self, feature_name: str) -> Image.Image:
        for key, factory in self._FEATURE_SPRITES.items():
            if key in feature_name:
                return factory(36)
        return eye_sprite(36)  # brows etc. map onto the eye-like sprite

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        self.validate_params(params)
        landmarks = require_landmarks(
            params, ["left_eye", "right_eye", "nose_tip", "mouth_center"])
        rng = np.random.default_rng(params.seed)
        canvas = _blank(params.output_size)

        # Ghost the original landmarks faintly, then stamp impossible swaps.
        for name, entry in sorted(landmarks.items()):
            pos = (float(entry["position"][0]), float(entry["position"][1]))
            _paste_sprite(canvas, self._sprite_for(name), pos, 0.6, 0.0, opacity=0.3)

        for src, dst in self._SWAPS:
            src_key = src if src in landmarks else (
                "mouth_center" if src == "mouth" else ("nose_tip" if src == "nose" else src))
            if src_key in landmarks and dst in landmarks:
                dst_pos = (float(landmarks[dst]["position"][0]),
                           float(landmarks[dst]["position"][1]))
                blend = float(rng.integers(5, 15))  # recorded via rotation jitter scale
                _paste_sprite(canvas, self._sprite_for(src_key), dst_pos,
                              scale=1.0 + blend / 50.0,
                              rotation=float(rng.uniform(-blend, blend)))
        return self._finalize(params, _arr(canvas))

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema()


class LandmarkNoiseGenerator(PatternGenerator):
    """Targeted noise around key facial landmarks (spec section 4.7)."""

    name = "landmark_noise"
    version = "1.0.0"
    category = "feature_disruption"
    priority = "P0"

    _IMPORTANCE = {
        "nose_tip": 1.0,
        "left_eye": 0.9,
        "right_eye": 0.9,
        "mouth_center": 0.8,
        "left_brow": 0.6,
        "right_brow": 0.6,
    }

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        self.validate_params(params)
        landmarks = require_landmarks(params, ["nose_tip"])
        rng = np.random.default_rng(params.seed)
        w, h = int(params.output_size[0]), int(params.output_size[1])
        canvas = np.full((h, w, 3), 128, dtype=np.float64)

        for name, entry in sorted(landmarks.items()):
            weight = self._IMPORTANCE.get(name, 0.5)
            radius = max(3, int(30 * weight))
            noise_type = ["gaussian", "uniform", "structured"][int(rng.integers(0, 3))]
            intensity = float(rng.uniform(0.3, 0.8)) * weight
            if noise_type == "gaussian":
                patch = rng.normal(0.0, 255 * intensity, (radius * 2, radius * 2, 1))
            elif noise_type == "uniform":
                patch = rng.uniform(-255 * intensity, 255 * intensity,
                                    (radius * 2, radius * 2, 1))
            else:  # structured: deterministic high-frequency checker-noise
                base = rng.integers(0, 2, (radius, radius, 1)) * 2 - 1
                patch = np.repeat(np.repeat(base, 2, axis=0), 2, axis=1) * 255 * intensity
            # Gaussian edge falloff mask.
            yy, xx = np.mgrid[0:radius * 2, 0:radius * 2]
            d2 = (yy - radius) ** 2 + (xx - radius) ** 2
            falloff = np.exp(-d2 / (2 * (radius / 1.5) ** 2))[:, :, None]
            cx, cy = int(round(float(entry["position"][0]))), int(round(float(entry["position"][1])))
            y0, y1 = cy - radius, cy + radius
            x0, x1 = cx - radius, cx + radius
            sy0, sy1 = max(0, -y0), min(2 * radius, h - y0)
            sx0, sx1 = max(0, -x0), min(2 * radius, w - x0)
            if sy1 <= sy0 or sx1 <= sx0:
                continue
            region = canvas[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1]
            delta = patch[sy0:sy1, sx0:sx1] * falloff[sy0:sy1, sx0:sx1]
            canvas[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] = region + delta

        return self._finalize(params, np.clip(canvas, 0, 255).astype(np.uint8))

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema({
            "intensity_min": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        })


class FeatureCollageGenerator(PatternGenerator):
    """External facial feature stamping (spec section 4.8).

    The "external feature library" is replaced by deterministic in-code
    synthetic sprites (no network, no asset files).
    """

    name = "feature_collage"
    version = "1.0.0"
    category = "feature_disruption"
    priority = "P0"

    def _feature_library(self) -> Dict[str, List[Image.Image]]:
        return {
            "eye": [eye_sprite(28, 0.30), eye_sprite(36, 0.40)],
            "mouth": [mouth_sprite(28), mouth_sprite(36)],
            "nose": [nose_sprite(28), nose_sprite(36)],
        }

    def generate(self, params: GeneratorParams) -> GeneratedPattern:
        self.validate_params(params)
        rng = np.random.default_rng(params.seed)
        w, h = int(params.output_size[0]), int(params.output_size[1])
        library = self._feature_library()
        canvas = _blank(params.output_size)

        stamp_count = int(rng.integers(20, 50))
        for _ in range(stamp_count):
            feature_type = ["eye", "mouth", "nose"][int(rng.integers(0, 3))]
            sprite = library[feature_type][int(rng.integers(0, len(library[feature_type])))]
            _paste_sprite(canvas, sprite,
                          (float(rng.uniform(0, w)), float(rng.uniform(0, h))),
                          scale=float(rng.uniform(0.3, 1.2)),
                          rotation=float(rng.uniform(-30, 30)),
                          opacity=float(rng.uniform(0.7, 1.0)))

        # Ensure overlap with real features: stamp one eye sprite on each eye
        # landmark when present.
        try:
            landmarks = require_landmarks(params, ["left_eye", "right_eye"])
            for key in ("left_eye", "right_eye"):
                pos = (float(landmarks[key]["position"][0]),
                       float(landmarks[key]["position"][1]))
                _paste_sprite(canvas, library["eye"][0], pos, 1.0, 0.0, opacity=0.9)
        except MissingLandmarksError:
            pass  # overlap enhancement only; core collage does not need landmarks

        return self._finalize(params, _arr(canvas))

    def get_param_schema(self) -> Dict[str, Any]:
        return base_param_schema({
            "stamp_count": {"type": "integer", "minimum": 20, "maximum": 50},
        })

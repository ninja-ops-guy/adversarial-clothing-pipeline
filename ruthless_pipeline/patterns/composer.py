"""Multi-generator composition (spec section 8).

DETERMINISM: compose() takes an explicit list of (generator, params) pairs —
each layer's generator receives its own fully-specified GeneratorParams
(including its own seed). This is the documented sub-seed policy: callers
derive per-layer seeds (e.g. sha256 of base seed + generator name) BEFORE
calling compose(); the composer itself performs no randomness.

The full composition_log records per-layer provenance_hash; the
composition_hash is sha256 of the canonical JSON log (tamper-evident).
Unknown blend modes fail closed with PatternCompositionError.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .base import (
    GeneratedPattern,
    GeneratorParams,
    PatternCompositionError,
    PatternGenerator,
)

BLEND_MODES = ("overlay", "multiply", "screen")


class ComposedPattern(GeneratedPattern):
    """GeneratedPattern plus composition provenance."""

    def __init__(self, *args: Any, composition_log: List[Dict[str, Any]],
                 composition_hash: str, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.composition_log = composition_log
        self.composition_hash = composition_hash

    def to_candidate(self) -> Dict[str, Any]:
        cand = super().to_candidate()
        cand["composition_log"] = self.composition_log
        cand["composition_hash"] = self.composition_hash
        return cand


class PatternComposer:
    """Compose multiple generators into complex patterns with provenance."""

    def __init__(self) -> None:
        self.composition_log: List[Dict[str, Any]] = []

    def compose(self,
                layers: Sequence[Tuple[PatternGenerator, GeneratorParams]],
                blend_modes: Sequence[str],
                weights: Sequence[float]) -> ComposedPattern:
        """Compose (generator, params) layers with blending.

        blend_modes[i] describes how layer i blends into the accumulated
        result; blend_modes[0] is validated but not applied (nothing to blend
        into). All sequences must have equal length.
        """
        if not layers:
            raise PatternCompositionError("compose() requires at least one layer")
        if not (len(layers) == len(blend_modes) == len(weights)):
            raise PatternCompositionError(
                "layers, blend_modes and weights must have equal length")
        for mode in blend_modes:
            if mode not in BLEND_MODES:
                raise PatternCompositionError(f"unknown blend mode: {mode!r}")

        self.composition_log = []
        accumulated: np.ndarray | None = None
        first_pattern: GeneratedPattern | None = None

        for (gen, params), blend, weight in zip(layers, blend_modes, weights):
            layer = gen.generate(params)
            self.composition_log.append({
                "generator": gen.name,
                "version": gen.version,
                "blend_mode": blend,
                "weight": float(weight),
                "provenance_hash": layer.provenance_hash,
            })
            img = layer.image.astype(np.float64) / 255.0
            if accumulated is None:
                accumulated = img
                first_pattern = layer
            else:
                accumulated = self._blend(accumulated, img, blend, float(weight))

        assert first_pattern is not None and accumulated is not None
        out = (np.clip(accumulated, 0.0, 1.0) * 255.0).round().astype(np.uint8)
        composition_hash = sha256_bytes(canonical_json(self.composition_log))
        return ComposedPattern(
            image=out,
            params=first_pattern.params,
            generator_version=first_pattern.generator_version,
            provenance_hash=first_pattern.provenance_hash,
            generator_name="composed:" + "+".join(
                entry["generator"] for entry in self.composition_log),
            composition_log=list(self.composition_log),
            composition_hash=composition_hash,
        )

    # -- blend math (numpy, float 0..1) --------------------------------------

    @staticmethod
    def _blend(base: np.ndarray, layer: np.ndarray, mode: str, weight: float) -> np.ndarray:
        if mode == "overlay":
            blended = np.where(base < 0.5, 2.0 * base * layer,
                               1.0 - 2.0 * (1.0 - base) * (1.0 - layer))
        elif mode == "multiply":
            blended = base * layer
        elif mode == "screen":
            blended = 1.0 - (1.0 - base) * (1.0 - layer)
        else:
            raise PatternCompositionError(f"unknown blend mode: {mode!r}")
        return base * (1.0 - weight) + blended * weight

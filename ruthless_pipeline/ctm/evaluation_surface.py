"""Machine-derived evaluation-surface semantics for CTM SPEC-12.

The CTM experiment manifest records an ``evaluation_audit`` block.  Free-text
``goodhart_guard`` remains useful narrative context, but it is not a reliable
machine contract.  This module derives the evaluation surfaces that are
knowable from structured audit fields so downstream analysis never has to
parse prose to determine threshold or temporal evaluation regimes.

This is additive and does not alter manifest canonical bytes or any frozen
schema.  Existing locked ``rac-ctm-experiment/1.1`` manifests remain byte
identical; callers can derive this view from ``manifest.evaluation_audit``.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

GOODHART_EXPOSURE_SCHEMA_VERSION = "rac-ctm-evaluation-surface/1.0"
THRESHOLD_REGIMES = frozenset({"fixed", "swept"})


@dataclass(frozen=True)
class EvaluationSurface:
    """Deterministic structured view of the evaluation choices in SPEC-12."""

    threshold_regime: str
    threshold_count: int
    temporal_regime: str
    frames_per_sample: int
    potential_goodhart_surfaces: tuple[str, ...]
    schema_version: str = GOODHART_EXPOSURE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "threshold_regime": self.threshold_regime,
            "threshold_count": self.threshold_count,
            "temporal_regime": self.temporal_regime,
            "frames_per_sample": self.frames_per_sample,
            "potential_goodhart_surfaces": list(self.potential_goodhart_surfaces),
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")


def derive_evaluation_surface(audit: dict[str, Any]) -> EvaluationSurface:
    """Derive machine-readable evaluation surfaces from a SPEC-12 audit.

    The derivation intentionally ignores ``goodhart_guard`` text.  It records
    only what can be known mechanically from structured fields:

    * fixed vs. swept threshold evaluation;
    * number of distinct thresholds;
    * single-frame vs. sequence evaluation.

    These are *potential* Goodhart surfaces, not claims that optimization
    actually exploited them.  Held-out exposure remains governed by the CTM
    provenance firewall and the pinned firewall attestation.
    """
    if not isinstance(audit, dict):
        raise ValueError("evaluation audit must be a dict")

    thresholds = audit.get("decision_thresholds")
    if not isinstance(thresholds, list) or not thresholds:
        raise ValueError("decision_thresholds must be a non-empty list")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        for value in thresholds
    ):
        raise ValueError("decision_thresholds must contain only finite numbers")

    regime = audit.get("threshold_regime")
    if regime not in THRESHOLD_REGIMES:
        raise ValueError(
            f"threshold_regime must be one of {sorted(THRESHOLD_REGIMES)}"
        )
    distinct_thresholds = len({float(value) for value in thresholds})
    if regime == "swept" and distinct_thresholds < 2:
        raise ValueError("swept threshold regime requires >=2 distinct thresholds")

    frames = audit.get("frames_per_sample")
    if isinstance(frames, bool) or not isinstance(frames, int) or frames < 1:
        raise ValueError("frames_per_sample must be an int >= 1")

    temporal_regime = "single_frame" if frames == 1 else "sequence"
    surfaces = [f"threshold_regime:{regime}", f"temporal_regime:{temporal_regime}"]
    if regime == "fixed":
        surfaces.append("fixed_threshold_selection_surface")
    else:
        surfaces.append("threshold_sweep_selection_surface")
    if frames == 1:
        surfaces.append("single_frame_selection_surface")

    return EvaluationSurface(
        threshold_regime=regime,
        threshold_count=distinct_thresholds,
        temporal_regime=temporal_regime,
        frames_per_sample=frames,
        potential_goodhart_surfaces=tuple(sorted(surfaces)),
    )


def derive_manifest_evaluation_surface(manifest: Any) -> EvaluationSurface:
    """Convenience adapter for ``CTMExperimentManifest`` without import cycles."""
    audit = getattr(manifest, "evaluation_audit", None)
    if audit is None:
        raise ValueError(
            "manifest has no evaluation_audit; structured evaluation surfaces "
            "require rac-ctm-experiment/1.1"
        )
    return derive_evaluation_surface(audit)

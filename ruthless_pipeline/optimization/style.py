"""Deterministic style-family scorer for the five Ruthless families.

Families: signal_shadow, machine_static, ghost_hound, broken_human,
error_garden. Motif/product anchors are read at runtime (read-only) from
design_profiles/ruthless_reference_v1.json.

The score is a DOCUMENTED PROXY over candidate feature dicts:
  score = w_motif * (motif overlap fraction)
        + w_product * (product in family products)
        + w_param * (mean Gaussian closeness of scale/density/distress to the
          family variant medians, sigma=25 on the 0-100 profile scale)

IMPORTANT: the style score is art-direction fit only. It is NOT RAC efficacy
evidence and must never be read as detector, transfer, or physical evidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .constraints import DEFAULT_PROFILE_PATH, load_style_profile
from .pareto import pareto_front

FAMILIES = (
    "signal_shadow",
    "machine_static",
    "ghost_hound",
    "broken_human",
    "error_garden",
)

_PARAM_KEYS = ("scale", "density", "distress")


@dataclass
class StyleFamilyScorer:
    """Proxy style scorer; profile loaded read-only at runtime."""

    profile_path: str | Path | None = None
    w_motif: float = 0.5
    w_product: float = 0.2
    w_param: float = 0.3
    param_sigma: float = 25.0

    def __post_init__(self) -> None:
        self.profile = load_style_profile(self.profile_path)
        total = self.w_motif + self.w_product + self.w_param
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("style scorer weights must sum to 1.0")

    def _family_spec(self, family: str) -> Mapping:
        families = self.profile.get("families", {})
        if family not in families:
            raise ValueError(f"unknown style family {family!r}")
        return families[family]

    def score(self, family: str, features: Mapping) -> float:
        """Deterministic proxy score in [0, 1] for ``features`` vs ``family``."""
        spec = self._family_spec(family)
        family_motifs = set(spec.get("motifs", []) or [])
        candidate_motifs = set(features.get("motifs", []) or [])
        motif = (
            len(candidate_motifs & family_motifs) / len(family_motifs) if family_motifs else 0.0
        )
        product = 1.0 if features.get("product") in (spec.get("products", []) or []) else 0.0

        variants = spec.get("variants", []) or []
        if variants:
            medians = {
                k: float(np.median([float(v.get(k, 0.0)) for v in variants]))
                for k in _PARAM_KEYS
            }
            closeness = []
            for k in _PARAM_KEYS:
                delta = float(features.get(k, medians[k])) - medians[k]
                closeness.append(math.exp(-(delta ** 2) / (2.0 * self.param_sigma ** 2)))
            param = float(np.mean(closeness))
        else:
            param = 0.0
        return float(self.w_motif * motif + self.w_product * product + self.w_param * param)

    def best_family(self, features: Mapping) -> tuple[str, float]:
        """Highest-scoring family; ties broken by FAMILIES order (deterministic)."""
        scores = [(self.score(f, features), f) for f in FAMILIES]
        return max(scores, key=lambda sf: (sf[0], -FAMILIES.index(sf[1])))[1], max(s for s, _ in scores)


@dataclass
class StyleOptimizationRecord:
    """Tracks style + objective trajectory for one optimization run.

    The style fields are art-direction metrics only — NOT RAC efficacy
    evidence.
    """

    candidate_id: str
    family: str
    initial_style_score: float
    final_style_score: float
    initial_detector_objective: float
    final_detector_objective: float
    initial_printability: float
    final_printability: float
    optimization_path: list[dict] = field(default_factory=list)
    # no certification from this infrastructure
    certification: None = None


def style_pareto_curve(
    records: Sequence[StyleOptimizationRecord],
) -> tuple[np.ndarray, np.ndarray]:
    """Style-vs-detector-objective Pareto front over optimization records.

    Points are (final_detector_objective [min], final_style_score [max]).
    Returns (front_indices, points) with shape (k,) and (n, 2). Uses
    pareto.py; no scalar collapse.
    """
    points = np.asarray(
        [[r.final_detector_objective, r.final_style_score] for r in records], dtype=float
    )
    if points.size == 0:
        return np.asarray([], dtype=int), points.reshape(0, 2)
    front = pareto_front(points, senses=("min", "max"))
    return front, points

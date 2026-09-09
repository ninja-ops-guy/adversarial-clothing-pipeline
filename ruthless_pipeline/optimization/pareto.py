"""Pareto utilities and rule-based candidate classification.

``dominates``/``pareto_front`` use the minimization convention (lower is
better) unless ``senses`` marks an objective as "max".

``classify`` assigns exactly one class per candidate by documented rules —
no single scalar collapse is used by default. Classification order of
priority (first matching rule wins):
  1. BALANCED                   — within ``balance_tol`` (relative to each
                                  metric's observed span) of the best on ALL
                                  four metrics
  2. DIGITAL_BEST               — best (min) detector_objective
  3. TRANSFER_BEST              — best (max) transfer score
  4. PHYSICAL_ROBUSTNESS_BEST   — best (max) physical_robustness score
  5. STYLE_BEST                 — best (max) style score
  6. fallback                   — class of the metric on which the candidate
                                  is relatively closest to the best (ties in
                                  the rule order above)

Ties for "best on a metric" are broken by input order (first wins), which is
deterministic. Every candidate receives exactly one class.

Candidates never receive scientific certification from this infrastructure;
every classification record carries ``certification = None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence

import numpy as np


class CandidateClass(Enum):
    DIGITAL_BEST = "DIGITAL_BEST"
    TRANSFER_BEST = "TRANSFER_BEST"
    PHYSICAL_ROBUSTNESS_BEST = "PHYSICAL_ROBUSTNESS_BEST"
    STYLE_BEST = "STYLE_BEST"
    BALANCED = "BALANCED"


def dominates(a: Sequence[float], b: Sequence[float], senses: Sequence[str] | None = None) -> bool:
    """True iff a Pareto-dominates b (>= on all, > on at least one).

    ``senses`` entries are "min" (default) or "max".
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise ValueError("objective vectors must have identical shapes")
    n = a.size
    senses = tuple(senses) if senses is not None else ("min",) * n
    better_or_equal = np.ones(n, dtype=bool)
    strictly_better = np.zeros(n, dtype=bool)
    for i, sense in enumerate(senses):
        if sense == "min":
            better_or_equal[i] = a[i] <= b[i]
            strictly_better[i] = a[i] < b[i]
        elif sense == "max":
            better_or_equal[i] = a[i] >= b[i]
            strictly_better[i] = a[i] > b[i]
        else:
            raise ValueError(f"unknown objective sense {sense!r}")
    return bool(np.all(better_or_equal) and np.any(strictly_better))


def pareto_front(
    points: np.ndarray,
    senses: Sequence[str] | None = None,
) -> np.ndarray:
    """Indices of the non-dominated points (rows of ``points``)."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2:
        raise ValueError("points must be a 2D array (n_points, n_objectives)")
    keep = []
    for i in range(pts.shape[0]):
        if not any(j != i and dominates(pts[j], pts[i], senses) for j in range(pts.shape[0])):
            keep.append(i)
    return np.asarray(keep, dtype=int)


@dataclass(frozen=True)
class ClassifiedCandidate:
    candidate_id: str
    classification: CandidateClass
    metrics: Mapping[str, float] = field(default_factory=dict)
    # no certification from this infrastructure
    certification: None = None


_METRIC_RULES = (
    ("detector_objective", "min", CandidateClass.DIGITAL_BEST),
    ("transfer", "max", CandidateClass.TRANSFER_BEST),
    ("physical_robustness", "max", CandidateClass.PHYSICAL_ROBUSTNESS_BEST),
    ("style", "max", CandidateClass.STYLE_BEST),
)


def classify(
    candidates: Sequence[Mapping],
    *,
    balance_tol: float = 0.1,
) -> list[ClassifiedCandidate]:
    """Rule-based classification of candidates with multi-metric dicts.

    Each candidate mapping must contain ``candidate_id`` and the four metric
    keys: detector_objective (min), transfer (max), physical_robustness
    (max), style (max). Missing metrics are treated as worst-case so such
    candidates can only be classified BALANCED-adjacent (they fall through).
    """
    if not candidates:
        return []
    n = len(candidates)
    values: dict[str, np.ndarray] = {}
    for key, sense, _ in _METRIC_RULES:
        worst = np.inf if sense == "min" else -np.inf
        values[key] = np.asarray(
            [float(c.get(key, worst)) for c in candidates], dtype=float
        )

    best = {
        key: (np.min(values[key]) if sense == "min" else np.max(values[key]))
        for key, sense, _ in _METRIC_RULES
    }

    def span(key: str) -> float:
        v = values[key]
        s = float(np.max(v) - np.min(v))
        return s if s > 0 else 1.0

    # Precompute the unique best-per-metric owner (ties: first in input order).
    owners: dict[str, int] = {}
    for key, sense, _ in _METRIC_RULES:
        idx = np.flatnonzero(values[key] == best[key])
        owners[key] = int(idx[0])

    results: list[ClassifiedCandidate] = []
    for i, cand in enumerate(candidates):
        cid = str(cand.get("candidate_id", f"candidate-{i}"))
        metrics = {key: float(values[key][i]) for key, _, _ in _METRIC_RULES}
        # Relative closeness to best per metric in [0, 1] (0 == best).
        closeness = {
            key: abs(values[key][i] - best[key]) / span(key) for key, _, _ in _METRIC_RULES
        }
        if all(c <= balance_tol for c in closeness.values()):
            label = CandidateClass.BALANCED
        else:
            label = None
            for key, _, cls in _METRIC_RULES:
                if owners[key] == i:
                    label = cls
                    break
            if label is None:
                # fallback: class of the metric the candidate is closest on
                nearest = min(
                    _METRIC_RULES, key=lambda rule: (closeness[rule[0]], _METRIC_RULES.index(rule))
                )
                label = nearest[2]
        results.append(
            ClassifiedCandidate(candidate_id=cid, classification=label, metrics=metrics)
        )
    return results

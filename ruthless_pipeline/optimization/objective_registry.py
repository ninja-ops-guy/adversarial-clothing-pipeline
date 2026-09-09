"""Composable objective registry.

J = detector_loss + lambda_print*printability + lambda_style*style
    + lambda_deformation*deformation + lambda_reg*regularization

Each term is a registered callable returning ``(value, metrics)`` so every
term is separately measurable per the frozen contract (log_separately = true).
Fail-closed: NaN/inf in any term raises NaNRefusalError.

Model-free infrastructure; no certification is produced here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Mapping

import numpy as np

from .schemas import DetectorAggregation, ObjectiveSpec

TermCallable = Callable[[np.ndarray], tuple[float, dict]]

TERM_NAMES = (
    "detector_loss",
    "printability_loss",
    "style_loss",
    "deformation_loss",
    "regularization",
)


class NaNRefusalError(RuntimeError):
    """Raised when any objective term evaluates to a non-finite value."""


@dataclass(frozen=True)
class ObjectiveEvaluation:
    """Per-term values plus the weighted total for one evaluation."""

    term_values: dict[str, float]
    weights: dict[str, float]
    total: float
    term_metrics: dict[str, dict] = field(default_factory=dict)


def aggregate_detector_scores(
    scores: Mapping[str, float] | np.ndarray | list[float],
    aggregation: DetectorAggregation,
    alpha: float | None = None,
) -> float:
    """Aggregate per-detector scores to a scalar detector loss.

    Convention matches the preregistered CVaR reference
    (ruthless_pipeline/certification/objectives.py): alpha -> 1 approaches
    the single worst detector and alpha -> 0 collapses to the mean;
    tail size k = max(1, ceil((1 - alpha) * n)). "Worst" here means the
    largest loss values.
    """
    values = np.asarray(
        list(scores.values()) if isinstance(scores, Mapping) else scores, dtype=float
    ).ravel()
    if values.size == 0:
        raise ValueError("at least one detector score is required")
    if not np.all(np.isfinite(values)):
        raise NaNRefusalError("non-finite detector score fed to aggregation")
    if aggregation is DetectorAggregation.MEAN:
        return float(np.mean(values))
    if aggregation is DetectorAggregation.WORST_CASE:
        return float(np.max(values))
    if aggregation is DetectorAggregation.CVAR:
        if alpha is None or not 0.0 < alpha <= 1.0:
            raise ValueError(f"CVaR requires alpha in (0, 1]; got {alpha!r}")
        k = max(1, math.ceil((1.0 - alpha) * values.size))
        worst = np.sort(values)[::-1][:k]
        return float(np.mean(worst))
    raise ValueError(f"unknown aggregation {aggregation!r}")


class Objective:
    """A composable objective bound to a validated ObjectiveSpec."""

    def __init__(self, spec: ObjectiveSpec):
        self.spec = spec
        self._terms: dict[str, TermCallable] = {}

    def register_term(self, name: str, fn: TermCallable) -> None:
        if name not in TERM_NAMES:
            raise ValueError(f"unknown objective term {name!r}; expected one of {TERM_NAMES}")
        if not callable(fn):
            raise TypeError("term must be callable")
        self._terms[name] = fn

    def evaluate(self, params: np.ndarray) -> ObjectiveEvaluation:
        weights = self.spec.weights()
        term_values: dict[str, float] = {}
        term_metrics: dict[str, dict] = {}
        total = 0.0
        for name, fn in self._terms.items():
            value, metrics = fn(np.asarray(params, dtype=float))
            value = float(value)
            if not math.isfinite(value):
                raise NaNRefusalError(
                    f"objective term {name!r} returned non-finite value {value!r}; refusing to continue"
                )
            term_values[name] = value
            term_metrics[name] = dict(metrics or {})
            total += weights.get(name, 0.0) * value
        if not math.isfinite(total):
            raise NaNRefusalError("weighted objective total is non-finite; refusing to continue")
        return ObjectiveEvaluation(
            term_values=term_values,
            weights={k: v for k, v in weights.items() if k in term_values},
            total=float(total),
            term_metrics=term_metrics,
        )

    def __call__(self, params: np.ndarray) -> float:
        return self.evaluate(params).total

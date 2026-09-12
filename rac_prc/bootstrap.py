from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from .calibration import calibration_metrics
from .prediction_freeze import FrozenPrediction

PredictionKey = tuple[str, str, str]


@dataclass(frozen=True)
class ConditionEstimate:
    key: PredictionKey
    predicted_delta: float
    physical_delta: float
    valid_trials: int
    invalid_trials: int
    direction_agrees: bool
    boundary_agrees: bool


def _group_physical(records: Iterable[dict[str, Any]]) -> dict[PredictionKey, list[dict[str, Any]]]:
    grouped: dict[PredictionKey, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = (str(record["condition_id"]), str(record["evaluator_id"]), str(record["endpoint_id"]))
        grouped[key].append(record)
    return dict(grouped)


def _direction_state(delta: float, margin: float) -> int:
    if abs(delta) <= margin:
        return 0
    return -1 if delta < 0 else 1


def _condition_estimate(
    pred: FrozenPrediction,
    records: list[dict[str, Any]],
    *,
    rng: np.random.Generator | None = None,
) -> ConditionEstimate | None:
    valid = [r for r in records if r.get("valid") is True]
    invalid_count = len(records) - len(valid)
    if not valid:
        return None
    if rng is not None:
        indices = rng.integers(0, len(valid), size=len(valid))
        valid = [valid[int(i)] for i in indices]
    control_rate = float(np.mean([bool(r["control_detected"]) for r in valid]))
    candidate_rate = float(np.mean([bool(r["candidate_detected"]) for r in valid]))
    physical_delta = candidate_rate - control_rate
    return ConditionEstimate(
        key=pred.key,
        predicted_delta=pred.predicted_delta,
        physical_delta=physical_delta,
        valid_trials=len(valid),
        invalid_trials=invalid_count,
        direction_agrees=_direction_state(pred.predicted_delta, pred.equivalence_margin)
        == _direction_state(physical_delta, pred.equivalence_margin),
        boundary_agrees=(pred.predicted_delta > pred.effect_boundary) == (physical_delta > pred.effect_boundary),
    )


def point_estimates(
    predictions: dict[PredictionKey, FrozenPrediction],
    physical_records: Iterable[dict[str, Any]],
) -> tuple[list[ConditionEstimate], list[PredictionKey]]:
    grouped = _group_physical(physical_records)
    estimates: list[ConditionEstimate] = []
    missing: list[PredictionKey] = []
    for key, pred in predictions.items():
        est = _condition_estimate(pred, grouped.get(key, []))
        if est is None:
            missing.append(key)
        else:
            estimates.append(est)
    return estimates, missing


def _metric_vector(estimates: list[ConditionEstimate]) -> dict[str, float | None]:
    predicted = [e.predicted_delta for e in estimates]
    observed = [e.physical_delta for e in estimates]
    base = calibration_metrics(predicted, observed)
    base["direction_agreement"] = float(np.mean([e.direction_agrees for e in estimates]))
    base["boundary_agreement"] = float(np.mean([e.boundary_agrees for e in estimates]))
    return base


def hierarchical_bootstrap(
    predictions: dict[PredictionKey, FrozenPrediction],
    physical_records: Iterable[dict[str, Any]],
    *,
    resamples: int = 5000,
    alpha: float = 0.05,
    seed: int = 20260911,
) -> dict[str, Any]:
    """Bootstrap conditions, then matched physical trials within each condition.

    Digital predictions remain fixed because they were prospectively frozen before
    physical unblinding. The physical trial, not video frame, is the resampling unit.
    """
    if resamples < 100:
        raise ValueError("hierarchical bootstrap requires at least 100 resamples")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    grouped = _group_physical(physical_records)
    eligible_keys = [key for key in predictions if any(r.get("valid") is True for r in grouped.get(key, []))]
    if not eligible_keys:
        raise ValueError("no prediction key has valid physical trials")

    point, missing = point_estimates(predictions, physical_records)
    point_metrics = _metric_vector(point)
    rng = np.random.default_rng(seed)
    metric_names = list(point_metrics)
    samples: dict[str, list[float]] = {name: [] for name in metric_names}

    for _ in range(resamples):
        outer = rng.integers(0, len(eligible_keys), size=len(eligible_keys))
        boot_estimates: list[ConditionEstimate] = []
        for idx in outer:
            key = eligible_keys[int(idx)]
            est = _condition_estimate(predictions[key], grouped[key], rng=rng)
            if est is not None:
                boot_estimates.append(est)
        metrics = _metric_vector(boot_estimates)
        for name, value in metrics.items():
            if value is not None and np.isfinite(value):
                samples[name].append(float(value))

    report_metrics: dict[str, dict[str, Any]] = {}
    low_q, high_q = alpha / 2, 1 - alpha / 2
    for name, point_value in point_metrics.items():
        vals = samples[name]
        report_metrics[name] = {
            "point_estimate": point_value,
            "confidence_interval": None
            if not vals
            else [float(np.quantile(vals, low_q)), float(np.quantile(vals, high_q))],
            "bootstrap_defined_fraction": len(vals) / resamples,
        }
    return {
        "schema": "rac.prospective-robustness-characterization.v1",
        "resampling_unit": "matched_physical_trial_nested_within_condition",
        "outer_unit": "prediction_condition",
        "bootstrap_seed": seed,
        "bootstrap_resamples": resamples,
        "conditions_evaluated": len(point),
        "conditions_missing_valid_physical_data": ["::".join(key) for key in missing],
        "valid_physical_trials": sum(e.valid_trials for e in point),
        "invalid_physical_trials": sum(e.invalid_trials for e in point),
        "condition_estimates": [
            {
                "key": "::".join(e.key),
                "predicted_delta": e.predicted_delta,
                "physical_delta": e.physical_delta,
                "valid_trials": e.valid_trials,
                "invalid_trials": e.invalid_trials,
                "direction_agrees": e.direction_agrees,
                "boundary_agrees": e.boundary_agrees,
            }
            for e in point
        ],
        "metrics": report_metrics,
    }

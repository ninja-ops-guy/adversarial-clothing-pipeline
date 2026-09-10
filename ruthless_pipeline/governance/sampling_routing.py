"""Empirical sampler routing for Governance Pass 6.

The selector consumes frozen coefficients calibrated outside this module. RAC does
not hard-code universal treewidth or variable-count cutoffs as scientific facts.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from .sampling import (
    BackendSelection,
    BackendTelemetry,
    SamplerLane,
    SamplingGovernanceError,
)


_ALLOWED_FEATURES = {
    "variable_count",
    "constraint_count",
    "independent_support_size",
    "graph_density",
    "treewidth_estimate",
    "historical_runtime_s",
    "historical_memory_mb",
    "max_constraint_arity",
    "propagation_rate",
}


@dataclass(frozen=True)
class EmpiricalLaneModel:
    """One frozen, externally calibrated cost model for a sampler lane."""

    lane: SamplerLane
    model_version: str
    intercept: float
    coefficients: Mapping[str, float]
    confidence: float
    training_observations: int

    def validate(self) -> None:
        if not isinstance(self.lane, SamplerLane):
            raise SamplingGovernanceError("empirical model lane must be a SamplerLane")
        if not isinstance(self.model_version, str) or not self.model_version.strip():
            raise SamplingGovernanceError("model_version is required")
        if not math.isfinite(self.intercept):
            raise SamplingGovernanceError("empirical model intercept must be finite")
        unknown = set(self.coefficients) - _ALLOWED_FEATURES
        if unknown:
            raise SamplingGovernanceError(
                f"unsupported empirical routing features: {sorted(unknown)}"
            )
        if any(not math.isfinite(value) for value in self.coefficients.values()):
            raise SamplingGovernanceError("empirical routing coefficients must be finite")
        if not 0.0 <= self.confidence <= 1.0:
            raise SamplingGovernanceError("empirical model confidence must be in [0,1]")
        if (
            not isinstance(self.training_observations, int)
            or isinstance(self.training_observations, bool)
            or self.training_observations <= 0
        ):
            raise SamplingGovernanceError(
                "training_observations must be a positive integer"
            )

    def predict_cost(self, telemetry: BackendTelemetry) -> float:
        self.validate()
        telemetry.validate()
        score = self.intercept
        for feature, coefficient in self.coefficients.items():
            raw = getattr(telemetry, feature)
            score += coefficient * (0.0 if raw is None else float(raw))
        return max(0.0, float(score))


def select_backend_empirical(
    telemetry: BackendTelemetry,
    *,
    selector_version: str,
    models: Sequence[EmpiricalLaneModel],
) -> BackendSelection:
    """Choose the lowest predicted-cost calibrated lane and record its evidence."""
    telemetry.validate()
    if not isinstance(selector_version, str) or not selector_version.strip():
        raise SamplingGovernanceError("selector_version is required")
    if len(models) < 2:
        raise SamplingGovernanceError(
            "empirical routing requires at least two calibrated lane models"
        )

    seen: set[SamplerLane] = set()
    scored: list[tuple[float, SamplerLane, EmpiricalLaneModel]] = []
    for model in models:
        model.validate()
        if model.lane in seen:
            raise SamplingGovernanceError(
                f"duplicate empirical model for lane {model.lane.value}"
            )
        seen.add(model.lane)
        scored.append((model.predict_cost(telemetry), model.lane, model))

    scored.sort(key=lambda item: (item[0], item[1].value))
    best_cost, selected, best_model = scored[0]
    _, alternate, _ = scored[1]
    return BackendSelection(
        selected=selected,
        alternate=alternate,
        predicted_cost=best_cost,
        confidence=best_model.confidence,
        selector_version=selector_version,
        selection_basis="frozen_empirical_cost_model",
        evidence_count=best_model.training_observations,
        lane_scores={lane.value: cost for cost, lane, _ in scored},
    )

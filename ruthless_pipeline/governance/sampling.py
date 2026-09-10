"""Sampling backends, selection, and representativeness diagnostics.

Governance Pass 6. This module is efficacy-blind and treats all scientific
thresholds as caller-supplied, versioned policy inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Mapping, Protocol, Sequence


class SamplingGovernanceError(RuntimeError):
    pass


class SamplerLane(str, Enum):
    EXACT = "exact_compiled"
    PROJECTED_HASHING = "projected_hashing"
    STRATIFIED = "stratified_constrained"
    DEGRADED = "degraded_proposal_rejection_importance"


class RepresentativenessState(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    LOW_REPRESENTATIVENESS = "LOW_REPRESENTATIVENESS"


@dataclass(frozen=True)
class SamplingRequest:
    target_distribution: str
    sample_count: int
    seed: int
    semantic_projection: tuple[str, ...]
    material_strata: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.target_distribution:
            raise SamplingGovernanceError("target_distribution is required")
        if self.sample_count <= 0:
            raise SamplingGovernanceError("sample_count must be positive")
        if self.seed < 0:
            raise SamplingGovernanceError("seed must be non-negative")
        if not self.semantic_projection:
            raise SamplingGovernanceError("semantic_projection is required")


@dataclass(frozen=True)
class SamplingResult:
    lane: SamplerLane
    samples: tuple[Mapping[str, Any], ...]
    target_distribution: str
    achieved_distribution: str
    weights: tuple[float, ...] = ()
    backend_version: str = "unknown"

    def validate(self, request: SamplingRequest) -> None:
        request.validate()
        if len(self.samples) != request.sample_count:
            raise SamplingGovernanceError("sample count does not match request")
        allowed = set(request.semantic_projection)
        for sample in self.samples:
            if not set(sample) <= allowed:
                raise SamplingGovernanceError("sample contains non-semantic variables")
        if self.weights and len(self.weights) != len(self.samples):
            raise SamplingGovernanceError("importance weights must align with samples")
        if any((not math.isfinite(w) or w < 0) for w in self.weights):
            raise SamplingGovernanceError("importance weights must be finite and non-negative")


class SamplerBackend(Protocol):
    lane: SamplerLane
    version: str

    def sample(self, request: SamplingRequest) -> SamplingResult:
        ...


@dataclass(frozen=True)
class BackendTelemetry:
    variable_count: int
    constraint_count: int
    independent_support_size: int
    graph_density: float | None = None
    treewidth_estimate: float | None = None
    historical_runtime_s: float | None = None
    historical_memory_mb: float | None = None


@dataclass(frozen=True)
class BackendSelection:
    selected: SamplerLane
    alternate: SamplerLane
    predicted_cost: float
    confidence: float
    selector_version: str


def select_backend(
    telemetry: BackendTelemetry,
    *,
    selector_version: str,
    exact_max_variables: int,
    hashing_max_support: int,
) -> BackendSelection:
    """Select a backend using explicitly versioned empirical policy thresholds."""
    if not selector_version:
        raise SamplingGovernanceError("selector_version is required")
    if exact_max_variables <= 0 or hashing_max_support <= 0:
        raise SamplingGovernanceError("selector thresholds must be positive")
    if telemetry.variable_count <= exact_max_variables:
        selected, alternate = SamplerLane.EXACT, SamplerLane.PROJECTED_HASHING
    elif telemetry.independent_support_size <= hashing_max_support:
        selected, alternate = SamplerLane.PROJECTED_HASHING, SamplerLane.STRATIFIED
    else:
        selected, alternate = SamplerLane.STRATIFIED, SamplerLane.DEGRADED
    cost = float(max(1, telemetry.variable_count) * max(1, telemetry.constraint_count))
    confidence = 1.0 if selected is SamplerLane.EXACT else 0.8
    return BackendSelection(selected, alternate, cost, confidence, selector_version)


@dataclass(frozen=True)
class DiagnosticPolicy:
    version: str
    minimum_material_strata_coverage: float
    maximum_duplicate_fraction: float
    minimum_effective_sample_size: float
    minimum_support_coverage: float

    def validate(self) -> None:
        if not self.version:
            raise SamplingGovernanceError("diagnostic policy version is required")
        for value in (
            self.minimum_material_strata_coverage,
            self.maximum_duplicate_fraction,
            self.minimum_support_coverage,
        ):
            if not (0.0 <= value <= 1.0):
                raise SamplingGovernanceError("fractional diagnostic thresholds must be in [0,1]")
        if self.minimum_effective_sample_size <= 0:
            raise SamplingGovernanceError("minimum ESS must be positive")


@dataclass(frozen=True)
class DiagnosticBundle:
    policy_version: str
    material_strata_coverage: float
    duplicate_fraction: float
    effective_sample_size: float
    support_coverage: float
    approximate_model_count: float | None
    approximate_model_count_interval: tuple[float, float] | None
    diagnostic_debt: float
    state: RepresentativenessState
    reasons: tuple[str, ...]


def _ess(weights: Sequence[float], n: int) -> float:
    if not weights:
        return float(n)
    total = sum(weights)
    denom = sum(w * w for w in weights)
    return 0.0 if denom == 0 else (total * total) / denom


def diagnose(
    request: SamplingRequest,
    result: SamplingResult,
    *,
    policy: DiagnosticPolicy,
    observed_material_strata: Sequence[str],
    support_coverage: float,
    approximate_model_count: float | None = None,
    approximate_model_count_interval: tuple[float, float] | None = None,
) -> DiagnosticBundle:
    request.validate(); result.validate(request); policy.validate()
    if not (0.0 <= support_coverage <= 1.0):
        raise SamplingGovernanceError("support_coverage must be in [0,1]")
    if approximate_model_count_interval is not None:
        lo, hi = approximate_model_count_interval
        if lo < 0 or hi < lo or not all(math.isfinite(x) for x in (lo, hi)):
            raise SamplingGovernanceError("invalid approximate model-count interval")
    unique = {tuple(sorted(sample.items())) for sample in result.samples}
    duplicate_fraction = 1.0 - len(unique) / len(result.samples)
    required = set(request.material_strata)
    strata_coverage = 1.0 if not required else len(required & set(observed_material_strata)) / len(required)
    ess = _ess(result.weights, len(result.samples))
    reasons: list[str] = []
    if strata_coverage < policy.minimum_material_strata_coverage: reasons.append("MATERIAL_STRATA_COVERAGE")
    if duplicate_fraction > policy.maximum_duplicate_fraction: reasons.append("DUPLICATE_CONCENTRATION")
    if ess < policy.minimum_effective_sample_size: reasons.append("LOW_ESS")
    if support_coverage < policy.minimum_support_coverage: reasons.append("LOW_SUPPORT_COVERAGE")
    if result.lane is SamplerLane.DEGRADED: reasons.append("DEGRADED_BACKEND")
    debt = float(len(reasons)) + (0.5 if approximate_model_count_interval is None and approximate_model_count is not None else 0.0)
    state = RepresentativenessState.ELIGIBLE if not reasons else RepresentativenessState.LOW_REPRESENTATIVENESS
    return DiagnosticBundle(policy.version, strata_coverage, duplicate_fraction, ess, support_coverage,
                            approximate_model_count, approximate_model_count_interval, debt, state, tuple(reasons))


def require_confirmatory_eligible(bundle: DiagnosticBundle) -> None:
    if bundle.state is not RepresentativenessState.ELIGIBLE:
        raise SamplingGovernanceError(
            "confirmatory inference denied: LOW_REPRESENTATIVENESS " + ",".join(bundle.reasons)
        )

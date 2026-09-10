"""Sampling contracts, exact calibration backend, manifests, and release diagnostics.

Governance Pass 6. This module is efficacy-blind. It samples explicitly defined
scientific populations and treats every routing/diagnostic threshold as a
caller-supplied, versioned policy input rather than a scientific constant.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
import random
from typing import Any, Callable, Mapping, Protocol, Sequence

from .ids import GovernanceId, IdKind


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


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SamplingGovernanceError(
            "sampling object must be canonically JSON serializable"
        ) from exc


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SamplingGovernanceError(f"{field_name} is required")


def _require_sha256(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise SamplingGovernanceError(f"{field_name} must be a lowercase sha256")


def _canonical_id(value: str, expected: IdKind, field_name: str) -> str:
    try:
        parsed = GovernanceId.parse(value)
    except Exception as exc:
        raise SamplingGovernanceError(
            f"{field_name} must be a valid governance identifier"
        ) from exc
    if parsed.kind is not expected or parsed.is_legacy_alias:
        raise SamplingGovernanceError(
            f"{field_name} must use canonical RAC-{expected.value} identity"
        )
    return parsed.canonical


def sample_key(sample: Mapping[str, Any]) -> str:
    return _canonical(dict(sample)).decode("utf-8")


def validate_projection_sample(
    sample: Mapping[str, Any],
    projection: Sequence[str],
    *,
    context: str,
) -> None:
    if not isinstance(sample, Mapping):
        raise SamplingGovernanceError(f"{context} must be a mapping")
    expected = set(projection)
    observed = set(sample)
    if observed != expected:
        extra = sorted(observed - expected)
        missing = sorted(expected - observed)
        if extra:
            raise SamplingGovernanceError(
                f"{context} contains non-semantic variables: {extra}"
            )
        raise SamplingGovernanceError(
            f"{context} is missing semantic variables: {missing}"
        )
    sample_key(sample)


@dataclass(frozen=True)
class PopulationIdentity:
    """Identity of the scientific population, independent of solver auxiliaries."""

    constraint_set_id: str
    constraint_version: str
    semantic_hash: str
    projection_version: str
    semantic_projection: tuple[str, ...]
    independent_support: tuple[str, ...] = ()

    def validate(self) -> None:
        _canonical_id(self.constraint_set_id, IdKind.CONSTRAINT, "constraint_set_id")
        _require_text(self.constraint_version, "constraint_version")
        _require_sha256(self.semantic_hash, "semantic_hash")
        _require_text(self.projection_version, "projection_version")
        if not self.semantic_projection:
            raise SamplingGovernanceError("scientific semantic_projection is required")
        if len(set(self.semantic_projection)) != len(self.semantic_projection):
            raise SamplingGovernanceError("semantic_projection variables must be unique")
        if len(set(self.independent_support)) != len(self.independent_support):
            raise SamplingGovernanceError("independent_support variables must be unique")
        if not set(self.independent_support) <= set(self.semantic_projection):
            raise SamplingGovernanceError(
                "independent_support must be a subset of the full semantic_projection"
            )

    @property
    def identity_hash(self) -> str:
        self.validate()
        return _sha256(
            {
                "constraint_set_id": self.constraint_set_id,
                "constraint_version": self.constraint_version,
                "semantic_hash": self.semantic_hash,
                "projection_version": self.projection_version,
                "semantic_projection": list(self.semantic_projection),
            }
        )


@dataclass(frozen=True)
class SamplingRequest:
    target_distribution: str
    sample_count: int
    seed: int
    semantic_projection: tuple[str, ...]
    material_strata: tuple[str, ...] = ()
    population: PopulationIdentity | None = None
    with_replacement: bool = False

    def validate(self) -> None:
        _require_text(self.target_distribution, "target_distribution")
        if (
            not isinstance(self.sample_count, int)
            or isinstance(self.sample_count, bool)
            or self.sample_count <= 0
        ):
            raise SamplingGovernanceError("sample_count must be positive")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise SamplingGovernanceError("seed must be non-negative")
        if not self.semantic_projection:
            raise SamplingGovernanceError("semantic_projection is required")
        if len(set(self.semantic_projection)) != len(self.semantic_projection):
            raise SamplingGovernanceError("semantic_projection variables must be unique")
        if len(set(self.material_strata)) != len(self.material_strata):
            raise SamplingGovernanceError("material_strata must be unique")
        if self.population is not None:
            self.population.validate()
            if self.semantic_projection != self.population.semantic_projection:
                raise SamplingGovernanceError(
                    "request projection must equal the full scientific population projection"
                )


@dataclass(frozen=True)
class SamplingResult:
    lane: SamplerLane
    samples: tuple[Mapping[str, Any], ...]
    target_distribution: str
    achieved_distribution: str
    weights: tuple[float, ...] = ()
    backend_version: str = "unknown"
    backend_id: str = "unknown"
    draw_probabilities: tuple[float, ...] = ()
    correlated_draws: bool = False
    effective_sample_size_estimate: float | None = None
    population_size: int | None = None

    def validate(self, request: SamplingRequest) -> None:
        request.validate()
        if not isinstance(self.lane, SamplerLane):
            raise SamplingGovernanceError("result lane must be a SamplerLane")
        if len(self.samples) != request.sample_count:
            raise SamplingGovernanceError("sample count does not match request")
        if self.target_distribution != request.target_distribution:
            raise SamplingGovernanceError("result target distribution differs from request")
        _require_text(self.achieved_distribution, "achieved_distribution")
        if self.achieved_distribution in {
            "first_sat_witness",
            "arbitrary_sat_witness",
            "solver_first_model",
        }:
            raise SamplingGovernanceError(
                "arbitrary/first SAT witnesses are not scientific samples"
            )
        _require_text(self.backend_version, "backend_version")
        _require_text(self.backend_id, "backend_id")
        for index, sample in enumerate(self.samples):
            validate_projection_sample(
                sample,
                request.semantic_projection,
                context=f"sample[{index}]",
            )
        if self.weights and len(self.weights) != len(self.samples):
            raise SamplingGovernanceError("importance weights must align with samples")
        if any((not math.isfinite(weight) or weight < 0) for weight in self.weights):
            raise SamplingGovernanceError(
                "importance weights must be finite and non-negative"
            )
        if self.weights and sum(self.weights) <= 0:
            raise SamplingGovernanceError("importance weights must have positive total mass")
        if self.draw_probabilities and len(self.draw_probabilities) != len(self.samples):
            raise SamplingGovernanceError("draw probabilities must align with samples")
        if any(
            (not math.isfinite(probability) or not 0.0 < probability <= 1.0)
            for probability in self.draw_probabilities
        ):
            raise SamplingGovernanceError(
                "draw probabilities must be finite and in (0,1]"
            )
        if self.effective_sample_size_estimate is not None:
            if (
                not math.isfinite(self.effective_sample_size_estimate)
                or self.effective_sample_size_estimate <= 0
                or self.effective_sample_size_estimate > len(self.samples)
            ):
                raise SamplingGovernanceError(
                    "effective_sample_size_estimate must be in (0, sample_count]"
                )
        if self.population_size is not None and self.population_size <= 0:
            raise SamplingGovernanceError("population_size must be positive when present")


class SamplerBackend(Protocol):
    lane: SamplerLane
    version: str

    def sample(self, request: SamplingRequest) -> SamplingResult:
        ...


class ExactProjectedPopulationBackend:
    """Exact uniform sampler over an explicitly enumerated projected population.

    It deliberately does not solve SAT. An upstream exact enumerator/compiler supplies
    distinct feasible projected assignments; this class is the trustworthy calibration
    oracle that samples those assignments uniformly and deterministically from the seed.
    """

    lane = SamplerLane.EXACT

    def __init__(
        self,
        population: Sequence[Mapping[str, Any]],
        *,
        backend_id: str = "builtin.exact_projected_population",
        version: str = "1.0",
    ) -> None:
        _require_text(backend_id, "backend_id")
        _require_text(version, "version")
        if not population:
            raise SamplingGovernanceError("exact projected population cannot be empty")
        self.backend_id = backend_id
        self.version = version
        self._population = tuple(dict(sample) for sample in population)

    def sample(self, request: SamplingRequest) -> SamplingResult:
        request.validate()
        if request.target_distribution != "uniform_over_feasible_projection":
            raise SamplingGovernanceError(
                "exact projected backend supports only uniform_over_feasible_projection"
            )
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, candidate in enumerate(self._population):
            validate_projection_sample(
                candidate,
                request.semantic_projection,
                context=f"exact_population[{index}]",
            )
            key = sample_key(candidate)
            if key in seen:
                raise SamplingGovernanceError(
                    "exact projected population must contain distinct projected assignments"
                )
            seen.add(key)
            normalized.append(dict(candidate))
        population_size = len(normalized)
        if not request.with_replacement and request.sample_count > population_size:
            raise SamplingGovernanceError(
                "sample_count exceeds exact population without replacement"
            )
        rng = random.Random(request.seed)
        if request.with_replacement:
            samples = tuple(
                dict(normalized[rng.randrange(population_size)])
                for _ in range(request.sample_count)
            )
            probabilities = tuple(
                1.0 / population_size for _ in range(request.sample_count)
            )
            achieved = "exact_uniform_iid_with_replacement"
        else:
            samples = tuple(
                dict(sample)
                for sample in rng.sample(normalized, request.sample_count)
            )
            probabilities = ()
            achieved = "exact_uniform_without_replacement"
        result = SamplingResult(
            lane=self.lane,
            samples=samples,
            target_distribution=request.target_distribution,
            achieved_distribution=achieved,
            backend_version=self.version,
            backend_id=self.backend_id,
            draw_probabilities=probabilities,
            population_size=population_size,
        )
        result.validate(request)
        return result


@dataclass(frozen=True)
class ExternalSamplerReply:
    """Raw output contract for a replaceable external sampler implementation."""

    samples: tuple[Mapping[str, Any], ...]
    achieved_distribution: str
    weights: tuple[float, ...] = ()
    draw_probabilities: tuple[float, ...] = ()
    correlated_draws: bool = False
    effective_sample_size_estimate: float | None = None
    population_size: int | None = None


class ProjectedSamplerAdapter:
    """Thin validated wrapper for external hashing/stratified/proposal samplers.

    The adapter owns no solver logic. It simply enforces the RAC scientific
    projection and provenance contract around a caller-supplied sampler callable.
    """

    def __init__(
        self,
        *,
        lane: SamplerLane,
        sampler: Callable[[SamplingRequest], ExternalSamplerReply],
        backend_id: str,
        version: str,
    ) -> None:
        if not isinstance(lane, SamplerLane):
            raise SamplingGovernanceError("lane must be a SamplerLane")
        if not callable(sampler):
            raise SamplingGovernanceError("sampler must be callable")
        _require_text(backend_id, "backend_id")
        _require_text(version, "version")
        self.lane = lane
        self._sampler = sampler
        self.backend_id = backend_id
        self.version = version

    def sample(self, request: SamplingRequest) -> SamplingResult:
        request.validate()
        reply = self._sampler(request)
        if not isinstance(reply, ExternalSamplerReply):
            raise SamplingGovernanceError(
                "external sampler must return ExternalSamplerReply"
            )
        result = SamplingResult(
            lane=self.lane,
            samples=tuple(dict(sample) for sample in reply.samples),
            target_distribution=request.target_distribution,
            achieved_distribution=reply.achieved_distribution,
            weights=tuple(reply.weights),
            backend_version=self.version,
            backend_id=self.backend_id,
            draw_probabilities=tuple(reply.draw_probabilities),
            correlated_draws=reply.correlated_draws,
            effective_sample_size_estimate=reply.effective_sample_size_estimate,
            population_size=reply.population_size,
        )
        result.validate(request)
        return result


@dataclass(frozen=True)
class BackendTelemetry:
    variable_count: int
    constraint_count: int
    independent_support_size: int
    graph_density: float | None = None
    treewidth_estimate: float | None = None
    historical_runtime_s: float | None = None
    historical_memory_mb: float | None = None
    max_constraint_arity: int | None = None
    propagation_rate: float | None = None

    def validate(self) -> None:
        for name in ("variable_count", "constraint_count", "independent_support_size"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise SamplingGovernanceError(f"{name} must be a non-negative integer")
        if self.independent_support_size > self.variable_count:
            raise SamplingGovernanceError(
                "independent_support_size cannot exceed variable_count"
            )
        if self.graph_density is not None and not 0.0 <= self.graph_density <= 1.0:
            raise SamplingGovernanceError("graph_density must be in [0,1]")
        for name in (
            "treewidth_estimate",
            "historical_runtime_s",
            "historical_memory_mb",
        ):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value < 0):
                raise SamplingGovernanceError(f"{name} must be finite and non-negative")
        if self.max_constraint_arity is not None and (
            not isinstance(self.max_constraint_arity, int)
            or isinstance(self.max_constraint_arity, bool)
            or self.max_constraint_arity < 0
        ):
            raise SamplingGovernanceError(
                "max_constraint_arity must be a non-negative integer"
            )
        if self.propagation_rate is not None and (
            not math.isfinite(self.propagation_rate)
            or not 0.0 <= self.propagation_rate <= 1.0
        ):
            raise SamplingGovernanceError("propagation_rate must be in [0,1]")


@dataclass(frozen=True)
class BackendSelection:
    selected: SamplerLane
    alternate: SamplerLane
    predicted_cost: float
    confidence: float
    selector_version: str
    selection_basis: str = "versioned_threshold_policy"
    evidence_count: int = 0
    lane_scores: Mapping[str, float] = field(default_factory=dict)


def select_backend(
    telemetry: BackendTelemetry,
    *,
    selector_version: str,
    exact_max_variables: int,
    hashing_max_support: int,
) -> BackendSelection:
    """Compatibility selector using explicitly supplied, versioned thresholds."""
    telemetry.validate()
    _require_text(selector_version, "selector_version")
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
    return BackendSelection(
        selected=selected,
        alternate=alternate,
        predicted_cost=cost,
        confidence=confidence,
        selector_version=selector_version,
    )


@dataclass(frozen=True)
class CalibrationMetrics:
    total_variation: float
    maximum_marginal_error: float
    maximum_pairwise_error: float

    def validate(self) -> None:
        for name in (
            "total_variation",
            "maximum_marginal_error",
            "maximum_pairwise_error",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise SamplingGovernanceError(f"{name} must be in [0,1]")


@dataclass(frozen=True)
class DiagnosticPolicy:
    version: str
    minimum_material_strata_coverage: float
    maximum_duplicate_fraction: float
    minimum_effective_sample_size: float
    minimum_support_coverage: float
    maximum_total_variation: float | None = None
    maximum_marginal_error: float | None = None
    maximum_pairwise_error: float | None = None
    maximum_seed_instability: float | None = None
    require_exact_calibration_when_available: bool = False
    require_external_sampler_test: bool = False

    def validate(self) -> None:
        _require_text(self.version, "diagnostic policy version")
        for name in (
            "minimum_material_strata_coverage",
            "maximum_duplicate_fraction",
            "minimum_support_coverage",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise SamplingGovernanceError(
                    "fractional diagnostic thresholds must be in [0,1]"
                )
        if self.minimum_effective_sample_size <= 0:
            raise SamplingGovernanceError("minimum ESS must be positive")
        for name in (
            "maximum_total_variation",
            "maximum_marginal_error",
            "maximum_pairwise_error",
            "maximum_seed_instability",
        ):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise SamplingGovernanceError(f"{name} must be in [0,1]")

    @property
    def threshold_hash(self) -> str:
        self.validate()
        return _sha256(asdict(self))


@dataclass(frozen=True)
class DiagnosticBundle:
    policy_version: str
    material_strata_coverage: float
    duplicate_fraction: float
    effective_sample_size: float | None
    support_coverage: float
    approximate_model_count: float | None
    approximate_model_count_interval: tuple[float, float] | None
    diagnostic_debt: float
    state: RepresentativenessState
    reasons: tuple[str, ...]
    exact_calibration_total_variation: float | None = None
    maximum_marginal_error: float | None = None
    maximum_pairwise_error: float | None = None
    repeated_seed_instability: float | None = None
    external_sampler_test_passed: bool | None = None
    constraint_sensitivity: Mapping[str, float] = field(default_factory=dict)
    constraint_sensitivity_intervals: Mapping[str, tuple[float, float]] = field(
        default_factory=dict
    )
    debt_components: tuple[tuple[str, float], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload


def _ess(weights: Sequence[float]) -> float:
    total = sum(weights)
    denominator = sum(weight * weight for weight in weights)
    return 0.0 if denominator == 0 else (total * total) / denominator


def _effective_sample_size(result: SamplingResult) -> float | None:
    if result.effective_sample_size_estimate is not None:
        return float(result.effective_sample_size_estimate)
    if result.weights:
        return _ess(result.weights)
    return None


def _violation_above(value: float, maximum: float) -> float:
    if value <= maximum:
        return 0.0
    return min(1.0, (value - maximum) / max(1e-12, 1.0 - maximum))


def _violation_below(value: float, minimum: float) -> float:
    if value >= minimum:
        return 0.0
    return min(1.0, (minimum - value) / max(1e-12, minimum))


def diagnose(
    request: SamplingRequest,
    result: SamplingResult,
    *,
    policy: DiagnosticPolicy,
    observed_material_strata: Sequence[str],
    support_coverage: float,
    approximate_model_count: float | None = None,
    approximate_model_count_interval: tuple[float, float] | None = None,
    calibration: CalibrationMetrics | None = None,
    repeated_seed_instability: float | None = None,
    external_sampler_test_passed: bool | None = None,
    constraint_sensitivity: Mapping[str, float] | None = None,
    constraint_sensitivity_intervals: Mapping[str, tuple[float, float]] | None = None,
) -> DiagnosticBundle:
    request.validate()
    result.validate(request)
    policy.validate()
    if not 0.0 <= support_coverage <= 1.0:
        raise SamplingGovernanceError("support_coverage must be in [0,1]")
    if approximate_model_count is not None and (
        not math.isfinite(approximate_model_count) or approximate_model_count < 0
    ):
        raise SamplingGovernanceError(
            "approximate_model_count must be finite and non-negative"
        )
    if approximate_model_count_interval is not None:
        lo, hi = approximate_model_count_interval
        if lo < 0 or hi < lo or not all(math.isfinite(value) for value in (lo, hi)):
            raise SamplingGovernanceError("invalid approximate model-count interval")
    if calibration is not None:
        calibration.validate()
    if repeated_seed_instability is not None and (
        not math.isfinite(repeated_seed_instability)
        or not 0.0 <= repeated_seed_instability <= 1.0
    ):
        raise SamplingGovernanceError("repeated_seed_instability must be in [0,1]")

    sensitivity = dict(constraint_sensitivity or {})
    for name, value in sensitivity.items():
        if not isinstance(name, str) or not name or not math.isfinite(value):
            raise SamplingGovernanceError("constraint sensitivity must be finite")
    sensitivity_intervals = dict(constraint_sensitivity_intervals or {})
    for name, interval in sensitivity_intervals.items():
        if name not in sensitivity:
            raise SamplingGovernanceError(
                "constraint sensitivity interval requires matching point estimate"
            )
        lo, hi = interval
        if not all(math.isfinite(value) for value in interval) or hi < lo:
            raise SamplingGovernanceError("invalid constraint sensitivity interval")

    unique = {sample_key(sample) for sample in result.samples}
    duplicate_fraction = 1.0 - len(unique) / len(result.samples)
    required = set(request.material_strata)
    strata_coverage = (
        1.0
        if not required
        else len(required & set(observed_material_strata)) / len(required)
    )
    ess = _effective_sample_size(result)
    reasons: list[str] = []
    debt_components: list[tuple[str, float]] = []

    def add_reason(code: str, debt: float) -> None:
        if code not in reasons:
            reasons.append(code)
        if debt > 0:
            debt_components.append((code, float(debt)))

    debt = _violation_below(
        strata_coverage,
        policy.minimum_material_strata_coverage,
    )
    if debt:
        add_reason("MATERIAL_STRATA_COVERAGE", debt)

    debt = _violation_above(
        duplicate_fraction,
        policy.maximum_duplicate_fraction,
    )
    if debt:
        add_reason("DUPLICATE_CONCENTRATION", debt)

    if ess is not None:
        if ess < policy.minimum_effective_sample_size:
            add_reason(
                "LOW_ESS",
                min(
                    1.0,
                    (policy.minimum_effective_sample_size - ess)
                    / policy.minimum_effective_sample_size,
                ),
            )
    elif result.correlated_draws:
        add_reason("MISSING_ESS_FOR_CORRELATED_SAMPLER", 1.0)

    debt = _violation_below(support_coverage, policy.minimum_support_coverage)
    if debt:
        add_reason("LOW_SUPPORT_COVERAGE", debt)

    if result.lane is SamplerLane.DEGRADED:
        add_reason("DEGRADED_BACKEND", 1.0)

    if policy.maximum_total_variation is not None:
        if calibration is None and policy.require_exact_calibration_when_available:
            add_reason("MISSING_EXACT_CALIBRATION", 1.0)
        elif calibration is not None:
            debt = _violation_above(
                calibration.total_variation,
                policy.maximum_total_variation,
            )
            if debt:
                add_reason("GLOBAL_DISTRIBUTION_MISMATCH", debt)

    if policy.maximum_marginal_error is not None and calibration is not None:
        debt = _violation_above(
            calibration.maximum_marginal_error,
            policy.maximum_marginal_error,
        )
        if debt:
            add_reason("MARGINAL_DISTRIBUTION_MISMATCH", debt)

    if policy.maximum_pairwise_error is not None and calibration is not None:
        debt = _violation_above(
            calibration.maximum_pairwise_error,
            policy.maximum_pairwise_error,
        )
        if debt:
            add_reason("PAIRWISE_DISTRIBUTION_MISMATCH", debt)

    if policy.maximum_seed_instability is not None:
        if repeated_seed_instability is None:
            add_reason("MISSING_REPEATED_SEED_DIAGNOSTIC", 1.0)
        else:
            debt = _violation_above(
                repeated_seed_instability,
                policy.maximum_seed_instability,
            )
            if debt:
                add_reason("REPEATED_SEED_INSTABILITY", debt)

    if policy.require_external_sampler_test and external_sampler_test_passed is not True:
        add_reason("EXTERNAL_SAMPLER_TEST_REQUIRED", 1.0)

    if approximate_model_count is not None and approximate_model_count_interval is None:
        debt_components.append(("MODEL_COUNT_UNCERTAINTY_MISSING", 0.5))

    diagnostic_debt = sum(value for _, value in debt_components)
    state = (
        RepresentativenessState.ELIGIBLE
        if not reasons
        else RepresentativenessState.LOW_REPRESENTATIVENESS
    )
    return DiagnosticBundle(
        policy_version=policy.version,
        material_strata_coverage=strata_coverage,
        duplicate_fraction=duplicate_fraction,
        effective_sample_size=ess,
        support_coverage=support_coverage,
        approximate_model_count=approximate_model_count,
        approximate_model_count_interval=approximate_model_count_interval,
        diagnostic_debt=diagnostic_debt,
        state=state,
        reasons=tuple(reasons),
        exact_calibration_total_variation=(
            calibration.total_variation if calibration is not None else None
        ),
        maximum_marginal_error=(
            calibration.maximum_marginal_error if calibration is not None else None
        ),
        maximum_pairwise_error=(
            calibration.maximum_pairwise_error if calibration is not None else None
        ),
        repeated_seed_instability=repeated_seed_instability,
        external_sampler_test_passed=external_sampler_test_passed,
        constraint_sensitivity=sensitivity,
        constraint_sensitivity_intervals=sensitivity_intervals,
        debt_components=tuple(debt_components),
    )


def require_confirmatory_eligible(bundle: DiagnosticBundle) -> None:
    if bundle.state is not RepresentativenessState.ELIGIBLE:
        raise SamplingGovernanceError(
            "confirmatory inference denied: LOW_REPRESENTATIVENESS "
            + ",".join(bundle.reasons)
        )


def build_sampling_manifest(
    *,
    sampling_id: str,
    experiment_id: str,
    request: SamplingRequest,
    result: SamplingResult,
    diagnostic_policy: DiagnosticPolicy,
    selector: BackendSelection | None = None,
) -> dict[str, Any]:
    """Build the adopted manifest with population, sampler, and threshold lineage."""
    request.validate()
    result.validate(request)
    diagnostic_policy.validate()
    if request.population is None:
        raise SamplingGovernanceError(
            "adopted Pass 6 sampling manifest requires immutable population identity"
        )
    population = request.population
    population.validate()
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "sampling_id": _canonical_id(
            sampling_id,
            IdKind.SAMPLING,
            "sampling_id",
        ),
        "experiment_id": _canonical_id(
            experiment_id,
            IdKind.EXPERIMENT,
            "experiment_id",
        ),
        "constraint_set_id": population.constraint_set_id,
        "constraint_version": population.constraint_version,
        "semantic_hash": population.semantic_hash,
        "scientific_projection_version": population.projection_version,
        "semantic_projection": list(population.semantic_projection),
        "independent_support": list(population.independent_support),
        "population_identity_hash": population.identity_hash,
        "seed": request.seed,
        "sample_count": request.sample_count,
        "target_distribution": request.target_distribution,
        "with_replacement": request.with_replacement,
        "sampler_lane": result.lane.value,
        "backend_id": result.backend_id,
        "sampler_version": result.backend_version,
        "achieved_distribution": result.achieved_distribution,
        "diagnostic_policy_version": diagnostic_policy.version,
        "diagnostic_threshold_hash": diagnostic_policy.threshold_hash,
    }
    if selector is not None:
        _require_text(selector.selector_version, "selector_version")
        payload.update(
            {
                "selector_version": selector.selector_version,
                "selector_basis": selector.selection_basis,
                "selector_confidence": selector.confidence,
                "selector_evidence_count": selector.evidence_count,
            }
        )
    return payload

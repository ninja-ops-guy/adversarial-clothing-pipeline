"""Constraint/support and sampling-policy overlap analysis (Governance Pass 4)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import math
import random
from statistics import NormalDist
from typing import Any, Callable, Iterable, Sequence

from .ids import GovernanceId, IdKind


class OverlapGovernanceError(RuntimeError):
    pass


def _require_kind(raw: str, kind: IdKind, field: str) -> None:
    parsed = GovernanceId.parse(raw)
    if parsed.kind is not kind:
        raise OverlapGovernanceError(f"{field} must be RAC-{kind.value}-...")


@dataclass(frozen=True)
class IntervalEstimate:
    estimate: float
    lower: float
    upper: float
    confidence: float
    method: str
    n: int | None = None
    hits: int | None = None

    def validate(self) -> None:
        if not (0.0 <= self.lower <= self.estimate <= self.upper <= 1.0):
            raise OverlapGovernanceError("probability interval must satisfy 0 <= lower <= estimate <= upper <= 1")
        if not (0.0 < self.confidence < 1.0):
            raise OverlapGovernanceError("confidence must be in (0, 1)")
        if self.n is not None and self.n <= 0:
            raise OverlapGovernanceError("n must be positive when present")
        if self.hits is not None and (self.n is None or not (0 <= self.hits <= self.n)):
            raise OverlapGovernanceError("hits must satisfy 0 <= hits <= n")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "estimate": self.estimate,
            "lower": self.lower,
            "upper": self.upper,
            "confidence": self.confidence,
            "method": self.method,
            "n": self.n,
            "hits": self.hits,
        }


def binomial_wilson(hits: int, n: int, confidence: float = 0.95) -> IntervalEstimate:
    if isinstance(hits, bool) or isinstance(n, bool) or not isinstance(hits, int) or not isinstance(n, int):
        raise OverlapGovernanceError("hits and n must be integers")
    if n <= 0 or not (0 <= hits <= n):
        raise OverlapGovernanceError("binomial counts must satisfy n > 0 and 0 <= hits <= n")
    if not (0.0 < confidence < 1.0):
        raise OverlapGovernanceError("confidence must be in (0, 1)")
    p = hits / n
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) / n) + z2 / (4.0 * n * n)) / denom
    result = IntervalEstimate(
        estimate=p,
        lower=max(0.0, center - half),
        upper=min(1.0, center + half),
        confidence=confidence,
        method="wilson_binomial",
        n=n,
        hits=hits,
    )
    result.validate()
    return result


@dataclass(frozen=True)
class CountEstimate:
    """Exact or approximate projected model count with explicit uncertainty."""

    estimate: float
    lower: float
    upper: float
    method: str

    def validate(self) -> None:
        if self.lower < 0 or self.estimate < 0 or self.upper < 0:
            raise OverlapGovernanceError("model counts cannot be negative")
        if not (self.lower <= self.estimate <= self.upper):
            raise OverlapGovernanceError("count interval must contain estimate")
        if not self.method:
            raise OverlapGovernanceError("count method is required")


def support_overlap_from_counts(
    old: CountEstimate,
    new: CountEstimate,
    intersection: CountEstimate,
    *,
    confidence: float = 0.95,
) -> IntervalEstimate:
    """Compute |F_old ∩ F_new| / min(|F_old|, |F_new|) with conservative bounds."""

    old.validate()
    new.validate()
    intersection.validate()
    denominator = min(old.estimate, new.estimate)
    if denominator <= 0:
        raise OverlapGovernanceError("support overlap is undefined when either feasible set is empty")
    point = min(1.0, intersection.estimate / denominator)
    denominator_upper = min(old.upper, new.upper)
    lower = 0.0 if denominator_upper <= 0 else min(1.0, intersection.lower / denominator_upper)
    denominator_lower = min(old.lower, new.lower)
    upper = 1.0 if denominator_lower <= 0 else min(1.0, intersection.upper / denominator_lower)
    lower = min(lower, point)
    upper = max(upper, point)
    result = IntervalEstimate(
        estimate=point,
        lower=lower,
        upper=upper,
        confidence=confidence,
        method=f"projected_count:{old.method}|{new.method}|{intersection.method}",
    )
    result.validate()
    return result


@dataclass(frozen=True)
class BidirectionalOverlapEstimate:
    old_to_new: IntervalEstimate
    new_to_old: IntervalEstimate
    support_overlap: IntervalEstimate

    def to_dict(self) -> dict[str, object]:
        return {
            "old_to_new": self.old_to_new.to_dict(),
            "new_to_old": self.new_to_old.to_dict(),
            "support_overlap": self.support_overlap.to_dict(),
        }


def estimate_bidirectional_overlap(
    old_samples: Sequence[Any],
    new_samples: Sequence[Any],
    *,
    old_feasible: Callable[[Any], bool],
    new_feasible: Callable[[Any], bool],
    confidence: float = 0.95,
) -> BidirectionalOverlapEstimate:
    """Estimate common support from both feasible populations with confidence intervals."""

    if not old_samples or not new_samples:
        raise OverlapGovernanceError("bidirectional overlap requires non-empty samples from both regimes")
    if any(not old_feasible(item) for item in old_samples):
        raise OverlapGovernanceError("old_samples contain specimens infeasible under the old constraint set")
    if any(not new_feasible(item) for item in new_samples):
        raise OverlapGovernanceError("new_samples contain specimens infeasible under the new constraint set")

    old_hits = sum(1 for item in old_samples if new_feasible(item))
    new_hits = sum(1 for item in new_samples if old_feasible(item))
    old_to_new = binomial_wilson(old_hits, len(old_samples), confidence)
    new_to_old = binomial_wilson(new_hits, len(new_samples), confidence)
    point = max(old_to_new.estimate, new_to_old.estimate)
    lower = max(old_to_new.lower, new_to_old.lower)
    upper = max(old_to_new.upper, new_to_old.upper)
    support = IntervalEstimate(
        estimate=point,
        lower=min(lower, point),
        upper=max(upper, point),
        confidence=confidence,
        method="bidirectional_monte_carlo_uniform_feasible_assumption",
        n=len(old_samples) + len(new_samples),
        hits=old_hits + new_hits,
    )
    support.validate()
    return BidirectionalOverlapEstimate(old_to_new, new_to_old, support)


def _policy_overlap(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    if not labels_a or not labels_b:
        raise OverlapGovernanceError("policy overlap requires non-empty samples from both policies")
    ca, cb = Counter(labels_a), Counter(labels_b)
    na, nb = len(labels_a), len(labels_b)
    strata = set(ca) | set(cb)
    return sum(min(ca[s] / na, cb[s] / nb) for s in strata)


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise OverlapGovernanceError("cannot take percentile of empty sequence")
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    fraction = pos - lo
    return sorted_values[lo] * (1.0 - fraction) + sorted_values[hi] * fraction


def estimate_policy_overlap(
    old_strata: Sequence[str],
    new_strata: Sequence[str],
    *,
    confidence: float = 0.95,
    bootstrap_seed: int,
    bootstrap_replicates: int = 400,
) -> IntervalEstimate:
    """Estimate 1-TV overlap of old/new stratum-mass distributions."""

    if not (0 <= bootstrap_seed < 2**32):
        raise OverlapGovernanceError("bootstrap_seed must be in [0, 2^32)")
    if bootstrap_replicates < 50:
        raise OverlapGovernanceError("bootstrap_replicates must be >= 50")
    if not (0.0 < confidence < 1.0):
        raise OverlapGovernanceError("confidence must be in (0, 1)")
    point = _policy_overlap(old_strata, new_strata)
    rng = random.Random(bootstrap_seed)
    reps: list[float] = []
    for _ in range(bootstrap_replicates):
        a = [old_strata[rng.randrange(len(old_strata))] for _ in old_strata]
        b = [new_strata[rng.randrange(len(new_strata))] for _ in new_strata]
        reps.append(_policy_overlap(a, b))
    reps.sort()
    alpha = 1.0 - confidence
    lower = _percentile(reps, alpha / 2.0)
    upper = _percentile(reps, 1.0 - alpha / 2.0)
    result = IntervalEstimate(
        estimate=point,
        lower=min(lower, point),
        upper=max(upper, point),
        confidence=confidence,
        method=f"empirical_stratum_overlap_bootstrap_{bootstrap_replicates}",
        n=len(old_strata) + len(new_strata),
    )
    result.validate()
    return result


@dataclass(frozen=True)
class MaterialityPolicy:
    mass_threshold: float
    hypothesis_named_strata: frozenset[str] = frozenset()
    mandatory_strata: frozenset[str] = frozenset()

    def validate(self) -> None:
        if not (0.0 <= self.mass_threshold <= 1.0):
            raise OverlapGovernanceError("material mass_threshold must be in [0, 1]")

    def material_strata(self, old_labels: Sequence[str], new_labels: Sequence[str]) -> frozenset[str]:
        self.validate()
        if not old_labels or not new_labels:
            raise OverlapGovernanceError("materiality estimation requires both old and new samples")
        old_counts, new_counts = Counter(old_labels), Counter(new_labels)
        strata = set(old_counts) | set(new_counts) | set(self.hypothesis_named_strata) | set(self.mandatory_strata)
        material: set[str] = set()
        for stratum in strata:
            old_mass = old_counts[stratum] / len(old_labels)
            new_mass = new_counts[stratum] / len(new_labels)
            if (
                old_mass >= self.mass_threshold
                or new_mass >= self.mass_threshold
                or stratum in self.hypothesis_named_strata
                or stratum in self.mandatory_strata
            ):
                material.add(stratum)
        return frozenset(material)


@dataclass(frozen=True)
class StratumOverlap:
    stratum: str
    old_to_new: IntervalEstimate | None
    new_to_old: IntervalEstimate | None
    support_overlap: IntervalEstimate | None

    @property
    def complete(self) -> bool:
        return self.old_to_new is not None and self.new_to_old is not None and self.support_overlap is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "stratum": self.stratum,
            "complete": self.complete,
            "old_to_new": None if self.old_to_new is None else self.old_to_new.to_dict(),
            "new_to_old": None if self.new_to_old is None else self.new_to_old.to_dict(),
            "support_overlap": None if self.support_overlap is None else self.support_overlap.to_dict(),
        }


def estimate_stratified_support(
    old_samples: Sequence[Any],
    new_samples: Sequence[Any],
    *,
    old_feasible: Callable[[Any], bool],
    new_feasible: Callable[[Any], bool],
    stratum_of: Callable[[Any], str],
    material_strata: Iterable[str],
    confidence: float = 0.95,
) -> tuple[StratumOverlap, ...]:
    material = tuple(sorted(set(material_strata)))
    rows: list[StratumOverlap] = []
    for stratum in material:
        old_s = [item for item in old_samples if stratum_of(item) == stratum]
        new_s = [item for item in new_samples if stratum_of(item) == stratum]
        if not old_s or not new_s:
            rows.append(StratumOverlap(stratum, None, None, None))
            continue
        estimate = estimate_bidirectional_overlap(
            old_s,
            new_s,
            old_feasible=old_feasible,
            new_feasible=new_feasible,
            confidence=confidence,
        )
        rows.append(StratumOverlap(stratum, estimate.old_to_new, estimate.new_to_old, estimate.support_overlap))
    return tuple(rows)


@dataclass(frozen=True)
class OverlapAnalysis:
    overlap_id: str
    old_constraint_id: str
    new_constraint_id: str
    material_strata: tuple[str, ...]
    support_by_stratum: tuple[StratumOverlap, ...]
    policy_overlap: IntervalEstimate
    method: str
    assumptions: tuple[str, ...] = ()

    def validate(self) -> None:
        _require_kind(self.overlap_id, IdKind.OVERLAP, "overlap_id")
        _require_kind(self.old_constraint_id, IdKind.CONSTRAINT, "old_constraint_id")
        _require_kind(self.new_constraint_id, IdKind.CONSTRAINT, "new_constraint_id")
        if self.old_constraint_id == self.new_constraint_id:
            raise OverlapGovernanceError("overlap analysis requires distinct constraint ids")
        if set(self.material_strata) != {row.stratum for row in self.support_by_stratum}:
            raise OverlapGovernanceError("support rows must exactly cover material_strata")
        self.policy_overlap.validate()
        if not self.method:
            raise OverlapGovernanceError("overlap method is required")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": "1.0",
            "overlap_id": self.overlap_id,
            "left_constraint_id": self.old_constraint_id,
            "right_constraint_id": self.new_constraint_id,
            "method": self.method,
            "material_strata": list(self.material_strata),
            "support_by_stratum": [row.to_dict() for row in self.support_by_stratum],
            "policy_overlap": self.policy_overlap.to_dict(),
            "assumptions": list(self.assumptions),
        }


class RegimeDecision(str, Enum):
    COMPARABLE_WITH_BRIDGE = "COMPARABLE_WITH_BRIDGE"
    REGIME_RESET = "REGIME_RESET"


@dataclass(frozen=True)
class RegimeDecisionPolicy:
    min_support_lower_bound: float
    min_policy_overlap_lower_bound: float

    def validate(self) -> None:
        for field in ("min_support_lower_bound", "min_policy_overlap_lower_bound"):
            value = getattr(self, field)
            if not (0.0 <= value <= 1.0):
                raise OverlapGovernanceError(f"{field} must be in [0, 1]")


def require_overlap_analysis_for_migration(
    old_constraint_id: str,
    new_constraint_id: str,
    analysis: OverlapAnalysis | None,
) -> OverlapAnalysis:
    """Law 4: migration cannot be treated as comparable without overlap analysis."""

    _require_kind(old_constraint_id, IdKind.CONSTRAINT, "old_constraint_id")
    _require_kind(new_constraint_id, IdKind.CONSTRAINT, "new_constraint_id")
    if old_constraint_id == new_constraint_id:
        raise OverlapGovernanceError("migration requires distinct old/new constraint ids")
    if analysis is None:
        raise OverlapGovernanceError("Law 4: constraint migration requires overlap analysis")
    analysis.validate()
    if analysis.old_constraint_id != old_constraint_id or analysis.new_constraint_id != new_constraint_id:
        raise OverlapGovernanceError("overlap analysis does not bind the migration pair")
    return analysis


def decide_regime(analysis: OverlapAnalysis, policy: RegimeDecisionPolicy) -> RegimeDecision:
    analysis.validate()
    policy.validate()
    for row in analysis.support_by_stratum:
        if not row.complete:
            return RegimeDecision.REGIME_RESET
        assert row.support_overlap is not None
        if row.support_overlap.lower < policy.min_support_lower_bound:
            return RegimeDecision.REGIME_RESET
    if analysis.policy_overlap.lower < policy.min_policy_overlap_lower_bound:
        return RegimeDecision.REGIME_RESET
    return RegimeDecision.COMPARABLE_WITH_BRIDGE

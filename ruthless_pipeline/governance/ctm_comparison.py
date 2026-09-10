"""Governance gate for CTM cross-cohort comparisons.

This module does not compute CTM effects or genome distances.  It decides
whether two already-sealed cohorts may enter a common comparison path when
constraint sets or evaluation pipelines differ.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .bridge_overlap import RegimeDecision


class CTMComparisonGovernanceError(RuntimeError):
    pass


class PipelineMigrationClass(str, Enum):
    UNCHANGED = "UNCHANGED"
    EQUIVALENT = "EQUIVALENT"
    BRIDGED = "BRIDGED"
    INCOMPARABLE = "INCOMPARABLE"


class ComparisonMode(str, Enum):
    DIRECT = "DIRECT"
    COMMON_SUPPORT = "COMMON_SUPPORT"
    BRIDGED = "BRIDGED"
    SEPARATE_REGIME = "SEPARATE_REGIME"


@dataclass(frozen=True)
class CohortComparisonContext:
    cohort_id: str
    seal_id: str
    constraint_set_id: str
    pipeline_id: str
    pipeline_version: str
    state: str = "SEALED"

    def validate(self) -> None:
        for name, value in (
            ("cohort_id", self.cohort_id),
            ("seal_id", self.seal_id),
            ("constraint_set_id", self.constraint_set_id),
            ("pipeline_id", self.pipeline_id),
            ("pipeline_version", self.pipeline_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise CTMComparisonGovernanceError(f"{name} is required")
        if self.state != "SEALED":
            raise CTMComparisonGovernanceError(
                f"CTM comparison requires sealed cohorts, got {self.state!r}"
            )


@dataclass(frozen=True)
class CTMComparisonDecision:
    eligible: bool
    mode: ComparisonMode
    constraint_changed: bool
    pipeline_changed: bool
    regime_decision: RegimeDecision
    overlap_analysis_id: str | None
    bridge_cohort_id: str | None
    pipeline_migration: PipelineMigrationClass
    reasons: tuple[str, ...]


def assess_ctm_comparison(
    left: CohortComparisonContext,
    right: CohortComparisonContext,
    *,
    regime_decision: RegimeDecision = RegimeDecision.COMPARABLE,
    overlap_analysis_id: str | None = None,
    bridge_cohort_id: str | None = None,
    pipeline_migration: PipelineMigrationClass | str | None = None,
) -> CTMComparisonDecision:
    """Classify whether the default CTM comparison path is scientifically legal.

    Constraint changes require an explicit overlap analysis.  Pipeline changes
    require an explicit migration classification.  A regime reset never enters
    the pooled/default path; it remains analyzable only as a separate regime.
    """
    left.validate()
    right.validate()
    try:
        regime = RegimeDecision(regime_decision)
    except ValueError as exc:
        raise CTMComparisonGovernanceError("invalid regime decision") from exc

    constraint_changed = left.constraint_set_id != right.constraint_set_id
    pipeline_changed = (
        left.pipeline_id != right.pipeline_id
        or left.pipeline_version != right.pipeline_version
    )

    reasons: list[str] = []
    if constraint_changed and not overlap_analysis_id:
        raise CTMComparisonGovernanceError(
            "constraint migration requires explicit overlap analysis"
        )

    if pipeline_changed:
        if pipeline_migration is None:
            raise CTMComparisonGovernanceError(
                "pipeline migration requires explicit classification"
            )
        try:
            pipeline_class = PipelineMigrationClass(pipeline_migration)
        except ValueError as exc:
            raise CTMComparisonGovernanceError(
                "invalid pipeline migration classification"
            ) from exc
        if pipeline_class is PipelineMigrationClass.UNCHANGED:
            raise CTMComparisonGovernanceError(
                "changed pipeline cannot be classified UNCHANGED"
            )
    else:
        if pipeline_migration is None:
            pipeline_class = PipelineMigrationClass.UNCHANGED
        else:
            pipeline_class = PipelineMigrationClass(pipeline_migration)
            if pipeline_class is not PipelineMigrationClass.UNCHANGED:
                raise CTMComparisonGovernanceError(
                    "unchanged pipeline must use UNCHANGED migration class"
                )

    if regime is RegimeDecision.REGIME_RESET:
        reasons.append("constraint/support migration declared a new regime")
        if pipeline_class is PipelineMigrationClass.INCOMPARABLE:
            reasons.append("pipeline migration is incomparable")
        return CTMComparisonDecision(
            eligible=False,
            mode=ComparisonMode.SEPARATE_REGIME,
            constraint_changed=constraint_changed,
            pipeline_changed=pipeline_changed,
            regime_decision=regime,
            overlap_analysis_id=overlap_analysis_id,
            bridge_cohort_id=bridge_cohort_id,
            pipeline_migration=pipeline_class,
            reasons=tuple(reasons),
        )

    if pipeline_class is PipelineMigrationClass.INCOMPARABLE:
        return CTMComparisonDecision(
            eligible=False,
            mode=ComparisonMode.SEPARATE_REGIME,
            constraint_changed=constraint_changed,
            pipeline_changed=pipeline_changed,
            regime_decision=regime,
            overlap_analysis_id=overlap_analysis_id,
            bridge_cohort_id=bridge_cohort_id,
            pipeline_migration=pipeline_class,
            reasons=("pipeline migration is incomparable",),
        )

    bridge_required = (
        regime is RegimeDecision.BRIDGE_REQUIRED
        or pipeline_class is PipelineMigrationClass.BRIDGED
    )
    if bridge_required and not bridge_cohort_id:
        raise CTMComparisonGovernanceError(
            "bridge-required comparison requires bridge_cohort_id"
        )

    if bridge_required:
        mode = ComparisonMode.BRIDGED
    elif constraint_changed:
        mode = ComparisonMode.COMMON_SUPPORT
    else:
        mode = ComparisonMode.DIRECT

    if constraint_changed:
        reasons.append("constraint migration covered by overlap analysis")
    if pipeline_class is PipelineMigrationClass.EQUIVALENT:
        reasons.append("pipeline migration explicitly classified equivalent")
    if bridge_required:
        reasons.append("comparison restricted to an explicit bridge path")

    return CTMComparisonDecision(
        eligible=True,
        mode=mode,
        constraint_changed=constraint_changed,
        pipeline_changed=pipeline_changed,
        regime_decision=regime,
        overlap_analysis_id=overlap_analysis_id,
        bridge_cohort_id=bridge_cohort_id,
        pipeline_migration=pipeline_class,
        reasons=tuple(reasons),
    )


def require_ctm_comparison_eligible(
    decision: CTMComparisonDecision,
) -> CTMComparisonDecision:
    if not decision.eligible:
        reason = "; ".join(decision.reasons) or "comparison is not eligible"
        raise CTMComparisonGovernanceError(
            f"default CTM comparison denied: {reason}"
        )
    return decision

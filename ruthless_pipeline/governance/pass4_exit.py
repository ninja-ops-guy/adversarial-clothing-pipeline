"""Integrated Governance Pass 4 exit fixture orchestration.

This module binds the already-adopted sentinel, constraint-bridge, overlap, and
ledger primitives into one reproducible migration flow.  It is deliberately
scientific-boundary preserving: it performs comparability governance only and
never reads efficacy outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from .bridge import ConstraintBridgeCohort, validate_common_support
from .ids import GovernanceId, IdKind
from .ledger import GovernanceEventType, GovernanceLedger
from .overlap import (
    BidirectionalOverlapEstimate,
    CountEstimate,
    DetailedRegimeDecision,
    IntervalEstimate,
    OverlapAnalysis,
    RegimeDecisionPolicy,
    decide_regime,
    estimate_bidirectional_overlap,
    estimate_policy_overlap,
    estimate_stratified_support,
    require_overlap_analysis_for_migration,
    support_overlap_from_counts,
)
from .seal import CohortSeal
from .sentinel import SentinelCohort, SentinelRegistry, create_sentinel


class Pass4ExitError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class MaterialStratumRegistry:
    """Frozen/versioned material-stratum registry used by an exit fixture."""

    version: str
    strata: tuple[str, ...]

    def validate(self) -> None:
        if not isinstance(self.version, str) or not self.version.strip():
            raise Pass4ExitError("material-stratum registry version is required")
        if not self.strata or len(set(self.strata)) != len(self.strata):
            raise Pass4ExitError("material-stratum registry requires unique strata")
        if any(not isinstance(value, str) or not value for value in self.strata):
            raise Pass4ExitError("material-stratum names must be non-empty strings")

    @property
    def registry_hash(self) -> str:
        self.validate()
        return sha256(_canonical({"version": self.version, "strata": list(self.strata)})).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {"version": self.version, "strata": list(self.strata), "registry_hash": self.registry_hash}


@dataclass(frozen=True)
class Pass4ExitRecord:
    sentinel: SentinelCohort
    bridge: ConstraintBridgeCohort
    new_cohort_id: str
    material_registry_version: str
    material_registry_hash: str
    projected_count_overlap: IntervalEstimate
    bidirectional_overlap: BidirectionalOverlapEstimate
    overlap_analysis: OverlapAnalysis
    decision: DetailedRegimeDecision
    decision_event_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "sentinel": self.sentinel.to_dict(),
            "bridge": self.bridge.to_dict(),
            "new_cohort_id": self.new_cohort_id,
            "material_registry_version": self.material_registry_version,
            "material_registry_hash": self.material_registry_hash,
            "projected_count_overlap": self.projected_count_overlap.to_dict(),
            "bidirectional_overlap": self.bidirectional_overlap.to_dict(),
            "overlap_analysis": self.overlap_analysis.to_dict(),
            "decision": self.decision.value,
            "decision_event_sha256": self.decision_event_sha256,
        }


def run_pass4_exit_fixture(
    *,
    source_wave_id: str,
    source_seal: CohortSeal,
    source_manifest: Mapping[str, object],
    sentinel_id: str,
    sentinel_specimen_ids: Sequence[str],
    sentinel_selection_seed: int,
    sentinel_selection_policy_hash: str,
    bridge: ConstraintBridgeCohort,
    bridge_specimens: Mapping[str, Any],
    new_cohort_id: str,
    old_samples: Sequence[Any],
    new_samples: Sequence[Any],
    old_feasible: Callable[[Any], bool],
    new_feasible: Callable[[Any], bool],
    stratum_of: Callable[[Any], str],
    old_policy_strata: Sequence[str],
    new_policy_strata: Sequence[str],
    old_count: CountEstimate,
    new_count: CountEstimate,
    intersection_count: CountEstimate,
    material_registry: MaterialStratumRegistry,
    overlap_id: str,
    decision_policy: RegimeDecisionPolicy,
    bootstrap_seed: int,
    ledger: GovernanceLedger,
    decision_event_id: str,
    actor: str,
    confidence: float = 0.95,
    bootstrap_replicates: int = 400,
) -> Pass4ExitRecord:
    """Execute the single adopted Pass-4 migration fixture end to end."""

    if source_seal.state != "SEALED":
        raise Pass4ExitError("Pass 4 exit requires a sealed source cohort")
    if source_seal.constraint_id != bridge.old_constraint_id:
        raise Pass4ExitError("bridge old constraint must match the sealed source cohort")
    if GovernanceId.parse(new_cohort_id).kind is not IdKind.COHORT:
        raise Pass4ExitError("new_cohort_id must be a governance cohort id")
    material_registry.validate()

    sentinel = create_sentinel(
        sentinel_id=sentinel_id,
        source_wave_id=source_wave_id,
        source_seal=source_seal,
        cohort_manifest=source_manifest,
        specimen_ids=sentinel_specimen_ids,
        selection_seed=sentinel_selection_seed,
        selection_policy_hash=sentinel_selection_policy_hash,
    )
    registry = SentinelRegistry()
    registry.register(sentinel)

    bridge.validate()
    if bridge.new_constraint_id == bridge.old_constraint_id:
        raise Pass4ExitError("Pass 4 exit requires a real constraint migration")
    validate_common_support(
        bridge,
        bridge_specimens,
        old_feasible=old_feasible,
        new_feasible=new_feasible,
    )

    projected_count_overlap = support_overlap_from_counts(
        old_count,
        new_count,
        intersection_count,
        confidence=confidence,
    )
    bidirectional = estimate_bidirectional_overlap(
        old_samples,
        new_samples,
        old_feasible=old_feasible,
        new_feasible=new_feasible,
        confidence=confidence,
    )
    policy_overlap = estimate_policy_overlap(
        old_policy_strata,
        new_policy_strata,
        confidence=confidence,
        bootstrap_seed=bootstrap_seed,
        bootstrap_replicates=bootstrap_replicates,
    )
    support_by_stratum = estimate_stratified_support(
        old_samples,
        new_samples,
        old_feasible=old_feasible,
        new_feasible=new_feasible,
        stratum_of=stratum_of,
        material_strata=material_registry.strata,
        confidence=confidence,
    )
    analysis = OverlapAnalysis(
        overlap_id=overlap_id,
        old_constraint_id=bridge.old_constraint_id,
        new_constraint_id=bridge.new_constraint_id,
        material_strata=material_registry.strata,
        support_by_stratum=support_by_stratum,
        policy_overlap=policy_overlap,
        method="integrated_projected_count_plus_bidirectional_monte_carlo",
        assumptions=(
            "projected-count uncertainty retained",
            "bidirectional Monte Carlo assumes feasible-regime samples",
            f"material_registry:{material_registry.version}:{material_registry.registry_hash}",
        ),
    )
    require_overlap_analysis_for_migration(
        bridge.old_constraint_id,
        bridge.new_constraint_id,
        analysis,
    )
    decision = decide_regime(analysis, decision_policy)

    event = ledger.append(
        event_id=decision_event_id,
        experiment_id=source_seal.experiment_id,
        event_type=GovernanceEventType.BRIDGE_DECISION,
        actor=actor,
        payload={
            "source_wave_id": source_wave_id,
            "source_cohort_id": source_seal.cohort_id,
            "sentinel": sentinel.to_dict(),
            "bridge": bridge.to_dict(),
            "new_cohort_id": new_cohort_id,
            "material_registry": material_registry.to_dict(),
            "projected_count_overlap": projected_count_overlap.to_dict(),
            "bidirectional_overlap": bidirectional.to_dict(),
            "overlap_analysis": analysis.to_dict(),
            "decision": decision.value,
            "decision_policy": {
                "min_support_lower_bound": decision_policy.min_support_lower_bound,
                "min_policy_overlap_lower_bound": decision_policy.min_policy_overlap_lower_bound,
            },
        },
    )

    return Pass4ExitRecord(
        sentinel=sentinel,
        bridge=bridge,
        new_cohort_id=new_cohort_id,
        material_registry_version=material_registry.version,
        material_registry_hash=material_registry.registry_hash,
        projected_count_overlap=projected_count_overlap,
        bidirectional_overlap=bidirectional,
        overlap_analysis=analysis,
        decision=decision,
        decision_event_sha256=event.event_sha256,
    )

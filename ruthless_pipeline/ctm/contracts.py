"""CTM-A frozen contracts for cumulative transfer-map claims.

This module defines the scientific claim ladder and the anti-optimization
invariant. It is additive to RAC evidence states: CTM claim maturity is not a
replacement for RAC-D/P/M evidence state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


CTM_SCHEMA_VERSION = "rac-ctm/1.0"


class CTMClaimState(str, Enum):
    CORRELATION = "correlation"
    ASSOCIATION = "association"
    CONTROLLED_EFFECT = "controlled_effect"


class CTMArtifactRole(str, Enum):
    DOE = "doe"
    GENERATOR = "generator"
    ACCEPTANCE = "acceptance"
    GENOME = "genome"
    SURROGATE_OBSERVATION = "surrogate_observation"
    HELDOUT_OBSERVATION = "heldout_observation"
    PHYSICAL_OBSERVATION = "physical_observation"
    NULL_DESIGN = "null_design"
    CLAIM = "claim"


@dataclass(frozen=True)
class CTMArtifactUse:
    artifact_id: str
    role: CTMArtifactRole
    sha256: str
    heldout_access: bool
    heldout_feedback_used: bool
    selection_influence: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.artifact_id:
            raise ValueError("artifact_id is required")
        if len(self.sha256) != 64:
            raise ValueError("sha256 must be 64 hex characters")
        try:
            int(self.sha256, 16)
        except ValueError as exc:
            raise ValueError("sha256 must be hexadecimal") from exc
        if self.selection_influence not in {
            "NONE_MEASUREMENT_ONLY",
            "SURROGATE_ONLY",
            "POST_FREEZE_ANALYSIS_ONLY",
            "NOT_APPLICABLE",
        }:
            raise ValueError(f"unknown selection_influence: {self.selection_influence!r}")


@dataclass(frozen=True)
class CTMClaim:
    claim_id: str
    state: CTMClaimState
    feature_id: str
    outcome_id: str
    source_commit: str
    consumed_artifacts: tuple[CTMArtifactUse, ...]
    independent_cohort_count: int = 1
    matched_null_design_ids: tuple[str, ...] = ()
    schema_version: str = CTM_SCHEMA_VERSION
    notes: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.schema_version != CTM_SCHEMA_VERSION:
            raise ValueError(f"unsupported CTM schema_version: {self.schema_version!r}")
        if not self.claim_id or not self.feature_id or not self.outcome_id:
            raise ValueError("claim_id, feature_id and outcome_id are required")
        if not self.source_commit:
            raise ValueError("source_commit is required")
        if self.independent_cohort_count < 1:
            raise ValueError("independent_cohort_count must be >= 1")
        if not self.consumed_artifacts:
            raise ValueError("consumed_artifacts must not be empty")
        for artifact in self.consumed_artifacts:
            artifact.validate()

        # Explicit maturity ladder. Replication can promote correlation to
        # association, but can NEVER substitute for a matched-property design.
        if self.state == CTMClaimState.ASSOCIATION and self.independent_cohort_count < 2:
            raise ValueError("association requires >=2 independent cohorts")
        if self.state == CTMClaimState.CONTROLLED_EFFECT:
            if self.independent_cohort_count < 2:
                raise ValueError("controlled_effect requires >=2 independent cohorts")
            if not self.matched_null_design_ids:
                raise ValueError(
                    "controlled_effect requires matched-property null presence; "
                    "replication alone cannot promote an unmatched association"
                )


PRE_OUTCOME_ROLES = frozenset({
    CTMArtifactRole.DOE,
    CTMArtifactRole.GENERATOR,
    CTMArtifactRole.ACCEPTANCE,
})


def validate_anti_optimization_invariant(claim: CTMClaim) -> None:
    """Refuse CTM claims whose pre-outcome machinery saw held-out information."""
    claim.validate()
    violations: list[str] = []
    for artifact in claim.consumed_artifacts:
        if artifact.role not in PRE_OUTCOME_ROLES:
            continue
        if artifact.heldout_access:
            violations.append(f"{artifact.artifact_id}: heldout_access=true")
        if artifact.heldout_feedback_used:
            violations.append(f"{artifact.artifact_id}: heldout_feedback_used=true")
        if artifact.selection_influence not in {"SURROGATE_ONLY", "NOT_APPLICABLE"}:
            violations.append(
                f"{artifact.artifact_id}: illegal pre-outcome selection influence "
                f"{artifact.selection_influence!r}"
            )
    if violations:
        raise ValueError("CTM anti-optimization invariant violated: " + "; ".join(violations))

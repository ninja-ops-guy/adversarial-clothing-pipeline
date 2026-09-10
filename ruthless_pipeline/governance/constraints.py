"""Constraint lineage and scientific-impact classification (Governance Pass 2)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .ids import GovernanceId, IdKind


class ConstraintImpact(str, Enum):
    NONE = "NONE"
    SEMANTIC_CORRECTION = "SEMANTIC_CORRECTION"
    POPULATION_CHANGE = "POPULATION_CHANGE"
    DEFINITION_CHANGE = "DEFINITION_CHANGE"


class MigrationOutcome(str, Enum):
    NO_IMPACT = "NO_IMPACT"
    MINOR_CORRECTION = "MINOR_CORRECTION"
    BRIDGE_REQUIRED = "BRIDGE_REQUIRED"
    COHORT_INVALIDATION = "COHORT_INVALIDATION"
    NEW_REGIME = "NEW_REGIME"


@dataclass(frozen=True)
class ConstraintSet:
    constraint_id: str
    parent_id: str | None
    semantic_hash: str
    rules_hash: str
    encoder_hash: str
    projection_version: str
    software_version: str
    impact: ConstraintImpact

    def validate(self) -> None:
        gid = GovernanceId.parse(self.constraint_id)
        if gid.kind is not IdKind.CONSTRAINT:
            raise ValueError("constraint_id must be RAC-CST-...")
        if self.parent_id is not None:
            parent = GovernanceId.parse(self.parent_id)
            if parent.kind is not IdKind.CONSTRAINT:
                raise ValueError("parent_id must be RAC-CST-...")
        for name in ("semantic_hash", "rules_hash", "encoder_hash"):
            value = getattr(self, name)
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be lowercase sha256")
        if not self.projection_version or not self.software_version:
            raise ValueError("projection_version and software_version are required")


def classify_migration(
    old: ConstraintSet,
    new: ConstraintSet,
    *,
    historical_population_changed: bool = False,
) -> MigrationOutcome:
    """Classify scientific compatibility separately from software-version change."""
    old.validate()
    new.validate()
    if new.parent_id != old.constraint_id:
        raise ValueError("new constraint set must reference old constraint_id as parent")
    if new.impact is ConstraintImpact.DEFINITION_CHANGE:
        return MigrationOutcome.NEW_REGIME
    if new.impact is ConstraintImpact.POPULATION_CHANGE:
        return MigrationOutcome.COHORT_INVALIDATION if historical_population_changed else MigrationOutcome.BRIDGE_REQUIRED
    if new.impact is ConstraintImpact.SEMANTIC_CORRECTION:
        return MigrationOutcome.BRIDGE_REQUIRED if historical_population_changed else MigrationOutcome.MINOR_CORRECTION
    if (old.semantic_hash, old.rules_hash, old.projection_version) != (
        new.semantic_hash,
        new.rules_hash,
        new.projection_version,
    ):
        raise ValueError("impact NONE is incompatible with scientific-semantic changes")
    return MigrationOutcome.NO_IMPACT

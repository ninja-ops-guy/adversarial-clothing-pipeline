"""Append-only recording for Governance Pass 2 constraint migrations."""

from __future__ import annotations

from .constraints import (
    MigrationDecisionRecord,
    assert_frozen_d2_artifacts_unchanged,
)
from .ledger import GovernanceEvent, GovernanceEventType, GovernanceLedger


def record_migration_decision(
    ledger: GovernanceLedger,
    decision: MigrationDecisionRecord,
    *,
    event_id: str,
    experiment_id: str,
    actor: str,
    created_at: str,
    frozen_d2_before: dict[str, str],
    frozen_d2_after: dict[str, str],
) -> GovernanceEvent:
    """Append one migration decision after proving frozen D2 inputs unchanged.

    The decision is copied into the event payload; neither the old nor new
    ``ConstraintSet`` object is mutated.  The historical D2 snapshots are a
    mandatory precondition rather than an optional post-hoc check.
    """
    assert_frozen_d2_artifacts_unchanged(frozen_d2_before, frozen_d2_after)
    return ledger.append(
        event_id=event_id,
        experiment_id=experiment_id,
        event_type=GovernanceEventType.CONSTRAINT_MIGRATION,
        payload={"migration_decision": decision.to_dict()},
        actor=actor,
        created_at=created_at,
    )

from __future__ import annotations

from ruthless_pipeline.governance.constraints import (
    FROZEN_D2_ARTIFACT_IDS,
    ConstraintImpact,
    ConstraintSet,
    EstimandImpact,
    FrozenArtifactMutationError,
    MigrationImpactAnalysis,
    MigrationOutcome,
    TolerancePolicy,
    assess_migration,
)
from ruthless_pipeline.governance.ledger import GovernanceEventType, GovernanceLedger
from ruthless_pipeline.governance.migration import record_migration_decision

import pytest


def _h(char: str) -> str:
    return char * 64


def _sets() -> tuple[ConstraintSet, ConstraintSet]:
    old = ConstraintSet(
        "RAC-CS-PASS2-LOG-001",
        None,
        _h("a"),
        _h("b"),
        _h("c"),
        "RAC-PG-1.0",
        "1.0.0",
        ConstraintImpact.NONE,
        "0.4.1",
    )
    new = ConstraintSet(
        "RAC-CS-PASS2-LOG-002",
        old.constraint_id,
        _h("a"),
        _h("b"),
        _h("d"),
        "RAC-PG-1.0",
        "1.0.1",
        ConstraintImpact.SEMANTIC_CORRECTION,
        "0.4.2",
    )
    return old, new


def _decision():
    old, new = _sets()
    decision = assess_migration(
        old,
        new,
        analysis=MigrationImpactAnalysis(
            constraint_family="ENCODER-CORRECTION",
            population_displacement=0.0,
            cohort_changed_count=0,
            cohort_total_count=12,
            estimand_impact=EstimandImpact.UNCHANGED,
        ),
        tolerance_policy=TolerancePolicy(
            constraint_family="ENCODER-CORRECTION",
            created_at="2026-09-10T00:00:00Z",
            max_population_displacement=0.01,
            max_cohort_change_fraction=0.01,
            registered_before_outcomes=True,
        ),
    )
    return old, new, decision


def test_encoder_bugfix_migration_is_logged_without_rewriting_predecessor() -> None:
    old, _, decision = _decision()
    old_before = old.to_dict()
    frozen = {artifact_id: _h("f") for artifact_id in FROZEN_D2_ARTIFACT_IDS}
    ledger = GovernanceLedger()

    event = record_migration_decision(
        ledger,
        decision,
        event_id="RAC-GOV-EVT-PASS2-MIGRATION-001",
        experiment_id="RAC-EXP-PASS2-MIGRATION",
        actor="pass2-test",
        created_at="2026-09-10T00:01:00Z",
        frozen_d2_before=frozen,
        frozen_d2_after=dict(frozen),
    )

    assert decision.outcome is MigrationOutcome.MINOR_CORRECTION
    assert event.event_type == GovernanceEventType.CONSTRAINT_MIGRATION.value
    assert event.payload["migration_decision"] == decision.to_dict()
    assert old.to_dict() == old_before
    assert ledger.verify() is True


def test_migration_event_refuses_changed_frozen_d2_input_before_append() -> None:
    _, _, decision = _decision()
    before = {artifact_id: _h("f") for artifact_id in FROZEN_D2_ARTIFACT_IDS}
    after = dict(before)
    after["RAC-PER-D2-0003"] = _h("e")
    ledger = GovernanceLedger()

    with pytest.raises(FrozenArtifactMutationError, match="D2-0003"):
        record_migration_decision(
            ledger,
            decision,
            event_id="RAC-GOV-EVT-PASS2-MIGRATION-002",
            experiment_id="RAC-EXP-PASS2-MIGRATION",
            actor="pass2-test",
            created_at="2026-09-10T00:02:00Z",
            frozen_d2_before=before,
            frozen_d2_after=after,
        )
    assert ledger.events == ()

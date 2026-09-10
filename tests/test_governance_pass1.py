from dataclasses import replace

import pytest

from ruthless_pipeline.governance.ids import GovernanceId, IdKind
from ruthless_pipeline.governance.ledger import GovernanceLedger, LedgerIntegrityError
from ruthless_pipeline.governance.state import ExperimentState, GovernanceStateMachine, StateTransitionError
from ruthless_pipeline.governance.validators import GovernanceValidationError, validate_manifest


def test_typed_ids_round_trip_and_reject_malformed():
    raw = "RAC-EXP-PASS1-001"
    parsed = GovernanceId.parse(raw)
    assert parsed.kind is IdKind.EXPERIMENT
    assert str(parsed) == raw
    with pytest.raises(ValueError):
        GovernanceId.parse("RAC-EXP-??")


def test_state_machine_happy_path_and_halt_path():
    machine = GovernanceStateMachine()
    for target in (ExperimentState.PREFLIGHT, ExperimentState.SEALED, ExperimentState.RUNNING, ExperimentState.COMPLETE):
        machine.transition(target)
    assert machine.state is ExperimentState.COMPLETE

    faulted = GovernanceStateMachine()
    faulted.transition(ExperimentState.PREFLIGHT)
    faulted.transition(ExperimentState.SEALED)
    faulted.transition(ExperimentState.RUNNING)
    assert faulted.halt() is ExperimentState.HALTED


def test_illegal_state_transition_denied():
    with pytest.raises(StateTransitionError):
        GovernanceStateMachine().transition(ExperimentState.RUNNING)


def _ledger():
    ledger = GovernanceLedger()
    first = ledger.append(
        event_id="RAC-EVT-PASS1-001",
        experiment_id="RAC-EXP-PASS1-001",
        event_type="PREFLIGHT",
        payload={"ok": True},
        timestamp_utc="2026-09-10T00:00:00Z",
    )
    second = ledger.append(
        event_id="RAC-EVT-PASS1-002",
        experiment_id="RAC-EXP-PASS1-001",
        event_type="SEALED",
        payload={"manifest": "fixture"},
        timestamp_utc="2026-09-10T00:00:01Z",
    )
    return ledger, first, second


def test_hash_chain_verifies():
    ledger, _, _ = _ledger()
    assert ledger.verify() is True


def test_corrupt_previous_hash_fails():
    ledger, first, second = _ledger()
    ledger._events[1] = replace(second, previous_hash="0" * 64)
    with pytest.raises(LedgerIntegrityError):
        ledger.verify()


def test_edited_historical_event_fails():
    ledger, first, _ = _ledger()
    ledger._events[0] = replace(first, payload={"ok": False})
    with pytest.raises(LedgerIntegrityError):
        ledger.verify()


def test_reversal_preserves_original_bytes_and_chain():
    ledger, first, _ = _ledger()
    original_hash = first.event_hash
    ledger.append(
        event_id="RAC-EVT-PASS1-003",
        experiment_id="RAC-EXP-PASS1-001",
        event_type="REVERSAL",
        payload={"reason": "fixture"},
        reverses_event_id=first.event_id,
        timestamp_utc="2026-09-10T00:00:02Z",
    )
    assert ledger.events[0].event_hash == original_hash
    assert ledger.verify() is True


def test_missing_required_manifest_field_denied():
    with pytest.raises(GovernanceValidationError):
        validate_manifest("sampling_manifest", {"schema_version": "1.0"})


def test_malformed_seed_and_hash_denied():
    with pytest.raises(GovernanceValidationError):
        validate_manifest("sampling_manifest", {
            "schema_version": "1.0",
            "sampling_id": "RAC-SMP-PASS1-001",
            "experiment_id": "RAC-EXP-PASS1-001",
            "seed": -1,
            "target_distribution": "uniform",
        })
    with pytest.raises(GovernanceValidationError):
        validate_manifest("cohort_manifest", {
            "schema_version": "1.0",
            "cohort_id": "RAC-COH-PASS1-001",
            "experiment_id": "RAC-EXP-PASS1-001",
            "specimen_ids": ["a"],
            "artifact_sha256": "bad",
        })


def test_valid_sampling_manifest_passes():
    assert validate_manifest("sampling_manifest", {
        "schema_version": "1.0",
        "sampling_id": "RAC-SMP-PASS1-001",
        "experiment_id": "RAC-EXP-PASS1-001",
        "seed": 1337,
        "target_distribution": "uniform",
    })

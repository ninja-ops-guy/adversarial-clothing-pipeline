from dataclasses import replace
import json
from pathlib import Path

import jsonschema
import pytest

from ruthless_pipeline.governance.ids import GovernanceId, IdKind
from ruthless_pipeline.governance.ledger import (
    GovernanceEventType,
    GovernanceLedger,
    LedgerIntegrityError,
)
from ruthless_pipeline.governance.state import (
    ExperimentState,
    GovernanceStateMachine,
    InvariantConflict,
    StateTransitionError,
)
from ruthless_pipeline.governance.validators import (
    GovernanceValidationError,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "ruthless_pipeline" / "governance" / "schemas"
EXPERIMENT_ID = "RAC-EXP-PASS1-001"
ACTOR = "pass1-test"


def _machine() -> tuple[GovernanceLedger, GovernanceStateMachine]:
    ledger = GovernanceLedger()
    machine = GovernanceStateMachine(
        experiment_id=EXPERIMENT_ID,
        ledger=ledger,
        actor=ACTOR,
    )
    return ledger, machine


def _advance_to_running(
    ledger: GovernanceLedger,
    machine: GovernanceStateMachine,
) -> None:
    del ledger
    for index, target in enumerate(
        (
            ExperimentState.PREFLIGHT,
            ExperimentState.SEALED,
            ExperimentState.RUNNING,
        ),
        start=1,
    ):
        machine.transition(
            target,
            event_id=f"RAC-GOV-EVT-PASS1-{index:03d}",
            created_at=f"2026-09-10T00:00:0{index}Z",
        )


def test_typed_ids_emit_canonical_and_read_legacy_aliases() -> None:
    canonical = GovernanceId.parse("RAC-CS-PASS1-001")
    assert canonical.kind is IdKind.CONSTRAINT
    assert canonical.canonical == "RAC-CS-PASS1-001"
    assert not canonical.is_legacy_alias

    legacy = GovernanceId.parse("RAC-CST-PASS1-001")
    assert legacy.kind is IdKind.CONSTRAINT
    assert legacy.is_legacy_alias
    assert legacy.canonical == "RAC-CS-PASS1-001"
    assert str(legacy) == "RAC-CST-PASS1-001"

    generated = GovernanceId(IdKind.EVENT, "PASS1-001")
    assert str(generated) == "RAC-GOV-EVT-PASS1-001"

    with pytest.raises(ValueError):
        GovernanceId.parse("RAC-EXP-??")


def test_state_machine_happy_path_is_fully_ledger_backed() -> None:
    ledger, machine = _machine()
    transitions = (
        ExperimentState.PREFLIGHT,
        ExperimentState.SEALED,
        ExperimentState.RUNNING,
        ExperimentState.COMPLETE,
    )
    for index, target in enumerate(transitions, start=1):
        machine.transition(
            target,
            event_id=f"RAC-GOV-EVT-HAPPY-{index:03d}",
            created_at=f"2026-09-10T00:01:0{index}Z",
        )

    assert machine.state is ExperimentState.COMPLETE
    assert len(ledger.events) == 4
    assert [event.event_type for event in ledger.events] == [
        GovernanceEventType.STATE_TRANSITION.value
    ] * 4
    assert ledger.events[0].payload == {
        "from_state": "DRAFT",
        "to_state": "PREFLIGHT",
    }
    assert ledger.events[-1].payload == {
        "from_state": "RUNNING",
        "to_state": "COMPLETE",
    }
    assert ledger.verify() is True


def test_invariant_conflict_produces_structured_halt_event() -> None:
    ledger, machine = _machine()
    _advance_to_running(ledger, machine)
    conflict = InvariantConflict(
        invariant_ids=("LAW-7",),
        affected_ids=(EXPERIMENT_ID, "RAC-COHORT-PASS1-001"),
        discovered_at="2026-09-10T00:00:10Z",
        evidence_status="PRE_RESULT",
        data_collection_occurred=False,
        required_governance_decision="resolve invariant conflict before resumption",
    )

    assert machine.halt_for_conflict(
        conflict,
        event_id="RAC-GOV-EVT-PASS1-HALT",
    ) is ExperimentState.HALTED
    assert machine.halt_record == conflict
    halt_event = ledger.events[-1]
    assert halt_event.event_type == GovernanceEventType.HALT.value
    assert halt_event.payload["from_state"] == "RUNNING"
    assert halt_event.payload["to_state"] == "HALTED"
    assert halt_event.payload["conflict"]["invariant_ids"] == ("LAW-7",)
    assert ledger.verify() is True


def test_generic_halt_and_direct_state_mutation_are_denied() -> None:
    ledger, machine = _machine()
    with pytest.raises(StateTransitionError):
        machine.transition(
            ExperimentState.HALTED,
            event_id="RAC-GOV-EVT-BYPASS-001",
            created_at="2026-09-10T00:02:00Z",
        )
    assert machine.state is ExperimentState.DRAFT
    assert ledger.events == ()
    assert not hasattr(machine, "halt")
    with pytest.raises(AttributeError):
        machine.state = ExperimentState.RUNNING  # type: ignore[misc]


def test_illegal_state_transition_fails_before_ledger_append() -> None:
    ledger, machine = _machine()
    with pytest.raises(StateTransitionError):
        machine.transition(
            ExperimentState.RUNNING,
            event_id="RAC-GOV-EVT-ILLEGAL-001",
            created_at="2026-09-10T00:03:00Z",
        )
    assert machine.state is ExperimentState.DRAFT
    assert ledger.events == ()


def _ledger() -> tuple[GovernanceLedger, object, object]:
    ledger = GovernanceLedger()
    first = ledger.append(
        event_id="RAC-GOV-EVT-PASS1-101",
        experiment_id=EXPERIMENT_ID,
        event_type=GovernanceEventType.CREATE,
        payload={"object": "fixture"},
        actor=ACTOR,
        created_at="2026-09-10T00:10:00Z",
    )
    second = ledger.append(
        event_id="RAC-GOV-EVT-PASS1-102",
        experiment_id=EXPERIMENT_ID,
        event_type=GovernanceEventType.SEAL,
        payload={"manifest": "fixture"},
        actor=ACTOR,
        created_at="2026-09-10T00:10:01Z",
    )
    return ledger, first, second


def test_hash_chain_verifies_and_validator_accepts_emitted_event() -> None:
    ledger, first, _ = _ledger()
    assert ledger.verify() is True
    assert validate_manifest("governance_event", first.to_dict())


def test_corrupt_previous_hash_fails() -> None:
    ledger, _, second = _ledger()
    ledger._events[1] = replace(second, previous_event_sha256="0" * 64)
    with pytest.raises(LedgerIntegrityError):
        ledger.verify()


def test_edited_historical_payload_fails() -> None:
    ledger, first, _ = _ledger()
    ledger._events[0] = replace(first, payload={"object": "tampered"})
    with pytest.raises(LedgerIntegrityError):
        ledger.verify()


def test_reversal_preserves_original_event_and_chain() -> None:
    ledger, first, _ = _ledger()
    original = first.to_dict()
    ledger.append(
        event_id="RAC-GOV-EVT-PASS1-103",
        experiment_id=EXPERIMENT_ID,
        event_type=GovernanceEventType.REVERSAL,
        payload={"reason": "fixture correction"},
        actor=ACTOR,
        reverses_event_id=first.event_id,
        created_at="2026-09-10T00:10:02Z",
    )
    assert ledger.events[0].to_dict() == original
    assert ledger.verify() is True


def test_reversal_must_reference_existing_same_experiment_event() -> None:
    ledger = GovernanceLedger()
    with pytest.raises(ValueError):
        ledger.append(
            event_id="RAC-GOV-EVT-PASS1-104",
            experiment_id=EXPERIMENT_ID,
            event_type=GovernanceEventType.REVERSAL,
            payload={"reason": "invalid fixture"},
            actor=ACTOR,
            reverses_event_id="RAC-GOV-EVT-PASS1-999",
            created_at="2026-09-10T00:10:03Z",
        )


def test_canonical_and_legacy_alias_cannot_duplicate_event_identity() -> None:
    ledger = GovernanceLedger()
    ledger.append(
        event_id="RAC-GOV-EVT-PASS1-201",
        experiment_id=EXPERIMENT_ID,
        event_type=GovernanceEventType.CREATE,
        payload={},
        actor=ACTOR,
        created_at="2026-09-10T00:11:00Z",
    )
    with pytest.raises(ValueError, match="duplicate governance event id"):
        ledger.append(
            event_id="RAC-EVT-PASS1-201",
            experiment_id=EXPERIMENT_ID,
            event_type=GovernanceEventType.CREATE,
            payload={},
            actor=ACTOR,
            created_at="2026-09-10T00:11:01Z",
        )


def test_event_validator_rejects_payload_tampering() -> None:
    _, first, _ = _ledger()
    payload = first.to_dict()
    payload["payload"] = {"object": "tampered"}
    with pytest.raises(GovernanceValidationError, match="payload_sha256"):
        validate_manifest("governance_event", payload)


def test_missing_required_manifest_field_denied() -> None:
    with pytest.raises(GovernanceValidationError):
        validate_manifest("sampling_manifest", {"schema_version": "1.0"})


def test_malformed_seed_and_hash_denied() -> None:
    with pytest.raises(GovernanceValidationError):
        validate_manifest(
            "sampling_manifest",
            {
                "schema_version": "1.0",
                "sampling_id": "RAC-SAMP-PASS1-001",
                "experiment_id": EXPERIMENT_ID,
                "seed": -1,
                "target_distribution": "uniform",
            },
        )
    with pytest.raises(GovernanceValidationError):
        validate_manifest(
            "cohort_manifest",
            {
                "schema_version": "1.0",
                "cohort_id": "RAC-COHORT-PASS1-001",
                "experiment_id": EXPERIMENT_ID,
                "specimen_ids": ["specimen-a"],
                "artifact_sha256": "bad",
            },
        )


def test_valid_canonical_sampling_manifest_passes() -> None:
    assert validate_manifest(
        "sampling_manifest",
        {
            "schema_version": "1.0",
            "sampling_id": "RAC-SAMP-PASS1-001",
            "experiment_id": EXPERIMENT_ID,
            "seed": 1337,
            "target_distribution": "uniform",
        },
    )


@pytest.mark.parametrize(
    ("filename", "manifest"),
    [
        (
            "constraint_set.schema.json",
            {
                "schema_version": "1.0",
                "constraint_id": "RAC-CS-PASS1-001",
                "semantic_hash": "a" * 64,
                "rules_hash": "b" * 64,
                "encoder_hash": "c" * 64,
            },
        ),
        (
            "overlap_analysis.schema.json",
            {
                "schema_version": "1.0",
                "overlap_id": "RAC-OVERLAP-PASS1-001",
                "left_constraint_id": "RAC-CS-PASS1-001",
                "right_constraint_id": "RAC-CS-PASS1-002",
                "method": "synthetic-fixture",
            },
        ),
        (
            "diagnostic_bundle.schema.json",
            {
                "schema_version": "1.0",
                "diagnostic_id": "RAC-DIAG-PASS1-001",
                "experiment_id": EXPERIMENT_ID,
                "checks": [],
                "thresholds_hash": "d" * 64,
            },
        ),
    ],
)
def test_adopted_canonical_ids_pass_json_schemas(
    filename: str,
    manifest: dict,
) -> None:
    schema = json.loads((SCHEMA_DIR / filename).read_text())
    jsonschema.Draft202012Validator(schema).validate(manifest)

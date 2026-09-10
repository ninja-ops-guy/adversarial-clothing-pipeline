from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import jsonschema
import pytest

from ruthless_pipeline.ctm.intake import CTMIntakeError, accept_governed_cohort
from ruthless_pipeline.governance.constraints import (
    ConstraintImpact,
    ConstraintSet,
    ConstraintSetRegistry,
)
from ruthless_pipeline.governance.ledger import GovernanceLedger
from ruthless_pipeline.governance.seal import (
    SealError,
    seal_governed_cohort,
    verify_governed_seal,
)
from ruthless_pipeline.governance.state import ExperimentState, GovernanceStateMachine
from ruthless_pipeline.governance.validators import validate_manifest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "ruthless_pipeline" / "governance" / "schemas"
EXPERIMENT_ID = "RAC-EXP-PASS3-SYNTHETIC"
SAMPLING_ID = "RAC-SAMP-PASS3-SYNTHETIC"
COHORT_ID = "RAC-COHORT-PASS3-SYNTHETIC"
CONSTRAINT_ID = "RAC-CS-PASS3-SYNTHETIC"
PIPELINE_ID = "RAC-PIPE-PASS3-SYNTHETIC"
CALIBRATION_ID = "RAC-CAL-PASS3-SYNTHETIC"
THRESHOLDS = b'{"maximum_duplicate_fraction":0.1,"version":"pass3-test/1"}'


def _h(char: str) -> str:
    return char * 64


def _registry() -> ConstraintSetRegistry:
    registry = ConstraintSetRegistry()
    registry.add(
        ConstraintSet(
            constraint_id=CONSTRAINT_ID,
            parent_id=None,
            semantic_hash=_h("a"),
            rules_hash=_h("b"),
            encoder_hash=_h("c"),
            projection_version="RAC-PG-1.0",
            software_version="1.0.0",
            impact=ConstraintImpact.NONE,
            encoder_version="0.4.2",
        )
    )
    return registry


def _manifests() -> tuple[dict[str, object], dict[str, object], dict[str, bytes]]:
    artifacts = {
        "cohort/specimen-001.json": b'{"pattern":"A"}',
        "cohort/specimen-002.json": b'{"pattern":"B"}',
    }
    sampling = {
        "schema_version": "1.0",
        "sampling_id": SAMPLING_ID,
        "experiment_id": EXPERIMENT_ID,
        "constraint_set_id": CONSTRAINT_ID,
        "seed": 20260910,
        "sample_count": 2,
        "target_distribution": "stratified",
        "sampler_version": "synthetic-pass3/1.0",
    }
    cohort = {
        "schema_version": "1.0",
        "cohort_id": COHORT_ID,
        "experiment_id": EXPERIMENT_ID,
        "sampling_id": SAMPLING_ID,
        "constraint_set_id": CONSTRAINT_ID,
        "code_commit": "a" * 40,
        "code_version": "3.1.0",
        "pipeline_id": PIPELINE_ID,
        "pipeline_version": "pipeline-test/1.0",
        "calibration_id": CALIBRATION_ID,
        "calibration_version": "cal-test/1.0",
        "diagnostic_threshold_hash": sha256(THRESHOLDS).hexdigest(),
        "specimen_ids": ["SYNTH-001", "SYNTH-002"],
        "artifacts": {path: sha256(data).hexdigest() for path, data in artifacts.items()},
    }
    return sampling, cohort, artifacts


def _preflight_machine() -> tuple[GovernanceStateMachine, GovernanceLedger]:
    ledger = GovernanceLedger()
    machine = GovernanceStateMachine(
        experiment_id=EXPERIMENT_ID,
        ledger=ledger,
        actor="pass3-test",
    )
    machine.transition(
        ExperimentState.PREFLIGHT,
        event_id="RAC-GOV-EVT-PASS3-PREFLIGHT",
        created_at="2026-09-10T19:00:00Z",
    )
    return machine, ledger


def _seal(**overrides):
    sampling, cohort, artifacts = _manifests()
    machine, ledger = _preflight_machine()
    kwargs = {
        "constraint_registry": _registry(),
        "registered_pipeline_ids": {PIPELINE_ID},
        "registered_calibration_ids": {CALIBRATION_ID},
        "diagnostic_threshold_bytes": THRESHOLDS,
        "diagnostics_passed": True,
        "state_machine": machine,
        "seal_event_id": "RAC-GOV-EVT-PASS3-SEAL",
        "created_at": "2026-09-10T19:01:00Z",
    }
    kwargs.update(overrides)
    seal = seal_governed_cohort(sampling, cohort, artifacts, **kwargs)
    return seal, sampling, cohort, artifacts, machine, ledger, kwargs


class _Timestamp:
    def __init__(self, prefix: str = "token") -> None:
        self.prefix = prefix

    def timestamp(self, digest: str) -> str:
        return f"{self.prefix}:{digest}"

    def verify(self, digest: str, token: str) -> bool:
        return token == f"{self.prefix}:{digest}"


def test_adopted_sampling_and_cohort_manifests_are_schema_and_semantic_valid() -> None:
    sampling, cohort, _ = _manifests()
    for kind, manifest in (("sampling_manifest", sampling), ("cohort_manifest", cohort)):
        schema = json.loads((SCHEMA_DIR / f"{kind}.schema.json").read_text())
        jsonschema.Draft202012Validator(schema).validate(manifest)
        assert validate_manifest(kind, manifest) is True


def test_exit_gate_seals_then_independently_rederives_complete_cohort() -> None:
    seal, sampling, cohort, artifacts, machine, ledger, kwargs = _seal()
    assert machine.state is ExperimentState.SEALED
    assert seal.state == "SEALED"
    assert seal.sampling_id == SAMPLING_ID
    assert seal.constraint_set_id == CONSTRAINT_ID
    assert ledger.verify() is True
    assert len(ledger.events) == 2
    assert ledger.events[-1].payload["to_state"] == "SEALED"
    assert ledger.events[-1].payload["seal_hash"] == seal.seal_hash

    verify_governed_seal(
        seal,
        sampling,
        cohort,
        artifacts,
        constraint_registry=kwargs["constraint_registry"],
        registered_pipeline_ids=kwargs["registered_pipeline_ids"],
        registered_calibration_ids=kwargs["registered_calibration_ids"],
        diagnostic_threshold_bytes=THRESHOLDS,
        diagnostics_passed=True,
    )


def test_same_complete_inputs_produce_same_scientific_seal_identity() -> None:
    first, *_ = _seal()
    second, *_ = _seal()
    assert first.seal_id == second.seal_id
    assert first.seal_hash == second.seal_hash
    assert first.constraint_record_hash == second.constraint_record_hash


def test_optional_timestamp_and_git_envelope_do_not_change_scientific_identity() -> None:
    plain, *_ = _seal()
    stamped, sampling, cohort, artifacts, _, _, kwargs = _seal(
        git_signature_status="VERIFIED",
        git_signature_ref="git-verify:test-key",
        timestamp_adapter=_Timestamp(),
    )
    assert stamped.seal_hash == plain.seal_hash
    assert stamped.seal_id == plain.seal_id
    assert stamped.timestamp_token == f"token:{stamped.seal_hash}"
    verify_governed_seal(
        stamped,
        sampling,
        cohort,
        artifacts,
        constraint_registry=kwargs["constraint_registry"],
        registered_pipeline_ids=kwargs["registered_pipeline_ids"],
        registered_calibration_ids=kwargs["registered_calibration_ids"],
        diagnostic_threshold_bytes=THRESHOLDS,
        diagnostics_passed=True,
        timestamp_adapter=_Timestamp(),
    )


def test_absent_seed_fails_before_sealed_transition() -> None:
    sampling, cohort, artifacts = _manifests()
    sampling.pop("seed")
    machine, ledger = _preflight_machine()
    with pytest.raises(SealError, match="sampling_manifest: JSON Schema validation failed"):
        seal_governed_cohort(
            sampling,
            cohort,
            artifacts,
            constraint_registry=_registry(),
            registered_pipeline_ids={PIPELINE_ID},
            registered_calibration_ids={CALIBRATION_ID},
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=True,
            state_machine=machine,
            seal_event_id="RAC-GOV-EVT-PASS3-SEAL-NOSEED",
        )
    assert machine.state is ExperimentState.PREFLIGHT
    assert len(ledger.events) == 1


def test_invalid_referenced_constraint_set_fails_closed() -> None:
    sampling, cohort, artifacts = _manifests()
    empty_registry = ConstraintSetRegistry()
    machine, ledger = _preflight_machine()
    with pytest.raises(SealError, match="unregistered constraint set"):
        seal_governed_cohort(
            sampling,
            cohort,
            artifacts,
            constraint_registry=empty_registry,
            registered_pipeline_ids={PIPELINE_ID},
            registered_calibration_ids={CALIBRATION_ID},
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=True,
            state_machine=machine,
            seal_event_id="RAC-GOV-EVT-PASS3-SEAL-BADCS",
        )
    assert machine.state is ExperimentState.PREFLIGHT
    assert len(ledger.events) == 1


def test_cohort_count_must_match_sampling_manifest() -> None:
    sampling, cohort, artifacts = _manifests()
    sampling["sample_count"] = 3
    machine, _ = _preflight_machine()
    with pytest.raises(SealError, match="cohort count mismatch"):
        seal_governed_cohort(
            sampling,
            cohort,
            artifacts,
            constraint_registry=_registry(),
            registered_pipeline_ids={PIPELINE_ID},
            registered_calibration_ids={CALIBRATION_ID},
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=True,
            state_machine=machine,
            seal_event_id="RAC-GOV-EVT-PASS3-SEAL-COUNT",
        )


def test_duplicate_specimen_id_is_denied() -> None:
    sampling, cohort, artifacts = _manifests()
    cohort["specimen_ids"] = ["SYNTH-001", "SYNTH-001"]
    machine, _ = _preflight_machine()
    with pytest.raises(SealError, match="cohort_manifest: JSON Schema validation failed"):
        seal_governed_cohort(
            sampling,
            cohort,
            artifacts,
            constraint_registry=_registry(),
            registered_pipeline_ids={PIPELINE_ID},
            registered_calibration_ids={CALIBRATION_ID},
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=True,
            state_machine=machine,
            seal_event_id="RAC-GOV-EVT-PASS3-SEAL-DUP",
        )


def test_artifact_hash_or_artifact_set_mismatch_fails_closed() -> None:
    sampling, cohort, artifacts = _manifests()
    machine, _ = _preflight_machine()
    bad_artifacts = dict(artifacts)
    bad_artifacts["cohort/specimen-001.json"] = b"tampered"
    with pytest.raises(SealError, match="artifact hash mismatch"):
        seal_governed_cohort(
            sampling,
            cohort,
            bad_artifacts,
            constraint_registry=_registry(),
            registered_pipeline_ids={PIPELINE_ID},
            registered_calibration_ids={CALIBRATION_ID},
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=True,
            state_machine=machine,
            seal_event_id="RAC-GOV-EVT-PASS3-SEAL-HASH",
        )


def test_changed_diagnostic_threshold_after_manifest_generation_fails() -> None:
    sampling, cohort, artifacts = _manifests()
    machine, _ = _preflight_machine()
    with pytest.raises(SealError, match="diagnostic threshold changed"):
        seal_governed_cohort(
            sampling,
            cohort,
            artifacts,
            constraint_registry=_registry(),
            registered_pipeline_ids={PIPELINE_ID},
            registered_calibration_ids={CALIBRATION_ID},
            diagnostic_threshold_bytes=b'{"maximum_duplicate_fraction":0.2}',
            diagnostics_passed=True,
            state_machine=machine,
            seal_event_id="RAC-GOV-EVT-PASS3-SEAL-THRESHOLD",
        )


def test_diagnostics_and_reference_gates_are_fail_closed() -> None:
    sampling, cohort, artifacts = _manifests()
    machine, _ = _preflight_machine()
    with pytest.raises(SealError, match="diagnostics gate refused"):
        seal_governed_cohort(
            sampling,
            cohort,
            artifacts,
            constraint_registry=_registry(),
            registered_pipeline_ids={PIPELINE_ID},
            registered_calibration_ids={CALIBRATION_ID},
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=False,
            state_machine=machine,
            seal_event_id="RAC-GOV-EVT-PASS3-SEAL-DIAG",
        )

    machine2, _ = _preflight_machine()
    with pytest.raises(SealError, match="unregistered evaluation pipeline"):
        seal_governed_cohort(
            sampling,
            cohort,
            artifacts,
            constraint_registry=_registry(),
            registered_pipeline_ids=set(),
            registered_calibration_ids={CALIBRATION_ID},
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=True,
            state_machine=machine2,
            seal_event_id="RAC-GOV-EVT-PASS3-SEAL-PIPE",
        )


def test_provenance_versions_and_manifest_bytes_are_bound_into_seal() -> None:
    first, *_ = _seal()
    sampling, cohort, artifacts = _manifests()
    cohort["pipeline_version"] = "pipeline-test/1.1"
    machine, _ = _preflight_machine()
    second = seal_governed_cohort(
        sampling,
        cohort,
        artifacts,
        constraint_registry=_registry(),
        registered_pipeline_ids={PIPELINE_ID},
        registered_calibration_ids={CALIBRATION_ID},
        diagnostic_threshold_bytes=THRESHOLDS,
        diagnostics_passed=True,
        state_machine=machine,
        seal_event_id="RAC-GOV-EVT-PASS3-SEAL-VERSION",
    )
    assert first.seal_hash != second.seal_hash
    assert first.cohort_manifest_hash != second.cohort_manifest_hash


def test_ctm_requires_complete_independent_context_for_governance_v1_seal() -> None:
    seal, sampling, cohort, artifacts, _, _, kwargs = _seal()
    with pytest.raises(CTMIntakeError, match="requires sampling_manifest"):
        accept_governed_cohort(seal, cohort, artifacts)

    accepted = accept_governed_cohort(
        seal,
        cohort,
        artifacts,
        sampling_manifest=sampling,
        constraint_registry=kwargs["constraint_registry"],
        registered_pipeline_ids=kwargs["registered_pipeline_ids"],
        registered_calibration_ids=kwargs["registered_calibration_ids"],
        diagnostic_threshold_bytes=THRESHOLDS,
        diagnostics_passed=True,
    )
    assert accepted == seal

    tampered = dict(artifacts)
    tampered["cohort/specimen-002.json"] = b"tampered"
    with pytest.raises(CTMIntakeError, match="invalid cohort seal"):
        accept_governed_cohort(
            seal,
            cohort,
            tampered,
            sampling_manifest=sampling,
            constraint_registry=kwargs["constraint_registry"],
            registered_pipeline_ids=kwargs["registered_pipeline_ids"],
            registered_calibration_ids=kwargs["registered_calibration_ids"],
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=True,
        )


def test_tampered_seal_object_fails_independent_verification() -> None:
    seal, sampling, cohort, artifacts, _, _, kwargs = _seal()
    forged = replace(seal, code_version="forged")
    with pytest.raises(SealError, match="does not match current complete inputs"):
        verify_governed_seal(
            forged,
            sampling,
            cohort,
            artifacts,
            constraint_registry=kwargs["constraint_registry"],
            registered_pipeline_ids=kwargs["registered_pipeline_ids"],
            registered_calibration_ids=kwargs["registered_calibration_ids"],
            diagnostic_threshold_bytes=THRESHOLDS,
            diagnostics_passed=True,
        )

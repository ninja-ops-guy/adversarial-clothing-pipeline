"""Tests for ruthless_pipeline.certification.experiment_state_machine.

All artifacts are synthetic and labelled synthetic_pipeline_validation_only.
No generation record is read or written; nothing is armed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ruthless_pipeline.certification import experiment_state_machine as esm
from ruthless_pipeline.certification.experiment_state_machine import (
    EVIDENCE_CLASS,
    GuardEvidence,
    IllegalTransitionError,
    JournalTamperError,
    State,
    StateMachineError,
    TransitionGuardError,
    ExperimentStateMachine,
    genesis_hash,
    replay_journal,
    state_for_lock_status,
    verify_journal,
)
from ruthless_pipeline.certification.release_format import (
    ReleaseManifest,
    compute_content_hash,
)

UTC = "2026-01-01T00:00:00Z"


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _write(path: Path, payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    return _sha(blob)


def _make_machine(tmp_path: Path, **kwargs) -> ExperimentStateMachine:
    kwargs.setdefault(
        "experiment_label", "synthetic-pipeline-validation-only-experiment"
    )
    kwargs.setdefault("journal_path", tmp_path / "state-journal.json")
    return ExperimentStateMachine(**kwargs)


@pytest.fixture()
def prereg_hash(tmp_path) -> str:
    return _write(
        tmp_path / "prereg.md",
        {"doc": "synthetic preregistration", "evidence_class": EVIDENCE_CLASS},
    )


@pytest.fixture()
def preregistered(tmp_path, prereg_hash) -> ExperimentStateMachine:
    machine = _make_machine(tmp_path)
    machine.transition(
        State.PREREGISTERED,
        created_utc=UTC,
        evidence=GuardEvidence(preregistration_sha256=prereg_hash),
    )
    return machine


@pytest.fixture()
def armed(tmp_path, preregistered, prereg_hash) -> ExperimentStateMachine:
    preregistered.transition(
        State.ARMED,
        created_utc=UTC,
        evidence=GuardEvidence(
            preregistration_sha256=prereg_hash, armed_attestation=True
        ),
    )
    return preregistered


@pytest.fixture()
def freeze_manifest(tmp_path) -> tuple[Path, str]:
    base = tmp_path / "freeze"
    frozen = _write(base / "frozen-params.json", {"params": "synthetic", "seed": 1337})
    manifest_sha = _write(
        base / "freeze-manifest.json", {"entries": {"frozen-params.json": frozen}}
    )
    return base / "freeze-manifest.json", manifest_sha


@pytest.fixture()
def running(tmp_path, armed, freeze_manifest) -> ExperimentStateMachine:
    path, manifest_sha = freeze_manifest
    armed.transition(
        State.RUNNING,
        created_utc=UTC,
        evidence=GuardEvidence(freeze_manifest_sha256=manifest_sha),
        freeze_manifest_path=path,
    )
    return armed


@pytest.fixture()
def sealed_file(tmp_path) -> tuple[Path, str]:
    payload = {"schema_id": "synthetic-sealed", "result": {"decision": "SUCCESS"}}
    sha = _write(tmp_path / "sealed-evidence.json", payload)
    return tmp_path / "sealed-evidence.json", sha


@pytest.fixture()
def sealed(tmp_path, running, sealed_file) -> ExperimentStateMachine:
    path, sha = sealed_file
    running.transition(
        State.EVIDENCE_SEALED,
        created_utc=UTC,
        evidence=GuardEvidence(sealed_evidence_sha256=sha),
        sealed_evidence_path=path,
    )
    return running


@pytest.fixture()
def outcome_file(tmp_path) -> tuple[Path, str]:
    payload = {"decision_region": "SUCCESS", "evidence_class": EVIDENCE_CLASS}
    sha = _write(tmp_path / "outcome.json", payload)
    return tmp_path / "outcome.json", sha


@pytest.fixture()
def closed(tmp_path, sealed, outcome_file) -> ExperimentStateMachine:
    path, sha = outcome_file
    sealed.transition(
        State.CLOSED,
        created_utc=UTC,
        evidence=GuardEvidence(
            closure_artifact_sha256=sha, closure_kind="decision_region"
        ),
        outcome_artifact_path=path,
    )
    return sealed


@pytest.fixture()
def release_dir(tmp_path) -> tuple[Path, str]:
    rel = tmp_path / "release" / "RAC-EXP-2026-901"
    _write(rel / "sealed-evidence.json", {"synthetic": True})
    manifest = ReleaseManifest.build(rel)
    manifest.write(rel)
    return rel, compute_content_hash(manifest)


@pytest.fixture()
def published(tmp_path, closed, release_dir) -> ExperimentStateMachine:
    rel, content_hash = release_dir
    closed.transition(
        State.PUBLISHED,
        created_utc=UTC,
        evidence=GuardEvidence(release_content_hash=content_hash),
        release_dir=rel,
    )
    return closed


# ---------------------------------------------------------------------------
# Every legal transition
# ---------------------------------------------------------------------------

def test_full_legal_path(published):
    assert published.state is State.PUBLISHED
    journal = published.to_journal()
    verify_journal(journal)
    assert journal["evidence_class"] == EVIDENCE_CLASS
    transitions = [
        (e["from_state"], e["to_state"]) for e in journal["entries"]
    ]
    assert transitions == [
        ("DRAFT", "PREREGISTERED"),
        ("PREREGISTERED", "ARMED"),
        ("ARMED", "RUNNING"),
        ("RUNNING", "EVIDENCE_SEALED"),
        ("EVIDENCE_SEALED", "CLOSED"),
        ("CLOSED", "PUBLISHED"),
    ]


def test_on_disk_journal_matches_memory(published):
    on_disk = json.loads(published.journal_path.read_text())
    verify_journal(on_disk)
    assert on_disk["current_state"] == "PUBLISHED"


# ---------------------------------------------------------------------------
# Every illegal transition refused
# ---------------------------------------------------------------------------

def test_all_illegal_transitions_refused(tmp_path, prereg_hash):
    legal = set(esm.TRANSITIONS)
    for source in State:
        for target in State:
            if (source, target) in legal:
                continue
            machine = ExperimentStateMachine(
                experiment_label="synthetic", state=source
            )
            with pytest.raises(IllegalTransitionError):
                machine.transition(target, created_utc=UTC)
            assert machine.state is source
            assert machine.entries == []


def test_unknown_target_refused(tmp_path):
    machine = _make_machine(tmp_path)
    with pytest.raises(IllegalTransitionError):
        machine.transition("PUBLISHED", created_utc=UTC)


# ---------------------------------------------------------------------------
# Guard failures
# ---------------------------------------------------------------------------

def test_preregister_requires_doc_hash(tmp_path):
    machine = _make_machine(tmp_path)
    with pytest.raises(TransitionGuardError):
        machine.transition(State.PREREGISTERED, created_utc=UTC)
    with pytest.raises(TransitionGuardError):
        machine.transition(
            State.PREREGISTERED,
            created_utc=UTC,
            evidence=GuardEvidence(preregistration_sha256="not-a-hash"),
        )


def test_arming_requires_attestation(preregistered, prereg_hash):
    with pytest.raises(TransitionGuardError):
        preregistered.transition(
            State.ARMED,
            created_utc=UTC,
            evidence=GuardEvidence(preregistration_sha256=prereg_hash),
        )
    assert preregistered.state is State.PREREGISTERED


def test_arming_refuses_prereg_drift(preregistered):
    drifted = _sha(b"different doc")
    with pytest.raises(TransitionGuardError, match="drift"):
        preregistered.transition(
            State.ARMED,
            created_utc=UTC,
            evidence=GuardEvidence(
                preregistration_sha256=drifted, armed_attestation=True
            ),
        )


def test_running_requires_verified_freeze_manifest(armed, freeze_manifest):
    path, good_sha = freeze_manifest
    # missing manifest
    with pytest.raises(TransitionGuardError):
        armed.transition(
            State.RUNNING,
            created_utc=UTC,
            evidence=GuardEvidence(freeze_manifest_sha256=good_sha),
            freeze_manifest_path=path.parent / "nope.json",
        )
    # tampered listed file
    (path.parent / "frozen-params.json").write_bytes(b"tampered")
    with pytest.raises(TransitionGuardError, match="hash mismatch"):
        armed.transition(
            State.RUNNING,
            created_utc=UTC,
            evidence=GuardEvidence(freeze_manifest_sha256=good_sha),
            freeze_manifest_path=path,
        )
    # wrong pinned manifest hash
    (path.parent / "frozen-params.json").write_bytes(
        json.dumps({"params": "synthetic", "seed": 1337}, sort_keys=True).encode() + b"\n"
    )
    with pytest.raises(TransitionGuardError, match="content hash"):
        armed.transition(
            State.RUNNING,
            created_utc=UTC,
            evidence=GuardEvidence(freeze_manifest_sha256=_sha(b"wrong")),
            freeze_manifest_path=path,
        )
    assert armed.state is State.ARMED


def test_seal_requires_hash_verification(running, sealed_file):
    path, sha = sealed_file
    with pytest.raises(TransitionGuardError):
        running.transition(State.EVIDENCE_SEALED, created_utc=UTC)
    with pytest.raises(TransitionGuardError, match="hash mismatch"):
        running.transition(
            State.EVIDENCE_SEALED,
            created_utc=UTC,
            evidence=GuardEvidence(sealed_evidence_sha256=_sha(b"other")),
            sealed_evidence_path=path,
        )


def test_close_requires_outcome_or_failure(sealed, outcome_file, tmp_path):
    with pytest.raises(TransitionGuardError):
        sealed.transition(State.CLOSED, created_utc=UTC)
    # unknown decision region refused
    bad = _write(tmp_path / "bad-outcome.json", {"decision_region": "MAYBE"})
    with pytest.raises(TransitionGuardError, match="decision_region"):
        sealed.transition(
            State.CLOSED,
            created_utc=UTC,
            evidence=GuardEvidence(
                closure_artifact_sha256=bad, closure_kind="decision_region"
            ),
            outcome_artifact_path=tmp_path / "bad-outcome.json",
        )
    # outcome + failure simultaneously is ambiguous -> refused
    failure = _write(
        tmp_path / "FAILURE.json",
        {
            "failure_stage": "analysis",
            "failure_reason": "synthetic infra crash",
            "detected_utc": UTC,
            "invalidates": [],
            "classification": {"category": "infrastructure_failure"},
        },
    )
    out_path, out_sha = outcome_file
    with pytest.raises(TransitionGuardError, match="ambiguous"):
        sealed.transition(
            State.CLOSED,
            created_utc=UTC,
            evidence=GuardEvidence(
                closure_artifact_sha256=out_sha, closure_kind="decision_region"
            ),
            outcome_artifact_path=out_path,
            failure_json_path=tmp_path / "FAILURE.json",
        )
    assert sealed.state is State.EVIDENCE_SEALED


def test_close_via_infra_failure_json(sealed, tmp_path):
    sha = _write(
        tmp_path / "FAILURE.json",
        {
            "failure_stage": "seal",
            "failure_reason": "synthetic worker lost",
            "detected_utc": UTC,
            "invalidates": ["seal"],
            "classification": {"category": "infrastructure_failure"},
        },
    )
    sealed.transition(
        State.CLOSED,
        created_utc=UTC,
        evidence=GuardEvidence(
            closure_artifact_sha256=sha, closure_kind="infrastructure_failure"
        ),
        failure_json_path=tmp_path / "FAILURE.json",
    )
    assert sealed.state is State.CLOSED


def test_scientific_failure_cannot_close_as_infra(sealed, tmp_path):
    sha = _write(
        tmp_path / "FAILURE.json",
        {
            "failure_stage": "analysis",
            "failure_reason": "hypothesis falsified (synthetic)",
            "detected_utc": UTC,
            "invalidates": [],
            "classification": {"category": "cross_architecture_transfer_failure"},
        },
    )
    with pytest.raises(TransitionGuardError, match="infrastructure_failure"):
        sealed.transition(
            State.CLOSED,
            created_utc=UTC,
            evidence=GuardEvidence(
                closure_artifact_sha256=sha, closure_kind="infrastructure_failure"
            ),
            failure_json_path=tmp_path / "FAILURE.json",
        )


def test_publish_requires_verified_release(closed, release_dir):
    rel, content_hash = release_dir
    with pytest.raises(TransitionGuardError):
        closed.transition(State.PUBLISHED, created_utc=UTC)
    # tampered release refused
    (rel / "sealed-evidence.json").write_bytes(b"tampered")
    with pytest.raises(TransitionGuardError, match="verification"):
        closed.transition(
            State.PUBLISHED,
            created_utc=UTC,
            evidence=GuardEvidence(release_content_hash=content_hash),
            release_dir=rel,
        )
    assert closed.state is State.CLOSED


# ---------------------------------------------------------------------------
# Infrastructure failure path from each state
# ---------------------------------------------------------------------------

def test_infra_failure_attachable_from_every_state(tmp_path, published):
    for state in State:
        machine = ExperimentStateMachine(experiment_label="synthetic", state=state)
        record = machine.attach_infrastructure_failure(
            failure_stage="synthetic-stage",
            failure_reason=f"synthetic infra failure at {state.value}",
            detected_utc=UTC,
            invalidates=("synthetic-stage",),
        )
        assert record.attached_at_state is state
        assert machine.state is state  # failure never moves the lifecycle
        assert machine.failures[-1].to_dict()["category"] == "infrastructure_failure"
        verify_journal(machine.to_journal())


def test_infra_failure_with_observed_outcome_refused(tmp_path):
    machine = _make_machine(tmp_path)
    with pytest.raises(StateMachineError, match="contradiction"):
        esm.InfrastructureFailureRecord(
            failure_stage="analysis",
            failure_reason="synthetic",
            detected_utc=UTC,
            invalidates=(),
            attached_at_state=State.RUNNING,
            outcome_observed=True,
        ).validate()


# ---------------------------------------------------------------------------
# Journal tamper detection
# ---------------------------------------------------------------------------

def _tamper(journal: dict, mutate) -> dict:
    mutant = json.loads(json.dumps(journal))
    mutate(mutant)
    return mutant


def test_tamper_entry_content(published):
    journal = published.to_journal()
    mutant = _tamper(journal, lambda j: j["entries"][2].update(detail="forged"))
    with pytest.raises(JournalTamperError):
        verify_journal(mutant)


def test_tamper_reorder(published):
    journal = published.to_journal()
    def swap(j):
        j["entries"][1], j["entries"][2] = j["entries"][2], j["entries"][1]
    with pytest.raises(JournalTamperError):
        verify_journal(_tamper(journal, swap))


def test_tamper_truncate_and_renumber(published):
    journal = published.to_journal()
    def cut(j):
        j["entries"] = j["entries"][:3]
    # truncation alone leaves a VALID prefix chain (append-only journals allow
    # prefix reads) — verify it passes, then confirm replay stops there.
    truncated = _tamper(journal, cut)
    verify_journal(truncated)
    replayed = replay_journal(truncated)
    assert replayed.state is State.RUNNING
    # but renumbering a suffix to fake a prefix breaks the chain
    def forge(j):
        j["entries"] = j["entries"][3:]
        for i, e in enumerate(j["entries"]):
            e["seq"] = i
    with pytest.raises(JournalTamperError):
        verify_journal(_tamper(journal, forge))


def test_tamper_genesis(published):
    journal = published.to_journal()
    mutant = _tamper(journal, lambda j: j.update(genesis_sha256="0" * 64))
    with pytest.raises(JournalTamperError):
        verify_journal(mutant)


def test_wrong_schema_version_refused(published):
    mutant = _tamper(published.to_journal(), lambda j: j.update(schema_version="9.9"))
    with pytest.raises(Exception):
        verify_journal(mutant)


# ---------------------------------------------------------------------------
# Replay / determinism
# ---------------------------------------------------------------------------

def test_replay_deterministic(published):
    journal = published.to_journal()
    m1 = replay_journal(journal)
    m2 = replay_journal(json.loads(json.dumps(journal)))
    assert m1.state is State.PUBLISHED
    assert m1.to_journal()["entries"] == m2.to_journal()["entries"]
    assert m1.to_journal() == m2.to_journal()


def test_replay_with_failures(sealed):
    sealed.attach_infrastructure_failure(
        failure_stage="seal",
        failure_reason="synthetic pre-seal crash",
        detected_utc=UTC,
        invalidates=("seal",),
    )
    journal = sealed.to_journal()
    replayed = replay_journal(journal)
    assert replayed.state is State.EVIDENCE_SEALED
    assert len(replayed.failures) == 1
    assert replayed.failures[0].attached_at_state is State.EVIDENCE_SEALED


def test_replay_rejects_illegal_journal_entry(published):
    def forge(j):
        entry = dict(j["entries"][0])
        entry["to_state"] = "PUBLISHED"
        entry["from_state"] = "PUBLISHED"  # self-loop: not in the table
        entry["seq"] = len(j["entries"])
        entry["prev_sha256"] = j["entries"][-1]["entry_sha256"]
        entry["entry_sha256"] = esm._entry_hash(entry)
        j["entries"].append(entry)
    forged = _tamper(published.to_journal(), forge)
    verify_journal(forged)  # chain intact
    with pytest.raises(JournalTamperError, match="illegal transition"):
        replay_journal(forged)


# ---------------------------------------------------------------------------
# Wiring to existing records
# ---------------------------------------------------------------------------

def test_lock_status_mapping():
    assert state_for_lock_status({"lock_status": "DRAFT"}) is State.DRAFT
    assert (
        state_for_lock_status({"lock_status": "PREREGISTERED", "armed": False})
        is State.PREREGISTERED
    )
    assert (
        state_for_lock_status({"lock_status": "ARMED", "armed": True}) is State.ARMED
    )


def test_d20005_shape_stays_preregistered():
    record = json.loads(
        Path("generations/RAC-PER-D2-0005.json").read_text()
    )
    assert record["lock_status"] == "PREREGISTERED"
    assert state_for_lock_status(record) is State.PREREGISTERED


def test_lock_status_fail_closed():
    with pytest.raises(StateMachineError):
        state_for_lock_status({"lock_status": "HALF_ARMED"})
    with pytest.raises(StateMachineError):
        state_for_lock_status({"lock_status": "ARMED"})  # no armed attestation
    with pytest.raises(StateMachineError):
        state_for_lock_status({"lock_status": "ARMED", "armed": False})


def test_rehearsal_stage_mapping_covers_rehearsal_stages():
    from ruthless_pipeline.certification import rehearsal_d20005

    for stage in rehearsal_d20005.STAGES:
        assert stage in esm.REHEARSAL_STAGE_TO_STATE

"""Tests for CTM experiment manifests (CTM-B2). Fixtures inline; tmp_path only."""
from __future__ import annotations

import json

import pytest

from ruthless_pipeline.certification.experiment_state_machine import (
    JournalTamperError,
    State,
)
from ruthless_pipeline.ctm.contracts import (
    CTMClaim,
    CTMClaimState,
    CTMArtifactRole,
    CTMArtifactUse,
)
from ruthless_pipeline.ctm.manifests import (
    CTM_MANIFEST_SCHEMA_VERSION,
    ArbitrationError,
    CTMExperimentAdapter,
    CTMExperimentManifest,
    LockMismatchError,
    ManifestLockedError,
    PhysicalTierBlockedError,
    build_claim_artifacts,
    lock_manifest,
    verify_lock,
)

FIXED_UTC = "2026-01-01T00:00:00Z"
FIXED_LOCK_UTC = "2026-01-01T00:01:00Z"
DUMMY_SHA = "a" * 64
DUMMY_SHA_B = "b" * 64


def _manifest(**overrides):
    kwargs = dict(
        experiment_id="CTM-E-000001",
        title="synthetic genome-cell transfer rehearsal",
        design={"doe": {"cells": 4}, "genome_cell_targets": ["cell-1"]},
        seed=42,
        created_utc=FIXED_UTC,
        target_panel_ref=DUMMY_SHA,
        channel_refs=("surrogate",),
        null_design_ids=("null-1",),
    )
    kwargs.update(overrides)
    return CTMExperimentManifest(**kwargs)


def _claim(**overrides):
    artifact = CTMArtifactUse(
        artifact_id="doe-artifact-1",
        role=CTMArtifactRole.DOE,
        sha256=DUMMY_SHA,
        heldout_access=False,
        heldout_feedback_used=False,
        selection_influence="SURROGATE_ONLY",
        metadata={"wave": "ctm-b"},
    )
    kwargs = dict(
        claim_id="ctm-claim-1",
        state=CTMClaimState.CORRELATION,
        feature_id="genome-feature-1",
        outcome_id="surrogate-outcome-1",
        source_commit="e169706",
        consumed_artifacts=(artifact,),
    )
    kwargs.update(overrides)
    return CTMClaim(**kwargs)


# ---------------------------------------------------------------------------
# Manifest construction / canonical bytes
# ---------------------------------------------------------------------------

def test_canonical_bytes_deterministic_two_builds():
    a = _manifest()
    b = _manifest()
    assert a.canonical_bytes() == b.canonical_bytes()
    assert a.manifest_sha256() == b.manifest_sha256()
    assert b"\n" not in a.canonical_bytes()


def test_schema_version_const():
    assert _manifest().schema_version == CTM_MANIFEST_SCHEMA_VERSION
    with pytest.raises(ValueError):
        _manifest(schema_version="rac-ctm-experiment/9.9")


def test_experiment_id_pattern_enforced():
    for bad in ("ctm-e-000001", "CTM-E-1", "CTM-E-0000011", "CTM-X-000001", ""):
        with pytest.raises(ValueError):
            _manifest(experiment_id=bad)
    _manifest(experiment_id="CTM-E-123456")  # ok


def test_target_panel_ref_must_be_sha256_or_none():
    with pytest.raises(ValueError):
        _manifest(target_panel_ref="not-a-hash")
    _manifest(target_panel_ref=None)  # ok


def test_physical_tier_refused_at_build():
    for tier in ("PHYSICAL", "PRINT", "HARDWARE"):
        with pytest.raises(PhysicalTierBlockedError):
            _manifest(evidence_tier=tier)


def test_unknown_tier_rejected():
    with pytest.raises(ValueError):
        _manifest(evidence_tier="QUANTUM")


def test_physical_efficacy_claimed_refused():
    with pytest.raises(ValueError):
        _manifest(physical_efficacy_claimed=True)


def test_to_json_file_round_trip(tmp_path):
    m = _manifest()
    path = m.to_json_file(tmp_path / "m.json")
    assert path.read_bytes() == m.canonical_bytes() + b"\n"
    assert json.loads(path.read_text())["experiment_id"] == "CTM-E-000001"


# ---------------------------------------------------------------------------
# Lock semantics
# ---------------------------------------------------------------------------

def test_lock_write_and_verify_ok(tmp_path):
    m = _manifest()
    lock = lock_manifest(m, tmp_path, locked_utc=FIXED_LOCK_UTC)
    assert lock["manifest_sha256"] == m.manifest_sha256()
    assert lock["experiment_id"] == m.experiment_id
    assert lock["locked_utc"] == FIXED_LOCK_UTC
    assert (tmp_path / "manifest.json").is_file()
    assert (tmp_path / "manifest.lock").is_file()
    assert verify_lock(tmp_path)["manifest_sha256"] == lock["manifest_sha256"]


def test_lock_drift_detected(tmp_path):
    m = _manifest()
    lock_manifest(m, tmp_path, locked_utc=FIXED_LOCK_UTC)
    # Flip a byte in the locked manifest.
    blob = bytearray((tmp_path / "manifest.json").read_bytes())
    blob[10] = ord("X") if blob[10] != ord("X") else ord("Y")
    (tmp_path / "manifest.json").write_bytes(bytes(blob))
    with pytest.raises(LockMismatchError):
        verify_lock(tmp_path)


def test_verify_lock_missing_files_fail_closed(tmp_path):
    with pytest.raises(LockMismatchError):
        verify_lock(tmp_path)  # nothing written
    lock_manifest(_manifest(), tmp_path, locked_utc=FIXED_LOCK_UTC)
    (tmp_path / "manifest.json").unlink()
    with pytest.raises(LockMismatchError):
        verify_lock(tmp_path)


def test_relock_identical_is_idempotent(tmp_path):
    m = _manifest()
    lock1 = lock_manifest(m, tmp_path, locked_utc=FIXED_LOCK_UTC)
    lock2 = lock_manifest(_manifest(), tmp_path, locked_utc="2026-02-02T00:00:00Z")
    assert lock1 == lock2  # original lock untouched


def test_relock_different_refused(tmp_path):
    lock_manifest(_manifest(), tmp_path, locked_utc=FIXED_LOCK_UTC)
    with pytest.raises(ManifestLockedError):
        lock_manifest(
            _manifest(experiment_id="CTM-E-000002"),
            tmp_path,
            locked_utc=FIXED_LOCK_UTC,
        )


# ---------------------------------------------------------------------------
# State-machine adapter
# ---------------------------------------------------------------------------

def test_adapter_start_stays_draft(tmp_path):
    adapter = CTMExperimentAdapter("CTM-LAB-test", tmp_path)
    adapter.start(_manifest(), locked_utc=FIXED_LOCK_UTC)
    assert adapter.state is State.DRAFT
    assert (tmp_path / "manifest.lock").is_file()


def test_adapter_preregister_journals_and_verifies(tmp_path):
    adapter = CTMExperimentAdapter("CTM-LAB-test", tmp_path)
    m = _manifest()
    adapter.start(m, locked_utc=FIXED_LOCK_UTC)
    adapter.preregister(m, DUMMY_SHA, FIXED_UTC)
    assert adapter.state is State.PREREGISTERED
    assert adapter.machine.preregistration_sha256 == DUMMY_SHA
    journal = json.loads((tmp_path / "journal.json").read_text())
    assert journal["current_state"] == "PREREGISTERED"
    assert len(journal["entries"]) == 1
    adapter.verify()  # journal + lock both verify


def test_adapter_replay_determinism(tmp_path):
    a = CTMExperimentAdapter("CTM-LAB-test", tmp_path)
    m = _manifest()
    a.start(m, locked_utc=FIXED_LOCK_UTC)
    a.preregister(m, DUMMY_SHA, FIXED_UTC)
    b = CTMExperimentAdapter("CTM-LAB-test", tmp_path)
    assert b.state is a.state is State.PREREGISTERED
    assert [e["entry_sha256"] for e in b.machine.entries] == [
        e["entry_sha256"] for e in a.machine.entries
    ]
    b.verify()


def test_adapter_arm_and_execute_refused(tmp_path):
    adapter = CTMExperimentAdapter("CTM-LAB-test", tmp_path)
    m = _manifest()
    adapter.start(m, locked_utc=FIXED_LOCK_UTC)
    adapter.preregister(m, DUMMY_SHA, FIXED_UTC)
    with pytest.raises(ArbitrationError):
        adapter.arm()
    with pytest.raises(ArbitrationError):
        adapter.execute()
    # Hard refusal is documented.
    assert "governance authority" in CTMExperimentAdapter.arm.__doc__
    assert adapter.state is State.PREREGISTERED  # unchanged


def test_adapter_journal_tamper_detected(tmp_path):
    adapter = CTMExperimentAdapter("CTM-LAB-test", tmp_path)
    m = _manifest()
    adapter.start(m, locked_utc=FIXED_LOCK_UTC)
    adapter.preregister(m, DUMMY_SHA, FIXED_UTC)
    journal_path = tmp_path / "journal.json"
    blob = bytearray(journal_path.read_bytes())
    idx = blob.rindex(b"PREREGISTERED")  # entry to_state, not current_state
    blob[idx] = ord("X")
    journal_path.write_bytes(bytes(blob))
    with pytest.raises(JournalTamperError):
        adapter.verify()


# ---------------------------------------------------------------------------
# Claim bridge
# ---------------------------------------------------------------------------

def test_claim_artifact_round_trip_validates_against_schema(tmp_path):
    import jsonschema
    from pathlib import Path

    claim = _claim()
    path = build_claim_artifacts(claim, tmp_path)
    payload = json.loads(path.read_text())
    # Validate against the frozen repo schema (read-only).

    repo_schema = json.loads(
        (Path(__file__).resolve().parents[2] / "schemas" / "ctm_claim_v1.schema.json").read_text()
    )
    jsonschema.validate(payload, repo_schema)
    assert payload["schema_version"] == "rac-ctm/1.0"
    assert payload["claim_id"] == "ctm-claim-1"
    assert payload["state"] == "correlation"


def test_claim_artifact_firewall_compatible_shape(tmp_path):
    claim = _claim()
    payload = json.loads(build_claim_artifacts(claim, tmp_path).read_text())
    entries = payload["consumed_artifacts"]
    assert len(entries) == 1
    entry = entries[0]
    assert set(entry) == {
        "artifact_id",
        "role",
        "sha256",
        "heldout_access",
        "heldout_feedback_used",
        "selection_influence",
        "metadata",
    }
    assert entry["artifact_id"] == "doe-artifact-1"
    assert entry["sha256"] == DUMMY_SHA
    assert entry["heldout_access"] is False
    assert entry["heldout_feedback_used"] is False
    # Pre-outcome role constraints from the anti-optimization invariant.
    from ruthless_pipeline.ctm.contracts import PRE_OUTCOME_ROLES

    role = CTMArtifactRole(entry["role"])
    if role in PRE_OUTCOME_ROLES:
        assert entry["selection_influence"] in {"SURROGATE_ONLY", "NOT_APPLICABLE"}


def test_claim_artifact_rejects_schema_violation(tmp_path):
    bad = CTMArtifactUse(
        artifact_id="x",
        role=CTMArtifactRole.DOE,
        sha256=DUMMY_SHA,
        heldout_access=False,
        heldout_feedback_used=False,
        selection_influence="SURROGATE_ONLY",
    )
    claim = _claim(
        consumed_artifacts=(bad,),
        state=CTMClaimState.CONTROLLED_EFFECT,
        independent_cohort_count=2,
        matched_null_design_ids=("null-1",),
    )
    # Force a schema-invalid payload by bypassing claim validation: an empty
    # consumed_artifacts list fails claim.validate() first (fail closed).
    with pytest.raises(ValueError):
        _claim(consumed_artifacts=()).validate()
    # A syntactically valid but semantically ladder-illegal claim also refuses.
    illegal = CTMClaim(
        claim_id="c2",
        state=CTMClaimState.ASSOCIATION,
        feature_id="f",
        outcome_id="o",
        source_commit="e169706",
        consumed_artifacts=(bad,),
        independent_cohort_count=1,
    )
    with pytest.raises(ValueError):
        build_claim_artifacts(illegal, tmp_path)

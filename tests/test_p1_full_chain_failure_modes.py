"""Deliberate-failure modes for scripts/p1_full_chain_dry_run.py.

Each test injects one failure class into the synthetic full chain and asserts
the pipeline rejects it fail-closed:

* calibration failure (acceptance must gate the chain),
* capture hash-chain break (sealed-session hash verification must trip),
* promotion attempt of synthetic evidence into the P1 trial store / release
  export path (the non-promotion invariant),
* cumulative-store contract violations on resume (schema version, replayed
  trials).

Nothing here promotes synthetic artifacts: the final stdout contract line
remains "RESULT: synthetic_pipeline_validation_only — not RAC evidence".
"""

import hashlib
import json
from pathlib import Path

import pytest

import scripts.ingest_capture_inference as ici
import scripts.p1_full_chain_dry_run as dryrun
from scripts.export_physical_release import build_release
from scripts.ingest_capture_inference import enforce_promotion_gate
from ruthless_pipeline.certification.schema_version import SchemaVersionError

EVIDENCE_CLASS = dryrun.EVIDENCE_CLASS


def test_calibration_failure_aborts_chain(monkeypatch, tmp_path: Path) -> None:
    """A failing calibration acceptance must stop the chain before any
    downstream artifact is produced."""

    class FailingProfile:
        profile_id = "SYNTHETIC-CALIBRATION-FAILING"

        def acceptance(self):
            return False, ["injected calibration failure"]

        def to_profile_json(self) -> str:
            return json.dumps({"profile_id": self.profile_id})

    monkeypatch.setattr(dryrun, "build_synthetic_calibration_profile", lambda: FailingProfile())
    with pytest.raises(RuntimeError, match="synthetic calibration must pass"):
        dryrun.run_chain(tmp_path / "run")


def test_capture_hash_chain_break_aborts_chain(monkeypatch, tmp_path: Path) -> None:
    """Corrupting one sealed capture after session build must trip the
    session hash-verification gate."""
    original = dryrun.build_capture_session

    def corrupted(output_dir, created_utc):
        session, sha = original(output_dir, created_utc)
        target = Path(output_dir) / "captures" / "control" / "still-00.png"
        blob = bytearray(target.read_bytes())
        blob[-1] ^= 0xFF
        target.write_bytes(bytes(blob))
        return session, sha

    monkeypatch.setattr(dryrun, "build_capture_session", corrupted)
    with pytest.raises(RuntimeError, match="sealed\\+clean"):
        dryrun.run_chain(tmp_path / "run")


def test_resume_with_wrong_store_schema_version_rejected(tmp_path: Path) -> None:
    """A pre-existing cumulative store with an unsupported schema_version
    fails closed on resume."""
    store_path = tmp_path / "store.json"
    store_path.write_text(json.dumps({"schema_version": "9.9", "trials": []}))
    with pytest.raises(SchemaVersionError, match="cumulative trial store"):
        dryrun.append_to_trial_store(store_path, [])


def test_replayed_trial_rejected_on_append(tmp_path: Path) -> None:
    out = tmp_path / "run"
    dryrun.run_chain(out)
    store = json.loads((out / "trial-store.json").read_text())
    records = store["trials"]
    store_path = tmp_path / "replay.json"
    store_path.write_text((out / "trial-store.json").read_text())
    with pytest.raises(ValueError, match="duplicate trial"):
        dryrun.append_to_trial_store(store_path, [records[0]])


def test_synthetic_session_cannot_pass_promotion_gate(tmp_path: Path) -> None:
    """The chain's own session (calibration passing, sealed) is still
    non-promotable: synthetic evidence_class is a hard stop."""
    out = tmp_path / "run"
    dryrun.run_chain(out)
    session = json.loads((out / "capture-session.json").read_text())
    assert session["evidence_class"] == EVIDENCE_CLASS
    assert session["calibration_pass"] is True
    with pytest.raises(ValueError, match="promotion gate"):
        enforce_promotion_gate(session)


def test_synthetic_trials_rejected_by_p1_release_export(tmp_path: Path) -> None:
    """Promotion attempt end to end: wrapping the synthetic chain's trials
    into a P1 trial store and exporting a release fails at the store gate,
    and no release directory is created."""
    out = tmp_path / "run"
    dryrun.run_chain(out)
    session = json.loads((out / "capture-session.json").read_text())
    store_path = tmp_path / "p1-store.jsonl"
    inference = {"result_sha256": hashlib.sha256(b"synthetic").hexdigest()}
    prev_sha = None
    for record in json.loads((out / "trial-store.json").read_text())["trials"]:
        trial = dryrun._trial_from_store_record(record)
        line = ici.trial_store_record(trial, session, inference, {}, prev_sha)
        ici.append_trial_store(store_path, line)
        prev_sha = hashlib.sha256(ici.canonical(line)).hexdigest()
    with pytest.raises(ValueError, match="promotion gate"):
        build_release(
            store_path,
            tmp_path / "calibration.json",
            dryrun.EXPERIMENT_ID,
            tmp_path / "releases",
            "2026-01-01T00:00:00Z",
            Path("physical/p1/STOPPING_RULE.json"),
            bootstrap_resamples=8,
        )
    assert not (tmp_path / "releases").exists()


def test_non_promotion_invariants_pinned(tmp_path: Path) -> None:
    """Pin the labels that keep synthetic output out of RAC evidence."""
    assert EVIDENCE_CLASS == "synthetic_pipeline_validation_only"
    assert dryrun.RESULT_LINE == "RESULT: synthetic_pipeline_validation_only — not RAC evidence"
    out = tmp_path / "run"
    summary = dryrun.run_chain(out)
    assert summary["rac_evidence_eligible"] is False
    store = json.loads((out / "trial-store.json").read_text())
    assert store["evidence_class"] == EVIDENCE_CLASS
    assert store["rac_evidence_eligible"] is False
    statistics = json.loads((out / "statistics.json").read_text())
    assert statistics["physical_evidence_eligible"] is False
    validation = json.loads((out / "validation.json").read_text())
    assert validation["physical_evidence_eligible"] is False
    release = json.loads((out / "release" / dryrun.EXPERIMENT_ID / "RELEASE.json").read_text())
    assert release["evidence_class"] == EVIDENCE_CLASS
    assert release["rac_evidence_eligible"] is False

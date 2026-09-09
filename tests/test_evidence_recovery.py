"""Failure-injection tests for evidence_recovery + scripts/recover_evidence.

All runs are the synthetic D2-0005 rehearsal (labelled
synthetic_pipeline_validation_only); no generation record is touched.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ruthless_pipeline.certification import evidence_recovery as er
from ruthless_pipeline.certification import rehearsal_d20005 as rehearsal
from ruthless_pipeline.certification.evidence_recovery import (
    InferenceRefusalError,
    RecoveryError,
    ScientificEvidenceError,
    StageStatus,
    UnsafeWriteError,
    assert_safe_write,
    classify_run,
    recover_run,
    refuse_inference_stage,
)

ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _full_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    rehearsal.run_rehearsal(run)
    return run


def _partial_run(tmp_path: Path, crash_after: str) -> Path:
    run = tmp_path / "run"
    with pytest.raises(rehearsal.RehearsalCrash):
        rehearsal.run_rehearsal(run, crash_after=crash_after)
    return run


def _snapshot_science(run: Path) -> dict[str, str]:
    names = (
        "fixture-manifest.json",
        "selection-report.json",
        "frozen-telemetry.json",
        "analysis.json",
        "cluster-outcomes.json",
        "sealed-evidence.json",
    )
    return {name: _sha(run / name) for name in names}


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def test_full_run_all_done(tmp_path):
    report = classify_run(_full_run(tmp_path))
    assert all(
        info["status"] == StageStatus.DONE.value
        for info in report["stages"].values()
    )


def test_partial_run_classification(tmp_path):
    run = _partial_run(tmp_path, "seal")
    report = classify_run(run)
    stages = report["stages"]
    for stage in ("fixture", "selection", "freeze", "analysis", "seal"):
        assert stages[stage]["status"] == StageStatus.DONE.value
    for stage in ("release", "export"):
        assert stages[stage]["status"] == StageStatus.INCOMPLETE.value
        assert stages[stage]["recoverable"] is True


# ---------------------------------------------------------------------------
# Recovery of non-scientific stages
# ---------------------------------------------------------------------------

def test_recover_after_crash_before_publication(tmp_path):
    """Crash after seal: publication + report/export resume, science intact."""
    run = _partial_run(tmp_path, "seal")
    science_before = _snapshot_science(run)
    journal_before = (run / "rehearsal_journal.json").read_bytes()

    report = recover_run(run)

    assert report["recovered"] == ["release", "export"]
    assert report["complete"] is True
    # sealed scientific evidence byte-identical
    assert _snapshot_science(run) == science_before
    # the journal only gained non-scientific entries
    journal = json.loads((run / "rehearsal_journal.json").read_text())
    assert journal["completed_stages"] == list(rehearsal.STAGES)
    assert len(journal_before) < len((run / "rehearsal_journal.json").read_bytes())


def test_recover_broken_artifact_upload(tmp_path):
    """Failure injection: a release file lost during upload -> rebuild."""
    run = _full_run(tmp_path)
    lost = run / "release" / rehearsal.RELEASE_ID / "sealed-evidence.json"
    lost.unlink()
    report = classify_run(run)
    assert report["stages"]["release"]["status"] == StageStatus.CORRUPT.value

    result = recover_run(run)
    assert result["complete"] is True
    # export is downstream of the corrupt stage, so it is rolled back and
    # rebuilt too (journal ordering is never violated)
    assert result["recovered"] == ["release", "export"]
    verify = rehearsal.verify_release_dir(run / "release" / rehearsal.RELEASE_ID)
    assert verify.ok


def test_recover_broken_status_publication(tmp_path):
    """Failure injection: RELEASE.json (status publication) corrupted."""
    run = _full_run(tmp_path)
    status = run / "release" / rehearsal.RELEASE_ID / "RELEASE.json"
    status.write_text('{"forged": true}\n')
    report = classify_run(run)
    assert report["stages"]["release"]["status"] == StageStatus.CORRUPT.value
    result = recover_run(run)
    assert result["complete"] is True


def test_recover_broken_report_generation(tmp_path):
    """Failure injection: report/export artifacts deleted -> rebuilt."""
    run = _full_run(tmp_path)
    (run / "export_synthetic" / "paper5_arms_rehearsal_synthetic.csv").unlink()
    report = classify_run(run)
    assert report["stages"]["export"]["status"] == StageStatus.CORRUPT.value
    result = recover_run(run)
    assert result["recovered"] == ["export"]
    assert result["complete"] is True


def test_dry_run_writes_nothing(tmp_path):
    run = _partial_run(tmp_path, "seal")
    before = {p: _sha(p) for p in run.rglob("*") if p.is_file()}
    report = recover_run(run, dry_run=True)
    assert report["dry_run"] is True
    assert report["recovered"] == []
    assert [a["stage"] for a in report["actions"]] == ["release", "export"]
    after = {p: _sha(p) for p in run.rglob("*") if p.is_file()}
    assert before == after


# ---------------------------------------------------------------------------
# Hard refusals
# ---------------------------------------------------------------------------

def test_missing_scientific_file_fails_closed(tmp_path):
    """Missing analysis.json on a DONE scientific stage: refuse to recover."""
    run = _partial_run(tmp_path, "seal")
    (run / "analysis.json").unlink()
    with pytest.raises(ScientificEvidenceError, match="corrupt"):
        recover_run(run)
    # sealed evidence itself untouched and still verifies
    journal = json.loads((run / "rehearsal_journal.json").read_text())
    assert "release" not in journal["completed_stages"]


def test_hash_mismatch_on_sealed_evidence_refused(tmp_path):
    run = _partial_run(tmp_path, "seal")
    sealed = run / "sealed-evidence.json"
    sealed.write_bytes(sealed.read_bytes() + b"tamper")
    with pytest.raises(ScientificEvidenceError):
        recover_run(run)


def test_unfinished_scientific_stage_raises_inference_refusal(tmp_path):
    """Crash before seal: resuming 'analysis' would re-run the benchmark."""
    run = _partial_run(tmp_path, "freeze")
    with pytest.raises(InferenceRefusalError, match="scientific"):
        recover_run(run)


@pytest.mark.parametrize(
    "stage",
    ["inference", "model_load", "benchmark", "candidate_generation",
     "generation", "fixture", "selection", "freeze", "analysis", "seal"],
)
def test_inference_tokens_always_refused(stage):
    with pytest.raises(InferenceRefusalError):
        refuse_inference_stage(stage)


@pytest.mark.parametrize(
    "stage", ["release", "publication", "packaging", "report", "export",
              "status_publication", "artifact_upload"],
)
def test_recoverable_stages_not_refused(stage):
    refuse_inference_stage(stage)  # must not raise
    assert er.stage_is_recoverable(stage)


def test_never_writes_generations(tmp_path):
    with pytest.raises(UnsafeWriteError):
        assert_safe_write(Path("/repo/generations/RAC-PER-D2-0005.json"))
    with pytest.raises(UnsafeWriteError):
        assert_safe_write(Path("/repo/manuscript/exports/x.csv"))
    with pytest.raises(UnsafeWriteError):
        recover_run(tmp_path / "generations" / "run")


def test_recovery_does_not_touch_generation_records(tmp_path):
    """Repo generation records are byte-identical after a full recovery."""
    gen_files = sorted((ROOT / "generations").glob("*.json"))
    before = {p.name: _sha(p) for p in gen_files}
    run = _partial_run(tmp_path, "seal")
    recover_run(run)
    after = {p.name: _sha(p) for p in gen_files}
    assert before == after


def test_unregistered_recoverable_stage_errors(tmp_path):
    run = _full_run(tmp_path)
    stages = rehearsal.STAGES + ("publication",)
    with pytest.raises(RecoveryError, match="no rebuilder"):
        recover_run(run, stages=stages, rebuilders={})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "recover_evidence.py"), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_cli_recovers_partial_run(tmp_path):
    run = _partial_run(tmp_path, "seal")
    proc = _cli("--run-dir", str(run))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    report = json.loads(proc.stdout.split("RESULT:")[0])
    assert report["complete"] is True
    assert "synthetic_pipeline_validation_only" in proc.stdout


def test_cli_refusal_exit_code(tmp_path):
    run = _partial_run(tmp_path, "freeze")
    proc = _cli("--run-dir", str(run))
    assert proc.returncode == 2
    assert "scientific" in proc.stdout


def test_cli_corrupt_science_exit_code(tmp_path):
    run = _full_run(tmp_path)
    (run / "sealed-evidence.json").write_bytes(b"tampered")
    proc = _cli("--run-dir", str(run))
    assert proc.returncode == 1


def test_cli_missing_journal(tmp_path):
    proc = _cli("--run-dir", str(tmp_path / "nope"))
    assert proc.returncode == 1


def test_cli_dry_run(tmp_path):
    run = _partial_run(tmp_path, "seal")
    proc = _cli("--run-dir", str(run), "--dry-run")
    assert proc.returncode == 1  # not complete yet; nothing written
    assert classify_run(run)["stages"]["release"]["status"] == "INCOMPLETE"

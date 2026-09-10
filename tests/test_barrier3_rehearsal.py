from __future__ import annotations

import json
from pathlib import Path

import pytest

from ruthless_pipeline.certification import rehearsal_barrier3 as b3


def _manifest() -> dict:
    return b3.build_default_manifest(run_id="BARRIER3-TEST", root_seed=20260909)


def test_default_manifest_is_synthetic_and_frozen():
    manifest = _manifest()
    assert manifest["evidence_class"] == b3.EVIDENCE_CLASS
    assert manifest["rac_evidence_eligible"] is False
    assert manifest["physical_efficacy_claimed"] is False
    assert manifest["generation_ref"] == "RAC-PER-D2-0005"
    assert manifest["arm_ref"]["heldout_access"] == "identity_hash_only"
    assert manifest["frozen_parameters"] == b3.FROZEN_PARAMETERS
    assert manifest["expected_stage_order"] == list(b3.STAGES)


def test_full_chain_runs_all_six_stages(tmp_path):
    out = tmp_path / "run"
    result = b3.run_rehearsal(out, _manifest())
    assert result["verification_ok"] is True
    assert result["stages"] == list(b3.STAGES)
    report = json.loads((out / "barrier3-report.json").read_text())
    assert report["BARRIER_3_RESULT"] == "PASS"
    assert report["STAGE_COUNT"] == 6
    assert report["HELDOUT_ACCESSED"] is False
    assert report["D2_0005_ARMED"] is False
    assert report["PHYSICAL_EFFICACY_CLAIMED"] is False
    for stage in b3.STAGES:
        assert (out / "stages" / f"{stage}.json").is_file()


def test_replay_is_byte_identical(tmp_path):
    manifest = _manifest()
    first = tmp_path / "a"
    second = tmp_path / "b"
    b3.run_rehearsal(first, manifest)
    b3.run_rehearsal(second, manifest)
    comparison = b3.compare_replays(first, second)
    assert comparison["identical"] is True
    assert comparison["differences"] == []


@pytest.mark.parametrize("stage", b3.STAGES)
def test_crash_after_each_stage_is_resumable_and_fail_closed(tmp_path, stage):
    out = tmp_path / stage
    manifest = _manifest()
    with pytest.raises(b3.RehearsalCrash, match=stage):
        b3.run_rehearsal(out, manifest, crash_after=stage)
    journal = json.loads((out / "rehearsal_journal.json").read_text())
    assert stage in journal["completed"]
    result = b3.run_rehearsal(out, manifest)
    assert result["verification_ok"] is True


def test_tampered_completed_stage_refuses_resume(tmp_path):
    out = tmp_path / "tamper"
    manifest = _manifest()
    with pytest.raises(b3.RehearsalCrash):
        b3.run_rehearsal(out, manifest, crash_after="optimization")
    stage_path = out / "stages" / "optimization.json"
    stage_path.write_text(stage_path.read_text() + "tamper")
    with pytest.raises(b3.ResumeIntegrityError, match="hash mismatch"):
        b3.run_rehearsal(out, manifest)


def test_wrong_frozen_surface_hash_fails_closed(tmp_path):
    manifest = _manifest()
    manifest["frozen_surface_manifest_sha256"] = "0" * 64
    with pytest.raises(b3.Barrier3Error, match="frozen-surface"):
        b3.run_rehearsal(tmp_path / "bad", manifest)


def test_wrong_input_hash_fails_closed(tmp_path):
    manifest = _manifest()
    key = next(iter(manifest["input_hashes"]))
    manifest["input_hashes"][key] = "0" * 64
    with pytest.raises(b3.Barrier3Error, match="input hash mismatch"):
        b3.run_rehearsal(tmp_path / "bad", manifest)


def test_manifest_refuses_non_synthetic_evidence():
    manifest = _manifest()
    manifest["evidence_class"] = "measured_physical_capture"
    with pytest.raises(Exception):
        b3.validate_run_manifest(manifest)


def test_manifest_refuses_heldout_access_mode():
    manifest = _manifest()
    manifest["arm_ref"]["heldout_access"] = "score"
    with pytest.raises(Exception):
        b3.validate_run_manifest(manifest)


def test_nonfinite_stage_boundary_fails_closed(tmp_path, monkeypatch):
    manifest = _manifest()

    def bad_stage(_manifest):
        return b3._label({
            "stage": "optimization",
            "stage_seed": 1,
            "best_value": float("nan"),
            "best_candidate_id": "bad",
            "best_params": [0.1, 0.2, 0.3],
            "n_evaluations": 1,
            "converged": True,
            "objective_spec": {},
            "certification": None,
        }), __import__("numpy").asarray([0.1, 0.2, 0.3])

    monkeypatch.setattr(b3, "_optimization_stage", bad_stage)
    with pytest.raises(b3.Barrier3Error, match="non-finite"):
        b3.run_rehearsal(tmp_path / "nan", manifest)


def test_synthetic_output_cannot_promote(tmp_path):
    out = tmp_path / "run"
    b3.run_rehearsal(out, _manifest())
    with pytest.raises(b3.PromotionRefusedError):
        b3.promote_to_measured(out)


def test_physical_transfer_record_remains_synthetic(tmp_path):
    out = tmp_path / "run"
    b3.run_rehearsal(out, _manifest())
    payload = json.loads((out / "stages" / "physical_transfer.json").read_text())
    record = payload["record"]
    assert record["evidence_class"] == b3.EVIDENCE_CLASS
    assert record["physical_efficacy_claimed"] is False
    assert "measured_evidence_ref" not in record


def test_manifest_schema_has_no_outcome_fields():
    schema = b3.load_run_schema()
    properties = schema["properties"]
    for forbidden in ("heldout_results", "heldout_scores", "measured_evidence", "physical_efficacy"):
        assert forbidden not in properties

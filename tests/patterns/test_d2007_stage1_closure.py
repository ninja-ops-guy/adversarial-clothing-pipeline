from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLOSURE = ROOT / "evidence" / "d2-0007" / "stage1-screening-closure.json"


def _record() -> dict:
    return json.loads(CLOSURE.read_text(encoding="utf-8"))


def test_stage1_closure_is_complete_screened_out_h0() -> None:
    record = _record()
    result = record["scientific_result"]
    assert record["generation_id"] == "RAC-PER-D2-0007"
    assert record["stage"] == "STAGE_1_MOTIF_SCREENING"
    assert record["decision"] == "SCREENED_OUT_H0"
    assert record["generation_status"] == "CLOSED_SCREENED_OUT_H0"
    assert result["model_set_id"] == "PERSON-SUR-v3"
    assert result["observed_composition_count"] == 64
    assert result["screening_budget_exhausted"] is True
    assert result["survivor_count"] == 0
    assert result["admitted_count"] == 0
    assert result["preregistered_h0_screened_out"] is True
    assert len(result["result_sha256"]) == 64


def test_stage1_null_cannot_advance_downstream_stages() -> None:
    record = _record()
    boundary = record["boundary_verification"]
    consequence = record["closure_consequence"]
    assert boundary["heldout_access"] is False
    assert boundary["body_garment_anchor_support_built"] is False
    assert boundary["optimization_opened"] is False
    assert boundary["candidate_freeze_created"] is False
    assert boundary["alpha_002_promoted"] is False
    assert boundary["d2_0005_touched"] is False
    assert boundary["alpha_001_rebound"] is False
    assert boundary["tracked_frozen_surface_diff_guard"] == "PASS"
    assert consequence["stage2_anchor_engineering_authorized"] is False
    assert consequence["stage3_optimization_authorized"] is False
    assert consequence["stage5_candidate_freeze_authorized"] is False
    assert consequence["stage6_heldout_evaluation_authorized"] is False
    assert consequence["alpha_002_promotion_authorized"] is False


def test_stage1_family_summaries_all_fail_frozen_survivor_rule() -> None:
    result = _record()["scientific_result"]
    rule = result["decision_rule"]
    families = result["family_best_summary"]
    assert len(families) == 8
    assert {f["generator_index"] for f in families} == set(range(8))
    for family in families:
        assert family["survives"] is False
        assert len(family["pattern_sha256"]) == 64
        meets_mean = family["mean_detection_rate_reduction"] >= rule["minimum_mean_detection_rate_reduction"]
        meets_models = family["improved_surrogate_count"] >= rule["minimum_improved_surrogates"]
        meets_invalid = family["invalid_condition_fraction"] <= rule["maximum_invalid_condition_fraction"]
        assert not (meets_mean and meets_models and meets_invalid)


def test_stage1_closure_is_bound_to_successful_workflow_artifact() -> None:
    record = _record()
    artifact = record["workflow_artifact"]
    assert record["source_commit"] == "43de0636ad06b70733eeefb6b31dafab87e3da65"
    assert record["workflow_run_id"] == 34587752211
    assert artifact["artifact_id"] == 10196062211
    assert artifact["name"] == "d2-0007-stage1-screening-34587752211"
    assert artifact["digest"] == "sha256:9021554aec02992f444a21f2704fa8cf29be6578733476c97cbe8998b3925500"

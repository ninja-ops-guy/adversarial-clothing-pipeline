import json
from pathlib import Path

from scripts.ingest_capture_inference import (
    build_trial,
    conservative_motion_decision,
    conservative_still_decision,
)


def test_still_conservative_rule_all_control_any_candidate():
    inference = {"paired_summary": {"model_outcomes": {
        "a": {"control_detected": True, "candidate_detected": False},
        "b": {"control_detected": True, "candidate_detected": True},
    }}}
    control, candidate, _ = conservative_still_decision(inference)
    assert control is True
    assert candidate is True


def test_still_control_failure_invalidates_candidate():
    inference = {"paired_summary": {"model_outcomes": {
        "a": {"control_detected": False, "candidate_detected": False},
        "b": {"control_detected": True, "candidate_detected": False},
    }}}
    control, candidate, _ = conservative_still_decision(inference)
    assert control is False
    assert candidate is False


def test_motion_uses_sequence_decisions():
    inference = {
        "models": {"a": {}, "b": {}},
        "motion": {"sequences": {
            "c": {"arm": "control", "models": {
                "a": {"sequence_detected": True}, "b": {"sequence_detected": True}}},
            "p": {"arm": "candidate", "models": {
                "a": {"sequence_detected": False}, "b": {"sequence_detected": True}}},
        }}
    }
    control, candidate, detail = conservative_motion_decision(inference)
    assert control is True
    assert candidate is True
    assert detail["a"]["candidate_detected"] is False


def test_build_trial_marks_flat_print_as_non_p1_metadata():
    session = {
        "session_id": "S1", "experiment_id": "RAC-EXP-2026-001",
        "evidence_class": "printed_flat_prototype",
        "camera_id": "C1", "lighting_id": "L1", "distance_m": 2,
        "yaw_deg": 0, "pose": "standing-front",
    }
    inference = {
        "result_sha256": "a" * 64,
        "paired_summary": {"model_outcomes": {
            "a": {"control_detected": True, "candidate_detected": False}
        }}
    }
    trial, _ = build_trial(session, inference, "still")
    assert trial.metadata["evidence_class"] == "printed_flat_prototype"


def test_promotion_gate_rejects_non_p1_classes():
    import pytest

    from scripts.ingest_capture_inference import enforce_promotion_gate

    for cls in ("synthetic_pipeline_validation_only", "printed_flat_prototype", "paper_prototype"):
        with pytest.raises(ValueError, match="promotion gate"):
            enforce_promotion_gate({"evidence_class": cls, "calibration_pass": True})
    with pytest.raises(ValueError, match="calibration_pass"):
        enforce_promotion_gate({"evidence_class": "physical_garment_p1", "calibration_pass": False})
    enforce_promotion_gate({"evidence_class": "physical_garment_p1", "calibration_pass": True})

import json
from pathlib import Path

from scripts.validate_capture_session import build_trial, load_session


def test_synthetic_session_is_never_physical_eligible(tmp_path: Path):
    p = tmp_path / "session.json"
    p.write_text(json.dumps({
        "schema_version": "1.0",
        "session_id": "S1", "experiment_id": "E1",
        "evidence_class": "synthetic_pipeline_validation_only",
        "actor_id": "A1", "camera_id": "C1",
        "captures": {"control": {}, "candidate": {}}
    }))
    payload = load_session(p)
    assert payload["physical_evidence_eligible"] is False


def test_capture_session_builds_physical_trial():
    payload = {
        "session_id": "S1", "experiment_id": "E1",
        "evidence_class": "physical_garment_p1",
        "actor_id": "A1", "camera_id": "C1",
        "distance_m": 3.0, "yaw_deg": 45, "pitch_deg": 0,
        "pose": "standing-front", "lighting_id": "L1",
    }
    trial = build_trial(payload, condition_id="COND1", control_detected=True,
                        candidate_detected=False, trial_id="T1")
    assert trial.control_detected is True
    assert trial.candidate_detected is False
    assert trial.metadata["session_id"] == "S1"

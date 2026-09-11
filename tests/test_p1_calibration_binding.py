from __future__ import annotations

import copy

import pytest

from ruthless_pipeline.certification.p1_calibration_binding import (
    evaluate_profile_payload,
    validate_session_calibration_binding,
)


def _profile(profile_id: str = "RAC-PCP-1-001") -> dict:
    patches = []
    for i in range(48):
        ref = [50.0 + (i % 3), 2.0, -2.0]
        patches.append({"patch_id": f"P{i:02d}", "reference_lab": ref, "measured_lab": ref[:]})
    registrations = [
        {"mark_id": "FID-TL", "nominal_xy_mm": [0.0, 0.0], "measured_xy_mm": [0.5, 0.5]},
        {"mark_id": "FID-TR", "nominal_xy_mm": [100.0, 0.0], "measured_xy_mm": [100.5, 0.5]},
        {"mark_id": "FID-BL", "nominal_xy_mm": [0.0, 100.0], "measured_xy_mm": [0.5, 100.5]},
        {"mark_id": "FID-BR", "nominal_xy_mm": [100.0, 100.0], "measured_xy_mm": [100.5, 100.5]},
    ]
    return {
        "profile_id": profile_id,
        "camera_id": "CAM-01",
        "lighting_id": "LIGHT-01",
        "created_utc": "2026-09-11T12:00:00Z",
        "patches": patches,
        "scales": [
            {"ruler_id": "S1", "nominal_cm": 10.0, "measured_px": 1000.0, "distance_m": 1.0},
            {"ruler_id": "S2", "nominal_cm": 10.0, "measured_px": 1005.0, "distance_m": 1.0},
        ],
        "resolutions": [],
        "registrations": registrations,
    }


def test_complete_measured_profile_accepts() -> None:
    receipt = evaluate_profile_payload(_profile(), "pre")
    assert receipt["accepted"] is True
    assert receipt["measurement_completeness"]["patches"] == 48
    assert receipt["measurement_completeness"]["scales"] == 2
    assert len(receipt["profile_sha256"]) == 64


def test_incomplete_profile_refuses() -> None:
    payload = _profile()
    payload["patches"] = payload["patches"][:-1]
    with pytest.raises(ValueError, match="48 measured patches"):
        evaluate_profile_payload(payload, "pre")


def test_bracketed_session_binding_requires_pre_and_post() -> None:
    pre = evaluate_profile_payload(_profile("RAC-PCP-1-001"), "pre")
    post_payload = _profile("RAC-PCP-1-002")
    post_payload["created_utc"] = "2026-09-11T13:00:00Z"
    post = evaluate_profile_payload(post_payload, "post")
    session = {
        "evidence_class": "physical_garment_p1",
        "camera_id": "CAM-01",
        "lighting_id": "LIGHT-01",
        "calibration_pass": True,
        "calibration_profile_id": pre["profile_id"],
        "calibration_profile_sha256": pre["profile_sha256"],
        "calibration": {"pre": pre, "post": post},
    }
    assert validate_session_calibration_binding(session) == {"pre": pre, "post": post}
    broken = copy.deepcopy(session)
    del broken["calibration"]["post"]
    with pytest.raises(ValueError, match="post-capture"):
        validate_session_calibration_binding(broken)


def test_calibration_binding_rejects_camera_drift() -> None:
    pre = evaluate_profile_payload(_profile("RAC-PCP-1-001"), "pre")
    post = evaluate_profile_payload(_profile("RAC-PCP-1-002"), "post")
    session = {
        "evidence_class": "physical_garment_p1",
        "camera_id": "OTHER-CAM",
        "lighting_id": "LIGHT-01",
        "calibration_pass": True,
        "calibration_profile_id": pre["profile_id"],
        "calibration_profile_sha256": pre["profile_sha256"],
        "calibration": {"pre": pre, "post": post},
    }
    with pytest.raises(ValueError, match="camera_id"):
        validate_session_calibration_binding(session)

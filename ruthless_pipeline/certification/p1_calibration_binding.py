"""Measured P1 calibration parsing, acceptance, and session binding.

Capture Lab may preview calibration acceptance for operator guidance, but the
browser is not the evidence authority. A sealed P1 session carries the exact
pre/post calibration JSON source text and SHA-256. Validation and ingestion
re-parse and re-evaluate those exact bytes with PrintCameraProfile here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from .calibration_ingest import (
    PatchMeasurement,
    PrintCameraProfile,
    RegistrationMeasurement,
    ResolutionMeasurement,
    ScaleMeasurement,
)

P1_EVIDENCE_CLASS = "physical_garment_p1"
MEASURED_EVIDENCE_LABEL = "internally_measured"
PHASES = ("pre", "post")
EXPECTED_PATCHES = 48
EXPECTED_FIDUCIALS = {"FID-TL", "FID-TR", "FID-BL", "FID-BR"}


def _tuple2(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} must contain two values")
    return (float(value[0]), float(value[1]))


def _tuple3(value: Any, label: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain three values")
    return (float(value[0]), float(value[1]), float(value[2]))


def _parse_utc(value: str, label: str) -> datetime:
    text = str(value or "")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{label} created_utc is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} created_utc must be timezone-aware")
    return parsed


def profile_from_payload(payload: dict[str, Any]) -> PrintCameraProfile:
    if not isinstance(payload, dict):
        raise ValueError("calibration profile must be a JSON object")
    patches = [
        PatchMeasurement(
            patch_id=str(item["patch_id"]),
            reference_lab=_tuple3(item["reference_lab"], "reference_lab"),
            measured_lab=_tuple3(item["measured_lab"], "measured_lab"),
        )
        for item in payload.get("patches", [])
    ]
    scales = [
        ScaleMeasurement(
            ruler_id=str(item["ruler_id"]),
            nominal_cm=float(item["nominal_cm"]),
            measured_px=float(item["measured_px"]),
            distance_m=float(item["distance_m"]),
        )
        for item in payload.get("scales", [])
    ]
    resolutions = [
        ResolutionMeasurement(
            lp_mm_steps=[(float(pair[0]), float(pair[1])) for pair in item.get("lp_mm_steps", [])]
        )
        for item in payload.get("resolutions", [])
    ]
    registrations = [
        RegistrationMeasurement(
            mark_id=str(item["mark_id"]),
            nominal_xy_mm=_tuple2(item["nominal_xy_mm"], "nominal_xy_mm"),
            measured_xy_mm=_tuple2(item["measured_xy_mm"], "measured_xy_mm"),
        )
        for item in payload.get("registrations", [])
    ]

    if len(patches) != EXPECTED_PATCHES:
        raise ValueError(f"P1 calibration requires exactly {EXPECTED_PATCHES} measured patches")
    if len(scales) < 2:
        raise ValueError("P1 calibration requires at least two scale measurements")
    observed_fiducials = {item.mark_id for item in registrations}
    if observed_fiducials != EXPECTED_FIDUCIALS or len(registrations) != len(EXPECTED_FIDUCIALS):
        raise ValueError("P1 calibration requires exactly the four frozen fiducials")

    profile = PrintCameraProfile(
        profile_id=str(payload.get("profile_id", "")),
        camera_id=str(payload.get("camera_id", "")),
        lighting_id=str(payload.get("lighting_id", "")),
        created_utc=str(payload.get("created_utc", "")),
        patches=patches,
        scales=scales,
        resolutions=resolutions,
        registrations=registrations,
    )
    profile.validate()
    _parse_utc(profile.created_utc, profile.profile_id or "calibration profile")
    return profile


def evaluate_profile_payload(
    payload: dict[str, Any], phase: str, *, source_bytes: bytes | None = None
) -> dict[str, Any]:
    if phase not in PHASES:
        raise ValueError(f"calibration phase must be one of {PHASES}")
    profile = profile_from_payload(payload)
    accepted, failures = profile.acceptance()
    hashed_bytes = source_bytes if source_bytes is not None else profile.to_profile_json().encode("utf-8")
    return {
        "schema_version": "1.0",
        "phase": phase,
        "profile_id": profile.profile_id,
        "camera_id": profile.camera_id,
        "lighting_id": profile.lighting_id,
        "created_utc": profile.created_utc,
        "profile_sha256": hashlib.sha256(hashed_bytes).hexdigest(),
        "evidence_label": MEASURED_EVIDENCE_LABEL,
        "accepted": accepted,
        "failures": failures,
        "summary": profile.summary(),
        "measurement_completeness": {
            "patches": len(profile.patches),
            "scales": len(profile.scales),
            "fiducials": sorted(item.mark_id for item in profile.registrations),
        },
        "acceptance_thresholds": {
            "max_mean_delta_e_2000": 6.0,
            "max_scale_error_pct": 2.0,
            "max_registration_error_mm": 3.0,
        },
    }


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _evaluate_session_phase(session: dict[str, Any], phase: str) -> dict[str, Any]:
    calibration = session.get("calibration")
    if not isinstance(calibration, dict):
        raise ValueError("P1 calibration binding: physical session is missing calibration")
    source = calibration.get(phase)
    if not isinstance(source, dict):
        raise ValueError(f"P1 calibration binding: missing {phase}-capture calibration source")
    source_text = source.get("source_text")
    source_sha256 = source.get("source_sha256")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError(f"P1 calibration binding: {phase} source_text is missing")
    if not _is_sha256(source_sha256):
        raise ValueError(f"P1 calibration binding: {phase} source_sha256 is invalid")
    actual_sha = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if actual_sha != source_sha256:
        raise ValueError(f"P1 calibration binding: {phase} calibration source hash mismatch")
    try:
        payload = json.loads(source_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"P1 calibration binding: {phase} calibration JSON is invalid") from exc
    receipt = evaluate_profile_payload(payload, phase, source_bytes=source_text.encode("utf-8"))
    if receipt["accepted"] is not True:
        detail = "; ".join(receipt["failures"]) or "unknown acceptance failure"
        raise ValueError(f"P1 calibration binding: {phase}-capture calibration failed: {detail}")
    if receipt["camera_id"] != session.get("camera_id"):
        raise ValueError(f"P1 calibration binding: {phase} camera_id does not match session")
    if receipt["lighting_id"] != session.get("lighting_id"):
        raise ValueError(f"P1 calibration binding: {phase} lighting_id does not match session")
    return receipt


def validate_session_calibration_binding(session: dict[str, Any]) -> dict[str, dict[str, Any]] | None:
    """Recompute and require accepted, distinct chronological P1 brackets."""
    if session.get("evidence_class") != P1_EVIDENCE_CLASS:
        return None
    receipts = {phase: _evaluate_session_phase(session, phase) for phase in PHASES}
    if receipts["pre"]["profile_id"] == receipts["post"]["profile_id"]:
        raise ValueError("P1 calibration binding: pre/post calibration profiles must be distinct")
    if receipts["pre"]["profile_sha256"] == receipts["post"]["profile_sha256"]:
        raise ValueError("P1 calibration binding: pre/post calibration sources must be distinct")
    if _parse_utc(receipts["post"]["created_utc"], "post calibration") <= _parse_utc(
        receipts["pre"]["created_utc"], "pre calibration"
    ):
        raise ValueError("P1 calibration binding: post-capture calibration must be later than pre-capture calibration")
    if session.get("calibration_pass") is not True:
        raise ValueError("P1 calibration binding: calibration_pass must reflect accepted bracketing profiles")
    if session.get("calibration_profile_id") != receipts["pre"]["profile_id"]:
        raise ValueError("P1 calibration binding: calibration_profile_id must bind the pre-capture profile")
    if session.get("calibration_profile_sha256") != receipts["pre"]["profile_sha256"]:
        raise ValueError("P1 calibration binding: calibration_profile_sha256 must bind the exact pre-capture source")
    return receipts


def canonical_receipt(receipt: dict[str, Any]) -> bytes:
    return (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

"""Measured P1 calibration parsing, acceptance, and session binding.

This module turns a measured PrintCameraProfile payload into a hash-bound
acceptance receipt and enforces the bracketing rule for real P1 sessions:
accepted pre-capture calibration before garment capture and accepted
post-capture calibration before the session may be sealed/ingested.

It does not estimate measurements from browser heuristics. The payload must
contain measured Lab/scale/registration values produced under the frozen P1
calibration procedure.
"""

from __future__ import annotations

import hashlib
import json
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
    return profile


def evaluate_profile_payload(payload: dict[str, Any], phase: str) -> dict[str, Any]:
    if phase not in PHASES:
        raise ValueError(f"calibration phase must be one of {PHASES}")
    profile = profile_from_payload(payload)
    accepted, failures = profile.acceptance()
    canonical_profile = profile.to_profile_json().encode("utf-8")
    return {
        "schema_version": "1.0",
        "phase": phase,
        "profile_id": profile.profile_id,
        "camera_id": profile.camera_id,
        "lighting_id": profile.lighting_id,
        "created_utc": profile.created_utc,
        "profile_sha256": hashlib.sha256(canonical_profile).hexdigest(),
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


def validate_session_calibration_binding(session: dict[str, Any]) -> dict[str, dict[str, Any]] | None:
    """Require accepted pre/post measured calibration for physical P1 only."""
    if session.get("evidence_class") != P1_EVIDENCE_CLASS:
        return None
    calibration = session.get("calibration")
    if not isinstance(calibration, dict):
        raise ValueError("P1 calibration binding: physical session is missing calibration")
    receipts: dict[str, dict[str, Any]] = {}
    for phase in PHASES:
        receipt = calibration.get(phase)
        if not isinstance(receipt, dict):
            raise ValueError(f"P1 calibration binding: missing {phase}-capture calibration receipt")
        if receipt.get("phase") != phase:
            raise ValueError(f"P1 calibration binding: {phase} receipt phase mismatch")
        if receipt.get("accepted") is not True:
            raise ValueError(f"P1 calibration binding: {phase}-capture calibration was not accepted")
        if receipt.get("evidence_label") != MEASURED_EVIDENCE_LABEL:
            raise ValueError(f"P1 calibration binding: {phase} receipt is not measured evidence")
        if not receipt.get("profile_id") or not _is_sha256(receipt.get("profile_sha256")):
            raise ValueError(f"P1 calibration binding: {phase} receipt identity/hash is invalid")
        completeness = receipt.get("measurement_completeness")
        if not isinstance(completeness, dict):
            raise ValueError(f"P1 calibration binding: {phase} receipt lacks measurement completeness")
        if completeness.get("patches") != EXPECTED_PATCHES:
            raise ValueError(f"P1 calibration binding: {phase} receipt patch count is incomplete")
        if int(completeness.get("scales", 0)) < 2:
            raise ValueError(f"P1 calibration binding: {phase} receipt scale measurements are incomplete")
        if set(completeness.get("fiducials", [])) != EXPECTED_FIDUCIALS:
            raise ValueError(f"P1 calibration binding: {phase} receipt fiducials are incomplete")
        if receipt.get("camera_id") != session.get("camera_id"):
            raise ValueError(f"P1 calibration binding: {phase} camera_id does not match session")
        if receipt.get("lighting_id") != session.get("lighting_id"):
            raise ValueError(f"P1 calibration binding: {phase} lighting_id does not match session")
        receipts[phase] = receipt
    if session.get("calibration_pass") is not True:
        raise ValueError("P1 calibration binding: calibration_pass must reflect accepted bracketing profiles")
    if session.get("calibration_profile_id") != receipts["pre"]["profile_id"]:
        raise ValueError("P1 calibration binding: calibration_profile_id must bind the pre-capture profile")
    if session.get("calibration_profile_sha256") != receipts["pre"]["profile_sha256"]:
        raise ValueError("P1 calibration binding: calibration_profile_sha256 must bind the pre-capture profile")
    return receipts


def canonical_receipt(receipt: dict[str, Any]) -> bytes:
    return (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

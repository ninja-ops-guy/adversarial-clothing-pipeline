from __future__ import annotations

from copy import deepcopy

import pytest

from ruthless_pipeline.certification import p1_pairing_schedule as ps
from ruthless_pipeline.certification.p1_session_binding import validate_session_schedule_binding


def _physical_session(entry: dict) -> dict:
    binding = {
        "contract_id": ps.CONTRACT_ID,
        "schedule_sha256": ps.schedule_sha256(ps.derive_schedule()),
        "trial_id": entry["trial_id"],
        "execution_position": entry["execution_position"],
        "cell_id": entry["cell_id"],
        "repetition": entry["repetition"],
        "first_arm": entry["first_arm"],
        "arms": entry["arms"],
        "distance_m": entry["distance_m"],
        "yaw_deg": entry["yaw_deg"],
        "pitch_deg": entry["pitch_deg"],
        "lighting_variant": entry["lighting_variant"],
        "pose": entry["pose"],
    }
    first, second = entry["arms"]
    return {
        "evidence_class": "physical_garment_p1",
        "trial_id": entry["trial_id"],
        "distance_m": entry["distance_m"],
        "yaw_deg": entry["yaw_deg"],
        "pitch_deg": entry["pitch_deg"],
        "pose": entry["pose"],
        "lighting_variant": entry["lighting_variant"],
        "p1_schedule": binding,
        "captures": {
            first: {"stills": [{"timestamp": "2026-09-11T12:00:00Z"}], "videos": []},
            second: {"stills": [{"timestamp": "2026-09-11T12:00:01Z"}], "videos": []},
        },
    }


def test_exact_frozen_trial_binding_passes() -> None:
    entry = ps.derive_schedule()[0]
    assert validate_session_schedule_binding(_physical_session(entry)) == entry


def test_geometry_drift_refuses() -> None:
    session = _physical_session(ps.derive_schedule()[0])
    session["distance_m"] = float(session["distance_m"]) + 1.0
    with pytest.raises(ValueError, match="distance_m"):
        validate_session_schedule_binding(session)


def test_schedule_hash_drift_refuses() -> None:
    session = _physical_session(ps.derive_schedule()[0])
    session["p1_schedule"]["schedule_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="schedule_sha256"):
        validate_session_schedule_binding(session)


def test_wrong_first_arm_refuses() -> None:
    session = _physical_session(ps.derive_schedule()[0])
    control = deepcopy(session["captures"].get("control", {"stills": [], "videos": []}))
    candidate = deepcopy(session["captures"].get("candidate", {"stills": [], "videos": []}))
    for record in control.get("stills", []):
        record["timestamp"] = "2026-09-11T12:00:00Z"
    for record in candidate.get("stills", []):
        record["timestamp"] = "2026-09-11T12:00:00Z"
    expected = session["p1_schedule"]["first_arm"]
    wrong = "candidate" if expected == "control" else "control"
    session["captures"][wrong]["stills"][0]["timestamp"] = "2026-09-11T11:59:59Z"
    with pytest.raises(ValueError, match="first captured arm"):
        validate_session_schedule_binding(session)


def test_non_physical_session_is_not_schedule_gated() -> None:
    assert validate_session_schedule_binding({"evidence_class": "printed_flat_prototype"}) is None

"""Fail-closed binding between a physical P1 Capture Lab session and the frozen schedule.

This module does not change the P1 schedule. It re-derives the existing frozen
``RAC-P1-PAIRING-2026-001`` schedule and checks that a real
``physical_garment_p1`` session names exactly one frozen trial and matches its
geometry and first-arm order.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from . import p1_pairing_schedule as schedule_contract

P1_EVIDENCE_CLASS = "physical_garment_p1"


def _parse_time(value: object) -> datetime:
    text = str(value or "")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def frozen_schedule_map() -> dict[str, dict[str, Any]]:
    return {entry["trial_id"]: entry for entry in schedule_contract.derive_schedule()}


def validate_capture_first_arm(session: dict[str, Any], expected_first_arm: str) -> None:
    captures = session.get("captures")
    if not isinstance(captures, dict):
        return
    observed: list[tuple[datetime, str]] = []
    for arm in ("control", "candidate"):
        arm_payload = captures.get(arm, {})
        if not isinstance(arm_payload, dict):
            continue
        for kind in ("stills", "videos"):
            for record in arm_payload.get(kind, []) or []:
                timestamp = record.get("timestamp") if isinstance(record, dict) else None
                if timestamp:
                    try:
                        observed.append((_parse_time(timestamp), arm))
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"P1 schedule binding: invalid capture timestamp {timestamp!r}") from exc
    if observed:
        observed.sort(key=lambda item: item[0])
        actual_first_arm = observed[0][1]
        if actual_first_arm != expected_first_arm:
            raise ValueError(
                "P1 schedule binding: first captured arm does not match frozen order "
                f"({actual_first_arm!r} != {expected_first_arm!r})"
            )


def validate_session_schedule_binding(
    session: dict[str, Any], *, verify_capture_order: bool = True
) -> dict[str, Any] | None:
    """Validate a physical session against one exact frozen schedule entry.

    Non-P1 prototype/synthetic sessions are intentionally outside this
    requirement and return ``None``.
    """
    if session.get("evidence_class") != P1_EVIDENCE_CLASS:
        return None

    binding = session.get("p1_schedule")
    if not isinstance(binding, dict):
        raise ValueError("P1 schedule binding: physical_garment_p1 session is missing p1_schedule")

    schedule = schedule_contract.derive_schedule()
    expected_schedule_sha = schedule_contract.schedule_sha256(schedule)
    trial_id = str(session.get("trial_id") or binding.get("trial_id") or "")
    if not trial_id:
        raise ValueError("P1 schedule binding: physical session is missing trial_id")
    entries = {entry["trial_id"]: entry for entry in schedule}
    entry = entries.get(trial_id)
    if entry is None:
        raise ValueError(f"P1 schedule binding: unknown frozen trial_id {trial_id!r}")

    expected_binding = {
        "contract_id": schedule_contract.CONTRACT_ID,
        "schedule_sha256": expected_schedule_sha,
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
    for field, expected in expected_binding.items():
        actual = binding.get(field)
        if actual != expected:
            raise ValueError(
                f"P1 schedule binding: {field} drifted from frozen trial {trial_id} "
                f"({actual!r} != {expected!r})"
            )

    top_level_checks = {
        "trial_id": entry["trial_id"],
        "distance_m": entry["distance_m"],
        "yaw_deg": entry["yaw_deg"],
        "pitch_deg": entry["pitch_deg"],
        "pose": entry["pose"],
        "lighting_variant": entry["lighting_variant"],
    }
    for field, expected in top_level_checks.items():
        actual = session.get(field)
        if actual != expected:
            raise ValueError(
                f"P1 schedule binding: session {field} does not match frozen trial {trial_id} "
                f"({actual!r} != {expected!r})"
            )

    if verify_capture_order:
        validate_capture_first_arm(session, entry["first_arm"])
    return entry

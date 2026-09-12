from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AuthorityError(ValueError):
    pass


@dataclass(frozen=True)
class AuthoritySnapshot:
    contract_id: str
    schedule_sha256: str
    schedule_file_sha256: str
    pairing_contract_file_sha256: str
    readiness_freeze_file_sha256: str
    trials: dict[str, dict[str, Any]]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_repository_authority(repo_root: str | Path) -> AuthoritySnapshot:
    """Validate PRC's read-only view of the frozen P1 logistics authority."""
    root = Path(repo_root)
    schedule_path = root / "physical/p1/P1_CAPTURE_SCHEDULE.json"
    pairing_path = root / "physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json"
    freeze_path = root / "physical/p1/P1_READINESS_FREEZE.json"

    schedule_doc = _read_json(schedule_path)
    pairing_doc = _read_json(pairing_path)
    freeze_doc = _read_json(freeze_path)

    if schedule_doc.get("contract_id") != pairing_doc.get("contract_id"):
        raise AuthorityError("schedule/pairing contract_id mismatch")
    if schedule_doc.get("schedule_sha256") != pairing_doc.get("schedule_sha256"):
        raise AuthorityError("schedule/pairing derived schedule hash mismatch")

    actual_schedule_file_sha = _file_sha256(schedule_path)
    actual_pairing_file_sha = _file_sha256(pairing_path)
    pinned = freeze_doc.get("artifact_sha256", {})
    if pinned.get("physical/p1/P1_CAPTURE_SCHEDULE.json") != actual_schedule_file_sha:
        raise AuthorityError("readiness freeze does not pin current P1_CAPTURE_SCHEDULE.json bytes")
    if pinned.get("physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json") != actual_pairing_file_sha:
        raise AuthorityError("readiness freeze does not pin current PAIRING_RANDOMIZATION_CONTRACT.json bytes")

    # Reuse the repository's existing single schedule derivation authority.
    from ruthless_pipeline.certification.p1_pairing_schedule import derive_schedule, schedule_sha256

    trials = derive_schedule()
    derived_sha = schedule_sha256(trials)
    if derived_sha != schedule_doc.get("schedule_sha256"):
        raise AuthorityError("derived 144-trial schedule no longer matches frozen schedule_sha256")
    if len(trials) != schedule_doc.get("planned_valid_trials"):
        raise AuthorityError("derived trial count no longer matches frozen planned_valid_trials")

    return AuthoritySnapshot(
        contract_id=str(schedule_doc["contract_id"]),
        schedule_sha256=str(schedule_doc["schedule_sha256"]),
        schedule_file_sha256=actual_schedule_file_sha,
        pairing_contract_file_sha256=actual_pairing_file_sha,
        readiness_freeze_file_sha256=_file_sha256(freeze_path),
        trials={str(row["trial_id"]): row for row in trials},
    )

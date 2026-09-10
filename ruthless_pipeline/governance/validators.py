"""Fail-closed semantic validation for Experimental Governance v1.

JSON Schema provides structural validation; this module enforces the semantic
relationships that schemas alone cannot express cleanly (typed RAC IDs,
hash binding, event-type/reference rules, and cross-field manifest checks).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from .ids import GovernanceId, IdKind
from .ledger import GovernanceEventType, payload_sha256

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GovernanceValidationError(ValueError):
    pass


REQUIRED = {
    "governance_event": (
        "schema_version",
        "event_id",
        "experiment_id",
        "event_type",
        "created_at",
        "actor",
        "payload",
        "payload_sha256",
        "previous_event_sha256",
        "event_sha256",
    ),
    "sampling_manifest": (
        "schema_version",
        "sampling_id",
        "experiment_id",
        "seed",
        "target_distribution",
    ),
    "cohort_manifest": (
        "schema_version",
        "cohort_id",
        "experiment_id",
        "specimen_ids",
        "artifact_sha256",
    ),
    "constraint_set": (
        "schema_version",
        "constraint_id",
        "semantic_hash",
        "rules_hash",
        "encoder_hash",
    ),
    "overlap_analysis": (
        "schema_version",
        "overlap_id",
        "left_constraint_id",
        "right_constraint_id",
        "method",
    ),
    "diagnostic_bundle": (
        "schema_version",
        "diagnostic_id",
        "experiment_id",
        "checks",
        "thresholds_hash",
    ),
}

ID_FIELDS = {
    "governance_event": ("event_id", IdKind.EVENT),
    "sampling_manifest": ("sampling_id", IdKind.SAMPLING),
    "cohort_manifest": ("cohort_id", IdKind.COHORT),
    "constraint_set": ("constraint_id", IdKind.CONSTRAINT),
    "overlap_analysis": ("overlap_id", IdKind.OVERLAP),
    "diagnostic_bundle": ("diagnostic_id", IdKind.DIAGNOSTIC),
}


def _typed_id(value: Any, expected: IdKind, field: str) -> GovernanceId:
    try:
        parsed = GovernanceId.parse(value)
    except Exception as exc:
        raise GovernanceValidationError(f"{field}: invalid identifier") from exc
    if parsed.kind is not expected:
        raise GovernanceValidationError(f"{field}: wrong identifier kind")
    return parsed


def _sha(value: Any, field: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise GovernanceValidationError(f"{field}: invalid sha256")


def _optional_sha(value: Any, field: str) -> None:
    if value is not None:
        _sha(value, field)


def _utc_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GovernanceValidationError(f"{field}: must be RFC3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GovernanceValidationError(f"{field}: invalid timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise GovernanceValidationError(f"{field}: must be UTC")


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _validate_governance_event(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest["actor"], str) or not manifest["actor"].strip():
        raise GovernanceValidationError("actor: non-empty string required")
    if not isinstance(manifest["payload"], dict):
        raise GovernanceValidationError("payload: object required")
    _utc_timestamp(manifest["created_at"], "created_at")
    _sha(manifest["payload_sha256"], "payload_sha256")
    _optional_sha(manifest["previous_event_sha256"], "previous_event_sha256")
    _sha(manifest["event_sha256"], "event_sha256")

    expected_payload_hash = payload_sha256(manifest["payload"])
    if manifest["payload_sha256"] != expected_payload_hash:
        raise GovernanceValidationError("payload_sha256: does not bind payload")

    try:
        event_type = GovernanceEventType(manifest["event_type"])
    except (TypeError, ValueError) as exc:
        raise GovernanceValidationError("event_type: unsupported governance event type") from exc

    reverses = manifest.get("reverses_event_id")
    supersedes = manifest.get("supersedes_event_id")
    if reverses is not None and supersedes is not None:
        raise GovernanceValidationError("event cannot reverse and supersede simultaneously")
    if event_type is GovernanceEventType.REVERSAL:
        if reverses is None:
            raise GovernanceValidationError("REVERSAL requires reverses_event_id")
        _typed_id(reverses, IdKind.EVENT, "reverses_event_id")
    elif reverses is not None:
        raise GovernanceValidationError("reverses_event_id valid only for REVERSAL")
    if event_type is GovernanceEventType.SUPERSESSION:
        if supersedes is None:
            raise GovernanceValidationError("SUPERSESSION requires supersedes_event_id")
        _typed_id(supersedes, IdKind.EVENT, "supersedes_event_id")
    elif supersedes is not None:
        raise GovernanceValidationError("supersedes_event_id valid only for SUPERSESSION")

    unsigned = {
        "schema_version": manifest["schema_version"],
        "event_id": manifest["event_id"],
        "experiment_id": manifest["experiment_id"],
        "event_type": manifest["event_type"],
        "created_at": manifest["created_at"],
        "actor": manifest["actor"],
        "payload_sha256": manifest["payload_sha256"],
        "previous_event_sha256": manifest["previous_event_sha256"],
        "reverses_event_id": reverses,
        "supersedes_event_id": supersedes,
    }
    expected_event_hash = hashlib.sha256(_canonical(unsigned)).hexdigest()
    if manifest["event_sha256"] != expected_event_hash:
        raise GovernanceValidationError("event_sha256: does not bind event metadata")


def validate_manifest(kind: str, manifest: dict[str, Any]) -> bool:
    if kind not in REQUIRED or not isinstance(manifest, dict):
        raise GovernanceValidationError("unknown manifest kind or invalid object")
    missing = [name for name in REQUIRED[kind] if name not in manifest]
    if missing:
        raise GovernanceValidationError("missing required fields: " + ", ".join(missing))
    if manifest["schema_version"] != "1.0":
        raise GovernanceValidationError("schema_version must be 1.0")

    if "experiment_id" in manifest:
        _typed_id(manifest["experiment_id"], IdKind.EXPERIMENT, "experiment_id")
    field, expected = ID_FIELDS[kind]
    _typed_id(manifest[field], expected, field)

    if kind == "governance_event":
        _validate_governance_event(manifest)
    elif kind == "sampling_manifest":
        if not isinstance(manifest["seed"], int) or isinstance(manifest["seed"], bool) or manifest["seed"] < 0:
            raise GovernanceValidationError("seed must be a non-negative integer")
        target = manifest["target_distribution"]
        if not isinstance(target, (str, dict)) or not target:
            raise GovernanceValidationError("target_distribution must be non-empty")
    elif kind == "cohort_manifest":
        ids = manifest["specimen_ids"]
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
            raise GovernanceValidationError("specimen_ids must be non-empty and unique")
        if any(not isinstance(specimen_id, str) or not specimen_id for specimen_id in ids):
            raise GovernanceValidationError("specimen_ids must contain non-empty strings")
        _sha(manifest["artifact_sha256"], "artifact_sha256")
    elif kind == "constraint_set":
        for name in ("semantic_hash", "rules_hash", "encoder_hash"):
            _sha(manifest[name], name)
    elif kind == "overlap_analysis":
        _typed_id(manifest["left_constraint_id"], IdKind.CONSTRAINT, "left_constraint_id")
        _typed_id(manifest["right_constraint_id"], IdKind.CONSTRAINT, "right_constraint_id")
        if not isinstance(manifest["method"], str) or not manifest["method"].strip():
            raise GovernanceValidationError("method must be a non-empty string")
    elif kind == "diagnostic_bundle":
        _sha(manifest["thresholds_hash"], "thresholds_hash")
        if not isinstance(manifest["checks"], list):
            raise GovernanceValidationError("checks must be a list")
    return True

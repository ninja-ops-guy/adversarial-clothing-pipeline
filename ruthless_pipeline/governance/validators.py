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
SCIENTIFIC_IMPACTS = {
    "NONE",
    "SEMANTIC_CORRECTION",
    "POPULATION_CHANGE",
    "DEFINITION_CHANGE",
}


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
    # Identity/version fields are handled below because Governance v1 accepts
    # the adopted constraint_set_id shape while preserving read compatibility
    # with the pre-adoption constraint_id prototype.
    "constraint_set": (
        "schema_version",
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
    "tolerance_policy": (
        "constraint_family",
        "created_at",
        "max_population_displacement",
        "max_cohort_change_fraction",
        "registered_before_outcomes",
        "version",
    ),
}

ID_FIELDS = {
    "governance_event": ("event_id", IdKind.EVENT),
    "sampling_manifest": ("sampling_id", IdKind.SAMPLING),
    "cohort_manifest": ("cohort_id", IdKind.COHORT),
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


def _validate_constraint_set(manifest: dict[str, Any]) -> None:
    for name in ("semantic_hash", "rules_hash", "encoder_hash"):
        _sha(manifest[name], name)

    canonical_present = "constraint_set_id" in manifest
    legacy_present = "constraint_id" in manifest
    if canonical_present == legacy_present:
        raise GovernanceValidationError(
            "constraint set must contain exactly one of constraint_set_id or constraint_id"
        )

    if legacy_present:
        _typed_id(manifest["constraint_id"], IdKind.CONSTRAINT, "constraint_id")
        return

    parsed = _typed_id(
        manifest["constraint_set_id"], IdKind.CONSTRAINT, "constraint_set_id"
    )
    if parsed.is_legacy_alias:
        raise GovernanceValidationError(
            "constraint_set_id must use the canonical RAC-CS-* prefix"
        )
    required = (
        "software_version",
        "parent_constraint_set_id",
        "encoder_version",
        "scientific_projection_version",
        "scientific_impact",
    )
    missing = [field for field in required if field not in manifest]
    if missing:
        raise GovernanceValidationError(
            "missing adopted constraint-set fields: " + ", ".join(missing)
        )
    parent = manifest["parent_constraint_set_id"]
    if parent is not None:
        parent_id = _typed_id(
            parent, IdKind.CONSTRAINT, "parent_constraint_set_id"
        )
        if parent_id.is_legacy_alias:
            raise GovernanceValidationError(
                "parent_constraint_set_id must use the canonical RAC-CS-* prefix"
            )
    for field in (
        "software_version",
        "encoder_version",
        "scientific_projection_version",
    ):
        if not isinstance(manifest[field], str) or not manifest[field].strip():
            raise GovernanceValidationError(f"{field}: non-empty string required")
    if manifest["scientific_impact"] not in SCIENTIFIC_IMPACTS:
        raise GovernanceValidationError("scientific_impact: unsupported classification")


def _validate_tolerance_policy(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest["constraint_family"], str) or not manifest[
        "constraint_family"
    ].strip():
        raise GovernanceValidationError("constraint_family: non-empty string required")
    _utc_timestamp(manifest["created_at"], "created_at")
    for field in (
        "max_population_displacement",
        "max_cohort_change_fraction",
    ):
        value = manifest[field]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0.0 <= float(value) <= 1.0
        ):
            raise GovernanceValidationError(f"{field}: must be numeric in [0, 1]")
    if manifest["registered_before_outcomes"] is not True:
        raise GovernanceValidationError(
            "registered_before_outcomes: must be true for preregistered policy"
        )
    if not isinstance(manifest["version"], str) or not manifest["version"].strip():
        raise GovernanceValidationError("version: non-empty string required")


def validate_manifest(kind: str, manifest: dict[str, Any]) -> bool:
    if kind not in REQUIRED or not isinstance(manifest, dict):
        raise GovernanceValidationError("unknown manifest kind or invalid object")
    missing = [name for name in REQUIRED[kind] if name not in manifest]
    if missing:
        raise GovernanceValidationError("missing required fields: " + ", ".join(missing))
    if kind != "tolerance_policy" and manifest["schema_version"] != "1.0":
        raise GovernanceValidationError("schema_version must be 1.0")

    if "experiment_id" in manifest:
        _typed_id(manifest["experiment_id"], IdKind.EXPERIMENT, "experiment_id")
    if kind in ID_FIELDS:
        field, expected = ID_FIELDS[kind]
        _typed_id(manifest[field], expected, field)

    if kind == "governance_event":
        _validate_governance_event(manifest)
    elif kind == "sampling_manifest":
        if (
            not isinstance(manifest["seed"], int)
            or isinstance(manifest["seed"], bool)
            or manifest["seed"] < 0
        ):
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
        _validate_constraint_set(manifest)
    elif kind == "overlap_analysis":
        _typed_id(manifest["left_constraint_id"], IdKind.CONSTRAINT, "left_constraint_id")
        _typed_id(manifest["right_constraint_id"], IdKind.CONSTRAINT, "right_constraint_id")
        if not isinstance(manifest["method"], str) or not manifest["method"].strip():
            raise GovernanceValidationError("method must be a non-empty string")
    elif kind == "diagnostic_bundle":
        _sha(manifest["thresholds_hash"], "thresholds_hash")
        if not isinstance(manifest["checks"], list):
            raise GovernanceValidationError("checks must be a list")
    elif kind == "tolerance_policy":
        _validate_tolerance_policy(manifest)
    return True

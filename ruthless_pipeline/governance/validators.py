"""Minimal fail-closed semantic validation for Governance Pass 1."""

from __future__ import annotations

import re
from typing import Any

from .ids import GovernanceId, IdKind

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GovernanceValidationError(ValueError):
    pass


REQUIRED = {
    "governance_event": ("schema_version", "event_id", "experiment_id", "event_type", "payload"),
    "sampling_manifest": ("schema_version", "sampling_id", "experiment_id", "seed", "target_distribution"),
    "cohort_manifest": ("schema_version", "cohort_id", "experiment_id", "specimen_ids", "artifact_sha256"),
    "constraint_set": ("schema_version", "constraint_id", "semantic_hash", "rules_hash", "encoder_hash"),
    "overlap_analysis": ("schema_version", "overlap_id", "left_constraint_id", "right_constraint_id", "method"),
    "diagnostic_bundle": ("schema_version", "diagnostic_id", "experiment_id", "checks", "thresholds_hash"),
}

ID_FIELDS = {
    "governance_event": ("event_id", IdKind.EVENT),
    "sampling_manifest": ("sampling_id", IdKind.SAMPLING),
    "cohort_manifest": ("cohort_id", IdKind.COHORT),
    "constraint_set": ("constraint_id", IdKind.CONSTRAINT),
    "overlap_analysis": ("overlap_id", IdKind.OVERLAP),
    "diagnostic_bundle": ("diagnostic_id", IdKind.DIAGNOSTIC),
}


def _typed_id(value: Any, expected: IdKind, field: str) -> None:
    try:
        parsed = GovernanceId.parse(value)
    except Exception as exc:
        raise GovernanceValidationError(f"{field}: invalid identifier") from exc
    if parsed.kind is not expected:
        raise GovernanceValidationError(f"{field}: wrong identifier kind")


def _sha(value: Any, field: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise GovernanceValidationError(f"{field}: invalid sha256")


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

    if kind == "sampling_manifest" and (not isinstance(manifest["seed"], int) or manifest["seed"] < 0):
        raise GovernanceValidationError("seed must be a non-negative integer")
    if kind == "cohort_manifest":
        ids = manifest["specimen_ids"]
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
            raise GovernanceValidationError("specimen_ids must be non-empty and unique")
        _sha(manifest["artifact_sha256"], "artifact_sha256")
    if kind == "constraint_set":
        for name in ("semantic_hash", "rules_hash", "encoder_hash"):
            _sha(manifest[name], name)
    if kind == "diagnostic_bundle":
        _sha(manifest["thresholds_hash"], "thresholds_hash")
        if not isinstance(manifest["checks"], list):
            raise GovernanceValidationError("checks must be a list")
    return True

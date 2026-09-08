"""Machine-readable separation of scientific outcome from downstream packaging.

Historical incident class: D2-0004's CI run failed inside the print-test-kit
(packaging) step, which made a sealed, closed scientific experiment look
unresolved because the status artifact had no machine-readable packaging
channel. This module defines the prospective status format so a packaging
failure is recorded as packaging metadata and can never overwrite the sealed
scientific decision/evidence fields.

Prospective-only: the sealed D2-0004 record (root ``d2-latest-status.json``)
is immutable and stays in the legacy unversioned format. This module reads
both the legacy format and the versioned ``1.0`` format; writers emit
``1.0`` for future generations only.

Status format ``1.0`` adds, on top of the legacy scientific fields:

``schema_version``: ``"1.0"``
``packaging``:
    ``production_packaging_status``: PENDING | COMPLETE | FAILED | NOT_ATTEMPTED
    ``packaging_failure_detail``: string or null
    ``scientific_result_independent_of_packaging``: always true
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema_version import SchemaVersionError, require_schema_version

D2_STATUS_SCHEMA_VERSION = "1.0"
LEGACY_SCHEMA_VERSION = "legacy-unversioned"

PACKAGING_PENDING = "PENDING"
PACKAGING_COMPLETE = "COMPLETE"
PACKAGING_FAILED = "FAILED"
PACKAGING_NOT_ATTEMPTED = "NOT_ATTEMPTED"
PACKAGING_STATES = frozenset(
    {PACKAGING_PENDING, PACKAGING_COMPLETE, PACKAGING_FAILED, PACKAGING_NOT_ATTEMPTED}
)

# Fields that constitute the sealed scientific record. The packaging channel
# must never overwrite these.
SCIENTIFIC_FIELDS = frozenset(
    {
        "candidate_id",
        "protocol_id",
        "protocol_version",
        "surrogate_model_set",
        "heldout_model_set",
        "source_commit",
        "decision",
        "evidence_state",
        "certificate_id",
        "bundle_verified",
        "verification_failures",
        "heldout",
        "invalid_condition_fraction",
    }
)


def make_packaging_block(
    status: str = PACKAGING_NOT_ATTEMPTED,
    failure_detail: str | None = None,
) -> dict[str, Any]:
    """Build a validated packaging block for the status format."""
    if status not in PACKAGING_STATES:
        raise ValueError(f"unknown production_packaging_status: {status!r}")
    if status == PACKAGING_FAILED and not failure_detail:
        raise ValueError("packaging FAILED requires a non-empty packaging_failure_detail")
    if status != PACKAGING_FAILED and failure_detail is not None:
        raise ValueError(
            f"packaging_failure_detail is only meaningful when FAILED (got status {status})"
        )
    return {
        "production_packaging_status": status,
        "packaging_failure_detail": failure_detail,
        "scientific_result_independent_of_packaging": True,
    }


def is_legacy_status(payload: dict[str, Any]) -> bool:
    """True when the payload predates the versioned status format."""
    return "schema_version" not in payload


def read_d2_status(path: str | Path) -> dict[str, Any]:
    """Load a d2 status file, accepting legacy (unversioned) and ``1.0`` formats.

    Legacy payloads (no ``schema_version``) are returned as-is; versioned
    payloads are validated fail-closed against :data:`D2_STATUS_SCHEMA_VERSION`.
    Anything else raises SchemaVersionError.
    """
    path = Path(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise SchemaVersionError(
            f"{path}: expected a JSON object; got {type(payload).__name__}"
        )
    if is_legacy_status(payload):
        return payload
    return require_schema_version(
        payload, D2_STATUS_SCHEMA_VERSION, label=f"d2 status {path}"
    )


def with_packaging(
    status: dict[str, Any],
    packaging_status: str,
    failure_detail: str | None = None,
) -> dict[str, Any]:
    """Return a copy of ``status`` with the packaging block replaced.

    Scientific fields are copied verbatim and never modified; only the
    ``packaging`` block and ``schema_version`` (upgraded to ``1.0``) change.
    """
    updated = dict(status)
    updated["schema_version"] = D2_STATUS_SCHEMA_VERSION
    updated["packaging"] = make_packaging_block(packaging_status, failure_detail)
    return updated


def write_d2_status(path: str | Path, status: dict[str, Any]) -> None:
    """Write a status payload in the canonical sorted, indented form."""
    Path(path).write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")

"""Builder/validator for RAC Physical Transfer Records.

Implements the FROZEN contract ``schemas/physical_transfer_record.schema.json``.

Guarantees beyond the schema itself (builder-level, fail-closed):

- ``emit()`` computes real sha256 hashes from the given artifact BYTES; it
  never accepts caller-supplied hash strings.
- Records produced from a synthetic captured-frame generator are FORCED to
  ``evidence_class='synthetic_pipeline_validation_only'``.
- ``evidence_class='measured_physical_capture'`` requires a non-empty
  ``measured_evidence_ref`` (schema also enforces this; the builder guard
  fails earlier and louder).
- ``physical_efficacy_claimed`` is hard-set to False.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

import jsonschema

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "physical_transfer_record.schema.json"
)

SYNTHETIC = "synthetic_pipeline_validation_only"
MEASURED = "measured_physical_capture"


class TransferRecordError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise TransferRecordError("artifact must be bytes")
    return hashlib.sha256(bytes(data)).hexdigest()


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def validate_record(record: dict) -> dict:
    """Validate a record dict against the frozen schema; returns it."""
    jsonschema.validate(instance=record, schema=load_schema())
    return record


def emit(
    *,
    artwork: bytes,
    template: bytes,
    mapping: bytes,
    captured_frame: bytes,
    garment_sku: str,
    fabric: str,
    print_process: str,
    capture_id: str,
    camera: str,
    lighting: str,
    pose: str,
    view: str,
    detector_response_refs: list[str] | None = None,
    evidence_class: str | None = None,
    measured_evidence_ref: str | None = None,
    synthetic_generator: bool = False,
    record_id: str | None = None,
) -> dict:
    """Build and validate a Physical Transfer Record from artifact bytes.

    ``synthetic_generator=True`` marks the captured frame as produced by a
    synthetic generator and FORCES evidence_class to
    'synthetic_pipeline_validation_only' regardless of the requested class.
    A measured record requires ``measured_evidence_ref``.
    """
    if synthetic_generator:
        evidence_class = SYNTHETIC
    if evidence_class is None:
        evidence_class = SYNTHETIC  # fail-closed default: never claim measured
    if evidence_class == MEASURED:
        if synthetic_generator:
            raise TransferRecordError(
                "synthetic frames can never be measured_physical_capture"
            )
        if not measured_evidence_ref or not str(measured_evidence_ref).strip():
            raise TransferRecordError(
                "evidence_class 'measured_physical_capture' requires "
                "measured_evidence_ref (builder-level guard; schema also enforces)"
            )
    record = {
        "schema_version": "1.0",
        "record_id": record_id or f"ptr-{uuid.uuid4()}",
        "artwork_sha256": sha256_bytes(artwork),
        "template_sha256": sha256_bytes(template),
        "mapping_sha256": sha256_bytes(mapping),
        "garment_sku": garment_sku,
        "fabric": fabric,
        "print_process": print_process,
        "capture_id": capture_id,
        "camera": camera,
        "lighting": lighting,
        "pose": pose,
        "view": view,
        "captured_frame_sha256": sha256_bytes(captured_frame),
        "detector_response_refs": list(detector_response_refs or []),
        "evidence_class": evidence_class,
        "physical_efficacy_claimed": False,
    }
    if measured_evidence_ref is not None:
        record["measured_evidence_ref"] = measured_evidence_ref
    return validate_record(record)

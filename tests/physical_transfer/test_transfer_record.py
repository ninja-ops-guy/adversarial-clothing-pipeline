"""Tests for physical-transfer record emission/validation."""

import hashlib

import jsonschema
import pytest

from ruthless_pipeline.physical_transfer.transfer_record import (
    MEASURED,
    SYNTHETIC,
    TransferRecordError,
    emit,
    sha256_bytes,
    validate_record,
)

KW = dict(
    artwork=b"artwork-bytes",
    template=b"template-bytes",
    mapping=b"mapping-bytes",
    captured_frame=b"frame-bytes",
    garment_sku="SKU-1",
    fabric="cotton",
    print_process="dtg",
    capture_id="cap-1",
    camera="cam-1",
    lighting="lab-d65",
    pose="front",
    view="front",
)


def test_round_trip_synthetic_default():
    rec = emit(**KW)
    assert rec["evidence_class"] == SYNTHETIC
    assert rec["physical_efficacy_claimed"] is False
    assert rec["artwork_sha256"] == hashlib.sha256(b"artwork-bytes").hexdigest()
    validate_record(rec)  # schema round-trip


def test_synthetic_generator_forces_synthetic_class():
    rec = emit(**KW, synthetic_generator=True, evidence_class=MEASURED,
               measured_evidence_ref="x")
    assert rec["evidence_class"] == SYNTHETIC


def test_measured_requires_ref_builder_guard():
    with pytest.raises(TransferRecordError):
        emit(**KW, evidence_class=MEASURED)


def test_measured_with_ref_passes_schema():
    rec = emit(**KW, evidence_class=MEASURED, measured_evidence_ref="vault://cap-1")
    assert rec["evidence_class"] == MEASURED
    assert rec["measured_evidence_ref"] == "vault://cap-1"
    validate_record(rec)


def test_schema_rejects_measured_without_ref():
    rec = emit(**KW)
    rec["evidence_class"] = MEASURED
    with pytest.raises(jsonschema.ValidationError):
        validate_record(rec)


def test_schema_rejects_efficacy_claim_and_bad_sha():
    rec = emit(**KW)
    rec["physical_efficacy_claimed"] = True
    with pytest.raises(jsonschema.ValidationError):
        validate_record(rec)
    rec2 = emit(**KW)
    rec2["artwork_sha256"] = "not-a-sha"
    with pytest.raises(jsonschema.ValidationError):
        validate_record(rec2)


def test_non_bytes_rejected():
    with pytest.raises(TransferRecordError):
        sha256_bytes("string-not-bytes")

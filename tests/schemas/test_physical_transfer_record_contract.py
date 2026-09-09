"""Contract tests for schemas/physical_transfer_record.schema.json."""

from __future__ import annotations

import copy

SCHEMA = "physical_transfer_record.schema.json"

H = "a" * 64  # valid lowercase sha256 hex


def _minimal():
    return {
        "schema_version": "1.0",
        "record_id": "PTR-0001",
        "artwork_sha256": H,
        "template_sha256": H,
        "mapping_sha256": H,
        "garment_sku": "RAC-TEE-BLK-M",
        "fabric": "cotton",
        "print_process": "dtg",
        "capture_id": "CAP-0001",
        "camera": "synthetic-cam",
        "lighting": "indoor-even",
        "pose": "standing",
        "view": "front",
        "captured_frame_sha256": H,
        "detector_response_refs": [],
        "evidence_class": "synthetic_pipeline_validation_only",
        "physical_efficacy_claimed": False,
    }


def _full():
    rec = _minimal()
    rec.update(
        {
            "detector_response_refs": ["DR-0001", "DR-0002"],
            "evidence_class": "measured_physical_capture",
            "measured_evidence_ref": "captures/D05_Y+030_P0_STANDING_INDOOR_EVEN__R1__candidate.jpg",
        }
    )
    return rec


def test_minimal_valid(validate):
    assert validate(SCHEMA, _minimal()) == []


def test_full_valid(validate):
    assert validate(SCHEMA, _full()) == []


def test_missing_required_field_fails(validate):
    rec = _minimal()
    del rec["artwork_sha256"]
    assert validate(SCHEMA, rec)


def test_bad_sha256_pattern_fails(validate):
    rec = _minimal()
    rec["captured_frame_sha256"] = "A" * 64  # uppercase not allowed
    assert validate(SCHEMA, rec)
    rec = _minimal()
    rec["artwork_sha256"] = "abc123"
    assert validate(SCHEMA, rec)


def test_additional_properties_fails(validate):
    rec = _minimal()
    rec["unexpected_field"] = "nope"
    assert validate(SCHEMA, rec)


def test_physical_efficacy_claimed_true_fails(validate):
    rec = _minimal()
    rec["physical_efficacy_claimed"] = True
    assert validate(SCHEMA, rec)


def test_wrong_evidence_class_fails(validate):
    rec = _minimal()
    rec["evidence_class"] = "log_attested"
    assert validate(SCHEMA, rec)


def test_measured_capture_requires_measured_evidence_ref(validate):
    rec = _full()
    del rec["measured_evidence_ref"]
    assert validate(SCHEMA, rec)


def test_detector_response_refs_must_be_strings(validate):
    rec = _minimal()
    rec["detector_response_refs"] = [1, 2]
    assert validate(SCHEMA, rec)


def test_examples_are_independent():
    a, b = _minimal(), _minimal()
    b["record_id"] = "PTR-OTHER"
    assert a != b and copy.deepcopy(a) == _minimal()

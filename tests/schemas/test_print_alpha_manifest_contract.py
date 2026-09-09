"""Contract tests for schemas/print_alpha_manifest.schema.json."""

from __future__ import annotations

SCHEMA = "print_alpha_manifest.schema.json"

H = "b" * 64


def _minimal():
    return {
        "schema_version": "1.0",
        "manifest_id": "RAC-PA-0001",
        "garment": {
            "sku": "RAC-TEE-BLK-M",
            "material": "100% cotton",
            "size": "M",
            "print_technology": "PENDING_USER_ACTION",
            "printer_vendor": "PENDING_USER_ACTION",
            "manufacturing_batch": None,
        },
        "control_artwork_ref": "print-alpha/CONTROL/control.png",
        "candidate_artwork_ref": {
            "ref": "print-alpha/CANDIDATE/candidate.png",
            "expected_sha256": H,
            "byte_identical_to_frozen_source": True,
        },
        "physical_efficacy_claimed": False,
        "evidence_class": "experimental_print_specimen",
        "user_action_refs": ["UA-1", "UA-2"],
    }


def _full():
    m = _minimal()
    m["garment"]["print_technology"] = "dtg"
    m["garment"]["printer_vendor"] = "vendor-x"
    m["garment"]["manufacturing_batch"] = "BATCH-2026-09"
    m["user_action_refs"] = []
    return m


def test_minimal_valid(validate):
    assert validate(SCHEMA, _minimal()) == []


def test_full_valid(validate):
    assert validate(SCHEMA, _full()) == []


def test_missing_required_field_fails(validate):
    m = _minimal()
    del m["garment"]
    assert validate(SCHEMA, m)


def test_bad_sha256_pattern_fails(validate):
    m = _minimal()
    m["candidate_artwork_ref"]["expected_sha256"] = "not-a-hash"
    assert validate(SCHEMA, m)


def test_additional_properties_fails(validate):
    m = _minimal()
    m["efficacy_notes"] = "works great"
    assert validate(SCHEMA, m)
    m = _minimal()
    m["garment"]["colorway"] = "black"
    assert validate(SCHEMA, m)


def test_physical_efficacy_claimed_true_fails(validate):
    m = _minimal()
    m["physical_efficacy_claimed"] = True
    assert validate(SCHEMA, m)


def test_wrong_evidence_class_fails(validate):
    m = _minimal()
    m["evidence_class"] = "synthetic_pipeline_validation_only"
    assert validate(SCHEMA, m)


def test_pending_user_action_literal_accepted(validate):
    m = _minimal()
    assert m["garment"]["printer_vendor"] == "PENDING_USER_ACTION"
    assert validate(SCHEMA, m) == []


def test_empty_vendor_field_fails(validate):
    m = _minimal()
    m["garment"]["printer_vendor"] = ""
    assert validate(SCHEMA, m)


def test_user_action_refs_must_be_strings(validate):
    m = _minimal()
    m["user_action_refs"] = [1]
    assert validate(SCHEMA, m)

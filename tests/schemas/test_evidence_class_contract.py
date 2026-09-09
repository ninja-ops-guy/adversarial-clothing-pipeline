"""Contract tests for schemas/evidence_class.schema.json."""

from __future__ import annotations

SCHEMA = "evidence_class.schema.json"

EXISTING = [
    "synthetic_pipeline_validation_only",
    "generated_digital_reference",
    "log_attested",
    "scenario_assumption",
]


def test_existing_classes_valid(validate):
    for cls in EXISTING:
        assert validate(SCHEMA, cls) == []


def test_new_experimental_print_specimen_valid(validate):
    assert validate(SCHEMA, "experimental_print_specimen") == []


def test_unknown_class_fails(validate):
    assert validate(SCHEMA, "physical_efficacy_proof")
    assert validate(SCHEMA, "measured_physical_capture")  # belongs to transfer record, not taxonomy


def test_non_string_fails(validate):
    assert validate(SCHEMA, 3)
    assert validate(SCHEMA, None)


def test_enum_is_exactly_five_classes(validate):
    from conftest import load_schema

    enum = load_schema(SCHEMA)["enum"]
    assert len(enum) == 5
    assert set(EXISTING + ["experimental_print_specimen"]) == set(enum)

"""Contract tests for ruthless_pipeline/evidence_classes_ext.py."""

from __future__ import annotations

import pytest

from ruthless_pipeline import evidence_classes_ext as ext


def test_registry_contains_all_six_classes():
    assert ext.EVIDENCE_CLASSES == frozenset(
        {
            "synthetic_pipeline_validation_only",
            "generated_digital_reference",
            "log_attested",
            "scenario_assumption",
            "experimental_print_specimen",
            "derived_digital_measurement",
        }
    )


def test_new_classes_registered():
    assert ext.EXPERIMENTAL_PRINT_SPECIMEN == "experimental_print_specimen"
    assert ext.EXPERIMENTAL_PRINT_SPECIMEN in ext.EVIDENCE_CLASSES
    assert ext.DERIVED_DIGITAL_MEASUREMENT == "derived_digital_measurement"
    assert ext.DERIVED_DIGITAL_MEASUREMENT in ext.EVIDENCE_CLASSES


def test_is_valid():
    assert ext.is_valid("experimental_print_specimen")
    assert ext.is_valid("log_attested")
    assert not ext.is_valid("physical_efficacy_proof")
    assert not ext.is_valid("")


def test_requires_user_action():
    assert ext.requires_user_action("experimental_print_specimen")
    assert not ext.requires_user_action("log_attested")
    with pytest.raises(KeyError):
        ext.requires_user_action("not_a_class")


def test_no_class_permits_physical_efficacy_claim():
    for cls in ext.EVIDENCE_CLASSES:
        assert ext.permits_physical_efficacy_claim(cls) is False
    with pytest.raises(KeyError):
        ext.permits_physical_efficacy_claim("nope")


def test_describe_covers_every_class():
    for cls in ext.EVIDENCE_CLASSES:
        assert ext.describe(cls)
    with pytest.raises(KeyError):
        ext.describe("nope")


def test_pending_user_action_literal():
    assert ext.PENDING_USER_ACTION == "PENDING_USER_ACTION"


def test_module_is_pure_stdlib():
    import inspect

    source = inspect.getsource(ext)
    assert "import torch" not in source
    assert "import requests" not in source

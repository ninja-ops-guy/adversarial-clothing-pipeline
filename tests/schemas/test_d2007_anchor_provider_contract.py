"""Contract tests for schemas/d2007_anchor_provider_v1.schema.json.

Declaration/validation surface only for RAC-PER-D2-0007 anchor providers.
No provider implementation exists or is exercised here; nothing is armed.
"""

from __future__ import annotations

SCHEMA = "d2007_anchor_provider_v1.schema.json"

_SHA = "a" * 64


def _minimal(**overrides):
    declaration = {
        "schema_version": "1.0",
        "declaration_id": "RAC-D2007-ANCHOR-001",
        "generation_id": "RAC-PER-D2-0007",
        "provider": {
            "identity": "fixed-torso-template",
            "version": "1.0.0",
            "artifact_sha256": _SHA,
            "configuration": {"torso_fraction": 0.6, "margin_px": 8},
        },
        "anchor_capabilities": ["torso_region", "silhouette_mask"],
        "provenance_class": "template_derived",
        "coordinate_convention": {
            "origin": "top_left",
            "axis_directions": "x right, y down",
            "normalization": "normalized_0_1",
            "units": "fraction_of_crop",
        },
        "confidence_handling": {
            "confidence_exposed_downstream": False,
            "low_confidence_fallback": "fixed_template_default",
        },
        "permitted_data_exposure": {
            "crosses_stage_boundary": True,
            "exposed_fields": ["coordinates", "mask"],
            "source_imagery_exposed": False,
            "heldout_derived_statistics_exposed": False,
        },
    }
    declaration.update(overrides)
    return declaration


def test_minimal_template_derived_declaration_valid(validate):
    assert validate(SCHEMA, _minimal()) == []


def test_model_derived_declaration_valid(validate):
    decl = _minimal(
        provenance_class="model_derived",
        anchor_capabilities=["bounding_region"],
    )
    decl["provider"]["identity"] = "governed-segmentation-model"
    decl["confidence_handling"]["threshold"] = 0.5
    assert validate(SCHEMA, decl) == []


def test_provenance_class_enum_is_closed(validate):
    decl = _minimal(provenance_class="hybrid_derived")
    errors = validate(SCHEMA, decl)
    assert errors, "unknown provenance class must be rejected"


def test_anchor_capability_vocabulary_is_closed(validate):
    decl = _minimal(anchor_capabilities=["torso_region", "gaze_keypoints"])
    errors = validate(SCHEMA, decl)
    assert errors, "capability outside the declared vocabulary must be rejected"


def test_missing_provider_governance_fields_rejected(validate):
    for field in ("identity", "version", "artifact_sha256", "configuration"):
        decl = _minimal()
        del decl["provider"][field]
        errors = validate(SCHEMA, decl)
        assert errors, f"provider.{field} is mandatory and its absence must fail"


def test_malformed_artifact_hash_rejected(validate):
    decl = _minimal()
    decl["provider"]["artifact_sha256"] = "not-a-sha256"
    assert validate(SCHEMA, decl), "non-sha256 artifact hash must be rejected"


def test_source_imagery_exposure_always_rejected(validate):
    decl = _minimal()
    decl["permitted_data_exposure"]["source_imagery_exposed"] = True
    assert validate(SCHEMA, decl), "source imagery exposure must always fail"


def test_heldout_derived_statistics_exposure_always_rejected(validate):
    decl = _minimal()
    decl["permitted_data_exposure"]["heldout_derived_statistics_exposed"] = True
    assert validate(SCHEMA, decl), "held-out-derived exposure must always fail"


def test_coordinate_convention_fields_mandatory(validate):
    for field in ("origin", "axis_directions", "normalization", "units"):
        decl = _minimal()
        del decl["coordinate_convention"][field]
        errors = validate(SCHEMA, decl)
        assert errors, f"coordinate_convention.{field} is mandatory"


def test_additional_properties_rejected(validate):
    decl = _minimal(undeclared_field="post-hoc extension")
    assert validate(SCHEMA, decl), "undeclared top-level fields must be rejected"


def test_wrong_generation_id_rejected(validate):
    decl = _minimal(generation_id="RAC-PER-D2-0005")
    assert validate(SCHEMA, decl), "declarations are bound to RAC-PER-D2-0007"

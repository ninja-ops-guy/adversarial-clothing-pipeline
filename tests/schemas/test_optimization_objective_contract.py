"""Contract tests for schemas/optimization_objective.schema.json."""

from __future__ import annotations

SCHEMA = "optimization_objective.schema.json"


def _minimal():
    return {
        "schema_version": "1.0",
        "objective_id": "RAC-OBJ-0001",
        "terms": {
            "detector_loss": {"aggregation": "MEAN", "log_separately": True},
        },
        "seed": 7,
        "future_generations_only": True,
    }


def _full():
    return {
        "schema_version": "1.0",
        "objective_id": "RAC-OBJ-0002",
        "terms": {
            "detector_loss": {"aggregation": "CVAR", "alpha": 0.1, "log_separately": True},
            "printability_loss": {"lambda_print": 0.5, "log_separately": True},
            "style_loss": {"lambda_style": 0.2, "log_separately": True},
            "deformation_loss": {"lambda_deformation": 0.1, "log_separately": True},
            "regularization": {"lambda_reg": 0.001, "log_separately": True},
        },
        "seed": 1234,
        "future_generations_only": True,
    }


def test_minimal_valid(validate):
    assert validate(SCHEMA, _minimal()) == []


def test_full_valid(validate):
    assert validate(SCHEMA, _full()) == []


def test_missing_required_field_fails(validate):
    o = _minimal()
    del o["terms"]
    assert validate(SCHEMA, o)


def test_cvar_without_alpha_fails(validate):
    o = _full()
    del o["terms"]["detector_loss"]["alpha"]
    assert validate(SCHEMA, o)


def test_cvar_alpha_out_of_range_fails(validate):
    o = _full()
    o["terms"]["detector_loss"]["alpha"] = 0.0
    assert validate(SCHEMA, o)
    o = _full()
    o["terms"]["detector_loss"]["alpha"] = 1.5
    assert validate(SCHEMA, o)


def test_bad_aggregation_enum_fails(validate):
    o = _minimal()
    o["terms"]["detector_loss"]["aggregation"] = "MEDIAN"
    assert validate(SCHEMA, o)


def test_future_generations_only_false_fails(validate):
    o = _minimal()
    o["future_generations_only"] = False
    assert validate(SCHEMA, o)


def test_additional_properties_fails(validate):
    o = _minimal()
    o["mystery"] = 1
    assert validate(SCHEMA, o)
    o = _minimal()
    o["terms"]["unknown_term"] = {"lambda_x": 1.0}
    assert validate(SCHEMA, o)


def test_negative_lambda_fails(validate):
    o = _full()
    o["terms"]["printability_loss"]["lambda_print"] = -0.1
    assert validate(SCHEMA, o)


def test_log_separately_must_be_true(validate):
    o = _minimal()
    o["terms"]["detector_loss"]["log_separately"] = False
    assert validate(SCHEMA, o)

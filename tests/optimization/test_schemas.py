"""synthetic_pipeline_validation_only — ObjectiveSpec schema validation tests."""

from __future__ import annotations

import json

import jsonschema
import pytest

from ruthless_pipeline.optimization.schemas import (
    DetectorAggregation,
    ObjectiveSpec,
    load_schema,
)

from conftest import synthetic_objective_dict


def test_valid_spec_loads():
    spec = ObjectiveSpec.from_dict(synthetic_objective_dict())
    assert spec.objective_id == "SYNTH-OPT-001"
    assert spec.aggregation is DetectorAggregation.MEAN
    assert spec.seed == 1234
    assert spec.future_generations_only is True
    weights = spec.weights()
    assert weights["detector_loss"] == 1.0
    assert weights["printability_loss"] == 0.5
    assert weights["regularization"] == 0.05


def test_cvar_requires_alpha():
    data = synthetic_objective_dict()
    data["terms"] = {"detector_loss": {"aggregation": "CVAR", "log_separately": True}}
    with pytest.raises(jsonschema.ValidationError):
        ObjectiveSpec.from_dict(data)


def test_cvar_alpha_bounds_enforced():
    for bad in (0.0, -0.1, 1.5):
        data = synthetic_objective_dict()
        data["terms"] = {
            "detector_loss": {"aggregation": "CVAR", "alpha": bad, "log_separately": True}
        }
        with pytest.raises((jsonschema.ValidationError, ValueError)):
            ObjectiveSpec.from_dict(data)


def test_cvar_valid_alpha_ok():
    data = synthetic_objective_dict()
    data["terms"] = {
        "detector_loss": {"aggregation": "CVAR", "alpha": 0.5, "log_separately": True}
    }
    spec = ObjectiveSpec.from_dict(data)
    assert spec.aggregation is DetectorAggregation.CVAR
    assert spec.alpha == 0.5


def test_future_generations_only_hard_frozen():
    data = synthetic_objective_dict(future_generations_only=False)
    with pytest.raises((jsonschema.ValidationError, ValueError)):
        ObjectiveSpec.from_dict(data)


def test_additional_properties_rejected():
    data = synthetic_objective_dict()
    data["surprise"] = 1
    with pytest.raises(jsonschema.ValidationError):
        ObjectiveSpec.from_dict(data)


def test_from_json_file_roundtrip(tmp_path):
    path = tmp_path / "obj.json"
    path.write_text(json.dumps(synthetic_objective_dict()))
    spec = ObjectiveSpec.from_json_file(path)
    assert spec.objective_id == "SYNTH-OPT-001"


def test_frozen_schema_on_disk_loads():
    schema = load_schema()
    assert schema["properties"]["future_generations_only"]["const"] is True

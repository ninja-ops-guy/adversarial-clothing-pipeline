"""Contract tests for schemas/detector_response.schema.json."""

from __future__ import annotations

SCHEMA = "detector_response.schema.json"


def _minimal():
    return {
        "schema_version": "1.0",
        "model_id": "yolov8n",
        "model_family": "yolo",
        "condition_id": "D05_Y+030_P0_STANDING_INDOOR_EVEN",
        "person_detected": True,
        "confidence": 0.87,
        "objectness": None,
        "class_score": 0.85,
        "box_count": 1,
        "best_box": {"xyxy": [10.0, 20.0, 110.0, 220.0], "score": 0.87},
        "localization_metrics": None,
        "segmentation_metrics": None,
        "invalid_condition": False,
        "evaluator_adapter": {"adapter_id": "rac-yolo-adapter", "adapter_version": "1.0.0"},
    }


def _full():
    r = _minimal()
    r.update(
        {
            "objectness": 0.91,
            "localization_metrics": {"iou_vs_reference": 0.74, "center_offset_px": 3.2},
            "segmentation_metrics": {"mask_iou": 0.68},
            "raw_provenance_ref": "raw/yolov8n/D05_Y+030.json",
        }
    )
    return r


def test_minimal_valid(validate):
    assert validate(SCHEMA, _minimal()) == []


def test_full_valid(validate):
    assert validate(SCHEMA, _full()) == []


def test_missing_required_field_fails(validate):
    r = _minimal()
    del r["evaluator_adapter"]
    assert validate(SCHEMA, r)


def test_additional_properties_fails(validate):
    r = _minimal()
    r["fabricated_internal"] = 0.5  # adapter must never smuggle unknown internals
    assert validate(SCHEMA, r)


def test_confidence_out_of_range_fails(validate):
    r = _minimal()
    r["confidence"] = 1.5
    assert validate(SCHEMA, r)


def test_bad_best_box_fails(validate):
    r = _minimal()
    r["best_box"] = {"xyxy": [1.0, 2.0, 3.0], "score": 0.5}  # not 4 coords
    assert validate(SCHEMA, r)


def test_objectness_must_be_rate_or_null(validate):
    r = _minimal()
    r["objectness"] = "high"
    assert validate(SCHEMA, r)


def test_adapter_missing_version_fails(validate):
    r = _minimal()
    r["evaluator_adapter"] = {"adapter_id": "rac-yolo-adapter"}
    assert validate(SCHEMA, r)


def test_no_fabrication_rule_documented(validate):
    # The anti-fabrication rule must be encoded in the schema description.
    from conftest import load_schema

    desc = load_schema(SCHEMA)["description"].lower()
    assert "never fabricat" in desc

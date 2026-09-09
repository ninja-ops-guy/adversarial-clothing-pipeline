"""Family registry coverage, fail-closed behaviour, concentration warnings."""

from __future__ import annotations

import pytest

from ruthless_pipeline.detector_science.family_registry import (
    UnknownFamilyError,
    concentration_report,
    family_for_model,
    load_registry,
    validate_coverage,
)

EXPECTED_FAMILIES = {
    "detr_resnet50": "transformer_encoder_decoder",
    "fasterrcnn_mobilenet_v3_320": "two_stage_rcnn",
    "fasterrcnn_resnet50_fpn_v2": "two_stage_rcnn",
    "fcos_resnet50_fpn": "one_stage_anchor",
    "maskrcnn_resnet50_fpn_v2": "two_stage_rcnn",
    "retinanet_resnet50_fpn_v2": "one_stage_anchor",
    "ssdlite320_mobilenet_v3": "one_stage_ssd",
    "yolov8n": "one_stage_yolo",
}


def test_registry_covers_all_eight_real_manifests():
    registry = validate_coverage()  # raises if any manifest uncovered/mismatched
    assert set(registry["models"]) == set(EXPECTED_FAMILIES)
    for model_id, family in EXPECTED_FAMILIES.items():
        assert family_for_model(model_id, registry) == family


def test_unknown_model_fails_closed():
    with pytest.raises(UnknownFamilyError):
        family_for_model("not_a_real_model", load_registry())


def test_concentration_warning_on_dominated_set():
    dominated = [
        "fasterrcnn_mobilenet_v3_320",
        "fasterrcnn_resnet50_fpn_v2",
        "maskrcnn_resnet50_fpn_v2",
        "yolov8n",
    ]
    report = concentration_report(dominated)
    assert report["warning"] is True
    assert report["max_family"] == "two_stage_rcnn"
    assert report["max_family_share"] == 0.75
    assert report["distinct_families"] == 2  # also below minimum of 3
    assert report["warning_reasons"]


def test_no_concentration_warning_on_balanced_set():
    balanced = [
        "detr_resnet50",
        "fasterrcnn_resnet50_fpn_v2",
        "fcos_resnet50_fpn",
        "ssdlite320_mobilenet_v3",
        "yolov8n",
    ]
    report = concentration_report(balanced)
    assert report["warning"] is False
    assert report["warning_reasons"] == []
    assert report["max_family_share"] == pytest.approx(0.2)
    assert report["distinct_families"] == 5


def test_concentration_threshold_configurable():
    models = [
        "detr_resnet50",
        "fasterrcnn_resnet50_fpn_v2",
        "fcos_resnet50_fpn",
        "ssdlite320_mobilenet_v3",
        "yolov8n",
        "yolov8n",  # duplicate model id still counts toward share
    ]
    strict = concentration_report(models, threshold=0.2, min_distinct_families=3)
    assert strict["warning"] is True
    lenient = concentration_report(models, threshold=0.9, min_distinct_families=2)
    assert lenient["warning"] is False


def test_concentration_empty_set_fails_closed():
    with pytest.raises(ValueError):
        concentration_report([])

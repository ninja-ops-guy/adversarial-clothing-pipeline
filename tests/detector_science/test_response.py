"""Schema round-trip and fabrication-guard tests for DetectorResponse."""

from __future__ import annotations

import pytest

from ruthless_pipeline.detector_science.adapters import (
    DetectionBatchAdapter,
    SyntheticDetectionAdapter,
)
from ruthless_pipeline.detector_science.response import (
    AdapterCapabilities,
    DetectorResponse,
    FabricationGuardError,
    validate,
)


def _response(**overrides):
    kwargs = dict(
        model_id="yolov8n",
        model_family="one_stage_yolo",
        condition_id="D05_SYNTH_001",
        person_detected=True,
        confidence=0.87,
        box_count=1,
        evaluator_adapter={"adapter_id": "rac-test", "adapter_version": "1.0.0"},
        capabilities=AdapterCapabilities(),
    )
    kwargs.update(overrides)
    return DetectorResponse(**kwargs)


def test_schema_round_trip():
    instance = _response(best_box={"xyxy": [1.0, 2.0, 3.0, 4.0], "score": 0.87}).validate()
    validate(instance)
    rebuilt = DetectorResponse.from_dict(instance)
    assert rebuilt.to_dict() == instance


def test_schema_round_trip_full():
    caps = AdapterCapabilities(
        exposes_objectness=True, exposes_class_score=True,
        exposes_localization=True, exposes_segmentation=True,
    )
    instance = _response(
        capabilities=caps,
        objectness=0.9,
        class_score=0.85,
        best_box={"xyxy": [1.0, 2.0, 3.0, 4.0], "score": 0.87},
        localization_metrics={"iou": 0.7},
        segmentation_metrics={"mask_iou": 0.6},
        raw_provenance_ref="raw/test.json",
    ).validate()
    assert DetectorResponse.from_dict(instance).to_dict() == instance


def test_fabrication_guard_objectness():
    with pytest.raises(FabricationGuardError):
        _response(objectness=0.5)  # not exposed by default capabilities


def test_fabrication_guard_best_box_when_boxes_not_exposed():
    with pytest.raises(FabricationGuardError):
        _response(
            capabilities=AdapterCapabilities(exposes_boxes=False),
            box_count=0,
            best_box={"xyxy": [0.0, 0.0, 1.0, 1.0], "score": 0.5},
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("localization_metrics", {"iou": 0.5}),
        ("segmentation_metrics", {"mask_iou": 0.5}),
        ("class_score", 0.5),
    ],
)
def test_fabrication_guard_other_fields(field, value):
    with pytest.raises(FabricationGuardError):
        _response(**{field: value})


def test_adapter_emits_none_objectness_and_passes():
    adapter = SyntheticDetectionAdapter()
    response = adapter.adapt(
        {"boxes": [[10.0, 20.0, 110.0, 220.0]], "scores": [0.9], "labels": [1]},
        model_id="synthetic",
        model_family="one_stage_yolo",
        condition_id="SYNTH_001",
    )
    instance = response.validate()
    assert instance["objectness"] is None
    assert instance["class_score"] is None
    assert instance["localization_metrics"] is None
    assert instance["segmentation_metrics"] is None
    assert instance["person_detected"] is True
    assert instance["best_box"]["score"] == 0.9


def test_adapter_below_threshold_not_detected():
    adapter = SyntheticDetectionAdapter()
    response = adapter.adapt(
        {"boxes": [[0.0, 0.0, 1.0, 1.0]], "scores": [0.3], "labels": [1]},
        model_id="synthetic",
        model_family="f",
        condition_id="c",
    )
    assert response.person_detected is False
    assert response.confidence == 0.3


class _FakeBatch:
    """Duck-typed stand-in for evaluators.DetectionBatch (no torch)."""

    class _T:
        def __init__(self, vals):
            self._vals = vals

        def tolist(self):
            return self._vals

    def __init__(self):
        self.boxes = [self._T([1.0, 2.0, 3.0, 4.0])]
        self.labels = [self._T([1])]
        self.scores = [self._T([0.8])]


def test_detection_batch_adapter_duck_typed():
    adapter = DetectionBatchAdapter()
    response = adapter.adapt(
        _FakeBatch(),
        model_id="detr_resnet50",
        model_family="transformer_encoder_decoder",
        condition_id="c",
        target_score=0.77,
    )
    instance = response.validate()
    assert instance["class_score"] == 0.77
    assert instance["objectness"] is None
    assert instance["box_count"] == 1


def test_adapter_label_filtering():
    adapter = SyntheticDetectionAdapter()
    response = adapter.adapt(
        {
            "boxes": [[0.0, 0.0, 1.0, 1.0], [0.0, 0.0, 2.0, 2.0]],
            "scores": [0.9, 0.95],
            "labels": [1, 7],
        },
        model_id="m",
        model_family="f",
        condition_id="c",
        target_label=1,
    )
    assert response.box_count == 1
    assert response.confidence == 0.9

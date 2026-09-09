"""Evaluator adapters producing DetectorResponse records.

Adapters declare their capabilities; anything the underlying detector does not
legitimately expose is forced to None by the DetectorResponse fabrication
guard. DetectionBatchAdapter bridges
``ruthless_pipeline.evaluators.DetectionBatch`` by duck-typing on
``.boxes`` / ``.labels`` / ``.scores`` attributes only — torch is never
imported here.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from .response import AdapterCapabilities, DetectorResponse


class AdapterRegistry:
    """Registry of (adapter_id, adapter_version, capabilities)."""

    def __init__(self) -> None:
        self._entries: dict[str, dict] = {}

    def register(
        self,
        adapter_id: str,
        adapter_version: str,
        capabilities: AdapterCapabilities,
    ) -> None:
        if adapter_id in self._entries:
            raise ValueError(f"adapter_id {adapter_id!r} already registered")
        self._entries[adapter_id] = {
            "adapter_id": adapter_id,
            "adapter_version": adapter_version,
            "capabilities": capabilities,
        }

    def get(self, adapter_id: str) -> dict:
        try:
            return self._entries[adapter_id]
        except KeyError:
            raise KeyError(f"unknown adapter_id {adapter_id!r}") from None

    def adapter_ref(self, adapter_id: str) -> dict:
        entry = self.get(adapter_id)
        return {
            "adapter_id": entry["adapter_id"],
            "adapter_version": entry["adapter_version"],
        }

    def list_adapters(self) -> list:
        return [
            {
                "adapter_id": e["adapter_id"],
                "adapter_version": e["adapter_version"],
                "capabilities": e["capabilities"].as_dict(),
            }
            for e in self._entries.values()
        ]


def _to_float_list(values: Any) -> list:
    """Convert tensor-like / array-like / sequence to a plain float list."""
    if values is None:
        return []
    if hasattr(values, "tolist"):  # numpy arrays, torch tensors, etc.
        values = values.tolist()
    if isinstance(values, (list, tuple)):
        out = []
        for v in values:
            if hasattr(v, "tolist"):
                v = v.tolist()
            if isinstance(v, (list, tuple)):
                out.append([float(x) for x in v])
            else:
                out.append(float(v))
        return out
    return [float(values)]


class SyntheticDetectionAdapter:
    """Adapter over dict / DetectionBatch-like tuples of boxes, scores, labels.

    Exposes boxes and scores ONLY: objectness, class_score, localization and
    segmentation metrics are legitimately unknown and are therefore forced to
    None by the fabrication guard.
    """

    ADAPTER_ID = "rac-synthetic-detection-adapter"
    ADAPTER_VERSION = "1.0.0"

    def __init__(self) -> None:
        self.capabilities = AdapterCapabilities(
            exposes_boxes=True,
            exposes_scores=True,
            exposes_objectness=False,
            exposes_class_score=False,
            exposes_localization=False,
            exposes_segmentation=False,
        )

    @property
    def adapter_ref(self) -> dict:
        return {"adapter_id": self.ADAPTER_ID, "adapter_version": self.ADAPTER_VERSION}

    def adapt(
        self,
        detection: Any,
        *,
        model_id: str,
        model_family: str,
        condition_id: str,
        decision_threshold: float = 0.5,
        target_label: Optional[Any] = None,
        invalid_condition: bool = False,
        raw_provenance_ref: Optional[str] = None,
    ) -> DetectorResponse:
        boxes, _labels, scores = self._unpack(detection, target_label)
        count = len(scores)
        best_score = max(scores) if scores else 0.0
        best_box = None
        if boxes and scores:
            best_idx = max(range(len(scores)), key=lambda i: scores[i])
            best_box = {"xyxy": [float(v) for v in boxes[best_idx]], "score": best_score}
        return DetectorResponse(
            model_id=model_id,
            model_family=model_family,
            condition_id=condition_id,
            person_detected=bool(scores) and best_score >= decision_threshold,
            confidence=best_score,
            box_count=count,
            evaluator_adapter=self.adapter_ref,
            capabilities=self.capabilities,
            objectness=None,  # not legitimately exposed
            class_score=None,  # not legitimately exposed
            best_box=best_box,
            localization_metrics=None,
            segmentation_metrics=None,
            invalid_condition=invalid_condition,
            raw_provenance_ref=raw_provenance_ref,
        )

    @staticmethod
    def _unpack(detection: Any, target_label: Optional[Any]) -> Tuple[list, list, list]:
        if isinstance(detection, Mapping):
            boxes = detection.get("boxes", [])
            labels = detection.get("labels")
            scores = detection.get("scores", [])
        else:  # DetectionBatch-like: duck-typed attribute access, no torch import
            boxes = getattr(detection, "boxes", [])
            labels = getattr(detection, "labels", None)
            scores = getattr(detection, "scores", [])
        boxes_l = _to_float_list(boxes)
        scores_l = [
            float(s[0]) if isinstance(s, list) else float(s)
            for s in _to_float_list(scores)
        ]
        labels_l = _to_float_list(labels) if labels is not None else None
        if labels_l is not None and target_label is not None:
            keep = [i for i, lab in enumerate(labels_l) if lab == float(target_label)]
            boxes_l = [boxes_l[i] for i in keep if i < len(boxes_l)]
            scores_l = [scores_l[i] for i in keep if i < len(scores_l)]
        return boxes_l, labels_l or [], scores_l


class DetectionBatchAdapter(SyntheticDetectionAdapter):
    """Bridge for ruthless_pipeline.evaluators.DetectionBatch.

    Duck-types on ``.boxes`` / ``.labels`` / ``.scores``; never imports torch.
    DetectionBatch exposes per-class target scores, so class_score is
    legitimately exposed when a ``target_score`` is provided by the caller.
    """

    ADAPTER_ID = "rac-detection-batch-adapter"
    ADAPTER_VERSION = "1.0.0"

    def __init__(self) -> None:
        super().__init__()
        self.capabilities = AdapterCapabilities(
            exposes_boxes=True,
            exposes_scores=True,
            exposes_objectness=False,
            exposes_class_score=True,
            exposes_localization=False,
            exposes_segmentation=False,
        )

    def adapt(
        self,
        detection: Any,
        *,
        target_score: Optional[float] = None,
        **kwargs: Any,
    ) -> DetectorResponse:
        response = super().adapt(detection, **kwargs)
        if target_score is not None:
            response = DetectorResponse(
                model_id=response.model_id,
                model_family=response.model_family,
                condition_id=response.condition_id,
                person_detected=response.person_detected,
                confidence=response.confidence,
                box_count=response.box_count,
                evaluator_adapter=response.evaluator_adapter,
                capabilities=response.capabilities,
                class_score=float(target_score),
                best_box=response.best_box,
                invalid_condition=response.invalid_condition,
                raw_provenance_ref=response.raw_provenance_ref,
            )
        return response


def default_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(
        SyntheticDetectionAdapter.ADAPTER_ID,
        SyntheticDetectionAdapter.ADAPTER_VERSION,
        SyntheticDetectionAdapter().capabilities,
    )
    registry.register(
        DetectionBatchAdapter.ADAPTER_ID,
        DetectionBatchAdapter.ADAPTER_VERSION,
        DetectionBatchAdapter().capabilities,
    )
    return registry

"""DetectorResponse record conforming to schemas/detector_response.schema.json.

ANTI-FABRICATION RULE (enforced in code): an evaluator adapter may only emit
fields the underlying model/API legitimately exposes. Fields whose capability
flag is False in the adapter's ``AdapterCapabilities`` MUST be None, and any
attempt to fill them raises ``FabricationGuardError`` — never silently
fabricated, interpolated, or back-filled.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import jsonschema

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "detector_response.schema.json"
)


def _load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate(instance: dict) -> None:
    """Validate an instance dict against the frozen detector-response schema.

    Raises jsonschema.ValidationError on contract violation.
    """
    jsonschema.validate(instance=instance, schema=_load_schema())


class FabricationGuardError(ValueError):
    """Raised when an adapter attempts to emit a field its capabilities do not expose."""


@dataclass(frozen=True)
class AdapterCapabilities:
    """What the underlying detector/API legitimately exposes."""

    exposes_boxes: bool = True
    exposes_scores: bool = True
    exposes_objectness: bool = False
    exposes_class_score: bool = False
    exposes_localization: bool = False
    exposes_segmentation: bool = False

    def as_dict(self) -> dict:
        return {
            "exposes_boxes": self.exposes_boxes,
            "exposes_scores": self.exposes_scores,
            "exposes_objectness": self.exposes_objectness,
            "exposes_class_score": self.exposes_class_score,
            "exposes_localization": self.exposes_localization,
            "exposes_segmentation": self.exposes_segmentation,
        }


@dataclass
class DetectorResponse:
    """One detector evaluation response (frozen Barrier 1 contract)."""

    model_id: str
    model_family: str
    condition_id: str
    person_detected: bool
    confidence: float
    box_count: int
    evaluator_adapter: dict
    capabilities: AdapterCapabilities = field(
        default_factory=AdapterCapabilities, repr=False, compare=False
    )
    objectness: Optional[float] = None
    class_score: Optional[float] = None
    best_box: Optional[dict] = None
    localization_metrics: Optional[dict] = None
    segmentation_metrics: Optional[dict] = None
    invalid_condition: bool = False
    raw_provenance_ref: Optional[str] = None
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        caps = self.capabilities
        guarded = [
            ("objectness", self.objectness, caps.exposes_objectness),
            ("class_score", self.class_score, caps.exposes_class_score),
            ("best_box", self.best_box, caps.exposes_boxes),
            (
                "localization_metrics",
                self.localization_metrics,
                caps.exposes_localization,
            ),
            (
                "segmentation_metrics",
                self.segmentation_metrics,
                caps.exposes_segmentation,
            ),
        ]
        for name, value, exposed in guarded:
            if value is not None and not exposed:
                raise FabricationGuardError(
                    f"adapter capabilities do not expose {name!r}; "
                    "field must be None (never fabricated/interpolated)"
                )
        if not caps.exposes_boxes and self.box_count != 0:
            raise FabricationGuardError(
                "adapter capabilities do not expose boxes; box_count must be 0"
            )

    def to_dict(self) -> dict:
        instance = {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_family": self.model_family,
            "condition_id": self.condition_id,
            "person_detected": bool(self.person_detected),
            "confidence": self.confidence,
            "objectness": self.objectness,
            "class_score": self.class_score,
            "box_count": self.box_count,
            "best_box": self.best_box,
            "localization_metrics": self.localization_metrics,
            "segmentation_metrics": self.segmentation_metrics,
            "invalid_condition": bool(self.invalid_condition),
            "evaluator_adapter": dict(self.evaluator_adapter),
        }
        if self.raw_provenance_ref is not None:
            instance["raw_provenance_ref"] = self.raw_provenance_ref
        return instance

    def validate(self) -> dict:
        """Return the schema-validated instance dict (raises on violation)."""
        instance = self.to_dict()
        validate(instance)
        return instance

    @classmethod
    def from_dict(cls, instance: dict, capabilities: Optional[AdapterCapabilities] = None) -> "DetectorResponse":
        validate(instance)
        return cls(
            model_id=instance["model_id"],
            model_family=instance["model_family"],
            condition_id=instance["condition_id"],
            person_detected=instance["person_detected"],
            confidence=instance["confidence"],
            box_count=instance["box_count"],
            evaluator_adapter=dict(instance["evaluator_adapter"]),
            capabilities=capabilities
            or AdapterCapabilities(
                exposes_boxes=instance.get("best_box") is not None,
                exposes_objectness=instance.get("objectness") is not None,
                exposes_class_score=instance.get("class_score") is not None,
                exposes_localization=instance.get("localization_metrics") is not None,
                exposes_segmentation=instance.get("segmentation_metrics") is not None,
            ),
            objectness=instance.get("objectness"),
            class_score=instance.get("class_score"),
            best_box=instance.get("best_box"),
            localization_metrics=instance.get("localization_metrics"),
            segmentation_metrics=instance.get("segmentation_metrics"),
            invalid_condition=instance.get("invalid_condition", False),
            raw_provenance_ref=instance.get("raw_provenance_ref"),
            schema_version=instance.get("schema_version", "1.0"),
        )

"""SPEC-11 — Mechanism-class tagging and head-class panel axis.

Head class is a stratification covariate, not a replacement for full target
identity. Mechanism labels are explicit and fail closed. Only the literal
``architecture_accident`` class is architecture-accident-bound; lower
expected generality alone does not imply that classification.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from .errors import CTMBridgeError

TARGET_SEMANTICS_SCHEMA_VERSION = "rac-ctm-target-semantics/1.0"
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "ctm_target_semantics_v1.schema.json"
)

class TargetSemanticsError(CTMBridgeError):
    """Target semantics contract violated (SPEC-11). Fail closed."""

HEAD_CLASSES = frozenset({"nms_based", "nms_free"})
MECHANISM_CLASSES = frozenset({
    "task_invariant",
    "training_data",
    "pipeline_structure",
    "physics",
    "hardware",
    "architecture_accident",
})

_EXPECTED_GENERALITY = {
    "task_invariant": 5,
    "training_data": 4,
    "pipeline_structure": 3,
    "physics": 3,
    "hardware": 2,
    "architecture_accident": 1,
}

def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()

def expected_generality(mechanism_class: str) -> int:
    """Relative expected generality (higher = more architecture-general)."""
    if mechanism_class not in MECHANISM_CLASSES:
        raise TargetSemanticsError(
            f"unknown mechanism_class {mechanism_class!r}; allowed: "
            f"{sorted(MECHANISM_CLASSES)} (fail closed)"
        )
    return _EXPECTED_GENERALITY[mechanism_class]

def is_architecture_accident_bound(mechanism_class: str) -> bool:
    """True only for mechanisms explicitly classified architecture_accident.

    Expected generality and mechanism class are separate semantics. Physics,
    hardware, training-data, and pipeline-structure mechanisms may rank below
    task-invariant mechanisms without becoming architecture accidents.
    """
    if mechanism_class not in MECHANISM_CLASSES:
        raise TargetSemanticsError(
            f"unknown mechanism_class {mechanism_class!r}; allowed: "
            f"{sorted(MECHANISM_CLASSES)} (fail closed)"
        )
    return mechanism_class == "architecture_accident"

def require_not_identity_collapse(target_identity: str) -> None:
    """Refuse use of a head-class label as the target identity itself."""
    if target_identity in HEAD_CLASSES:
        raise TargetSemanticsError(
            f"target identity {target_identity!r} is a head_class value: "
            "head_class is a covariate, never an identity collapse — the "
            "target taxonomy must not be reduced to nms_based/nms_free "
            "(fail closed)"
        )

@dataclass(frozen=True)
class MechanismTag:
    """Required mechanism-class tag for heuristic registry entries."""

    mechanism_class: str
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.mechanism_class:
            raise TargetSemanticsError(
                "mechanism_class is required on heuristic registry entries "
                "(missing mechanism_class fails closed)"
            )
        if self.mechanism_class not in MECHANISM_CLASSES:
            raise TargetSemanticsError(
                f"unknown mechanism_class {self.mechanism_class!r}; allowed: "
                f"{sorted(MECHANISM_CLASSES)} (fail closed)"
            )

    @property
    def architecture_accident_bound(self) -> bool:
        return is_architecture_accident_bound(self.mechanism_class)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mechanism_class": self.mechanism_class,
            "rationale": self.rationale,
            "architecture_accident_bound": self.architecture_accident_bound,
        }

@dataclass(frozen=True)
class TargetSemantics:
    """Target-semantics panel record.

    ``head_class`` is a stratification covariate. The full target identity
    remains target/architecture/weights/threshold configuration.
    """

    target_id: str
    head_class: str
    threshold_config_sha256: str
    architecture: str = ""
    weights_ref: str = ""
    schema_version: str = TARGET_SEMANTICS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TARGET_SEMANTICS_SCHEMA_VERSION:
            raise TargetSemanticsError(
                f"unsupported target_semantics schema_version: {self.schema_version!r}"
            )
        if not self.target_id:
            raise TargetSemanticsError("target_id is required (fail closed)")
        require_not_identity_collapse(self.target_id)
        if not self.head_class:
            raise TargetSemanticsError(
                "head_class is required on panel target records "
                "(missing head_class fails closed)"
            )
        if self.head_class not in HEAD_CLASSES:
            raise TargetSemanticsError(
                f"unknown head_class {self.head_class!r}; allowed: "
                f"{sorted(HEAD_CLASSES)} (fail closed)"
            )
        if not _is_sha256(self.threshold_config_sha256):
            raise TargetSemanticsError(
                "threshold_config_sha256 must be a lowercase 64-hex sha256 "
                "binding the evaluated threshold configuration (fail closed)"
            )

    @property
    def stratification_covariates(self) -> dict[str, str]:
        return {"head_class": self.head_class}

    def stratification_label(self) -> str:
        return self.head_class

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "architecture": self.architecture,
            "weights_ref": self.weights_ref,
            "threshold_config_sha256": self.threshold_config_sha256,
        }

    def target_identity_sha256(self) -> str:
        return sha256_bytes(canonical_json(self._identity_payload()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "target_id": self.target_id,
            "architecture": self.architecture,
            "weights_ref": self.weights_ref,
            "head_class": self.head_class,
            "threshold_config_sha256": self.threshold_config_sha256,
            "target_identity_sha256": self.target_identity_sha256(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def target_semantics_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise TargetSemanticsError(
                f"target semantics record fails ctm_target_semantics_v1 schema: "
                f"{exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetSemantics":
        if not isinstance(payload, dict):
            raise TargetSemanticsError("target semantics payload must be an object")
        record = cls(
            target_id=payload.get("target_id", ""),
            architecture=payload.get("architecture", ""),
            weights_ref=payload.get("weights_ref", ""),
            head_class=payload.get("head_class", ""),
            threshold_config_sha256=payload.get("threshold_config_sha256", ""),
            schema_version=payload.get("schema_version", ""),
        )
        asserted = payload.get("target_identity_sha256")
        if asserted is not None and asserted != record.target_identity_sha256():
            raise TargetSemanticsError(
                f"user-asserted target_identity_sha256 {asserted!r} disagrees "
                f"with the derived hash {record.target_identity_sha256()!r} "
                "(fail closed)"
            )
        return record

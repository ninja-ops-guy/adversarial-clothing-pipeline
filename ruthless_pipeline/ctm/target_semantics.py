"""SPEC-11 — Mechanism-class tagging and head-class panel axis (CTM-A enum →
CTM-C panel → CTM-F attribution).

Lesson L11: high-transfer surfaces are properties of what the model was
trained to do (task-invariant), while low-transfer surfaces are
architectural accidents (NMS internals, anchor layout, token grids). The
target panel's axis of variation includes head class (NMS-based vs.
NMS-free) as a first-class COVARIATE — never an identity collapse of the
whole target taxonomy onto two labels.

Hard rules (fail closed with :class:`TargetSemanticsError`):

- ``head_class`` is required and must be ``nms_based | nms_free``.
- ``mechanism_class`` is required on heuristic tags and must be one of the
  six SPEC-11 values; missing/invalid fails closed.
- ``head_class`` is a stratification covariate, never a target identity:
  :func:`require_not_identity_collapse` refuses any attempt to use a head
  class as a target identity, and target identity hashing binds
  ``threshold_config_sha256`` (L12: decision thresholds are part of target
  identity), not the covariate alone.
- ``threshold_config_sha256`` must be a lowercase 64-hex sha256 binding the
  evaluated threshold configuration.

Additive: serialized records are governed by
``schemas/ctm_target_semantics_v1.schema.json``.
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


#: SPEC-11(a): required head-class covariate enum.
HEAD_CLASSES = frozenset({"nms_based", "nms_free"})

#: SPEC-11(a): required mechanism-class enum (exactly the six spec values).
MECHANISM_CLASSES = frozenset({
    "task_invariant",
    "training_data",
    "pipeline_structure",
    "physics",
    "hardware",
    "architecture_accident",
})

#: Expected-generality ordering used by CTM-F stratification reports: a
#: task-invariant mechanism is expected to survive panel extension to new
#: architectures; an architecture-accident mechanism is expected not to.
_EXPECTED_GENERALITY = {
    "task_invariant": 5,
    "training_data": 4,
    "pipeline_structure": 3,
    "physics": 3,
    "hardware": 2,
    "architecture_accident": 1,
}

_SHA256_LEN = 64


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def expected_generality(mechanism_class: str) -> int:
    """Relative expected generality of a mechanism class (higher = more
    architecture-general). Fails closed on unknown classes."""
    if mechanism_class not in MECHANISM_CLASSES:
        raise TargetSemanticsError(
            f"unknown mechanism_class {mechanism_class!r}; allowed: "
            f"{sorted(MECHANISM_CLASSES)} (fail closed)"
        )
    return _EXPECTED_GENERALITY[mechanism_class]


def is_architecture_accident_bound(mechanism_class: str) -> bool:
    """True when a heuristic's mechanism is bound to an architectural
    accident and therefore has lower expected generality than a
    task-invariant mechanism (SPEC-11(c) labelling rule)."""
    return expected_generality(mechanism_class) < expected_generality("task_invariant")


def require_not_identity_collapse(target_identity: str) -> None:
    """Fail-closed guard: a head class is a stratification covariate, never
    a target identity. Refusing the collapse keeps the full target taxonomy
    from being reduced to NMS/NMS-free."""
    if target_identity in HEAD_CLASSES:
        raise TargetSemanticsError(
            f"target identity {target_identity!r} is a head_class value: "
            "head_class is a covariate, never an identity collapse — the "
            "target taxonomy must not be reduced to nms_based/nms_free "
            "(fail closed)"
        )


@dataclass(frozen=True)
class MechanismTag:
    """SPEC-11(a) required mechanism-class tag for heuristic registry
    entries."""

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
    """SPEC-11(b) target-semantics panel record.

    ``head_class`` and ``threshold_config_sha256`` extend target identity
    for the panel; the threshold config hash binds the evaluated decision
    thresholds (L12: thresholds are load-bearing target identity).
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
                f"unsupported target_semantics schema_version: "
                f"{self.schema_version!r}"
            )
        if not self.target_id:
            raise TargetSemanticsError("target_id is required (fail closed)")
        require_not_identity_collapse(self.target_id)
        if not self.head_class:
            raise TargetSemanticsError(
                "head_class is required on panel target records (missing "
                "head_class fails closed)"
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

    # -- stratification --------------------------------------------------------

    @property
    def stratification_covariates(self) -> dict[str, str]:
        """Head class as a first-class covariate for CTM-F stratified
        reporting. This is a covariate view only; identity is hashed
        separately and never collapses to head_class."""
        return {"head_class": self.head_class}

    def stratification_label(self) -> str:
        return self.head_class

    # -- canonical serialization ----------------------------------------------

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "architecture": self.architecture,
            "weights_ref": self.weights_ref,
            "threshold_config_sha256": self.threshold_config_sha256,
        }

    def target_identity_sha256(self) -> str:
        """Content hash of the target identity (threshold configuration
        included; head_class deliberately excluded — it is a covariate,
        not an identity)."""
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
                f"target semantics record fails ctm_target_semantics_v1 "
                f"schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetSemantics":
        """Parse a serialized record, REFUSING a user-asserted identity hash
        that disagrees with the derived hash."""
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

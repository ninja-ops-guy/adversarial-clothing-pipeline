"""SPEC-13 — Cascade-stage scope labels and scope-conformance checking.

Lesson L13: deployed identification is a multi-stage cascade (person
detection -> face detection -> face recognition -> Re-ID/gait fallback), and
the detector-centric corpus conflates stages. Every efficacy, robustness, or
transfer claim artifact must declare exactly which stage(s) its outcome
covers. The invariant is structural: narrative scope may never exceed
structured claim scope.

Hard rules (fail closed with :class:`PipelineStageError` subclasses):

- ``pipeline_stages`` is required and non-empty on every efficacy /
  robustness / transfer claim. A claim spanning multiple stages must either
  declare ``fusion`` or list the stages explicitly with a
  ``multi_stage_basis`` — silently generalizing from one stage is refused.
- FR-family results enter the living corpus as cross-domain boundary papers
  but do NOT inherit person-detection claims without an explicit bridge
  (:func:`require_cross_domain_bridge`).
- :func:`check_prose_scope` enforces the structural invariant on manuscript
  prose: prose may not name a stage outside the declared scope, and broad
  terms (invisibility, evasion, surveillance) require stage-bounded wording.

This module is additive; it does not mutate any frozen claim schema.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .errors import CTMBridgeError

CLAIM_SCOPE_SCHEMA_VERSION = "rac-ctm-claim-scope/1.0"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "ctm_claim_scope_v1.schema.json"
)

#: Required pipeline_stage enum (SPEC-13).
PIPELINE_STAGES = frozenset({
    "person_detection",
    "face_detection",
    "face_recognition",
    "reid_tracking",
    "fusion",
})

#: Claim kinds that MUST declare pipeline-stage scope.
SCOPED_CLAIM_KINDS = frozenset({"efficacy", "robustness", "transfer"})

CLAIM_KINDS = SCOPED_CLAIM_KINDS | frozenset({"descriptive", "infrastructure"})

#: Broad terms that require stage-bounded wording in prose (SPEC-13 rule 4).
BROAD_TERMS = frozenset({"invisibility", "invisible", "evasion", "evade", "surveillance"})

#: Prose phrases mapped to the stage they imply.
_STAGE_PROSE = {
    "person_detection": ("person detection", "person detector", "pedestrian detection"),
    "face_detection": ("face detection", "face detector"),
    "face_recognition": ("face recognition", "facial recognition"),
    "reid_tracking": ("re-id", "reid", "re-identification", "gait", "tracking"),
    "fusion": ("fusion", "cascade", "multi-stage", "end-to-end pipeline"),
}

_STAGE_BOUNDS = {
    "person_detection": ("person detection", "person-detection", "person detector"),
    "face_detection": ("face detection", "face-detection", "face detector"),
    "face_recognition": ("face recognition", "face-recognition", "facial recognition"),
    "reid_tracking": ("re-id", "reid", "re-identification", "gait"),
    "fusion": ("fusion", "cascade", "multi-stage"),
}


class PipelineStageError(CTMBridgeError):
    """Base class for pipeline-stage scope failures (SPEC-13). Fail closed."""


class ScopeConformanceError(PipelineStageError):
    """Narrative scope exceeds structured claim scope."""


@dataclass(frozen=True)
class ClaimScope:
    """Immutable pipeline-stage scope record for a claim artifact."""

    claim_id: str
    claim_kind: str
    pipeline_stages: tuple[str, ...]
    multi_stage_basis: str = ""
    schema_version: str = CLAIM_SCOPE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAIM_SCOPE_SCHEMA_VERSION:
            raise PipelineStageError(
                f"unsupported claim-scope schema_version: {self.schema_version!r}"
            )
        if not self.claim_id:
            raise PipelineStageError("claim_id is required")
        if self.claim_kind not in CLAIM_KINDS:
            raise PipelineStageError(
                f"unknown claim_kind {self.claim_kind!r}; allowed: {sorted(CLAIM_KINDS)}"
            )
        if self.claim_kind in SCOPED_CLAIM_KINDS and not self.pipeline_stages:
            raise PipelineStageError(
                f"{self.claim_kind} claim {self.claim_id!r} must declare "
                "pipeline_stages: every efficacy/robustness/transfer claim names "
                "exactly which cascade stage(s) its outcome covers (fail closed)"
            )
        for stage in self.pipeline_stages:
            if stage not in PIPELINE_STAGES:
                raise PipelineStageError(
                    f"unknown pipeline_stage {stage!r}; allowed: {sorted(PIPELINE_STAGES)}"
                )
        if len(set(self.pipeline_stages)) != len(self.pipeline_stages):
            raise PipelineStageError("pipeline_stages must not contain duplicates")
        non_fusion = [s for s in self.pipeline_stages if s != "fusion"]
        if "fusion" in self.pipeline_stages and non_fusion:
            raise PipelineStageError(
                "fusion must not be combined with individual stages: either the "
                "claim covers the fused cascade (fusion) or it lists explicit stages"
            )
        if len(non_fusion) > 1 and not self.multi_stage_basis:
            raise PipelineStageError(
                f"claim {self.claim_id!r} spans multiple stages {non_fusion}: an "
                "explicit multi_stage_basis is required rather than silently "
                "generalizing from one stage (fail closed)"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "claim_kind": self.claim_kind,
            "pipeline_stages": list(self.pipeline_stages),
            "multi_stage_basis": self.multi_stage_basis,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def claim_scope_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise PipelineStageError(
                f"claim scope fails ctm_claim_scope_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClaimScope":
        if not isinstance(payload, dict):
            raise PipelineStageError("claim scope payload must be an object")
        return cls(
            claim_id=payload.get("claim_id", ""),
            claim_kind=payload.get("claim_kind", ""),
            pipeline_stages=tuple(payload.get("pipeline_stages", ())),
            multi_stage_basis=payload.get("multi_stage_basis", ""),
            schema_version=payload.get("schema_version", ""),
        )


def _mentioned_stages(prose_lower: str) -> set[str]:
    mentioned: set[str] = set()
    for stage, phrases in _STAGE_PROSE.items():
        if any(p in prose_lower for p in phrases):
            mentioned.add(stage)
    return mentioned


def check_prose_scope(prose: str, scope: ClaimScope) -> list[str]:
    """Return scope-conformance violations of manuscript ``prose`` against the
    structured ``scope`` (empty list = conformant).

    Violations:
    - prose names a cascade stage outside the declared scope (narrative scope
      may never exceed structured claim scope);
    - prose uses a broad term (invisibility / evasion / surveillance) without
      accompanying stage-bounded wording naming a declared stage.
    """
    if not isinstance(prose, str) or not prose.strip():
        return ["prose is empty: nothing to check is itself a scope failure"]
    scope.validate_against_schema()
    violations: list[str] = []
    prose_lower = prose.lower()
    declared = set(scope.pipeline_stages)
    mentioned = _mentioned_stages(prose_lower)
    if "fusion" in declared:
        # fusion covers the whole cascade; individual stage names are allowed
        allowed_mentioned = set(PIPELINE_STAGES)
    else:
        allowed_mentioned = declared
    out_of_scope = mentioned - allowed_mentioned
    for stage in sorted(out_of_scope):
        violations.append(
            f"prose names stage {stage!r} outside the declared scope "
            f"{sorted(declared)}: narrative scope may never exceed structured "
            "claim scope"
        )
    if any(term in prose_lower for term in BROAD_TERMS):
        bounds = [p for s in declared for p in _STAGE_BOUNDS.get(s, ())]
        if not any(b in prose_lower for b in bounds):
            violations.append(
                "prose uses a broad term (invisibility/evasion/surveillance) "
                "without stage-bounded wording naming a declared stage "
                f"{sorted(declared)}"
            )
    return violations


def require_prose_conformant(prose: str, scope: ClaimScope) -> None:
    """Fail-closed variant of :func:`check_prose_scope` for manuscript export."""
    violations = check_prose_scope(prose, scope)
    if violations:
        raise ScopeConformanceError(
            f"manuscript prose for claim {scope.claim_id!r} exceeds its "
            "structured pipeline-stage scope: " + "; ".join(violations)
        )


def require_cross_domain_bridge(
    scope: ClaimScope, *, source_stage: str, bridged: bool
) -> None:
    """FR-family (and other cross-domain) results do NOT inherit
    person-detection claims without an explicit bridge (SPEC-13 rule 5).

    ``bridged=True`` declares that an explicit bridge argument exists in the
    claim artifact; without it, a scope covering a stage other than the
    result's source stage refuses.
    """
    if source_stage not in PIPELINE_STAGES:
        raise PipelineStageError(f"unknown source_stage {source_stage!r}")
    scope.validate_against_schema()
    if "fusion" in scope.pipeline_stages and not bridged:
        raise ScopeConformanceError(
            f"cross-domain result from {source_stage!r} cannot claim fusion "
            "scope without an explicit bridge"
        )
    extras = set(scope.pipeline_stages) - {source_stage, "fusion"}
    if extras and not bridged:
        raise ScopeConformanceError(
            f"cross-domain result from {source_stage!r} does not inherit "
            f"{sorted(extras)} claims without an explicit bridge (fail closed)"
        )

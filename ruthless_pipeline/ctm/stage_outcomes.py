"""NR-04 — Stage outcomes and denominator integrity (additive, fail-closed).

Basis: RAC claim-scope contract (SPEC-13, ``pipeline_stage.py``) and the
NORECOGNITION review NR-04: reports must distinguish *direct stage
measurements* from *upstream-dependent outcomes* and from *stages that were
not evaluated*. A missing input to recognition is not a measured recognition
score; a skipped stage never receives a fabricated numeric result; one
upstream failure can never be counted as two independent downstream
successes.

Hard rules (fail closed with :class:`StageOutcomeError`):

- ``outcome_kind`` is exactly one of ``direct_measurement`` /
  ``upstream_dependent`` / ``not_evaluated`` on every stage outcome.
- ``not_evaluated`` carries NO numeric or discrete result: ``measured_value``,
  ``discrete_outcome`` and ``confidence_delta`` must all be absent.
- ``upstream_dependent`` must name its ``upstream_stages``;
  ``direct_measurement`` and ``not_evaluated`` must not.
- Confidence changes (``confidence_delta``) and discrete task outcomes
  (``discrete_outcome``) are separate fields and are never merged.
- :class:`StageOutcomeSet` refuses any downstream outcome that claims
  ``success`` while depending on a stage whose discrete outcome is
  ``failure`` — one upstream failure is never two independent successes.
- :func:`multi_model_summary` refuses to emit an unlabeled summary: every
  record must carry specimen, cohort and condition context, and the summary
  states explicitly whether specimen / cohort / conditions were shared.

This module is additive; it mutates no frozen schema and promotes no
synthetic evidence to measured.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .errors import CTMBridgeError
from .pipeline_stage import PIPELINE_STAGES

STAGE_OUTCOMES_SCHEMA_VERSION = "rac-ctm-stage-outcomes/1.0"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "ctm_stage_outcomes_v1.schema.json"
)

#: Outcome provenance kinds (NR-04(a)).
OUTCOME_KINDS = frozenset({"direct_measurement", "upstream_dependent", "not_evaluated"})

#: Discrete task outcomes, kept separate from confidence deltas (NR-04(e)).
DISCRETE_OUTCOMES = frozenset({"success", "failure", "inconclusive"})


class StageOutcomeError(CTMBridgeError):
    """Stage-outcome integrity contract violated (NR-04). Fail closed."""


def _require_finite(value: float, *, field_name: str) -> float:
    v = float(value)
    if not math.isfinite(v):
        raise StageOutcomeError(f"{field_name} must be finite, got {value!r}")
    return v


@dataclass(frozen=True)
class StageOutcome:
    """One pipeline stage's outcome with explicit provenance kind."""

    stage: str
    outcome_kind: str
    measured_value: float | None = None
    discrete_outcome: str | None = None
    confidence_delta: float | None = None
    upstream_stages: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        if self.stage not in PIPELINE_STAGES:
            raise StageOutcomeError(
                f"unknown stage {self.stage!r}; allowed: {sorted(PIPELINE_STAGES)}"
            )
        if self.outcome_kind not in OUTCOME_KINDS:
            raise StageOutcomeError(
                f"unknown outcome_kind {self.outcome_kind!r}; "
                f"allowed: {sorted(OUTCOME_KINDS)}"
            )
        for up in self.upstream_stages:
            if up not in PIPELINE_STAGES:
                raise StageOutcomeError(f"unknown upstream stage {up!r}")
        if len(set(self.upstream_stages)) != len(self.upstream_stages):
            raise StageOutcomeError("upstream_stages must not contain duplicates")
        if self.discrete_outcome is not None and self.discrete_outcome not in DISCRETE_OUTCOMES:
            raise StageOutcomeError(
                f"unknown discrete_outcome {self.discrete_outcome!r}; "
                f"allowed: {sorted(DISCRETE_OUTCOMES)}"
            )
        if self.measured_value is not None:
            object.__setattr__(
                self, "measured_value",
                _require_finite(self.measured_value, field_name="measured_value"),
            )
        if self.confidence_delta is not None:
            object.__setattr__(
                self, "confidence_delta",
                _require_finite(self.confidence_delta, field_name="confidence_delta"),
            )
        if self.outcome_kind == "not_evaluated":
            # NR-04(c): a skipped stage cannot receive a fabricated numeric
            # result — not a value, not a discrete outcome, not a delta.
            if (
                self.measured_value is not None
                or self.discrete_outcome is not None
                or self.confidence_delta is not None
            ):
                raise StageOutcomeError(
                    f"stage {self.stage!r} is not_evaluated but carries a "
                    "result: a skipped stage never receives a fabricated "
                    "numeric or discrete outcome (fail closed)"
                )
            if self.upstream_stages:
                raise StageOutcomeError(
                    f"stage {self.stage!r} is not_evaluated and must not "
                    "declare upstream_stages"
                )
        elif self.outcome_kind == "upstream_dependent":
            # NR-04(a): an upstream-dependent outcome (e.g. recognition
            # scored only when detection produced an input) is not a direct
            # stage measurement and must name its inputs.
            if not self.upstream_stages:
                raise StageOutcomeError(
                    f"stage {self.stage!r} is upstream_dependent and must "
                    "declare upstream_stages (fail closed)"
                )
        else:  # direct_measurement
            if self.upstream_stages:
                raise StageOutcomeError(
                    f"stage {self.stage!r} is a direct_measurement and must "
                    "not declare upstream_stages; dependent outcomes use "
                    "outcome_kind='upstream_dependent'"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "stage": self.stage,
            "outcome_kind": self.outcome_kind,
        }
        if self.measured_value is not None:
            payload["measured_value"] = self.measured_value
        if self.discrete_outcome is not None:
            payload["discrete_outcome"] = self.discrete_outcome
        if self.confidence_delta is not None:
            payload["confidence_delta"] = self.confidence_delta
        if self.upstream_stages:
            payload["upstream_stages"] = list(self.upstream_stages)
        if self.note:
            payload["note"] = self.note
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StageOutcome":
        if not isinstance(payload, Mapping):
            raise StageOutcomeError("stage outcome payload must be an object")
        return cls(
            stage=payload.get("stage", ""),
            outcome_kind=payload.get("outcome_kind", ""),
            measured_value=payload.get("measured_value"),
            discrete_outcome=payload.get("discrete_outcome"),
            confidence_delta=payload.get("confidence_delta"),
            upstream_stages=tuple(payload.get("upstream_stages", ())),
            note=payload.get("note", ""),
        )


@dataclass(frozen=True)
class StageOutcomeSet:
    """A complete, schema-versioned set of per-stage outcomes for one claim
    artifact. Hash-pinned via :meth:`outcomes_sha256`."""

    set_id: str
    evidence_label: str
    outcomes: tuple[StageOutcome, ...]
    schema_version: str = STAGE_OUTCOMES_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != STAGE_OUTCOMES_SCHEMA_VERSION:
            raise StageOutcomeError(
                f"unsupported stage-outcomes schema_version: {self.schema_version!r}"
            )
        if not self.set_id:
            raise StageOutcomeError("set_id is required")
        if not self.evidence_label:
            raise StageOutcomeError("evidence_label is required")
        if not self.outcomes:
            raise StageOutcomeError("outcomes must be non-empty")
        stages = [o.stage for o in self.outcomes]
        if len(set(stages)) != len(stages):
            raise StageOutcomeError("each stage may appear at most once per outcome set")
        by_stage = {o.stage: o for o in self.outcomes}
        failed = {
            o.stage for o in self.outcomes if o.discrete_outcome == "failure"
        }
        for o in self.outcomes:
            for up in o.upstream_stages:
                if up not in by_stage:
                    raise StageOutcomeError(
                        f"stage {o.stage!r} depends on {up!r}, which has no "
                        "outcome record in this set: an undeclared upstream "
                        "stage cannot ground a dependent outcome (fail closed)"
                    )
            # NR-04(b): one upstream failure is never counted as an
            # independent downstream success — whether one or several
            # downstream stages attempt it.
            if o.discrete_outcome == "success" and failed & set(o.upstream_stages):
                raise StageOutcomeError(
                    f"stage {o.stage!r} claims success while upstream stage(s) "
                    f"{sorted(failed & set(o.upstream_stages))} failed: one "
                    "upstream failure cannot be counted as an independent "
                    "success (fail closed)"
                )
            if o.outcome_kind == "upstream_dependent":
                missing_input = [
                    up
                    for up in o.upstream_stages
                    if by_stage[up].outcome_kind == "not_evaluated"
                    or (
                        by_stage[up].measured_value is None
                        and by_stage[up].discrete_outcome is None
                    )
                ]
                if missing_input and o.measured_value is not None:
                    raise StageOutcomeError(
                        f"stage {o.stage!r} carries a measured value but its "
                        f"input stage(s) {missing_input} produced no result: "
                        "a missing input is not a measured score (fail closed)"
                    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "set_id": self.set_id,
            "evidence_label": self.evidence_label,
            "outcomes": [o.to_dict() for o in self.outcomes],
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def outcomes_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise StageOutcomeError(
                f"stage outcome set fails ctm_stage_outcomes_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StageOutcomeSet":
        if not isinstance(payload, Mapping):
            raise StageOutcomeError("stage outcome set payload must be an object")
        return cls(
            set_id=payload.get("set_id", ""),
            evidence_label=payload.get("evidence_label", ""),
            outcomes=tuple(
                StageOutcome.from_dict(o) for o in payload.get("outcomes", ())
            ),
            schema_version=payload.get("schema_version", ""),
        )


# ---------------------------------------------------------------------------
# NR-04(d): multi-model summaries must state whether specimen, cohort, and
# conditions were shared. An unlabeled summary is refused (fail closed).
# ---------------------------------------------------------------------------

MULTI_MODEL_SUMMARY_SCHEMA_VERSION = "rac-ctm-multi-model-summary/1.0"

_CONTEXT_FIELDS = ("specimen_id", "cohort_id", "condition_ids")


def multi_model_summary(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize per-model outcome records with explicit shared-context labels.

    Every record must carry ``model_id``, ``specimen_id``, ``cohort_id``,
    ``condition_ids`` (list) and ``outcome``. A record missing context makes
    the summary unlabelable and is refused. The result states — for specimen,
    cohort, and conditions separately — whether all models shared the same
    context, plus the count of conditions shared by every model.
    """
    rows = list(records)
    if len(rows) < 2:
        raise StageOutcomeError(
            "multi-model summary requires at least 2 model records"
        )
    for row in rows:
        missing = [f for f in ("model_id", "outcome") + _CONTEXT_FIELDS if f not in row]
        if missing:
            raise StageOutcomeError(
                f"model record {row.get('model_id', '<unknown>')!r} is missing "
                f"context field(s) {missing}: a multi-model summary without "
                "specimen/cohort/condition labels is refused (fail closed)"
            )
        if not row["condition_ids"]:
            raise StageOutcomeError(
                f"model record {row['model_id']!r} has empty condition_ids"
            )
    models = sorted({str(r["model_id"]) for r in rows})
    if len(models) != len(rows):
        raise StageOutcomeError("duplicate model_id in multi-model records")
    specimens = {str(r["specimen_id"]) for r in rows}
    cohorts = {str(r["cohort_id"]) for r in rows}
    condition_sets = [set(map(str, r["condition_ids"])) for r in rows]
    shared_conditions = sorted(set.intersection(*condition_sets))
    return {
        "schema_version": MULTI_MODEL_SUMMARY_SCHEMA_VERSION,
        "n_models": len(models),
        "model_ids": models,
        "specimen_shared": len(specimens) == 1,
        "cohort_shared": len(cohorts) == 1,
        "conditions_shared": all(cs == condition_sets[0] for cs in condition_sets),
        "n_shared_conditions": len(shared_conditions),
        "shared_condition_ids": shared_conditions,
        "label_note": (
            "context labels only: specimen_shared/cohort_shared/"
            "conditions_shared describe measurement context, not efficacy"
        ),
    }

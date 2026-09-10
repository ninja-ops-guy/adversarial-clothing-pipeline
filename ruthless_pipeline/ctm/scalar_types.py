"""SPEC-2 — Scalar-class typing and analysis-role separation (CTM-A extension).

Lesson L3: a perturbation tolerance, an evaluation metric, and a measured
pattern feature are all scalars but different KINDS of thing. The CTM
attribution layer rests on never conflating them:

- ``scalar_class`` is IMMUTABLE after ingestion:
  ``pattern_feature | evaluation_metric | perturbation_tolerance |
  effect_size | covariate``.
- ``analysis_role`` is a SEPARATE axis:
  ``predictor | outcome | adjustment_covariate | descriptive_only``.

A perturbation tolerance may be used as a predictor, but it stays typed
``perturbation_tolerance`` — it can never be silently reclassed as a
``pattern_feature`` (:meth:`TypedScalar.reclass` always refuses;
:meth:`TypedScalar.with_analysis_role` re-roles without reclassing).

An evaluation metric may be an outcome, but it may not be promoted into a
causal mechanism merely because it predicts another metric
(:func:`require_class_consistency` refuses any claim artifact whose implied
class differs from the registered class).

CTM-F association/promotion reports must render BOTH scalar class and
analysis role — :meth:`TypedScalar.to_dict` always serializes both.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .errors import ScalarTypingError

SCALAR_TYPING_SCHEMA_VERSION = "rac-ctm-scalar-typing/1.0"

#: Immutable epistemic class of a quantitative value (SPEC-2).
SCALAR_CLASSES = frozenset({
    "pattern_feature",
    "evaluation_metric",
    "perturbation_tolerance",
    "effect_size",
    "covariate",
})

#: Separate analysis axis; independent of scalar_class.
ANALYSIS_ROLES = frozenset({
    "predictor",
    "outcome",
    "adjustment_covariate",
    "descriptive_only",
})

RELATION_TYPES = frozenset({
    "association",
    "causal_mechanism",
    "descriptive",
})


@dataclass(frozen=True)
class TypedScalar:
    """A quantitative value with an immutable scalar class and a separate,
    mutable-by-reconstruction analysis role.

    The dataclass is frozen: ``scalar_class`` cannot be mutated in place,
    and :meth:`reclass` refuses unconditionally — there is no code path that
    silently coerces one scalar class into another.
    """

    value_id: str
    scalar_class: str
    analysis_role: str = "descriptive_only"
    relation_type: str | None = None
    outcome_id: str | None = None
    schema_version: str = SCALAR_TYPING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCALAR_TYPING_SCHEMA_VERSION:
            raise ScalarTypingError(
                f"unsupported scalar typing schema_version: {self.schema_version!r}"
            )
        if not self.value_id:
            raise ScalarTypingError("value_id is required")
        if self.scalar_class not in SCALAR_CLASSES:
            raise ScalarTypingError(
                f"unknown scalar_class {self.scalar_class!r}; allowed: "
                f"{sorted(SCALAR_CLASSES)} (fail closed)"
            )
        if self.analysis_role not in ANALYSIS_ROLES:
            raise ScalarTypingError(
                f"unknown analysis_role {self.analysis_role!r}; allowed: "
                f"{sorted(ANALYSIS_ROLES)} (fail closed)"
            )
        if self.relation_type is not None and self.relation_type not in RELATION_TYPES:
            raise ScalarTypingError(
                f"unknown relation_type {self.relation_type!r}; allowed: "
                f"{sorted(RELATION_TYPES)} (fail closed)"
            )
        if self.relation_type == "causal_mechanism":
            # An evaluation metric may not be promoted into a causal mechanism
            # merely because it predicts another metric; tolerances are
            # optimizer-side quantities and likewise can never be mechanisms.
            if self.scalar_class in {"evaluation_metric", "perturbation_tolerance"}:
                raise ScalarTypingError(
                    f"a {self.scalar_class} may not carry relation_type "
                    "'causal_mechanism' (fail closed: prediction of a metric "
                    "does not promote it to a mechanism)"
                )
        if self.analysis_role == "outcome" and not self.outcome_id:
            raise ScalarTypingError("outcome_id is required when analysis_role='outcome'")

    # -- class immutability ----------------------------------------------------

    def reclass(self, new_scalar_class: str) -> "TypedScalar":
        """REFUSED unconditionally: scalar_class is immutable after ingestion.
        A tolerance used as a predictor stays a tolerance; it may never be
        serialized or discussed as a measured pattern feature."""
        raise ScalarTypingError(
            f"scalar_class is immutable: refusing to reclass {self.value_id!r} "
            f"from {self.scalar_class!r} to {new_scalar_class!r}. Register a "
            "new value_id if a genuinely different quantity is being measured."
        )

    def with_analysis_role(
        self,
        analysis_role: str,
        *,
        relation_type: str | None = None,
        outcome_id: str | None = None,
    ) -> "TypedScalar":
        """Return a copy with a new analysis role. The scalar_class is
        preserved verbatim — re-roling is legal, reclassing never is."""
        return TypedScalar(
            value_id=self.value_id,
            scalar_class=self.scalar_class,
            analysis_role=analysis_role,
            relation_type=relation_type if relation_type is not None else self.relation_type,
            outcome_id=outcome_id if outcome_id is not None else self.outcome_id,
            schema_version=self.schema_version,
        )

    # -- canonical serialization ------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Both scalar_class AND analysis_role are always rendered (CTM-F
        association/promotion reports must show both axes)."""
        return {
            "schema_version": self.schema_version,
            "value_id": self.value_id,
            "scalar_class": self.scalar_class,
            "analysis_role": self.analysis_role,
            "relation_type": self.relation_type,
            "outcome_id": self.outcome_id,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def typed_scalar_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TypedScalar":
        if not isinstance(payload, dict):
            raise ScalarTypingError("typed scalar payload must be an object")
        return cls(
            value_id=payload.get("value_id", ""),
            scalar_class=payload.get("scalar_class", ""),
            analysis_role=payload.get("analysis_role", "descriptive_only"),
            relation_type=payload.get("relation_type"),
            outcome_id=payload.get("outcome_id"),
            schema_version=payload.get("schema_version", ""),
        )


def require_class_consistency(registered: TypedScalar, implied_scalar_class: str) -> None:
    """Fail closed when a claim artifact's prose/structured interpretation
    implies a scalar class different from the registered class."""
    if implied_scalar_class != registered.scalar_class:
        raise ScalarTypingError(
            f"claim interpretation implies scalar_class {implied_scalar_class!r} "
            f"but {registered.value_id!r} is registered as "
            f"{registered.scalar_class!r}: scalar classes are immutable and "
            "cross-class statements must use explicit roles (fail closed)"
        )

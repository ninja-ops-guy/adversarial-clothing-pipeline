"""SPEC-1 — Factor-swap validity contract (CTM-A extension, enforced CTM-C/CTM-F).

Lesson L2: a decomposition experiment is only interpretable if the swapped
factor's relationship to the optimizer's constraint set is recorded. An
out-of-optimum swap (e.g. repainting a pattern optimized under a hard palette
constraint) is an *invalidation test*, not a main-effect probe; pooling the
two silently is the scientific error class this module makes mechanically
impossible.

Hard rules (fail closed with :class:`SwapValidityError`):

- ``interpretation_class`` is DERIVED, never user-asserted. Serializing a
  record whose asserted class disagrees with the derived class is refused.
- ``out_of_optimum`` scope always derives ``invalidation_test`` — an
  out-of-optimum swap cannot serialize as ``main_effect_probe``.
- ``main_effect_probe`` is derived only when the swap stays within the
  preregistered optimization neighborhood AND the varied factor is an
  ``optimized_variable`` AND every held factor has a known relationship that
  keeps it valid (``hard_constraint``, ``bounded_constraint``,
  ``soft_regularizer`` or ``unconstrained``).
- ``reoptimized_after_swap`` derives ``reoptimized_swap``: reoptimization
  rows cannot be pooled with non-reoptimized main-effect rows without an
  explicit interaction model (:func:`check_pooling`).
- :func:`check_pooling` refuses to pool rows of different interpretation
  classes (CTM-F refuses to pool ``invalidation_test`` with
  ``main_effect_probe``).
- Missing or unknown factor relationships fail closed for controlled-effect
  promotion (:func:`require_controlled_effect_eligible`) but may remain
  observational/exploratory (:func:`is_observational_only`).

This module is additive: it does not mutate the frozen
``schemas/ctm_matched_null_v1.schema.json`` core contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .errors import SwapValidityError

SWAP_VALIDITY_SCHEMA_VERSION = "rac-ctm-swap-validity/1.0"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "ctm_swap_validity_v1.schema.json"
)

#: Required factor_relationships enum (SPEC-1).
FACTOR_RELATIONSHIPS = frozenset({
    "optimized_variable",
    "hard_constraint",
    "bounded_constraint",
    "soft_regularizer",
    "derived_dependency",
    "unconstrained",
    "posthoc_only",
})

SWAP_SCOPES = frozenset({
    "within_optimization_neighborhood",
    "out_of_optimum",
    "reoptimized_after_swap",
})

INTERPRETATION_CLASSES = frozenset({
    "main_effect_probe",
    "invalidation_test",
    "reoptimized_swap",
})

#: Held-factor relationships that keep a held factor valid while the varied
#: factor is probed inside the optimization neighborhood.
_HELD_OK_FOR_MAIN_EFFECT = frozenset({
    "hard_constraint",
    "bounded_constraint",
    "soft_regularizer",
    "unconstrained",
})

_SHA256_LEN = 64


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def derive_interpretation_class(
    *,
    swap_scope: str,
    varied_factor_relationship: str,
    held_relationships: Iterable[str],
) -> str:
    """Derive the interpretation class. Pure function; the ONLY source of
    interpretation classes in CTM. Raises nothing for unknown inputs —
    unknowns yield ``invalidation_test``-incompatible conservative results
    handled by the caller's fail-closed validation."""
    if swap_scope == "out_of_optimum":
        return "invalidation_test"
    if swap_scope == "reoptimized_after_swap":
        return "reoptimized_swap"
    if swap_scope == "within_optimization_neighborhood":
        if varied_factor_relationship != "optimized_variable":
            return "invalidation_test"
        if any(rel not in _HELD_OK_FOR_MAIN_EFFECT for rel in held_relationships):
            return "invalidation_test"
        return "main_effect_probe"
    raise SwapValidityError(f"unknown swap_scope {swap_scope!r} (fail closed)")


@dataclass(frozen=True)
class SwapValidity:
    """Immutable, versioned factor-swap validity record.

    ``interpretation_class`` is excluded from construction: it is derived by
    :meth:`__post_init__` from the swap semantics and can never be asserted.
    """

    varied_factor: str
    factor_relationships: dict[str, str]
    constraint_set_ref: str
    swap_scope: str = "within_optimization_neighborhood"
    held_factors: tuple[str, ...] = ()
    schema_version: str = SWAP_VALIDITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SWAP_VALIDITY_SCHEMA_VERSION:
            raise SwapValidityError(
                f"unsupported swap_validity schema_version: {self.schema_version!r}"
            )
        if not self.varied_factor:
            raise SwapValidityError("varied_factor is required")
        if self.swap_scope not in SWAP_SCOPES:
            raise SwapValidityError(
                f"unknown swap_scope {self.swap_scope!r}; allowed: {sorted(SWAP_SCOPES)}"
            )
        if not _is_sha256(self.constraint_set_ref):
            raise SwapValidityError(
                "constraint_set_ref must be a lowercase 64-hex sha256 of the "
                "optimizer constraint set (SPEC-5 optimizer_constraints block)"
            )
        if not self.factor_relationships:
            raise SwapValidityError(
                "factor_relationships must not be empty: the varied factor's "
                "relationship to the optimizer constraint set is required"
            )
        for factor, rel in sorted(self.factor_relationships.items()):
            if not factor:
                raise SwapValidityError("factor_relationships keys must be non-empty")
            if rel not in FACTOR_RELATIONSHIPS:
                raise SwapValidityError(
                    f"unknown factor relationship {rel!r} for factor {factor!r}; "
                    f"allowed: {sorted(FACTOR_RELATIONSHIPS)} (fail closed)"
                )
        # The varied factor's relationship MUST be recorded (fail closed).
        if self.varied_factor not in self.factor_relationships:
            raise SwapValidityError(
                f"factor_relationships is missing the varied factor "
                f"{self.varied_factor!r}: an unrecorded varied-factor "
                "relationship cannot be interpreted (fail closed)"
            )
        for held in self.held_factors:
            if not held:
                raise SwapValidityError("held_factors must be non-empty strings")
            if held == self.varied_factor:
                raise SwapValidityError(
                    "held_factors must not contain the varied factor"
                )
            if held not in self.factor_relationships:
                raise SwapValidityError(
                    f"factor_relationships is missing held factor {held!r} "
                    "(fail closed: missing relationship)"
                )

    @property
    def interpretation_class(self) -> str:
        """Derived, never user-asserted."""
        return derive_interpretation_class(
            swap_scope=self.swap_scope,
            varied_factor_relationship=self.factor_relationships[self.varied_factor],
            held_relationships=tuple(
                self.factor_relationships[h] for h in self.held_factors
            ),
        )

    # -- canonical serialization --------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "varied_factor": self.varied_factor,
            "held_factors": list(self.held_factors),
            "factor_relationships": dict(
                sorted(self.factor_relationships.items())
            ),
            "swap_scope": self.swap_scope,
            "constraint_set_ref": self.constraint_set_ref,
            "interpretation_class": self.interpretation_class,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def swap_validity_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise SwapValidityError(
                f"swap_validity record fails ctm_swap_validity_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SwapValidity":
        """Parse a serialized record, REFUSING any user-asserted
        interpretation_class that disagrees with the derived class.
"""
        if not isinstance(payload, dict):
            raise SwapValidityError("swap_validity payload must be an object")
        asserted = payload.get("interpretation_class")
        record = cls(
            varied_factor=payload.get("varied_factor", ""),
            held_factors=tuple(payload.get("held_factors", ())),
            factor_relationships=dict(payload.get("factor_relationships", {})),
            swap_scope=payload.get("swap_scope", ""),
            constraint_set_ref=payload.get("constraint_set_ref", ""),
            schema_version=payload.get("schema_version", ""),
        )
        if asserted is not None and asserted != record.interpretation_class:
            raise SwapValidityError(
                f"user-asserted interpretation_class {asserted!r} disagrees with "
                f"the derived class {record.interpretation_class!r}: "
                "interpretation_class is derived, never user-asserted "
                f"(an out-of-optimum swap cannot serialize as main_effect_probe)"
            )
        return record


# ---------------------------------------------------------------------------
# Pooling and promotion gates (CTM-F enforcement points)
# ---------------------------------------------------------------------------

def check_pooling(rows: Iterable[SwapValidity], *, interaction_model: bool = False) -> str:
    """Return the shared interpretation class of a pool of swap-validity
    records, or refuse (fail closed) when the pool mixes classes.

    CTM-F refuses to pool ``invalidation_test`` rows with
    ``main_effect_probe`` rows. ``reoptimized_swap`` rows cannot be pooled
    with non-reoptimized main-effect rows without an explicit interaction
    model (``interaction_model=True``); an interaction model never legalizes
    pooling with ``invalidation_test`` rows.
    """
    rows = list(rows)
    if not rows:
        raise SwapValidityError("cannot pool an empty set of swap-validity rows")
    classes = {row.interpretation_class for row in rows}
    if len(classes) == 1:
        return classes.pop()
    if "invalidation_test" in classes:
        raise SwapValidityError(
            f"refusing to pool interpretation classes {sorted(classes)}: "
            "invalidation_test rows can never be pooled with other rows"
        )
    if classes == {"main_effect_probe", "reoptimized_swap"}:
        if not interaction_model:
            raise SwapValidityError(
                "reoptimization after a swap cannot be pooled with "
                "non-reoptimized main-effect rows without an explicit "
                "interaction model (pass interaction_model=True to declare one)"
            )
        return "main_effect_probe"
    raise SwapValidityError(
        f"refusing to pool interpretation classes {sorted(classes)} (fail closed)"
    )


def require_controlled_effect_eligible(swap_validity: SwapValidity | None) -> None:
    """Fail-closed gate for controlled-effect promotion.

    Missing swap semantics (``None``), or any record that does not derive
    ``main_effect_probe``, refuses promotion. Observational/exploratory claims
    may proceed regardless — see :func:`is_observational_only`.
    """
    if swap_validity is None:
        raise SwapValidityError(
            "controlled-effect promotion refused: swap_validity semantics are "
            "absent (missing factor relationships fail closed)"
        )
    if swap_validity.interpretation_class != "main_effect_probe":
        raise SwapValidityError(
            f"controlled-effect promotion refused: swap derives "
            f"{swap_validity.interpretation_class!r}, not 'main_effect_probe' "
            "(only within-neighborhood main-effect probes support "
            "controlled-effect claims)"
        )


def is_observational_only(swap_validity: SwapValidity | None) -> bool:
    """True when the record can only support observational/exploratory claims.
    Observational claims may proceed with missing or non-main-effect swap
    semantics; only controlled-effect promotion fails closed."""
    if swap_validity is None:
        return True
    return swap_validity.interpretation_class != "main_effect_probe"

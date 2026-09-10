"""Semantic validation layer for RAC constraint encoders.

Solver certificates validate a compiled problem. They do not establish that the
encoder faithfully represents the scientific constraint specification. This
module keeps that second obligation explicit through differential probes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .cic_adapter import CICError, ConstraintRepresentation


SemanticEvaluator = Callable[[Mapping[str, Any]], bool]
CompiledEvaluator = Callable[[ConstraintRepresentation, Mapping[str, Any]], bool]


@dataclass(frozen=True)
class SemanticValidationReport:
    constraint_set_id: str
    constraint_version: str
    representation: str
    encoder_id: str
    encoder_version: str
    semantic_hash: str
    compiled_hash: str
    probe_count: int
    method: str = "differential_probe"
    validation_scope: str = "tested_probe_assignments_only"


def differential_validate_encoding(
    representation: ConstraintRepresentation,
    probes: Sequence[Mapping[str, Any]],
    *,
    semantic_evaluator: SemanticEvaluator,
    compiled_evaluator: CompiledEvaluator,
) -> SemanticValidationReport:
    """Compare reference semantics and one compiled encoding on fixed probes.

    This is a regression/property-testing gate, not a formal equivalence proof.
    The caller controls probe construction and may use exhaustive assignments
    for small domains or preregistered boundary/property cases for larger ones.
    """

    representation.validate()
    if not probes:
        raise CICError("semantic differential validation requires probes")

    for index, assignment in enumerate(probes):
        missing = [
            name
            for name in representation.semantic_variables
            if name not in assignment
        ]
        if missing:
            raise CICError(
                f"semantic probe {index} missing variables: {missing}"
            )
        reference = bool(semantic_evaluator(assignment))
        compiled = bool(compiled_evaluator(representation, assignment))
        if reference != compiled:
            raise CICError(
                "encoder semantic mismatch at probe "
                f"{index}: reference={reference} compiled={compiled}"
            )

    return SemanticValidationReport(
        constraint_set_id=representation.constraint_set_id,
        constraint_version=representation.constraint_version,
        representation=representation.representation,
        encoder_id=representation.encoder_id,
        encoder_version=representation.encoder_version,
        semantic_hash=representation.semantic_hash,
        compiled_hash=representation.compiled_hash,
        probe_count=len(probes),
    )

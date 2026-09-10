"""Bounded formal-methods adapter for RAC experimental governance.

This module is deliberately efficacy-blind. It can establish feasibility,
validate solver assignments, preserve semantic/compiled identity separation,
and emit structural routing metadata. It must never score adversarial efficacy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Callable, Mapping, Protocol, Sequence


class CICError(RuntimeError):
    """Fail-closed CIC adapter error."""


class SolveStatus(str, Enum):
    SAT = "SAT"
    UNSAT = "UNSAT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ConstraintRepresentation:
    """Stable representation contract for CNF/PB/SMT or external encodings."""

    representation: str
    semantic_payload: Mapping[str, Any]
    compiled_payload: Mapping[str, Any]
    semantic_variables: tuple[str, ...]
    auxiliary_variables: tuple[str, ...] = ()
    independent_support: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.representation not in {"CNF", "PB", "SMT", "EXTERNAL"}:
            raise CICError(f"unsupported representation: {self.representation}")
        semantic = set(self.semantic_variables)
        auxiliary = set(self.auxiliary_variables)
        support = set(self.independent_support)
        if not semantic:
            raise CICError("scientific projection must contain semantic variables")
        if semantic & auxiliary:
            raise CICError("semantic and auxiliary variable sets must be disjoint")
        if not support <= semantic:
            raise CICError("independent support must be a subset of semantic variables")

    @property
    def semantic_hash(self) -> str:
        return _digest({"representation": self.representation, "payload": self.semantic_payload})

    @property
    def compiled_hash(self) -> str:
        return _digest({"representation": self.representation, "payload": self.compiled_payload})


@dataclass(frozen=True)
class StructuralMetrics:
    variable_count: int
    semantic_variable_count: int
    auxiliary_variable_count: int
    independent_support_size: int
    constraint_count: int | None = None
    graph_density: float | None = None
    treewidth_estimate: float | None = None


@dataclass(frozen=True)
class SolverReply:
    status: SolveStatus
    assignment: Mapping[str, Any] | None = None
    unsat_core: tuple[str, ...] = ()
    proof_artifact: str | None = None
    backend: str = "unknown"


@dataclass(frozen=True)
class CICResult:
    status: SolveStatus
    semantic_hash: str
    compiled_hash: str
    scientific_projection: Mapping[str, Any] | None
    independent_support: tuple[str, ...]
    unsat_core: tuple[str, ...]
    proof_artifact: str | None
    backend: str
    metrics: StructuralMetrics


class SolverBackend(Protocol):
    def check(self, representation: ConstraintRepresentation, *, explain_unsat: bool) -> SolverReply:
        ...


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _project_assignment(
    assignment: Mapping[str, Any], semantic_variables: Sequence[str]
) -> dict[str, Any]:
    missing = [name for name in semantic_variables if name not in assignment]
    if missing:
        raise CICError(f"SAT assignment missing semantic variables: {missing}")
    return {name: assignment[name] for name in semantic_variables}


def check(
    representation: ConstraintRepresentation,
    *,
    backend: SolverBackend,
    assignment_verifier: Callable[[Mapping[str, Any]], bool],
    explain_unsat: bool = True,
    metrics: StructuralMetrics | None = None,
) -> CICResult:
    """Run a bounded feasibility check with independent SAT verification.

    The adapter never receives or emits efficacy scores. A SAT assignment is
    accepted only after an independent verifier confirms it. Only semantic
    variables are returned in the scientific projection; auxiliaries are
    structurally incapable of entering downstream scientific manifests.
    """

    representation.validate()
    reply = backend.check(representation, explain_unsat=explain_unsat)
    if not isinstance(reply.status, SolveStatus):
        raise CICError("backend returned invalid solve status")

    projection: Mapping[str, Any] | None = None
    if reply.status is SolveStatus.SAT:
        if reply.assignment is None:
            raise CICError("SAT backend reply requires assignment")
        if not assignment_verifier(reply.assignment):
            raise CICError("independent verifier rejected SAT assignment")
        projection = _project_assignment(reply.assignment, representation.semantic_variables)
    elif reply.assignment is not None:
        raise CICError("non-SAT backend reply must not carry an assignment")

    structural = metrics or StructuralMetrics(
        variable_count=len(representation.semantic_variables) + len(representation.auxiliary_variables),
        semantic_variable_count=len(representation.semantic_variables),
        auxiliary_variable_count=len(representation.auxiliary_variables),
        independent_support_size=len(representation.independent_support),
    )

    return CICResult(
        status=reply.status,
        semantic_hash=representation.semantic_hash,
        compiled_hash=representation.compiled_hash,
        scientific_projection=projection,
        independent_support=tuple(representation.independent_support),
        unsat_core=tuple(reply.unsat_core) if explain_unsat else (),
        proof_artifact=reply.proof_artifact,
        backend=reply.backend,
        metrics=structural,
    )


def require_cross_encoding_agreement(results: Sequence[CICResult]) -> None:
    """Require semantically equivalent exact fixtures to agree on feasibility.

    Callers are responsible for supplying results that represent the same
    frozen semantic fixture. Compiled hashes may differ by design.
    """

    if len(results) < 2:
        raise CICError("cross-encoding agreement requires at least two results")
    semantic_hashes = {result.semantic_hash for result in results}
    if len(semantic_hashes) != 1:
        raise CICError("results do not share one semantic identity")
    statuses = {result.status for result in results}
    if len(statuses) != 1:
        raise CICError("semantically equivalent encodings disagree on solve status")

"""Bounded formal-methods adapter for RAC experimental governance.

This module is deliberately efficacy-blind. It establishes feasibility,
validates solver assignments, preserves semantic/compiled identity separation,
and emits structural routing metadata. It must never score adversarial efficacy.

UNSAT certificates in this module attest only to the compiled representation.
They do not prove that an encoder faithfully represents the scientific
constraint specification; semantic encoder validation remains a separate gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping, Protocol, Sequence

from .ids import GovernanceId, IdKind


class CICError(RuntimeError):
    """Fail-closed CIC governance boundary error."""


class SolveStatus(str, Enum):
    SAT = "SAT"
    UNSAT = "UNSAT"
    UNKNOWN = "UNKNOWN"


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CICError(f"{field} is required")


def _require_sha256(value: str, field: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CICError(f"{field} must be a lowercase sha256")


def _require_constraint_id(value: str) -> None:
    try:
        parsed = GovernanceId.parse(value)
    except Exception as exc:
        raise CICError("constraint_set_id must be a valid governance identifier") from exc
    if parsed.kind is not IdKind.CONSTRAINT or parsed.is_legacy_alias:
        raise CICError("constraint_set_id must use the canonical RAC-CS prefix")


@dataclass(frozen=True)
class ConstraintRepresentation:
    """One compiled form of one immutable scientific constraint specification."""

    representation: str
    semantic_payload: Mapping[str, Any]
    compiled_payload: Any
    semantic_variables: tuple[str, ...]
    constraint_set_id: str
    constraint_version: str
    encoder_id: str
    encoder_version: str
    auxiliary_variables: tuple[str, ...] = ()
    independent_support: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.representation not in {"CNF", "PB", "SMT", "EXTERNAL"}:
            raise CICError(f"unsupported representation: {self.representation}")
        _require_constraint_id(self.constraint_set_id)
        _require_text(self.constraint_version, "constraint_version")
        _require_text(self.encoder_id, "encoder_id")
        _require_text(self.encoder_version, "encoder_version")
        semantic = set(self.semantic_variables)
        auxiliary = set(self.auxiliary_variables)
        independent = set(self.independent_support)
        if not semantic:
            raise CICError("scientific projection must contain semantic variables")
        if len(semantic) != len(self.semantic_variables):
            raise CICError("semantic variables must be unique")
        if len(auxiliary) != len(self.auxiliary_variables):
            raise CICError("auxiliary variables must be unique")
        if semantic & auxiliary:
            raise CICError("semantic and auxiliary variable sets must be disjoint")
        if not independent <= semantic:
            raise CICError("independent support must be a subset of semantic variables")

    @property
    def semantic_hash(self) -> str:
        """Hash only scientific semantics, independent of computational encoding."""
        return _digest(self.semantic_payload)

    @property
    def compiled_hash(self) -> str:
        """Hash the exact computational representation and its encoder lineage."""
        return _digest(
            {
                "representation": self.representation,
                "payload": self.compiled_payload,
                "semantic_variables": list(self.semantic_variables),
                "auxiliary_variables": list(self.auxiliary_variables),
                "independent_support": list(self.independent_support),
                "constraint_set_id": self.constraint_set_id,
                "constraint_version": self.constraint_version,
                "encoder_id": self.encoder_id,
                "encoder_version": self.encoder_version,
            }
        )


@dataclass(frozen=True)
class StructuralMetrics:
    """Computational routing metadata; never an efficacy score."""

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
    backend: str
    backend_version: str
    assignment: Mapping[str, Any] | None = None
    unsat_core: tuple[str, ...] = ()
    proof_artifact: str | None = None
    proof_sha256: str | None = None
    proof_format: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class CICResult:
    status: SolveStatus
    constraint_set_id: str
    constraint_version: str
    representation: str
    encoder_id: str
    encoder_version: str
    semantic_hash: str
    compiled_hash: str
    scientific_projection: Mapping[str, Any] | None
    assignment_verified: bool
    independent_support: tuple[str, ...]
    unsat_core: tuple[str, ...]
    proof_artifact: str | None
    proof_sha256: str | None
    proof_format: str | None
    proof_verified: bool
    proof_scope: str | None
    backend: str
    backend_version: str
    metrics: StructuralMetrics
    note: str | None = None


class SolverBackend(Protocol):
    def check(
        self,
        representation: ConstraintRepresentation,
        *,
        explain_unsat: bool,
    ) -> SolverReply: ...


ProofVerifier = Callable[[ConstraintRepresentation, SolverReply], bool]
AssignmentVerifier = Callable[[Mapping[str, Any]], bool]


def check(
    representation: ConstraintRepresentation,
    *,
    backend: SolverBackend,
    assignment_verifier: AssignmentVerifier,
    explain_unsat: bool = True,
    metrics: StructuralMetrics | None = None,
    proof_verifier: ProofVerifier | None = None,
    require_verified_unsat: bool = True,
) -> CICResult:
    """Run one governed feasibility check and independently verify its evidence.

    SAT is accepted only after an independent assignment verifier succeeds.
    In the default strict mode, UNSAT is accepted only when proof metadata is
    present and an independent proof verifier accepts it. Otherwise the result
    is downgraded to UNKNOWN rather than overstating certainty.
    """

    representation.validate()
    reply = backend.check(representation, explain_unsat=explain_unsat)
    if not isinstance(reply.status, SolveStatus):
        raise CICError("backend returned invalid solve status")
    _require_text(reply.backend, "backend")
    _require_text(reply.backend_version, "backend_version")

    if reply.proof_sha256 is not None:
        _require_sha256(reply.proof_sha256, "proof_sha256")
    if reply.proof_artifact is not None and reply.proof_sha256 is None:
        raise CICError("proof_artifact requires proof_sha256")
    if reply.proof_sha256 is not None and reply.proof_artifact is None:
        raise CICError("proof_sha256 requires proof_artifact")
    if reply.proof_format is not None and reply.proof_artifact is None:
        raise CICError("proof_format requires proof_artifact")

    status = reply.status
    projection: Mapping[str, Any] | None = None
    assignment_verified = False
    proof_verified = False
    proof_scope: str | None = None
    note = reply.note

    if status is SolveStatus.SAT:
        if reply.assignment is None:
            raise CICError("SAT backend reply requires assignment")
        if not assignment_verifier(reply.assignment):
            raise CICError("independent verifier rejected SAT assignment")
        missing = [
            name
            for name in representation.semantic_variables
            if name not in reply.assignment
        ]
        if missing:
            raise CICError(f"SAT assignment missing semantic variables: {missing}")
        projection = {
            name: reply.assignment[name]
            for name in representation.semantic_variables
        }
        assignment_verified = True
    elif reply.assignment is not None:
        raise CICError("non-SAT backend reply must not carry an assignment")

    if status is SolveStatus.UNSAT:
        complete_proof = all(
            value is not None
            for value in (
                reply.proof_artifact,
                reply.proof_sha256,
                reply.proof_format,
            )
        )
        if complete_proof and proof_verifier is not None:
            try:
                proof_verified = bool(proof_verifier(representation, reply))
            except Exception as exc:  # verifier failure must not certify UNSAT
                note = _join_note(note, f"proof verifier failed: {exc}")
                proof_verified = False
        if proof_verified:
            proof_scope = "compiled_problem_only"
        elif require_verified_unsat:
            status = SolveStatus.UNKNOWN
            note = _join_note(
                note,
                "UNSAT downgraded to UNKNOWN because the compiled-problem proof "
                "was not independently verified",
            )

    computed_metrics = metrics or StructuralMetrics(
        len(representation.semantic_variables)
        + len(representation.auxiliary_variables),
        len(representation.semantic_variables),
        len(representation.auxiliary_variables),
        len(representation.independent_support),
    )

    return CICResult(
        status=status,
        constraint_set_id=representation.constraint_set_id,
        constraint_version=representation.constraint_version,
        representation=representation.representation,
        encoder_id=representation.encoder_id,
        encoder_version=representation.encoder_version,
        semantic_hash=representation.semantic_hash,
        compiled_hash=representation.compiled_hash,
        scientific_projection=projection,
        assignment_verified=assignment_verified,
        independent_support=tuple(representation.independent_support),
        unsat_core=(
            tuple(reply.unsat_core)
            if explain_unsat and reply.status is SolveStatus.UNSAT
            else ()
        ),
        proof_artifact=reply.proof_artifact,
        proof_sha256=reply.proof_sha256,
        proof_format=reply.proof_format,
        proof_verified=proof_verified,
        proof_scope=proof_scope,
        backend=reply.backend,
        backend_version=reply.backend_version,
        metrics=computed_metrics,
        note=note,
    )


def require_cross_encoding_agreement(results: Sequence[CICResult]) -> None:
    """Require semantic agreement across genuinely distinct encodings."""

    if len(results) < 2:
        raise CICError("cross-encoding agreement requires at least two results")
    if len({(r.constraint_set_id, r.constraint_version) for r in results}) != 1:
        raise CICError("results do not share one immutable constraint-set version")
    if len({r.semantic_hash for r in results}) != 1:
        raise CICError("results do not share one semantic identity")
    if len({r.status for r in results}) != 1:
        raise CICError("semantically equivalent encodings disagree on solve status")
    encodings = {
        (r.representation, r.encoder_id, r.encoder_version, r.compiled_hash)
        for r in results
    }
    if len(encodings) < 2:
        raise CICError("cross-encoding agreement requires distinct compiled encodings")
    status = results[0].status
    if status is SolveStatus.SAT and not all(r.assignment_verified for r in results):
        raise CICError("cross-encoding SAT agreement requires verified assignments")
    if status is SolveStatus.UNSAT and not all(r.proof_verified for r in results):
        raise CICError("cross-encoding UNSAT agreement requires verified proofs")


class ExternalCICCoreBackend:
    """Black-box adapter for an existing external CIC checkout.

    No CIC source is copied into RAC. CIC ``dpll_solve`` currently returns
    ``None`` for both timeout and UNSAT, so ``None`` is always normalized to
    UNKNOWN. This backend therefore never invents an UNSAT certificate.
    """

    backend = "cic-core"
    backend_version = "external"

    def __init__(self, cic_root: str | Path, *, timeout_seconds: float = 30.0) -> None:
        self.cic_root = Path(cic_root)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds <= 0:
            raise CICError("timeout_seconds must be positive")
        self._module = self._load_core()

    def _load_core(self) -> ModuleType:
        path = self.cic_root / "security_tools" / "shared" / "cic_core.py"
        if not path.is_file():
            raise CICError(f"CIC core not found: {path}")
        spec = importlib.util.spec_from_file_location("rac_external_cic_core", path)
        if spec is None or spec.loader is None:
            raise CICError("unable to load CIC core module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "dpll_solve"):
            raise CICError("CIC core missing required symbol: dpll_solve")
        return module

    def check(
        self,
        representation: ConstraintRepresentation,
        *,
        explain_unsat: bool,
    ) -> SolverReply:
        del explain_unsat
        representation.validate()
        if representation.representation != "CNF":
            return SolverReply(
                SolveStatus.UNKNOWN,
                self.backend,
                self.backend_version,
                note="external CIC core adapter currently supports CNF only",
            )
        clauses = [list(clause) for clause in _cnf_clauses(representation.compiled_payload)]
        num_vars = _cnf_num_vars(representation.compiled_payload, clauses)
        model = self._module.dpll_solve(
            clauses,
            num_vars,
            timeout=self.timeout_seconds,
        )
        if model is None:
            return SolverReply(
                SolveStatus.UNKNOWN,
                self.backend,
                self.backend_version,
                note="CIC returned None; RAC cannot distinguish UNSAT from timeout",
            )
        assignment = _decode_external_assignment(representation, model)
        return SolverReply(
            SolveStatus.SAT,
            self.backend,
            self.backend_version,
            assignment=assignment,
        )


def _cnf_clauses(payload: Any) -> tuple[tuple[int, ...], ...]:
    raw = payload.get("clauses") if isinstance(payload, Mapping) else payload
    if not isinstance(raw, (list, tuple)):
        raise CICError("CNF compiled_payload must contain a sequence of clauses")
    clauses: list[tuple[int, ...]] = []
    for index, clause in enumerate(raw):
        if not isinstance(clause, (list, tuple)) or not clause:
            raise CICError(f"CNF clause {index} must be a non-empty sequence")
        normalized: list[int] = []
        for literal in clause:
            if isinstance(literal, bool) or not isinstance(literal, int) or literal == 0:
                raise CICError(f"invalid CNF literal {literal!r} in clause {index}")
            normalized.append(literal)
        clauses.append(tuple(normalized))
    return tuple(clauses)


def _cnf_num_vars(payload: Any, clauses: Sequence[Sequence[int]]) -> int:
    inferred = max((abs(lit) for clause in clauses for lit in clause), default=0)
    if isinstance(payload, Mapping) and "num_vars" in payload:
        raw = payload["num_vars"]
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < inferred:
            raise CICError("CNF num_vars must be an integer covering every literal")
        return raw
    if inferred <= 0:
        raise CICError("CNF representation must contain at least one variable")
    return inferred


def _decode_external_assignment(
    representation: ConstraintRepresentation,
    model: Any,
) -> Mapping[str, Any]:
    if not isinstance(model, Mapping):
        raise CICError("external CIC model must be a mapping")
    names = representation.semantic_variables + representation.auxiliary_variables
    if all(name in model for name in representation.semantic_variables):
        return {name: model[name] for name in names if name in model}
    if not isinstance(representation.compiled_payload, Mapping):
        raise CICError("external CIC integer model requires compiled variable_map")
    variable_map = representation.compiled_payload.get("variable_map")
    if not isinstance(variable_map, Mapping):
        raise CICError("external CIC integer model requires compiled variable_map")
    assignment: dict[str, Any] = {}
    for name in names:
        index = variable_map.get(name)
        if index is not None and index in model:
            assignment[name] = model[index]
    return assignment


def _join_note(left: str | None, right: str) -> str:
    return right if not left else f"{left}; {right}"

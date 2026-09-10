"""Bounded CIC formal-methods adapter for RAC Governance Pass 5.

CIC is a verification and structural-analysis dependency, never an efficacy
optimizer. This module deliberately does not accept detector scores, held-out
outcomes, or CTM labels.

The external CIC core currently represents both UNSAT and timeout as ``None``.
Accordingly :class:`ExternalCICCoreBackend` maps that result to UNKNOWN. RAC
only accepts an UNSAT conclusion from a backend that can distinguish it, and
critical UNSAT claims can require independent corroborators.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Mapping, Protocol, Sequence


class CICAdapterError(RuntimeError):
    """Fail-closed CIC/RAC boundary violation."""


class EncodingKind(str, Enum):
    CNF = "CNF"
    PB = "PB"
    SMT = "SMT"


class SolveStatus(str, Enum):
    SAT = "SAT"
    UNSAT = "UNSAT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class StructuralReport:
    num_vars: int
    num_constraints: int
    max_constraint_arity: int
    treewidth_estimate: int | None = None
    independent_support_size: int | None = None
    graph_density: float | None = None
    backend_note: str = ""

    def validate(self) -> None:
        if self.num_vars < 0 or self.num_constraints < 0 or self.max_constraint_arity < 0:
            raise CICAdapterError("structural counts must be non-negative")
        if self.treewidth_estimate is not None and self.treewidth_estimate < 0:
            raise CICAdapterError("treewidth_estimate must be non-negative")
        if self.independent_support_size is not None and not 0 <= self.independent_support_size <= self.num_vars:
            raise CICAdapterError("invalid independent_support_size")
        if self.graph_density is not None and not 0.0 <= self.graph_density <= 1.0:
            raise CICAdapterError("graph_density must be in [0,1]")


@dataclass(frozen=True)
class ConstraintEncoding:
    """One compiled representation of a frozen semantic constraint set.

    ``semantic_hash`` identifies the meaning of the constraints. ``compiled_hash``
    is derived from the concrete encoding. Auxiliary variables are explicitly
    separated from scientific genome variables and can never enter the
    scientific projection.
    """

    encoding_kind: EncodingKind
    semantic_hash: str
    num_vars: int
    compiled_payload: object
    semantic_vars: frozenset[int]
    auxiliary_vars: frozenset[int] = frozenset()
    scientific_projection: frozenset[int] = frozenset()
    independent_support: frozenset[int] = frozenset()
    encoder_id: str = ""
    encoder_version: str = ""

    def validate(self) -> None:
        _require_sha256(self.semantic_hash, "semantic_hash")
        if self.num_vars <= 0:
            raise CICAdapterError("num_vars must be positive")
        if not self.semantic_vars:
            raise CICAdapterError("semantic_vars must not be empty")
        universe = set(range(1, self.num_vars + 1))
        if not set(self.semantic_vars) <= universe or not set(self.auxiliary_vars) <= universe:
            raise CICAdapterError("semantic/auxiliary variable outside declared variable universe")
        if self.semantic_vars & self.auxiliary_vars:
            raise CICAdapterError("semantic_vars and auxiliary_vars must be disjoint")
        if not self.scientific_projection:
            raise CICAdapterError("scientific_projection must not be empty")
        if not self.scientific_projection <= self.semantic_vars:
            raise CICAdapterError("scientific projection may contain only semantic genome variables")
        if not self.independent_support <= self.scientific_projection:
            raise CICAdapterError("independent support must be a subset of scientific projection")
        if self.encoding_kind is EncodingKind.CNF:
            _validate_cnf_payload(self.compiled_payload, self.num_vars)
        if not self.encoder_id or not self.encoder_version:
            raise CICAdapterError("encoder_id and encoder_version are required")

    @property
    def compiled_hash(self) -> str:
        self.validate()
        body = {
            "encoding_kind": self.encoding_kind.value,
            "num_vars": self.num_vars,
            "compiled_payload": self.compiled_payload,
            "semantic_vars": sorted(self.semantic_vars),
            "auxiliary_vars": sorted(self.auxiliary_vars),
            "scientific_projection": sorted(self.scientific_projection),
            "independent_support": sorted(self.independent_support),
            "encoder_id": self.encoder_id,
            "encoder_version": self.encoder_version,
        }
        return sha256(_canonical(body)).hexdigest()


@dataclass(frozen=True)
class BackendResult:
    status: SolveStatus
    assignment: Mapping[int, bool] | None = None
    unsat_core: tuple[str, ...] | None = None
    proof_ref: str | None = None
    proof_sha256: str | None = None
    solver_id: str = ""
    solver_version: str = ""
    note: str = ""

    def validate(self) -> None:
        if not self.solver_id or not self.solver_version:
            raise CICAdapterError("solver identity/version are required")
        if self.status is SolveStatus.SAT and self.assignment is None:
            raise CICAdapterError("SAT backend result requires an assignment")
        if self.status is not SolveStatus.SAT and self.assignment is not None:
            raise CICAdapterError("only SAT backend results may carry an assignment")
        if self.proof_sha256 is not None:
            _require_sha256(self.proof_sha256, "proof_sha256")
            if self.proof_ref is None:
                raise CICAdapterError("proof_sha256 requires proof_ref")


class CICBackend(Protocol):
    backend_id: str
    backend_version: str

    def solve(self, encoding: ConstraintEncoding) -> BackendResult: ...

    def structural_report(self, encoding: ConstraintEncoding) -> StructuralReport: ...


@dataclass(frozen=True)
class RoutingPolicy:
    """Versioned empirical routing thresholds; these are not scientific laws."""

    version: str
    exact_max_treewidth: int = 20
    hashing_max_treewidth: int = 50
    stratified_max_treewidth: int = 80

    def validate(self) -> None:
        if not self.version:
            raise CICAdapterError("routing policy version is required")
        if not 0 <= self.exact_max_treewidth <= self.hashing_max_treewidth <= self.stratified_max_treewidth:
            raise CICAdapterError("routing treewidth thresholds must be monotone")


@dataclass(frozen=True)
class CICPreflightResult:
    status: SolveStatus
    assignment_verified: bool
    solver_id: str
    solver_version: str
    semantic_hash: str
    compiled_hash: str
    structural_report: StructuralReport
    sampler_routing_hint: str
    routing_policy_version: str
    corroborating_solvers: tuple[str, ...] = ()
    unsat_core: tuple[str, ...] | None = None
    proof_ref: str | None = None
    proof_sha256: str | None = None
    note: str = ""


def preflight(
    encoding: ConstraintEncoding,
    backend: CICBackend,
    *,
    corroborators: Sequence[CICBackend] = (),
    routing_policy: RoutingPolicy | None = None,
    require_unsat_corroboration: bool = True,
) -> CICPreflightResult:
    """Run a bounded solver preflight without any efficacy-scoring inputs."""

    encoding.validate()
    report = backend.structural_report(encoding)
    report.validate()
    if report.num_vars != encoding.num_vars:
        raise CICAdapterError("backend structural report disagrees with encoding num_vars")

    raw = backend.solve(encoding)
    raw.validate()
    verified = False
    status = raw.status
    corroborating: list[str] = []
    note = raw.note

    if status is SolveStatus.SAT:
        if encoding.encoding_kind is not EncodingKind.CNF:
            raise CICAdapterError("independent SAT verification is currently implemented only for CNF")
        assert raw.assignment is not None
        verify_cnf_assignment(encoding, raw.assignment)
        verified = True
    elif status is SolveStatus.UNSAT and require_unsat_corroboration:
        if not corroborators:
            status = SolveStatus.UNKNOWN
            note = _join_note(note, "UNSAT withheld: no independent corroborator supplied")
        else:
            for other in corroborators:
                check = other.solve(encoding)
                check.validate()
                if check.status is not SolveStatus.UNSAT:
                    status = SolveStatus.UNKNOWN
                    note = _join_note(note, f"UNSAT not corroborated by {check.solver_id}")
                    corroborating.clear()
                    break
                corroborating.append(f"{check.solver_id}@{check.solver_version}")

    policy = routing_policy or RoutingPolicy(version="rac-routing-hint/1.0")
    policy.validate()
    hint = routing_hint(report, policy)

    return CICPreflightResult(
        status=status,
        assignment_verified=verified,
        solver_id=raw.solver_id,
        solver_version=raw.solver_version,
        semantic_hash=encoding.semantic_hash,
        compiled_hash=encoding.compiled_hash,
        structural_report=report,
        sampler_routing_hint=hint,
        routing_policy_version=policy.version,
        corroborating_solvers=tuple(corroborating),
        unsat_core=raw.unsat_core if status is SolveStatus.UNSAT else None,
        proof_ref=raw.proof_ref if status is SolveStatus.UNSAT else None,
        proof_sha256=raw.proof_sha256 if status is SolveStatus.UNSAT else None,
        note=note,
    )


def verify_cnf_assignment(encoding: ConstraintEncoding, assignment: Mapping[int, bool]) -> None:
    """Independently verify that a candidate model satisfies every CNF clause."""

    encoding.validate()
    if encoding.encoding_kind is not EncodingKind.CNF:
        raise CICAdapterError("CNF assignment verifier received non-CNF encoding")
    normalized: dict[int, bool] = {}
    for var, value in assignment.items():
        if isinstance(var, bool) or not isinstance(var, int) or var < 1 or var > encoding.num_vars:
            raise CICAdapterError(f"assignment contains invalid variable: {var!r}")
        if not isinstance(value, bool):
            raise CICAdapterError(f"assignment for variable {var} must be bool")
        normalized[var] = value

    clauses = _cnf_clauses(encoding.compiled_payload)
    needed = {abs(lit) for clause in clauses for lit in clause}
    missing = sorted(needed - set(normalized))
    if missing:
        raise CICAdapterError(f"SAT assignment is incomplete; missing variables: {missing}")
    for index, clause in enumerate(clauses):
        if not any(normalized[abs(lit)] if lit > 0 else not normalized[abs(lit)] for lit in clause):
            raise CICAdapterError(f"backend returned invalid SAT witness; clause {index} is false")


def routing_hint(report: StructuralReport, policy: RoutingPolicy) -> str:
    """Return a non-binding Pass-6 sampler routing hint from structural width."""

    report.validate()
    policy.validate()
    width = report.treewidth_estimate
    if width is None:
        return "proposal_or_empirical_probe"
    if width <= policy.exact_max_treewidth:
        return "exact_or_compiled"
    if width <= policy.hashing_max_treewidth:
        return "projected_hashing"
    if width <= policy.stratified_max_treewidth:
        return "stratified_constrained"
    return "proposal_or_rejection"


class ExternalCICCoreBackend:
    """Adapter for the existing ``security_tools/shared/cic_core.py`` checkout.

    No CIC code is vendored into RAC. The caller points this adapter at a local
    CIC checkout. CIC's ``dpll_solve`` cannot distinguish timeout from UNSAT,
    so a ``None`` result is intentionally normalized to UNKNOWN.
    """

    backend_id = "cic-core"
    backend_version = "external"

    def __init__(self, cic_root: str | Path, *, timeout_seconds: float = 30.0) -> None:
        self.cic_root = Path(cic_root)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds <= 0:
            raise CICAdapterError("timeout_seconds must be positive")
        self._module = self._load_core()

    def _load_core(self) -> ModuleType:
        path = self.cic_root / "security_tools" / "shared" / "cic_core.py"
        if not path.is_file():
            raise CICAdapterError(f"CIC core not found: {path}")
        spec = importlib.util.spec_from_file_location("rac_external_cic_core", path)
        if spec is None or spec.loader is None:
            raise CICAdapterError("unable to load CIC core module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in ("dpll_solve", "build_primal_graph", "minfill_treewidth"):
            if not hasattr(module, name):
                raise CICAdapterError(f"CIC core missing required symbol: {name}")
        return module

    def solve(self, encoding: ConstraintEncoding) -> BackendResult:
        encoding.validate()
        if encoding.encoding_kind is not EncodingKind.CNF:
            return BackendResult(
                SolveStatus.UNKNOWN,
                solver_id=self.backend_id,
                solver_version=self.backend_version,
                note="external CIC core adapter currently supports CNF only",
            )
        clauses = [list(c) for c in _cnf_clauses(encoding.compiled_payload)]
        model = self._module.dpll_solve(clauses, encoding.num_vars, timeout=self.timeout_seconds)
        if model is None:
            return BackendResult(
                SolveStatus.UNKNOWN,
                solver_id=self.backend_id,
                solver_version=self.backend_version,
                note="CIC returned None; RAC cannot distinguish UNSAT from timeout",
            )
        return BackendResult(
            SolveStatus.SAT,
            assignment=dict(model),
            solver_id=self.backend_id,
            solver_version=self.backend_version,
        )

    def structural_report(self, encoding: ConstraintEncoding) -> StructuralReport:
        encoding.validate()
        if encoding.encoding_kind is not EncodingKind.CNF:
            return StructuralReport(
                encoding.num_vars,
                0,
                0,
                independent_support_size=len(encoding.independent_support),
                backend_note="CIC structural analysis currently supports CNF only",
            )
        clauses = [list(c) for c in _cnf_clauses(encoding.compiled_payload)]
        graph = self._module.build_primal_graph(encoding.num_vars, clauses)
        _, width = self._module.minfill_treewidth(graph)
        possible_edges = encoding.num_vars * (encoding.num_vars - 1) / 2
        edge_count = sum(len(neighbors) for neighbors in graph.values()) / 2
        density = 0.0 if possible_edges == 0 else edge_count / possible_edges
        return StructuralReport(
            num_vars=encoding.num_vars,
            num_constraints=len(clauses),
            max_constraint_arity=max((len(c) for c in clauses), default=0),
            treewidth_estimate=int(width),
            independent_support_size=len(encoding.independent_support),
            graph_density=float(density),
            backend_note="MinFill treewidth estimate from external CIC core",
        )


def _validate_cnf_payload(payload: object, num_vars: int) -> None:
    clauses = _cnf_clauses(payload)
    for index, clause in enumerate(clauses):
        if not clause:
            raise CICAdapterError(f"CNF clause {index} is empty")
        for lit in clause:
            if isinstance(lit, bool) or not isinstance(lit, int) or lit == 0 or abs(lit) > num_vars:
                raise CICAdapterError(f"invalid CNF literal {lit!r} in clause {index}")


def _cnf_clauses(payload: object) -> tuple[tuple[int, ...], ...]:
    if not isinstance(payload, (list, tuple)):
        raise CICAdapterError("CNF compiled_payload must be a sequence of clauses")
    clauses: list[tuple[int, ...]] = []
    for clause in payload:
        if not isinstance(clause, (list, tuple)):
            raise CICAdapterError("each CNF clause must be a sequence")
        clauses.append(tuple(clause))
    return tuple(clauses)


def _require_sha256(value: str, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise CICAdapterError(f"{field} must be a lowercase sha256")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _join_note(left: str, right: str) -> str:
    return right if not left else f"{left}; {right}"

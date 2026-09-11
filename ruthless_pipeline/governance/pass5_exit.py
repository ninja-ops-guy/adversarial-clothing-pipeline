"""Integrated Governance Pass 5 CIC preflight and cross-encoding exit gates.

The surface is intentionally efficacy-blind.  It consumes immutable scientific
constraint semantics, verifies compiled feasibility evidence, compares projected
sample distributions, and emits only structural sampler-routing metadata.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence

from .cic_adapter import (
    CICError,
    CICResult,
    ConstraintRepresentation,
    ProofVerifier,
    AssignmentVerifier,
    SolveStatus,
    SolverBackend,
    check,
    require_cross_encoding_agreement,
)
from .sampling import BackendSelection, BackendTelemetry, select_backend


class Pass5ExitError(RuntimeError):
    pass


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _projected_key(sample: Mapping[str, Any], projection: Sequence[str]) -> str:
    if set(sample) != set(projection):
        raise Pass5ExitError("cross-encoding sample does not match the common scientific projection")
    return _canonical({name: sample[name] for name in projection})


@dataclass(frozen=True)
class CrossEncodingDistributionReport:
    projection: tuple[str, ...]
    encodings: tuple[str, ...]
    maximum_pairwise_total_variation: float
    acceptance_bound: float
    pairwise_total_variation: tuple[tuple[str, str, float], ...]

    @property
    def passed(self) -> bool:
        return self.maximum_pairwise_total_variation <= self.acceptance_bound

    def to_dict(self) -> dict[str, object]:
        return {
            "projection": list(self.projection),
            "encodings": list(self.encodings),
            "maximum_pairwise_total_variation": self.maximum_pairwise_total_variation,
            "acceptance_bound": self.acceptance_bound,
            "passed": self.passed,
            "pairwise_total_variation": [
                {"left": left, "right": right, "total_variation": tv}
                for left, right, tv in self.pairwise_total_variation
            ],
        }


@dataclass(frozen=True)
class Pass5PreflightRecord:
    semantic_constraint_input: Mapping[str, Any]
    results: tuple[CICResult, ...]
    distribution_report: CrossEncodingDistributionReport
    backend_selection: BackendSelection

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "semantic_constraint_input": dict(self.semantic_constraint_input),
            "results": [
                {
                    "status": result.status.value,
                    "constraint_set_id": result.constraint_set_id,
                    "constraint_version": result.constraint_version,
                    "representation": result.representation,
                    "encoder_id": result.encoder_id,
                    "encoder_version": result.encoder_version,
                    "semantic_hash": result.semantic_hash,
                    "compiled_hash": result.compiled_hash,
                    "scientific_projection": None if result.scientific_projection is None else dict(result.scientific_projection),
                    "assignment_verified": result.assignment_verified,
                    "proof_verified": result.proof_verified,
                    "proof_scope": result.proof_scope,
                    "backend": result.backend,
                    "backend_version": result.backend_version,
                }
                for result in self.results
            ],
            "distribution_report": self.distribution_report.to_dict(),
            "backend_selection": {
                "selected": self.backend_selection.selected.value,
                "alternate": self.backend_selection.alternate.value,
                "predicted_cost": self.backend_selection.predicted_cost,
                "confidence": self.backend_selection.confidence,
                "selector_version": self.backend_selection.selector_version,
                "selection_basis": self.backend_selection.selection_basis,
            },
        }


def compare_projected_distributions(
    sample_sets: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    projection: Sequence[str],
    acceptance_bound: float,
) -> CrossEncodingDistributionReport:
    """Frozen global multivariate comparison on the full scientific projection."""
    if not 0.0 <= acceptance_bound <= 1.0:
        raise Pass5ExitError("acceptance_bound must be in [0,1]")
    if len(sample_sets) < 2:
        raise Pass5ExitError("global cross-encoding comparison requires at least two encodings")
    if not projection:
        raise Pass5ExitError("scientific projection is required")

    counts: dict[str, Counter[str]] = {}
    totals: dict[str, int] = {}
    for encoding, samples in sample_sets.items():
        if not samples:
            raise Pass5ExitError(f"encoding {encoding} has no projected samples")
        counts[encoding] = Counter(_projected_key(sample, projection) for sample in samples)
        totals[encoding] = len(samples)

    rows: list[tuple[str, str, float]] = []
    names = sorted(counts)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            support = set(counts[left]) | set(counts[right])
            tv = 0.5 * sum(
                abs(counts[left][key] / totals[left] - counts[right][key] / totals[right])
                for key in support
            )
            rows.append((left, right, tv))
    maximum = max((row[2] for row in rows), default=0.0)
    report = CrossEncodingDistributionReport(
        projection=tuple(projection),
        encodings=tuple(names),
        maximum_pairwise_total_variation=maximum,
        acceptance_bound=acceptance_bound,
        pairwise_total_variation=tuple(rows),
    )
    if not report.passed:
        raise Pass5ExitError(
            "global cross-encoding multivariate comparison failed: "
            f"TV={maximum:.6f} > bound={acceptance_bound:.6f}"
        )
    return report


def run_pass5_preflight(
    *,
    semantic_constraint_input: Mapping[str, Any],
    representations: Sequence[ConstraintRepresentation],
    backends: Mapping[str, SolverBackend],
    assignment_verifier: AssignmentVerifier,
    projected_sample_sets: Mapping[str, Sequence[Mapping[str, Any]]],
    global_tv_acceptance_bound: float,
    selector_version: str,
    exact_max_variables: int,
    hashing_max_support: int,
) -> Pass5PreflightRecord:
    """Run semantic input -> verified CIC feasibility -> structural routing."""
    if len(representations) < 2:
        raise Pass5ExitError("integrated preflight requires multiple compiled encodings")
    expected_semantics = _canonical(dict(semantic_constraint_input))
    projection = representations[0].semantic_variables
    results: list[CICResult] = []
    for representation in representations:
        if _canonical(dict(representation.semantic_payload)) != expected_semantics:
            raise Pass5ExitError("compiled representation semantic payload differs from frozen RAC input")
        if representation.semantic_variables != projection:
            raise Pass5ExitError("compiled encodings do not share one scientific projection")
        try:
            backend = backends[representation.representation]
        except KeyError as exc:
            raise Pass5ExitError(f"missing backend for {representation.representation}") from exc
        result = check(
            representation,
            backend=backend,
            assignment_verifier=assignment_verifier,
            explain_unsat=True,
        )
        if result.status is not SolveStatus.SAT:
            raise Pass5ExitError(
                f"feasible preflight requires verified SAT; {representation.representation} returned {result.status.value}"
            )
        results.append(result)

    try:
        require_cross_encoding_agreement(results)
    except CICError as exc:
        raise Pass5ExitError(str(exc)) from exc

    required_sample_keys = {representation.representation for representation in representations}
    if set(projected_sample_sets) != required_sample_keys:
        raise Pass5ExitError("projected sample sets must exactly cover the compiled encodings")
    distribution_report = compare_projected_distributions(
        projected_sample_sets,
        projection=projection,
        acceptance_bound=global_tv_acceptance_bound,
    )

    metrics = results[0].metrics
    selection = select_backend(
        BackendTelemetry(
            variable_count=metrics.variable_count,
            constraint_count=metrics.constraint_count or 0,
            independent_support_size=metrics.independent_support_size,
            graph_density=metrics.graph_density,
            treewidth_estimate=metrics.treewidth_estimate,
        ),
        selector_version=selector_version,
        exact_max_variables=exact_max_variables,
        hashing_max_support=hashing_max_support,
    )
    return Pass5PreflightRecord(
        semantic_constraint_input=dict(semantic_constraint_input),
        results=tuple(results),
        distribution_report=distribution_report,
        backend_selection=selection,
    )


def verify_explainable_unsat(
    representation: ConstraintRepresentation,
    *,
    backend: SolverBackend,
    assignment_verifier: AssignmentVerifier,
    proof_verifier: ProofVerifier,
) -> CICResult:
    """Require verified compiled-problem UNSAT provenance and a non-empty core."""
    result = check(
        representation,
        backend=backend,
        assignment_verifier=assignment_verifier,
        explain_unsat=True,
        proof_verifier=proof_verifier,
        require_verified_unsat=True,
    )
    if result.status is not SolveStatus.UNSAT or not result.proof_verified:
        raise Pass5ExitError("contradictory fixture did not produce independently verified UNSAT")
    if not result.unsat_core:
        raise Pass5ExitError("verified contradictory fixture must retain an explainable UNSAT core")
    if result.proof_scope != "compiled_problem_only":
        raise Pass5ExitError("UNSAT proof scope must remain compiled_problem_only")
    return result

from __future__ import annotations

import inspect

import pytest

from ruthless_pipeline.governance.cic_adapter import (
    ConstraintRepresentation,
    SolveStatus,
    SolverReply,
)
from ruthless_pipeline.governance.pass5_exit import (
    Pass5ExitError,
    run_pass5_preflight,
    verify_explainable_unsat,
)
from ruthless_pipeline.governance.sampling import SamplerLane


SEMANTICS = {"formula": "x XOR y", "domain": {"x": [0, 1], "y": [0, 1]}}


class SatBackend:
    def __init__(self, name: str):
        self.name = name

    def check(self, representation, *, explain_unsat):
        del representation, explain_unsat
        return SolverReply(
            status=SolveStatus.SAT,
            backend=self.name,
            backend_version="fixture-1",
            assignment={"x": 1, "y": 0, "aux": True},
        )


class UnsatBackend:
    def check(self, representation, *, explain_unsat):
        del representation, explain_unsat
        return SolverReply(
            status=SolveStatus.UNSAT,
            backend="fixture-unsat",
            backend_version="1",
            unsat_core=("c1", "c2"),
            proof_artifact="fixture-proof.drat",
            proof_sha256="a" * 64,
            proof_format="DRAT",
        )


def _repr(kind: str, compiled, encoder: str) -> ConstraintRepresentation:
    return ConstraintRepresentation(
        representation=kind,
        semantic_payload=SEMANTICS,
        compiled_payload=compiled,
        semantic_variables=("x", "y"),
        auxiliary_variables=("aux",),
        independent_support=("x",),
        constraint_set_id="RAC-CS-PASS5FIXTURE",
        constraint_version="v1",
        encoder_id=encoder,
        encoder_version="1",
    )


def _representations():
    return (
        _repr("CNF", {"clauses": [[1, 2], [-1, -2]]}, "fixture.cnf"),
        _repr("PB", {"constraints": ["x+y=1"]}, "fixture.pb"),
        _repr("SMT", {"assert": "xor(x,y)"}, "fixture.smt"),
    )


def _projected_samples():
    samples = (
        {"x": 0, "y": 1},
        {"x": 1, "y": 0},
        {"x": 0, "y": 1},
        {"x": 1, "y": 0},
    )
    return {"CNF": samples, "PB": samples, "SMT": samples}


def test_pass5_integrated_preflight_routes_only_after_verified_cross_encoding_agreement():
    reps = _representations()
    record = run_pass5_preflight(
        semantic_constraint_input=SEMANTICS,
        representations=reps,
        backends={name: SatBackend(name) for name in ("CNF", "PB", "SMT")},
        assignment_verifier=lambda assignment: assignment["x"] + assignment["y"] == 1,
        projected_sample_sets=_projected_samples(),
        global_tv_acceptance_bound=0.0,
        selector_version="fixture-selector-v1",
        exact_max_variables=4,
        hashing_max_support=2,
    )
    assert all(result.status is SolveStatus.SAT for result in record.results)
    assert all(result.assignment_verified for result in record.results)
    assert record.distribution_report.passed
    assert record.distribution_report.maximum_pairwise_total_variation == 0.0
    assert record.backend_selection.selected is SamplerLane.EXACT


def test_pass5_preflight_surface_is_efficacy_blind():
    signature = inspect.signature(run_pass5_preflight)
    assert not any("efficacy" in name.lower() for name in signature.parameters)
    assert "efficacy" not in record_fields()


def record_fields():
    from ruthless_pipeline.governance.pass5_exit import Pass5PreflightRecord
    return {field.name.lower() for field in Pass5PreflightRecord.__dataclass_fields__.values()}


def test_pass5_global_multivariate_mismatch_fails_closed():
    samples = _projected_samples()
    samples["SMT"] = (
        {"x": 1, "y": 0},
        {"x": 1, "y": 0},
        {"x": 1, "y": 0},
        {"x": 1, "y": 0},
    )
    with pytest.raises(Pass5ExitError, match="multivariate comparison failed"):
        run_pass5_preflight(
            semantic_constraint_input=SEMANTICS,
            representations=_representations(),
            backends={name: SatBackend(name) for name in ("CNF", "PB", "SMT")},
            assignment_verifier=lambda assignment: assignment["x"] + assignment["y"] == 1,
            projected_sample_sets=samples,
            global_tv_acceptance_bound=0.10,
            selector_version="fixture-selector-v1",
            exact_max_variables=4,
            hashing_max_support=2,
        )


def test_pass5_contradictory_fixture_retains_verified_core_and_compiled_scope():
    representation = ConstraintRepresentation(
        representation="CNF",
        semantic_payload={"formula": "x AND NOT x"},
        compiled_payload={"clauses": [[1], [-1]]},
        semantic_variables=("x",),
        constraint_set_id="RAC-CS-PASS5UNSAT",
        constraint_version="v1",
        encoder_id="fixture.cnf",
        encoder_version="1",
    )
    result = verify_explainable_unsat(
        representation,
        backend=UnsatBackend(),
        assignment_verifier=lambda assignment: False,
        proof_verifier=lambda representation, reply: (
            representation.representation == "CNF" and reply.proof_sha256 == "a" * 64
        ),
    )
    assert result.status is SolveStatus.UNSAT
    assert result.proof_verified is True
    assert result.proof_scope == "compiled_problem_only"
    assert result.unsat_core == ("c1", "c2")

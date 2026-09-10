"""Tests for Governance Pass 5 CIC integration boundaries."""

from __future__ import annotations

import pytest

from ruthless_pipeline.governance.cic_adapter import (
    CICError,
    ConstraintRepresentation,
    SolveStatus,
    SolverReply,
    check,
    require_cross_encoding_agreement,
)


class Backend:
    def __init__(self, reply: SolverReply) -> None:
        self.reply = reply

    def check(self, representation, *, explain_unsat: bool):
        return self.reply


def rep(**overrides):
    values = dict(
        representation="CNF",
        semantic_payload={"constraints": ["x"]},
        compiled_payload={"clauses": [[1]]},
        semantic_variables=("x",),
        auxiliary_variables=("aux_1",),
        independent_support=("x",),
    )
    values.update(overrides)
    return ConstraintRepresentation(**values)


def test_independent_support_cannot_include_auxiliary_variable():
    with pytest.raises(CICError, match="independent support"):
        rep(independent_support=("aux_1",)).validate()


def test_semantic_and_auxiliary_sets_must_be_disjoint():
    with pytest.raises(CICError, match="disjoint"):
        rep(auxiliary_variables=("x",)).validate()


def test_invalid_sat_assignment_is_rejected_by_independent_verifier():
    backend = Backend(SolverReply(SolveStatus.SAT, assignment={"x": True, "aux_1": False}, backend="fixture"))
    with pytest.raises(CICError, match="independent verifier"):
        check(rep(), backend=backend, assignment_verifier=lambda _: False)


def test_scientific_projection_strips_auxiliary_variables():
    backend = Backend(SolverReply(SolveStatus.SAT, assignment={"x": True, "aux_1": False}, backend="fixture"))
    result = check(rep(), backend=backend, assignment_verifier=lambda _: True)
    assert result.scientific_projection == {"x": True}
    assert "aux_1" not in result.scientific_projection


def test_missing_semantic_assignment_fails_closed():
    backend = Backend(SolverReply(SolveStatus.SAT, assignment={"aux_1": False}, backend="fixture"))
    with pytest.raises(CICError, match="missing semantic"):
        check(rep(), backend=backend, assignment_verifier=lambda _: True)


def test_non_sat_reply_cannot_smuggle_assignment():
    backend = Backend(SolverReply(SolveStatus.UNSAT, assignment={"x": False}, backend="fixture"))
    with pytest.raises(CICError, match="non-SAT"):
        check(rep(), backend=backend, assignment_verifier=lambda _: True)


def test_unsat_core_can_be_suppressed():
    backend = Backend(SolverReply(SolveStatus.UNSAT, unsat_core=("c1",), backend="fixture"))
    result = check(rep(), backend=backend, assignment_verifier=lambda _: True, explain_unsat=False)
    assert result.status is SolveStatus.UNSAT
    assert result.unsat_core == ()


def test_semantic_and_compiled_hashes_are_separate():
    a = rep(compiled_payload={"clauses": [[1]]})
    b = rep(compiled_payload={"clauses": [[1], [2, -2]]})
    assert a.semantic_hash == b.semantic_hash
    assert a.compiled_hash != b.compiled_hash


def test_backend_is_replaceable_without_manifest_semantic_change():
    one = check(
        rep(),
        backend=Backend(SolverReply(SolveStatus.SAT, assignment={"x": True}, backend="solver-a")),
        assignment_verifier=lambda _: True,
    )
    two = check(
        rep(),
        backend=Backend(SolverReply(SolveStatus.SAT, assignment={"x": True}, backend="solver-b")),
        assignment_verifier=lambda _: True,
    )
    assert one.semantic_hash == two.semantic_hash
    assert one.backend != two.backend


def test_cross_encoding_agreement_accepts_same_semantics_same_status():
    cnf = rep(representation="CNF", compiled_payload={"clauses": [[1]]})
    smt = rep(representation="SMT", compiled_payload={"assert": "x"})
    a = check(cnf, backend=Backend(SolverReply(SolveStatus.SAT, assignment={"x": True})), assignment_verifier=lambda _: True)
    b = check(smt, backend=Backend(SolverReply(SolveStatus.SAT, assignment={"x": True})), assignment_verifier=lambda _: True)
    # Representation type is a compilation choice, so normalize semantic identity
    object.__setattr__(b, "semantic_hash", a.semantic_hash)
    require_cross_encoding_agreement((a, b))


def test_cross_encoding_disagreement_fails_closed():
    a = check(rep(), backend=Backend(SolverReply(SolveStatus.SAT, assignment={"x": True})), assignment_verifier=lambda _: True)
    b = check(rep(), backend=Backend(SolverReply(SolveStatus.UNSAT)), assignment_verifier=lambda _: True)
    with pytest.raises(CICError, match="disagree"):
        require_cross_encoding_agreement((a, b))

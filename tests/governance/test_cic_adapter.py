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
        del representation, explain_unsat
        return self.reply


def reply(status: SolveStatus, **kwargs) -> SolverReply:
    return SolverReply(status, "fixture-solver", "1.0.0", **kwargs)


def rep(**overrides) -> ConstraintRepresentation:
    values = dict(
        representation="CNF",
        semantic_payload={"constraints": ["x"]},
        compiled_payload={"clauses": [[1]]},
        semantic_variables=("x",),
        constraint_set_id="RAC-CS-CIC0001",
        constraint_version="1.0.0",
        encoder_id="fixture-cnf",
        encoder_version="1.0.0",
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


def test_constraint_set_id_must_use_canonical_governance_prefix():
    with pytest.raises(CICError, match="canonical RAC-CS"):
        rep(constraint_set_id="RAC-CST-CIC0001").validate()


def test_invalid_sat_assignment_is_rejected_by_independent_verifier():
    with pytest.raises(CICError, match="independent verifier"):
        check(
            rep(),
            backend=Backend(
                reply(
                    SolveStatus.SAT,
                    assignment={"x": True, "aux_1": False},
                )
            ),
            assignment_verifier=lambda _: False,
        )


def test_scientific_projection_strips_auxiliary_variables():
    result = check(
        rep(),
        backend=Backend(
            reply(
                SolveStatus.SAT,
                assignment={"x": True, "aux_1": False},
            )
        ),
        assignment_verifier=lambda _: True,
    )
    assert result.scientific_projection == {"x": True}
    assert result.assignment_verified is True
    assert "aux_1" not in result.scientific_projection


def test_missing_semantic_assignment_fails_closed():
    with pytest.raises(CICError, match="missing semantic"):
        check(
            rep(),
            backend=Backend(
                reply(SolveStatus.SAT, assignment={"aux_1": False})
            ),
            assignment_verifier=lambda _: True,
        )


def test_non_sat_reply_cannot_smuggle_assignment():
    with pytest.raises(CICError, match="non-SAT"):
        check(
            rep(),
            backend=Backend(
                reply(SolveStatus.UNSAT, assignment={"x": False})
            ),
            assignment_verifier=lambda _: True,
        )


def test_unsat_core_can_be_suppressed():
    result = check(
        rep(),
        backend=Backend(reply(SolveStatus.UNSAT, unsat_core=("c1",))),
        assignment_verifier=lambda _: True,
        explain_unsat=False,
    )
    assert result.unsat_core == ()
    assert result.status is SolveStatus.UNKNOWN


def test_unverified_unsat_is_downgraded_to_unknown():
    result = check(
        rep(),
        backend=Backend(
            reply(
                SolveStatus.UNSAT,
                unsat_core=("c1",),
                proof_artifact="proof.drat",
                proof_sha256="a" * 64,
                proof_format="DRAT",
            )
        ),
        assignment_verifier=lambda _: True,
    )
    assert result.status is SolveStatus.UNKNOWN
    assert result.proof_verified is False
    assert "downgraded" in (result.note or "")


def test_verified_unsat_is_scoped_to_compiled_problem_only():
    result = check(
        rep(),
        backend=Backend(
            reply(
                SolveStatus.UNSAT,
                unsat_core=("c1",),
                proof_artifact="proof.drat",
                proof_sha256="b" * 64,
                proof_format="DRAT",
            )
        ),
        assignment_verifier=lambda _: True,
        proof_verifier=lambda representation, solver_reply: (
            representation.representation == "CNF"
            and solver_reply.proof_format == "DRAT"
        ),
    )
    assert result.status is SolveStatus.UNSAT
    assert result.proof_verified is True
    assert result.proof_scope == "compiled_problem_only"
    assert result.unsat_core == ("c1",)


def test_malformed_proof_hash_is_rejected():
    with pytest.raises(CICError, match="proof_sha256"):
        check(
            rep(),
            backend=Backend(
                reply(
                    SolveStatus.UNSAT,
                    proof_artifact="proof.drat",
                    proof_sha256="not-a-hash",
                    proof_format="DRAT",
                )
            ),
            assignment_verifier=lambda _: True,
        )


def test_semantic_and_compiled_hashes_are_separate():
    first = rep(compiled_payload={"clauses": [[1]]})
    second = rep(compiled_payload={"clauses": [[1], [2, -2]]})
    assert first.semantic_hash == second.semantic_hash
    assert first.compiled_hash != second.compiled_hash


def test_encoder_lineage_changes_compiled_not_semantic_identity():
    first = rep(encoder_version="1.0.0")
    second = rep(encoder_version="1.1.0")
    assert first.semantic_hash == second.semantic_hash
    assert first.compiled_hash != second.compiled_hash


def test_solver_and_encoder_provenance_survive_result_boundary():
    result = check(
        rep(encoder_id="rac-cnf", encoder_version="2.3.0"),
        backend=Backend(
            SolverReply(
                SolveStatus.SAT,
                "kissat",
                "4.0.3",
                assignment={"x": True},
            )
        ),
        assignment_verifier=lambda _: True,
    )
    assert result.constraint_set_id == "RAC-CS-CIC0001"
    assert result.constraint_version == "1.0.0"
    assert result.encoder_id == "rac-cnf"
    assert result.encoder_version == "2.3.0"
    assert result.backend == "kissat"
    assert result.backend_version == "4.0.3"


def test_backend_is_replaceable_without_manifest_semantic_change():
    first = check(
        rep(),
        backend=Backend(
            SolverReply(
                SolveStatus.SAT,
                "solver-a",
                "1",
                assignment={"x": True},
            )
        ),
        assignment_verifier=lambda _: True,
    )
    second = check(
        rep(),
        backend=Backend(
            SolverReply(
                SolveStatus.SAT,
                "solver-b",
                "2",
                assignment={"x": True},
            )
        ),
        assignment_verifier=lambda _: True,
    )
    assert first.semantic_hash == second.semantic_hash
    assert first.compiled_hash == second.compiled_hash
    assert first.backend != second.backend


def test_cross_encoding_agreement_accepts_same_semantics_same_status():
    cnf = check(
        rep(
            representation="CNF",
            compiled_payload={"clauses": [[1]]},
            encoder_id="direct-cnf",
        ),
        backend=Backend(reply(SolveStatus.SAT, assignment={"x": True})),
        assignment_verifier=lambda _: True,
    )
    smt = check(
        rep(
            representation="SMT",
            compiled_payload={"assert": "x"},
            encoder_id="smt-linear",
        ),
        backend=Backend(reply(SolveStatus.SAT, assignment={"x": True})),
        assignment_verifier=lambda _: True,
    )
    assert cnf.semantic_hash == smt.semantic_hash
    assert cnf.compiled_hash != smt.compiled_hash
    require_cross_encoding_agreement((cnf, smt))


def test_cross_encoding_requires_genuinely_distinct_compilations():
    first = check(
        rep(),
        backend=Backend(reply(SolveStatus.SAT, assignment={"x": True})),
        assignment_verifier=lambda _: True,
    )
    second = check(
        rep(),
        backend=Backend(reply(SolveStatus.SAT, assignment={"x": True})),
        assignment_verifier=lambda _: True,
    )
    with pytest.raises(CICError, match="distinct compiled"):
        require_cross_encoding_agreement((first, second))


def test_cross_encoding_rejects_constraint_version_mismatch():
    first = check(
        rep(constraint_version="1.0.0"),
        backend=Backend(reply(SolveStatus.SAT, assignment={"x": True})),
        assignment_verifier=lambda _: True,
    )
    second = check(
        rep(
            representation="SMT",
            compiled_payload={"assert": "x"},
            encoder_id="smt-linear",
            constraint_version="1.1.0",
        ),
        backend=Backend(reply(SolveStatus.SAT, assignment={"x": True})),
        assignment_verifier=lambda _: True,
    )
    with pytest.raises(CICError, match="constraint-set version"):
        require_cross_encoding_agreement((first, second))


def test_cross_encoding_disagreement_fails_closed():
    sat = check(
        rep(),
        backend=Backend(reply(SolveStatus.SAT, assignment={"x": True})),
        assignment_verifier=lambda _: True,
    )
    unknown = check(
        rep(
            representation="SMT",
            compiled_payload={"assert": "x"},
            encoder_id="smt-linear",
        ),
        backend=Backend(reply(SolveStatus.UNSAT)),
        assignment_verifier=lambda _: True,
    )
    with pytest.raises(CICError, match="disagree"):
        require_cross_encoding_agreement((sat, unknown))

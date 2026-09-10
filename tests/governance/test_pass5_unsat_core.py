"""Fail-closed handling of unverified backend contradiction data."""

from ruthless_pipeline.governance.cic_adapter import (
    ConstraintRepresentation,
    SolveStatus,
    SolverReply,
    check,
)


class Backend:
    def check(self, representation, *, explain_unsat: bool):
        del representation, explain_unsat
        return SolverReply(
            SolveStatus.UNSAT,
            "fixture-solver",
            "1.0.0",
            unsat_core=("constraint-a", "constraint-b"),
        )


def test_unverified_unsat_core_is_not_exposed_after_unknown_downgrade():
    representation = ConstraintRepresentation(
        representation="CNF",
        semantic_payload={"constraints": ["x", "not-x"]},
        compiled_payload={"clauses": [[1], [-1]]},
        semantic_variables=("x",),
        constraint_set_id="RAC-CS-CICCORE1",
        constraint_version="1.0.0",
        encoder_id="fixture-cnf",
        encoder_version="1.0.0",
        independent_support=("x",),
    )
    result = check(
        representation,
        backend=Backend(),
        assignment_verifier=lambda _: True,
    )
    assert result.status is SolveStatus.UNKNOWN
    assert result.unsat_core == ()
    assert result.proof_verified is False

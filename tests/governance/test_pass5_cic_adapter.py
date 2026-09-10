from __future__ import annotations

from dataclasses import replace

import pytest

from ruthless_pipeline.governance.cic_adapter import (
    BackendResult,
    CICAdapterError,
    ConstraintEncoding,
    EncodingKind,
    RoutingPolicy,
    SolveStatus,
    StructuralReport,
    preflight,
    routing_hint,
    verify_cnf_assignment,
)


SEM = "a" * 64


def _encoding(**overrides) -> ConstraintEncoding:
    data = dict(
        encoding_kind=EncodingKind.CNF,
        semantic_hash=SEM,
        num_vars=4,
        compiled_payload=((1, 2), (-1, 3), (-2, 4)),
        semantic_vars=frozenset({1, 2, 3}),
        auxiliary_vars=frozenset({4}),
        scientific_projection=frozenset({1, 2, 3}),
        independent_support=frozenset({1, 2}),
        encoder_id="rac-test-cnf",
        encoder_version="1.0.0",
    )
    data.update(overrides)
    return ConstraintEncoding(**data)


class FakeBackend:
    backend_id = "fake"
    backend_version = "1.0"

    def __init__(self, result: BackendResult, *, width: int = 3):
        self.result = result
        self.width = width

    def solve(self, encoding):
        return self.result

    def structural_report(self, encoding):
        return StructuralReport(
            num_vars=encoding.num_vars,
            num_constraints=len(encoding.compiled_payload),
            max_constraint_arity=max(len(c) for c in encoding.compiled_payload),
            treewidth_estimate=self.width,
            independent_support_size=len(encoding.independent_support),
            graph_density=0.5,
        )


def _sat_result(**overrides):
    data = dict(
        status=SolveStatus.SAT,
        assignment={1: True, 2: False, 3: True, 4: True},
        solver_id="fake",
        solver_version="1.0",
    )
    data.update(overrides)
    return BackendResult(**data)


def _unsat_result(solver_id="fake"):
    return BackendResult(
        status=SolveStatus.UNSAT,
        solver_id=solver_id,
        solver_version="1.0",
    )


def test_scientific_projection_excludes_auxiliary_variables():
    _encoding().validate()
    with pytest.raises(CICAdapterError, match="scientific projection"):
        _encoding(scientific_projection=frozenset({1, 4})).validate()


def test_independent_support_is_inside_scientific_projection():
    with pytest.raises(CICAdapterError, match="independent support"):
        _encoding(independent_support=frozenset({1, 4})).validate()


def test_semantic_and_compiled_hashes_are_separate():
    first = _encoding()
    second = _encoding(compiled_payload=((1, 2), (-1, 3), (-2, 4), (3, 4)))
    assert first.semantic_hash == second.semantic_hash
    assert first.compiled_hash != second.compiled_hash


def test_equivalent_encoding_languages_can_share_semantic_identity():
    cnf = _encoding()
    pb = _encoding(
        encoding_kind=EncodingKind.PB,
        compiled_payload={"constraints": ["x1+x2>=1"]},
        encoder_id="rac-test-pb",
    )
    smt = _encoding(
        encoding_kind=EncodingKind.SMT,
        compiled_payload="(assert (or x1 x2))",
        encoder_id="rac-test-smt",
    )
    pb.validate()
    smt.validate()
    assert {cnf.semantic_hash, pb.semantic_hash, smt.semantic_hash} == {SEM}
    assert len({cnf.compiled_hash, pb.compiled_hash, smt.compiled_hash}) == 3


def test_valid_sat_witness_is_independently_verified():
    result = preflight(_encoding(), FakeBackend(_sat_result()))
    assert result.status is SolveStatus.SAT
    assert result.assignment_verified is True
    assert result.semantic_hash == SEM
    assert result.compiled_hash == _encoding().compiled_hash


def test_invalid_sat_witness_is_rejected_even_if_backend_claims_sat():
    bad = _sat_result(assignment={1: False, 2: False, 3: False, 4: False})
    with pytest.raises(CICAdapterError, match="invalid SAT witness"):
        preflight(_encoding(), FakeBackend(bad))


def test_incomplete_sat_witness_is_rejected():
    with pytest.raises(CICAdapterError, match="incomplete"):
        verify_cnf_assignment(_encoding(), {1: True, 2: False})


def test_unsat_without_corroboration_is_withheld_as_unknown():
    result = preflight(_encoding(), FakeBackend(_unsat_result()))
    assert result.status is SolveStatus.UNKNOWN
    assert "withheld" in result.note


def test_unsat_requires_all_corroborators_to_agree():
    primary = FakeBackend(_unsat_result("primary"))
    agree = FakeBackend(_unsat_result("cadical"))
    result = preflight(_encoding(), primary, corroborators=(agree,))
    assert result.status is SolveStatus.UNSAT
    assert result.corroborating_solvers == ("cadical@1.0",)

    disagree = FakeBackend(_sat_result(solver_id="other"))
    result = preflight(_encoding(), primary, corroborators=(agree, disagree))
    assert result.status is SolveStatus.UNKNOWN
    assert result.corroborating_solvers == ()


def test_backend_structural_report_must_match_encoding():
    class WrongBackend(FakeBackend):
        def structural_report(self, encoding):
            return replace(super().structural_report(encoding), num_vars=99)

    with pytest.raises(CICAdapterError, match="num_vars"):
        preflight(_encoding(), WrongBackend(_sat_result()))


def test_structural_routing_hint_is_versioned_and_nonbinding():
    policy = RoutingPolicy(
        version="fixture/1",
        exact_max_treewidth=2,
        hashing_max_treewidth=5,
        stratified_max_treewidth=8,
    )
    assert routing_hint(StructuralReport(4, 3, 2, treewidth_estimate=2), policy) == "exact_or_compiled"
    assert routing_hint(StructuralReport(4, 3, 2, treewidth_estimate=4), policy) == "projected_hashing"
    assert routing_hint(StructuralReport(4, 3, 2, treewidth_estimate=7), policy) == "stratified_constrained"
    assert routing_hint(StructuralReport(4, 3, 2, treewidth_estimate=9), policy) == "proposal_or_rejection"


def test_backend_result_rejects_malformed_proof_metadata():
    with pytest.raises(CICAdapterError, match="proof_ref"):
        BackendResult(
            SolveStatus.UNSAT,
            solver_id="x",
            solver_version="1",
            proof_sha256="b" * 64,
        ).validate()

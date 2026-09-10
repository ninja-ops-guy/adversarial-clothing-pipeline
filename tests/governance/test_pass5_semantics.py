"""Differential semantic validation for distinct CIC encodings."""

from __future__ import annotations

import pytest

from ruthless_pipeline.governance.cic_adapter import CICError, ConstraintRepresentation
from ruthless_pipeline.governance.cic_semantics import differential_validate_encoding


PROBES = (
    {"x": False, "y": False},
    {"x": False, "y": True},
    {"x": True, "y": False},
    {"x": True, "y": True},
)


def representation(kind: str, payload, encoder_id: str) -> ConstraintRepresentation:
    return ConstraintRepresentation(
        representation=kind,
        semantic_payload={"operator": "or", "operands": ["x", "y"]},
        compiled_payload=payload,
        semantic_variables=("x", "y"),
        constraint_set_id="RAC-CS-CICSEM1",
        constraint_version="1.0.0",
        encoder_id=encoder_id,
        encoder_version="1.0.0",
        independent_support=("x", "y"),
    )


def semantic_or(assignment):
    return assignment["x"] or assignment["y"]


def eval_cnf(rep, assignment):
    variable_map = rep.compiled_payload["variable_map"]
    by_index = {index: bool(assignment[name]) for name, index in variable_map.items()}
    return all(
        any(by_index[abs(literal)] if literal > 0 else not by_index[abs(literal)] for literal in clause)
        for clause in rep.compiled_payload["clauses"]
    )


def eval_smt_or(rep, assignment):
    assert rep.compiled_payload["assert"] == "(or x y)"
    return assignment["x"] or assignment["y"]


def test_direct_cnf_and_smt_reformulations_match_reference_semantics():
    cnf = representation(
        "CNF",
        {"clauses": [[1, 2]], "variable_map": {"x": 1, "y": 2}},
        "direct-cnf",
    )
    smt = representation("SMT", {"assert": "(or x y)"}, "smt-bool")

    cnf_report = differential_validate_encoding(
        cnf,
        PROBES,
        semantic_evaluator=semantic_or,
        compiled_evaluator=eval_cnf,
    )
    smt_report = differential_validate_encoding(
        smt,
        PROBES,
        semantic_evaluator=semantic_or,
        compiled_evaluator=eval_smt_or,
    )

    assert cnf_report.semantic_hash == smt_report.semantic_hash
    assert cnf_report.compiled_hash != smt_report.compiled_hash
    assert cnf_report.validation_scope == "tested_probe_assignments_only"
    assert smt_report.validation_scope == "tested_probe_assignments_only"
    assert cnf_report.probe_count == len(PROBES)


def test_semantic_mismatch_fails_closed():
    incorrect_cnf = representation(
        "CNF",
        {"clauses": [[1], [2]], "variable_map": {"x": 1, "y": 2}},
        "bad-direct-cnf",
    )
    with pytest.raises(CICError, match="encoder semantic mismatch"):
        differential_validate_encoding(
            incorrect_cnf,
            PROBES,
            semantic_evaluator=semantic_or,
            compiled_evaluator=eval_cnf,
        )


def test_missing_probe_variable_fails_closed():
    cnf = representation(
        "CNF",
        {"clauses": [[1, 2]], "variable_map": {"x": 1, "y": 2}},
        "direct-cnf",
    )
    with pytest.raises(CICError, match="missing variables"):
        differential_validate_encoding(
            cnf,
            ({"x": True},),
            semantic_evaluator=semantic_or,
            compiled_evaluator=eval_cnf,
        )

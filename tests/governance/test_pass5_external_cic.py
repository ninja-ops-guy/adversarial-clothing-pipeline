"""Regression tests for the external CIC black-box adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from ruthless_pipeline.governance.cic_adapter import (
    CICError,
    ConstraintRepresentation,
    ExternalCICCoreBackend,
    SolveStatus,
    check,
)


CORE = """
def dpll_solve(clauses, num_vars, timeout=30.0):
    del num_vars, timeout
    if clauses == [[1]]:
        return {1: True}
    return None
"""


def install_fake_cic(root: Path) -> None:
    target = root / "security_tools" / "shared"
    target.mkdir(parents=True)
    (target / "cic_core.py").write_text(CORE, encoding="utf-8")


def representation(clauses, *, kind="CNF") -> ConstraintRepresentation:
    return ConstraintRepresentation(
        representation=kind,
        semantic_payload={"constraints": ["x"]},
        compiled_payload={
            "clauses": clauses,
            "num_vars": 1,
            "variable_map": {"x": 1},
        },
        semantic_variables=("x",),
        constraint_set_id="RAC-CS-CICEXT1",
        constraint_version="1.0.0",
        encoder_id="external-cnf-bridge",
        encoder_version="1.0.0",
        independent_support=("x",),
    )


def test_missing_external_cic_checkout_fails_closed(tmp_path):
    with pytest.raises(CICError, match="CIC core not found"):
        ExternalCICCoreBackend(tmp_path)


def test_external_cic_sat_model_is_independently_verified(tmp_path):
    install_fake_cic(tmp_path)
    result = check(
        representation([[1]]),
        backend=ExternalCICCoreBackend(tmp_path),
        assignment_verifier=lambda assignment: assignment == {"x": True},
    )
    assert result.status is SolveStatus.SAT
    assert result.assignment_verified is True
    assert result.scientific_projection == {"x": True}
    assert result.backend == "cic-core"
    assert result.backend_version == "external"


def test_external_cic_none_is_unknown_never_unsat(tmp_path):
    install_fake_cic(tmp_path)
    result = check(
        representation([[1], [-1]]),
        backend=ExternalCICCoreBackend(tmp_path),
        assignment_verifier=lambda _: True,
    )
    assert result.status is SolveStatus.UNKNOWN
    assert result.proof_verified is False
    assert "cannot distinguish UNSAT from timeout" in (result.note or "")


def test_external_cic_non_cnf_is_unknown(tmp_path):
    install_fake_cic(tmp_path)
    result = check(
        representation([[1]], kind="SMT"),
        backend=ExternalCICCoreBackend(tmp_path),
        assignment_verifier=lambda _: True,
    )
    assert result.status is SolveStatus.UNKNOWN
    assert "supports CNF only" in (result.note or "")

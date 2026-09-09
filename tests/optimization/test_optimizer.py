"""synthetic_pipeline_validation_only — baseline candidate-pool parity tests."""

from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.optimization.objective_registry import Objective
from ruthless_pipeline.optimization.optimizer import (
    Candidate,
    CandidatePoolSearchOptimizer,
    Optimizer,
)


def _table_objective(spec, table):
    """Objective whose detector_loss reads a synthetic detector-score table."""
    obj = Objective(spec)
    obj.register_term(
        "detector_loss",
        lambda x: (float(table[int(round(x[0]))]), {}),
    )
    return obj


def _synthetic_pool(table):
    return [
        Candidate(candidate_id=f"CAND-{i:03d}", params=np.array([float(i), 0.0]))
        for i in range(len(table))
    ]


def test_pool_parity_with_brute_force_min(spec):
    rng = np.random.default_rng(7)
    table = rng.uniform(0.0, 1.0, size=25).tolist()
    pool = _synthetic_pool(table)
    result = CandidatePoolSearchOptimizer(_table_objective(spec, table), pool).optimize()
    # Independent brute-force reference: argmin with candidate_id tie-break.
    best_id, best_val = None, np.inf
    for c in sorted(pool, key=lambda c: c.candidate_id):
        v = table[int(round(c.params[0]))]
        if v < best_val:
            best_id, best_val = c.candidate_id, v
    assert result.best_candidate_id == best_id
    assert result.best_value == pytest.approx(best_val)
    assert result.n_evaluations == len(pool)
    assert result.certification is None


def test_pool_parity_with_brute_force_max(spec):
    rng = np.random.default_rng(11)
    table = rng.uniform(0.0, 1.0, size=25).tolist()
    pool = _synthetic_pool(table)
    result = CandidatePoolSearchOptimizer(
        _table_objective(spec, table), pool, maximize=True
    ).optimize()
    best_id, best_val = None, -np.inf
    for c in sorted(pool, key=lambda c: c.candidate_id):
        v = table[int(round(c.params[0]))]
        if v > best_val:
            best_id, best_val = c.candidate_id, v
    assert result.best_candidate_id == best_id
    assert result.best_value == pytest.approx(best_val)


def test_tie_break_by_candidate_id(spec):
    table = [0.5, 0.5, 0.5]
    pool = _synthetic_pool(table)
    result = CandidatePoolSearchOptimizer(_table_objective(spec, table), pool).optimize()
    assert result.best_candidate_id == "CAND-000"


def test_selective_evaluation_subset(spec):
    table = [0.1, 0.2, 0.05, 0.3]
    pool = _synthetic_pool(table)
    result = CandidatePoolSearchOptimizer(
        _table_objective(spec, table), pool, candidate_ids=["CAND-001", "CAND-003"]
    ).optimize()
    assert result.best_candidate_id == "CAND-001"
    assert result.n_evaluations == 2


def test_empty_pool_rejected(spec):
    with pytest.raises(ValueError):
        CandidatePoolSearchOptimizer(_table_objective(spec, [0.1]), [])


def test_duplicate_ids_rejected(spec):
    pool = [Candidate("X", np.zeros(2)), Candidate("X", np.ones(2))]
    with pytest.raises(ValueError):
        CandidatePoolSearchOptimizer(_table_objective(spec, [0.1, 0.2]), pool)


def test_protocol_conformance(spec):
    opt = CandidatePoolSearchOptimizer(_table_objective(spec, [0.1]), _synthetic_pool([0.1]))
    assert isinstance(opt, Optimizer)

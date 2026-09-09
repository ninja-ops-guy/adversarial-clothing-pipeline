"""synthetic_pipeline_validation_only — (1+1)-ES black-box backend tests."""

from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.optimization.blackbox_backend import OnePlusOneESOptimizer
from ruthless_pipeline.optimization.constraints import BoxConstraint
from ruthless_pipeline.optimization.gradient_backend import DivergenceRefusalError
from ruthless_pipeline.optimization.objective_registry import Objective
from ruthless_pipeline.optimization.trajectory import TrajectoryRecorder

from conftest import make_quadratic_objective


def _run(spec, seed=42, max_iter=60):
    obj = make_quadratic_objective(spec)
    box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
    rec = TrajectoryRecorder(objective_id="es", seed=seed)
    opt = OnePlusOneESOptimizer(
        obj, np.array([0.9, -0.9]), box, seed=seed, sigma0=0.2,
        max_iter=max_iter, recorder=rec,
    )
    return opt.optimize(), rec


def test_same_seed_identical_trajectory(spec):
    res1, rec1 = _run(spec)
    res2, rec2 = _run(spec)
    assert rec1 == rec2
    assert res1.best_value == res2.best_value
    assert np.array_equal(res1.best_params, res2.best_params)
    assert res1.n_evaluations == res2.n_evaluations


def test_different_seeds_diverge(spec):
    _, rec1 = _run(spec, seed=1)
    _, rec2 = _run(spec, seed=2)
    assert rec1 != rec2


def test_improves_objective(spec):
    obj = make_quadratic_objective(spec)
    result, _ = _run(spec, max_iter=200)
    assert result.best_value < obj(np.array([0.9, -0.9]))
    assert result.certification is None


def test_respects_box(spec):
    c = np.array([3.0, 3.0])
    obj = Objective(spec)
    obj.register_term("detector_loss", lambda x: (float(np.sum((x - c) ** 2)), {}))
    box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
    opt = OnePlusOneESOptimizer(obj, np.zeros(2), box, seed=3, max_iter=50)
    result = opt.optimize()
    assert box.contains(result.best_params)


def test_divergence_refusal(spec):
    obj = Objective(spec)
    obj.register_term("detector_loss", lambda x: (float(np.sum(x ** 2)), {}))
    box = BoxConstraint(np.full(2, -1e9, dtype=float), np.full(2, 1e9, dtype=float))
    opt = OnePlusOneESOptimizer(
        obj, np.full(2, 1e6), box, seed=0, max_iter=5, divergence_bound=1e6
    )
    with pytest.raises(DivergenceRefusalError):
        opt.optimize()


def test_trajectory_provenance(spec):
    _, rec = _run(spec, max_iter=20)
    assert len(rec.steps) == 21  # initial + 20 iterations
    for step in rec.steps:
        assert len(step.params_hash) == 64
        assert step.term_values  # per-term values present
        assert "detector_loss" in step.term_values

"""synthetic_pipeline_validation_only — gradient backend tests."""

from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.optimization.constraints import BoxConstraint
from ruthless_pipeline.optimization.gradient_backend import (
    DivergenceRefusalError,
    GradientOptimizer,
    finite_difference_gradient,
)
from ruthless_pipeline.optimization.objective_registry import Objective
from ruthless_pipeline.optimization.trajectory import TrajectoryRecorder

from tests.optimization.conftest import make_quadratic_objective


def test_finite_difference_gradient_on_quadratic():
    # f(x) = sum((x - c)^2); grad = 2(x - c)
    c = np.array([0.3, -0.2, 0.7])
    f = lambda x: float(np.sum((x - c) ** 2))
    x = np.array([0.9, 0.1, -0.4])
    numeric = finite_difference_gradient(f, x, eps=1e-5)
    analytic = 2.0 * (x - c)
    err = float(np.max(np.abs(numeric - analytic)))
    assert err < 1e-4


def test_gradient_descent_converges_near_minimum(spec):
    obj = make_quadratic_objective(spec)
    box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
    opt = GradientOptimizer(obj, np.array([0.9, 0.9]), box, lr=0.05, max_iter=500)
    result = opt.optimize()
    # Weighted-sum minimizer is near (0.3, -0.2); check objective improves.
    assert result.best_value < obj(np.array([0.9, 0.9]))


def test_gradient_ascent_maximize(spec):
    # Maximize -sum((x-c)^2): optimum at c.
    c = np.array([0.4, 0.4])
    obj = Objective(spec)
    obj.register_term("detector_loss", lambda x: (-float(np.sum((x - c) ** 2)), {}))
    box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
    opt = GradientOptimizer(
        obj, np.array([-0.9, -0.9]), box, lr=0.1, max_iter=500, maximize=True
    )
    result = opt.optimize()
    assert np.allclose(result.best_params, c, atol=1e-2)


def test_projection_respects_box(spec):
    c = np.array([5.0, 5.0])  # unconstrained optimum far outside the box
    obj = Objective(spec)
    obj.register_term("detector_loss", lambda x: (float(np.sum((x - c) ** 2)), {}))
    box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
    opt = GradientOptimizer(obj, np.zeros(2), box, lr=0.5, max_iter=200)
    result = opt.optimize()
    assert box.contains(result.best_params)
    assert np.allclose(result.best_params, np.ones(2), atol=1e-6)


def test_divergence_refusal_on_bound(spec):
    obj = Objective(spec)
    obj.register_term("detector_loss", lambda x: (float(np.sum(x ** 2)), {}))
    box = BoxConstraint(np.full(2, -1e9), np.full(2, 1e9))
    opt = GradientOptimizer(
        obj, np.full(2, 5e5), box, lr=0.1, max_iter=5, divergence_bound=1e6
    )
    with pytest.raises(DivergenceRefusalError):
        opt.optimize()


def test_divergence_refusal_non_finite_gradient(spec):
    obj = Objective(spec)
    # finite at the start point but explodes under finite-difference probes
    obj.register_term(
        "detector_loss",
        lambda x: (0.0 if np.all(np.abs(x) < 0.5) else float("inf"), {}),
    )
    box = BoxConstraint(np.full(2, -2.0), np.full(2, 2.0))
    opt = GradientOptimizer(obj, np.array([0.4999995, 0.0]), box, lr=0.1, max_iter=3)
    from ruthless_pipeline.optimization.objective_registry import NaNRefusalError

    with pytest.raises((DivergenceRefusalError, NaNRefusalError)):
        opt.optimize()


def test_deterministic_same_seed_trajectory(spec):
    def run():
        obj = make_quadratic_objective(spec)
        box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
        rec = TrajectoryRecorder(objective_id="det", seed=spec.seed)
        opt = GradientOptimizer(
            obj, np.array([0.8, -0.6]), box, lr=0.05, max_iter=25, recorder=rec
        )
        result = opt.optimize()
        return rec, result

    rec1, res1 = run()
    rec2, res2 = run()
    assert rec1 == rec2
    assert res1.best_value == res2.best_value
    assert np.array_equal(res1.best_params, res2.best_params)

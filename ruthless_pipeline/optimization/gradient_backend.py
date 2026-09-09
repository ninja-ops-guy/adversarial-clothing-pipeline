"""Projected-gradient optimizer over box-constrained continuous vectors.

Pure numpy. Includes a central finite-difference gradient for sanity checks
and fail-closed divergence refusal: any non-finite objective/gradient, or
|J| exceeding a configurable bound, raises DivergenceRefusalError.
"""

from __future__ import annotations

import math

import numpy as np

from .constraints import BoxConstraint
from .objective_registry import Objective
from .optimizer import OptimizerResult
from .trajectory import TrajectoryRecorder


class DivergenceRefusalError(RuntimeError):
    """Raised when the objective or gradient diverges / goes non-finite."""


def finite_difference_gradient(
    fn,
    x: np.ndarray,
    eps: float = 1e-6,
) -> np.ndarray:
    """Central-difference gradient of a scalar function.

    For a quadratic with well-scaled eps the error is O(eps^2) (plus float
    roundoff), so agreement with the analytic gradient is expected well
    below 1e-4.
    """
    x = np.asarray(x, dtype=float)
    grad = np.zeros_like(x)
    for i in range(x.size):
        step = np.zeros_like(x)
        h = eps * max(1.0, abs(x[i]))
        step[i] = h
        fp = float(fn(x + step))
        fm = float(fn(x - step))
        if not (math.isfinite(fp) and math.isfinite(fm)):
            raise DivergenceRefusalError("non-finite objective during finite differencing")
        grad[i] = (fp - fm) / (2.0 * h)
    return grad


class GradientOptimizer:
    """Projected gradient ascent/descent on a box-constrained vector."""

    def __init__(
        self,
        objective: Objective,
        x0: np.ndarray,
        box: BoxConstraint,
        *,
        lr: float = 0.1,
        max_iter: int = 200,
        tol: float = 1e-9,
        maximize: bool = False,
        divergence_bound: float = 1e12,
        recorder: TrajectoryRecorder | None = None,
        analytic_gradient=None,
    ):
        if lr <= 0 or max_iter < 1:
            raise ValueError("lr must be > 0 and max_iter >= 1")
        if not (math.isfinite(divergence_bound) and divergence_bound > 0):
            raise ValueError("divergence_bound must be a positive finite number")
        self.objective = objective
        self.x = box.project(np.asarray(x0, dtype=float))
        self.box = box
        self.lr = float(lr)
        self.max_iter = int(max_iter)
        self.tol = float(tol)
        self.maximize = bool(maximize)
        self.divergence_bound = float(divergence_bound)
        self.recorder = recorder
        self.analytic_gradient = analytic_gradient

    def _check_value(self, value: float) -> float:
        if not math.isfinite(value) or abs(value) > self.divergence_bound:
            raise DivergenceRefusalError(
                f"objective value {value!r} diverged (bound {self.divergence_bound}); refusing to continue"
            )
        return value

    def _gradient(self, x: np.ndarray) -> np.ndarray:
        if self.analytic_gradient is not None:
            g = np.asarray(self.analytic_gradient(x), dtype=float)
        else:
            g = finite_difference_gradient(lambda v: self._check_value(self.objective(v)), x)
        if not np.all(np.isfinite(g)) or np.any(np.abs(g) > self.divergence_bound):
            raise DivergenceRefusalError("non-finite or exploding gradient; refusing to continue")
        return g

    def optimize(self) -> OptimizerResult:
        x = self.x.copy()
        n_eval = 0
        converged = False
        prev_value = None
        sign = 1.0 if self.maximize else -1.0
        for it in range(self.max_iter):
            evaluation = self.objective.evaluate(x)
            value = self._check_value(evaluation.total)
            n_eval += 1
            if self.recorder is not None:
                self.recorder.record(it, x, evaluation.term_values, value)
            grad = self._gradient(x)
            n_eval += 2 * x.size if self.analytic_gradient is None else 0
            x_new = self.box.project(x + sign * self.lr * grad)
            if prev_value is not None and abs(value - prev_value) < self.tol and np.allclose(
                x_new, x, atol=self.tol
            ):
                converged = True
                x = x_new
                break
            prev_value = value
            x = x_new
        final_value = self._check_value(self.objective(x))
        n_eval += 1
        return OptimizerResult(
            best_value=float(final_value),
            best_params=x,
            best_candidate_id=None,
            n_evaluations=n_eval,
            converged=converged,
            metadata={
                "mode": "maximize" if self.maximize else "minimize",
                "iterations_recorded": len(self.recorder.steps) if self.recorder else None,
            },
        )

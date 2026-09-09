"""Gradient-free black-box optimizer: seeded (1+1) evolution strategy.

Pure numpy, fully seeded (numpy Generator with PCG64). Each step proposes
x + sigma * N(0, I), projects onto the box, and accepts the proposal iff
it improves the objective (with deterministic one-fifth-rule step-size
adaptation). Same seed -> identical trajectory.
"""

from __future__ import annotations

import math

import numpy as np

from .constraints import BoxConstraint
from .gradient_backend import DivergenceRefusalError
from .objective_registry import Objective
from .optimizer import OptimizerResult
from .trajectory import TrajectoryRecorder


class OnePlusOneESOptimizer:
    """(1+1)-ES with 1/5th success-rule sigma adaptation, seeded."""

    def __init__(
        self,
        objective: Objective,
        x0: np.ndarray,
        box: BoxConstraint,
        *,
        seed: int = 0,
        sigma0: float = 0.1,
        max_iter: int = 200,
        maximize: bool = False,
        divergence_bound: float = 1e12,
        adaptation_window: int = 10,
        recorder: TrajectoryRecorder | None = None,
    ):
        if sigma0 <= 0 or max_iter < 1:
            raise ValueError("sigma0 must be > 0 and max_iter >= 1")
        if not (math.isfinite(divergence_bound) and divergence_bound > 0):
            raise ValueError("divergence_bound must be a positive finite number")
        self.objective = objective
        self.box = box
        self.x = box.project(np.asarray(x0, dtype=float))
        self.rng = np.random.default_rng(int(seed))
        self.seed = int(seed)
        self.sigma = float(sigma0)
        self.max_iter = int(max_iter)
        self.maximize = bool(maximize)
        self.divergence_bound = float(divergence_bound)
        self.adaptation_window = max(1, int(adaptation_window))
        self.recorder = recorder

    def _check(self, value: float) -> float:
        if not math.isfinite(value) or abs(value) > self.divergence_bound:
            raise DivergenceRefusalError(
                f"objective value {value!r} diverged (bound {self.divergence_bound}); refusing to continue"
            )
        return value

    def _improves(self, candidate: float, incumbent: float) -> bool:
        return candidate > incumbent if self.maximize else candidate < incumbent

    def optimize(self) -> OptimizerResult:
        x = self.x.copy()
        best_eval = self.objective.evaluate(x)
        best_value = self._check(best_eval.total)
        n_eval = 1
        if self.recorder is not None:
            self.recorder.record(0, x, best_eval.term_values, best_value)
        successes: list[int] = []
        for it in range(1, self.max_iter + 1):
            proposal = self.box.project(x + self.sigma * self.rng.standard_normal(x.size))
            evaluation = self.objective.evaluate(proposal)
            value = self._check(evaluation.total)
            n_eval += 1
            if self._improves(value, best_value):
                x = proposal
                best_value = value
                successes.append(1)
            else:
                successes.append(0)
            if self.recorder is not None:
                self.recorder.record(it, x, evaluation.term_values, best_value)
            if len(successes) >= self.adaptation_window:
                rate = float(np.mean(successes[-self.adaptation_window :]))
                # deterministic 1/5th-rule adaptation
                self.sigma *= 1.2 if rate > 0.2 else 0.82
                successes.clear()
            if self.recorder is not None:
                self.recorder.optimizer_state = {
                    "sigma": self.sigma,
                    "x": x.tolist(),
                    "best_value": best_value,
                    "n_evaluations": n_eval,
                }
        return OptimizerResult(
            best_value=float(best_value),
            best_params=x,
            best_candidate_id=None,
            n_evaluations=n_eval,
            converged=True,
            metadata={
                "mode": "maximize" if self.maximize else "minimize",
                "final_sigma": self.sigma,
                "seed": self.seed,
            },
        )

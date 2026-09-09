"""Base optimizer protocol + finite-pool candidate search (BASELINE PATH).

CandidatePoolSearchOptimizer preserves the existing finite-selection
baseline semantics: evaluate every candidate in the pool with the
objective and pick the argmin (or argmax when maximize=True), breaking
ties deterministically by candidate_id sort. It is the reference against
which all continuous optimizers in this namespace are validated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, runtime_checkable

import numpy as np

from .objective_registry import Objective
from .trajectory import TrajectoryRecorder


@dataclass
class Candidate:
    candidate_id: str
    params: np.ndarray
    metadata: dict = field(default_factory=dict)


@dataclass
class OptimizerResult:
    best_value: float
    best_params: np.ndarray | None = None
    best_candidate_id: str | None = None
    n_evaluations: int = 0
    converged: bool = False
    metadata: dict = field(default_factory=dict)
    # no certification from this infrastructure
    certification: None = None


@runtime_checkable
class Optimizer(Protocol):
    """Common optimizer protocol (minimization unless maximize=True)."""

    maximize: bool

    def optimize(self) -> OptimizerResult: ...


def _is_better(value: float, best: float, maximize: bool) -> bool:
    return value > best if maximize else value < best


class CandidatePoolSearchOptimizer:
    """Exhaustive (or selective) evaluation over a finite candidate pool.

    Baseline path — semantics preserved:
      * deterministic argmin/argmax;
      * ties broken by candidate_id ascending sort;
      * optional candidate_id allowlist for selective evaluation.
    """

    def __init__(
        self,
        objective: Objective,
        pool: Sequence[Candidate],
        *,
        maximize: bool = False,
        candidate_ids: Sequence[str] | None = None,
        recorder: TrajectoryRecorder | None = None,
    ):
        if not pool:
            raise ValueError("candidate pool must be non-empty")
        ids = [c.candidate_id for c in pool]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate candidate_id in pool")
        self.objective = objective
        self.maximize = bool(maximize)
        allow = set(candidate_ids) if candidate_ids is not None else None
        self.pool = sorted(
            (c for c in pool if allow is None or c.candidate_id in allow),
            key=lambda c: c.candidate_id,
        )
        if not self.pool:
            raise ValueError("candidate selection is empty after filtering")
        self.recorder = recorder

    def optimize(self) -> OptimizerResult:
        best: Candidate | None = None
        best_value = -np.inf if self.maximize else np.inf
        n_eval = 0
        for i, candidate in enumerate(self.pool):
            evaluation = self.objective.evaluate(candidate.params)
            n_eval += 1
            if self.recorder is not None:
                self.recorder.record(
                    iteration=i,
                    params=candidate.params,
                    term_values=evaluation.term_values,
                    total=evaluation.total,
                )
            value = evaluation.total
            # strict comparison + candidate_id-sorted iteration order gives
            # deterministic tie-breaking by candidate_id ascending.
            if best is None or _is_better(value, best_value, self.maximize):
                best = candidate
                best_value = value
        assert best is not None
        return OptimizerResult(
            best_value=float(best_value),
            best_params=np.asarray(best.params, dtype=float),
            best_candidate_id=best.candidate_id,
            n_evaluations=n_eval,
            converged=True,
            metadata={"mode": "maximize" if self.maximize else "minimize"},
        )

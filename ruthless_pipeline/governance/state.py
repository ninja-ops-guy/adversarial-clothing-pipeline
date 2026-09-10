"""Fail-closed experiment lifecycle for prospective governance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExperimentState(str, Enum):
    DRAFT = "DRAFT"
    PREFLIGHT = "PREFLIGHT"
    SEALED = "SEALED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    HALTED = "HALTED"


_ALLOWED = {
    ExperimentState.DRAFT: {ExperimentState.PREFLIGHT, ExperimentState.HALTED},
    ExperimentState.PREFLIGHT: {ExperimentState.SEALED, ExperimentState.HALTED},
    ExperimentState.SEALED: {ExperimentState.RUNNING, ExperimentState.HALTED},
    ExperimentState.RUNNING: {ExperimentState.COMPLETE, ExperimentState.HALTED},
    ExperimentState.COMPLETE: set(),
    ExperimentState.HALTED: set(),
}


class StateTransitionError(RuntimeError):
    pass


@dataclass
class GovernanceStateMachine:
    state: ExperimentState = ExperimentState.DRAFT

    def transition(self, target: ExperimentState) -> ExperimentState:
        if target not in _ALLOWED[self.state]:
            raise StateTransitionError(f"illegal governance transition: {self.state.value} -> {target.value}")
        self.state = target
        return self.state

    def halt(self) -> ExperimentState:
        if self.state in {ExperimentState.COMPLETE, ExperimentState.HALTED}:
            raise StateTransitionError(f"cannot halt terminal state: {self.state.value}")
        self.state = ExperimentState.HALTED
        return self.state

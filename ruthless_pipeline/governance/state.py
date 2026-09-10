"""Fail-closed experiment lifecycle for prospective governance.

Every state transition is ledger-backed.  The public ``state`` property is
read-only so callers cannot silently jump around governance checks, and HALT
requires a structured invariant-conflict record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

from .ids import GovernanceId, IdKind
from .ledger import GovernanceEventType, GovernanceLedger


class ExperimentState(str, Enum):
    DRAFT = "DRAFT"
    PREFLIGHT = "PREFLIGHT"
    SEALED = "SEALED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    HALTED = "HALTED"


_ALLOWED = {
    ExperimentState.DRAFT: {ExperimentState.PREFLIGHT},
    ExperimentState.PREFLIGHT: {ExperimentState.SEALED},
    ExperimentState.SEALED: {ExperimentState.RUNNING},
    ExperimentState.RUNNING: {ExperimentState.COMPLETE},
    ExperimentState.COMPLETE: set(),
    ExperimentState.HALTED: set(),
}


class StateTransitionError(RuntimeError):
    pass


@dataclass(frozen=True)
class InvariantConflict:
    invariant_ids: tuple[str, ...]
    affected_ids: tuple[str, ...]
    discovered_at: str
    evidence_status: str
    data_collection_occurred: bool
    required_governance_decision: str
    resolution_event_id: str | None = None

    def validate(self) -> None:
        if not self.invariant_ids or any(not value for value in self.invariant_ids):
            raise ValueError("invariant_ids must be non-empty")
        if not self.affected_ids or any(not value for value in self.affected_ids):
            raise ValueError("affected_ids must be non-empty")
        if not self.discovered_at.endswith("Z"):
            raise ValueError("discovered_at must be a UTC timestamp ending in Z")
        if not self.evidence_status:
            raise ValueError("evidence_status is required")
        if not isinstance(self.data_collection_occurred, bool):
            raise ValueError("data_collection_occurred must be boolean")
        if not self.required_governance_decision:
            raise ValueError("required_governance_decision is required")
        if self.resolution_event_id is not None:
            gid = GovernanceId.parse(self.resolution_event_id)
            if gid.kind is not IdKind.EVENT:
                raise ValueError("resolution_event_id must be a governance event id")


class GovernanceStateMachine:
    """Ledger-backed prospective governance state machine.

    ``HALTED`` is deliberately not reachable through :meth:`transition`; use
    :meth:`halt_for_conflict` so Law 7 always produces the required conflict
    record and append-only HALT event.
    """

    __slots__ = ("_state", "_halt_record", "_experiment_id", "_ledger", "_actor")

    def __init__(
        self,
        *,
        experiment_id: str,
        ledger: GovernanceLedger,
        actor: str,
    ) -> None:
        gid = GovernanceId.parse(experiment_id)
        if gid.kind is not IdKind.EXPERIMENT:
            raise ValueError("experiment_id must be RAC-EXP-*")
        if not isinstance(ledger, GovernanceLedger):
            raise TypeError("ledger must be a GovernanceLedger")
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor is required")
        self._state = ExperimentState.DRAFT
        self._halt_record: InvariantConflict | None = None
        self._experiment_id = experiment_id
        self._ledger = ledger
        self._actor = actor.strip()

    @property
    def state(self) -> ExperimentState:
        return self._state

    @property
    def halt_record(self) -> InvariantConflict | None:
        return self._halt_record

    @property
    def experiment_id(self) -> str:
        return self._experiment_id

    def transition(
        self,
        target: ExperimentState,
        *,
        event_id: str,
        created_at: str | None = None,
        payload: dict | None = None,
    ) -> ExperimentState:
        if target is ExperimentState.HALTED:
            raise StateTransitionError(
                "HALTED requires halt_for_conflict(); generic transition is forbidden"
            )
        if target not in _ALLOWED[self._state]:
            raise StateTransitionError(
                f"illegal governance transition: {self._state.value} -> {target.value}"
            )
        event_payload = {
            "from_state": self._state.value,
            "to_state": target.value,
            **(payload or {}),
        }
        # Append succeeds before the in-memory state changes.  If ledger
        # validation fails, the state remains unchanged (fail closed).
        self._ledger.append(
            event_id=event_id,
            experiment_id=self._experiment_id,
            event_type=GovernanceEventType.STATE_TRANSITION,
            payload=event_payload,
            actor=self._actor,
            created_at=created_at,
        )
        self._state = target
        return self._state

    def halt_for_conflict(
        self,
        conflict: InvariantConflict,
        *,
        event_id: str,
    ) -> ExperimentState:
        if self._state in {ExperimentState.COMPLETE, ExperimentState.HALTED}:
            raise StateTransitionError(f"cannot halt terminal state: {self._state.value}")
        conflict.validate()
        payload = {
            "from_state": self._state.value,
            "to_state": ExperimentState.HALTED.value,
            "conflict": asdict(conflict),
        }
        self._ledger.append(
            event_id=event_id,
            experiment_id=self._experiment_id,
            event_type=GovernanceEventType.HALT,
            payload=payload,
            actor=self._actor,
            created_at=conflict.discovered_at,
        )
        self._halt_record = conflict
        self._state = ExperimentState.HALTED
        return self._state

"""Append-only hash-chained governance event ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from .ids import GovernanceId, IdKind


class LedgerIntegrityError(RuntimeError):
    pass


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class GovernanceEvent:
    event_id: str
    experiment_id: str
    event_type: str
    timestamp_utc: str
    payload: dict[str, Any]
    previous_hash: str | None
    event_hash: str
    reverses_event_id: str | None = None
    supersedes_event_id: str | None = None

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "experiment_id": self.experiment_id,
            "event_type": self.event_type,
            "timestamp_utc": self.timestamp_utc,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
            "reverses_event_id": self.reverses_event_id,
            "supersedes_event_id": self.supersedes_event_id,
        }


class GovernanceLedger:
    """In-memory append-only ledger primitive used by higher-level persistence adapters."""

    def __init__(self) -> None:
        self._events: list[GovernanceEvent] = []

    @property
    def events(self) -> tuple[GovernanceEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        *,
        event_id: str,
        experiment_id: str,
        event_type: str,
        payload: dict[str, Any],
        timestamp_utc: str | None = None,
        reverses_event_id: str | None = None,
        supersedes_event_id: str | None = None,
    ) -> GovernanceEvent:
        GovernanceId.parse(event_id)
        GovernanceId.parse(experiment_id)
        if GovernanceId.parse(event_id).kind is not IdKind.EVENT:
            raise ValueError("event_id must be RAC-EVT-...")
        if GovernanceId.parse(experiment_id).kind is not IdKind.EXPERIMENT:
            raise ValueError("experiment_id must be RAC-EXP-...")
        if not event_type or not isinstance(payload, dict):
            raise ValueError("event_type and dict payload are required")
        previous_hash = self._events[-1].event_hash if self._events else None
        ts = timestamp_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        unsigned = {
            "event_id": event_id,
            "experiment_id": experiment_id,
            "event_type": event_type,
            "timestamp_utc": ts,
            "payload": payload,
            "previous_hash": previous_hash,
            "reverses_event_id": reverses_event_id,
            "supersedes_event_id": supersedes_event_id,
        }
        digest = hashlib.sha256(_canonical(unsigned)).hexdigest()
        event = GovernanceEvent(event_hash=digest, **unsigned)
        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous: str | None = None
        seen_ids: set[str] = set()
        for event in self._events:
            if event.event_id in seen_ids:
                raise LedgerIntegrityError(f"duplicate event id: {event.event_id}")
            if event.previous_hash != previous:
                raise LedgerIntegrityError(f"broken previous_hash at {event.event_id}")
            expected = hashlib.sha256(_canonical(event.unsigned_dict())).hexdigest()
            if expected != event.event_hash:
                raise LedgerIntegrityError(f"event hash mismatch at {event.event_id}")
            seen_ids.add(event.event_id)
            previous = event.event_hash
        return True

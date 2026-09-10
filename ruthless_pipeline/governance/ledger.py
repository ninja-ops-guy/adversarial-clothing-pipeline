"""Append-only hash-chained governance event ledger.

The event representation follows Experimental Governance v1 §5.  Payload
bytes are hash-bound separately from event metadata, the chain points to the
previous event digest, and corrective history is represented by reversal or
supersession events rather than mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any

from .ids import GovernanceId, IdKind


class LedgerIntegrityError(RuntimeError):
    pass


class GovernanceEventType(str, Enum):
    CREATE = "CREATE"
    STATE_TRANSITION = "STATE_TRANSITION"
    SEAL = "SEAL"
    HALT = "HALT"
    RESUME = "RESUME"
    REVERSAL = "REVERSAL"
    SUPERSESSION = "SUPERSESSION"
    INVALIDATION = "INVALIDATION"
    CONSTRAINT_MIGRATION = "CONSTRAINT_MIGRATION"
    PIPELINE_MIGRATION = "PIPELINE_MIGRATION"
    RESCREEN = "RESCREEN"
    BRIDGE_DECISION = "BRIDGE_DECISION"
    REGIME_RESET = "REGIME_RESET"


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def payload_sha256(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise ValueError("governance event payload must be a dict")
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _require_utc_timestamp(value: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("created_at must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("created_at must be a valid RFC3339 UTC timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("created_at must be UTC")


@dataclass(frozen=True)
class GovernanceEvent:
    schema_version: str
    event_id: str
    experiment_id: str
    event_type: str
    created_at: str
    actor: str
    payload: dict[str, Any]
    payload_sha256: str
    previous_event_sha256: str | None
    event_sha256: str
    reverses_event_id: str | None = None
    supersedes_event_id: str | None = None

    def unsigned_dict(self) -> dict[str, Any]:
        """Hash-bound event metadata, excluding the payload bytes themselves."""
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "experiment_id": self.experiment_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
            "actor": self.actor,
            "payload_sha256": self.payload_sha256,
            "previous_event_sha256": self.previous_event_sha256,
            "reverses_event_id": self.reverses_event_id,
            "supersedes_event_id": self.supersedes_event_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.unsigned_dict(),
            "payload": self.payload,
            "event_sha256": self.event_sha256,
        }

    # Read-compatibility properties for the pre-adoption prototype API.
    @property
    def timestamp_utc(self) -> str:
        return self.created_at

    @property
    def previous_hash(self) -> str | None:
        return self.previous_event_sha256

    @property
    def event_hash(self) -> str:
        return self.event_sha256


class GovernanceLedger:
    """Single-writer append-only ledger primitive.

    Persistence adapters may store the immutable events elsewhere, but all
    writes pass through :meth:`append` and all loaded histories must pass
    :meth:`verify` before use.
    """

    def __init__(self) -> None:
        self._events: list[GovernanceEvent] = []

    @property
    def events(self) -> tuple[GovernanceEvent, ...]:
        return tuple(self._events)

    def _seen_by_canonical_id(self) -> dict[str, GovernanceEvent]:
        seen: dict[str, GovernanceEvent] = {}
        for event in self._events:
            parsed = GovernanceId.parse(event.event_id)
            seen[parsed.canonical] = event
        return seen

    def append(
        self,
        *,
        event_id: str,
        experiment_id: str,
        event_type: str | GovernanceEventType,
        payload: dict[str, Any],
        actor: str,
        created_at: str | None = None,
        timestamp_utc: str | None = None,
        reverses_event_id: str | None = None,
        supersedes_event_id: str | None = None,
    ) -> GovernanceEvent:
        event_gid = GovernanceId.parse(event_id)
        experiment_gid = GovernanceId.parse(experiment_id)
        if event_gid.kind is not IdKind.EVENT:
            raise ValueError("event_id must be a RAC-GOV-EVT-* governance event id")
        if experiment_gid.kind is not IdKind.EXPERIMENT:
            raise ValueError("experiment_id must be RAC-EXP-*")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict")
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor is required")
        if created_at is not None and timestamp_utc is not None:
            raise ValueError("provide created_at or timestamp_utc, not both")

        try:
            event_type_value = GovernanceEventType(event_type).value
        except ValueError as exc:
            raise ValueError(f"unsupported governance event type: {event_type!r}") from exc

        seen = self._seen_by_canonical_id()
        if event_gid.canonical in seen:
            raise ValueError(f"duplicate governance event id: {event_gid.canonical}")

        if reverses_event_id is not None and supersedes_event_id is not None:
            raise ValueError("an event cannot reverse and supersede simultaneously")
        if event_type_value == GovernanceEventType.REVERSAL.value:
            if reverses_event_id is None:
                raise ValueError("REVERSAL requires reverses_event_id")
        elif reverses_event_id is not None:
            raise ValueError("reverses_event_id is valid only on REVERSAL events")
        if event_type_value == GovernanceEventType.SUPERSESSION.value:
            if supersedes_event_id is None:
                raise ValueError("SUPERSESSION requires supersedes_event_id")
        elif supersedes_event_id is not None:
            raise ValueError("supersedes_event_id is valid only on SUPERSESSION events")

        for label, reference in (
            ("reverses_event_id", reverses_event_id),
            ("supersedes_event_id", supersedes_event_id),
        ):
            if reference is None:
                continue
            ref_gid = GovernanceId.parse(reference)
            if ref_gid.kind is not IdKind.EVENT:
                raise ValueError(f"{label} must reference a governance event id")
            prior = seen.get(ref_gid.canonical)
            if prior is None:
                raise ValueError(f"{label} must reference an earlier ledger event")
            if GovernanceId.parse(prior.experiment_id).canonical != experiment_gid.canonical:
                raise ValueError(f"{label} cannot cross experiment histories")

        previous_event_sha256 = self._events[-1].event_sha256 if self._events else None
        ts = created_at or timestamp_utc
        if ts is None:
            ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        _require_utc_timestamp(ts)

        p_hash = payload_sha256(payload)
        unsigned = {
            "schema_version": "1.0",
            "event_id": event_id,
            "experiment_id": experiment_id,
            "event_type": event_type_value,
            "created_at": ts,
            "actor": actor.strip(),
            "payload_sha256": p_hash,
            "previous_event_sha256": previous_event_sha256,
            "reverses_event_id": reverses_event_id,
            "supersedes_event_id": supersedes_event_id,
        }
        digest = hashlib.sha256(_canonical(unsigned)).hexdigest()
        event = GovernanceEvent(
            payload=dict(payload),
            event_sha256=digest,
            **unsigned,
        )
        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous: str | None = None
        seen: dict[str, GovernanceEvent] = {}
        for event in self._events:
            try:
                event_gid = GovernanceId.parse(event.event_id)
                experiment_gid = GovernanceId.parse(event.experiment_id)
            except ValueError as exc:
                raise LedgerIntegrityError("ledger contains malformed governance id") from exc
            if event_gid.kind is not IdKind.EVENT or experiment_gid.kind is not IdKind.EXPERIMENT:
                raise LedgerIntegrityError("ledger contains wrong governance id kind")
            if event_gid.canonical in seen:
                raise LedgerIntegrityError(
                    f"duplicate semantic event id: {event_gid.canonical}"
                )
            if event.schema_version != "1.0":
                raise LedgerIntegrityError(
                    f"unsupported event schema at {event.event_id}: {event.schema_version}"
                )
            try:
                GovernanceEventType(event.event_type)
                _require_utc_timestamp(event.created_at)
            except ValueError as exc:
                raise LedgerIntegrityError(f"invalid event metadata at {event.event_id}") from exc
            if not event.actor.strip():
                raise LedgerIntegrityError(f"missing actor at {event.event_id}")
            if event.previous_event_sha256 != previous:
                raise LedgerIntegrityError(
                    f"broken previous_event_sha256 at {event.event_id}"
                )
            expected_payload_hash = payload_sha256(event.payload)
            if expected_payload_hash != event.payload_sha256:
                raise LedgerIntegrityError(f"payload hash mismatch at {event.event_id}")
            expected_event_hash = hashlib.sha256(_canonical(event.unsigned_dict())).hexdigest()
            if expected_event_hash != event.event_sha256:
                raise LedgerIntegrityError(f"event hash mismatch at {event.event_id}")

            for label, reference, expected_type in (
                ("reverses_event_id", event.reverses_event_id, GovernanceEventType.REVERSAL),
                ("supersedes_event_id", event.supersedes_event_id, GovernanceEventType.SUPERSESSION),
            ):
                if event.event_type == expected_type.value:
                    if reference is None:
                        raise LedgerIntegrityError(
                            f"{event.event_type} missing {label} at {event.event_id}"
                        )
                elif reference is not None:
                    raise LedgerIntegrityError(
                        f"unexpected {label} at {event.event_id}"
                    )
                if reference is not None:
                    try:
                        ref_gid = GovernanceId.parse(reference)
                    except ValueError as exc:
                        raise LedgerIntegrityError(
                            f"invalid {label} at {event.event_id}"
                        ) from exc
                    prior = seen.get(ref_gid.canonical)
                    if prior is None:
                        raise LedgerIntegrityError(
                            f"{label} does not reference prior event at {event.event_id}"
                        )
                    if GovernanceId.parse(prior.experiment_id).canonical != experiment_gid.canonical:
                        raise LedgerIntegrityError(
                            f"{label} crosses experiment history at {event.event_id}"
                        )

            seen[event_gid.canonical] = event
            previous = event.event_sha256
        return True

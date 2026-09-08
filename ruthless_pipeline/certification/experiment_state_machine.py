"""Formal experiment lifecycle state machine (fail-closed).

States (the scientific lifecycle, strictly ordered):

    DRAFT -> PREREGISTERED -> ARMED -> RUNNING -> EVIDENCE_SEALED -> CLOSED
    -> PUBLISHED

INFRASTRUCTURE_FAILURE is deliberately NOT a state: an infrastructure failure
(no outcome produced) can attach at ANY state and is recorded as an
orthogonal failure record on the machine, mirroring the D2-0006
interpretation policy (``d20006_governance.INFRASTRUCTURE_FAILURE_BRANCH`` /
``INFRASTRUCTURE_FAILURE_CATEGORY`` are reused, not duplicated). A failure
record never fabricates a decision region and never advances the lifecycle
by itself; CLOSED may be reached through the failure path only when a sealed
infra ``FAILURE.json`` is presented as the closure artifact.

Guards (fail closed; violations raise, nothing is half-applied):

- DRAFT -> PREREGISTERED: a preregistration document reference with a
  64-hex sha256 must be supplied (the frozen doc hash is pinned here).
- PREREGISTERED -> ARMED: the presented preregistration hash must equal the
  hash pinned at preregistration (no drift between preregistration and
  arming), and an explicit ``armed: true`` attestation is required. This
  mirrors generations/*.json ``lock_status``/``armed`` semantics: a record
  that stays ``PREREGISTERED, armed:false`` (e.g. D2-0005) can never be
  armed through this machine without that attestation.
- ARMED -> RUNNING: a freeze manifest (relpath -> sha256) must be present
  on disk and every listed file must hash-verify.
- RUNNING -> EVIDENCE_SEALED: the sealed evidence artifact must re-hash to
  its pinned/embedded digest (content re-hash, not filename trust).
- EVIDENCE_SEALED -> CLOSED: requires EITHER a decision-region outcome
  artifact whose ``decision_region`` is one of the preregistered regions
  (``d20006_governance.DECISION_REGION_BRANCHES``) OR an infrastructure
  FAILURE.json whose ``classification.category`` is
  ``"infrastructure_failure"``. Both at once is ambiguous and refused.
- CLOSED -> PUBLISHED: requires a release directory that passes
  ``release_format.verify_release`` (no tampered/missing/extra files).

Every accepted transition and every failure attachment is logged to an
append-only, sha-chained journal: each entry embeds the sha256 of the
previous entry, so truncation, reordering, or edit of any entry is detected
by ``verify_journal``. ``replay_journal`` deterministically reconstructs a
machine from a journal, re-checking transition legality (but not re-running
guards; each entry pins a ``guard_proof`` hash of the guard evidence that
was verified at append time).

Wiring to existing records: ``state_for_lock_status`` maps a generation
record's ``lock_status``/``armed`` fields onto this machine without ever
writing to the record. Rehearsal stage names are mapped via
``REHEARSAL_STAGE_TO_STATE`` so the rehearsal journal
(``rehearsal_d20005.STAGES``) can be read as lifecycle progress.

Everything exercised in tests is synthetic and labelled
``synthetic_pipeline_validation_only``. This module NEVER writes to
generations/, never arms D2-0005, and never touches thresholds.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .d20006_governance import (
    DECISION_REGION_BRANCHES,
    INFRASTRUCTURE_FAILURE_CATEGORY,
)
from .release_format import hash_file, verify_release
from .schema_version import require_schema_version

import hashlib

SCHEMA_VERSION = "1.0"
JOURNAL_SCHEMA_ID = "experiment-state-machine-journal"
EVIDENCE_CLASS = "synthetic_pipeline_validation_only"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class State(Enum):
    """The ordered scientific lifecycle states."""

    DRAFT = "DRAFT"
    PREREGISTERED = "PREREGISTERED"
    ARMED = "ARMED"
    RUNNING = "RUNNING"
    EVIDENCE_SEALED = "EVIDENCE_SEALED"
    CLOSED = "CLOSED"
    PUBLISHED = "PUBLISHED"


#: The only legal lifecycle transitions (strictly forward, no skips).
TRANSITIONS: tuple[tuple[State, State], ...] = (
    (State.DRAFT, State.PREREGISTERED),
    (State.PREREGISTERED, State.ARMED),
    (State.ARMED, State.RUNNING),
    (State.RUNNING, State.EVIDENCE_SEALED),
    (State.EVIDENCE_SEALED, State.CLOSED),
    (State.CLOSED, State.PUBLISHED),
)

#: Mapping from a generation record's lock_status to a machine state. Armed
#: requires the separate explicit ``armed: true`` field (see
#: :func:`state_for_lock_status`); a PREREGISTERED lock never implies ARMED.
LOCK_STATUS_TO_STATE = {
    "DRAFT": State.DRAFT,
    "PREREGISTERED": State.PREREGISTERED,
    "ARMED": State.ARMED,
    "RUNNING": State.RUNNING,
    "EVIDENCE_SEALED": State.EVIDENCE_SEALED,
    "CLOSED": State.CLOSED,
    "PUBLISHED": State.PUBLISHED,
}

#: Rehearsal journal stage -> lifecycle state reached on its completion
#: (rehearsal_d20005.STAGES: fixture, selection, freeze, analysis, seal,
#: release, export). fixture/selection are pre-arming preparation; freeze
#: enters RUNNING; seal seals evidence; release/export are post-close
#: publication work.
REHEARSAL_STAGE_TO_STATE = {
    "fixture": State.PREREGISTERED,
    "selection": State.PREREGISTERED,
    "freeze": State.RUNNING,
    "analysis": State.RUNNING,
    "seal": State.EVIDENCE_SEALED,
    "release": State.PUBLISHED,
    "export": State.PUBLISHED,
}


class StateMachineError(ValueError):
    """Base class for all state-machine refusals (fail closed)."""


class IllegalTransitionError(StateMachineError):
    """The requested (from, to) pair is not in the transition table."""


class TransitionGuardError(StateMachineError):
    """A legal transition's guard evidence was missing or failed checks."""


class JournalTamperError(StateMachineError):
    """The append-only journal failed sha-chain verification."""


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GuardEvidence:
    """Machine-readable proof that a transition guard was satisfied.

    Exactly the fields relevant to the transition are populated; the guard
    proof hash is computed over whichever fields are present.
    """

    preregistration_sha256: str | None = None
    armed_attestation: bool | None = None
    freeze_manifest_sha256: str | None = None
    sealed_evidence_sha256: str | None = None
    closure_artifact_sha256: str | None = None
    closure_kind: str | None = None  # "decision_region" | "infrastructure_failure"
    release_content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in {
            "preregistration_sha256": self.preregistration_sha256,
            "armed_attestation": self.armed_attestation,
            "freeze_manifest_sha256": self.freeze_manifest_sha256,
            "sealed_evidence_sha256": self.sealed_evidence_sha256,
            "closure_artifact_sha256": self.closure_artifact_sha256,
            "closure_kind": self.closure_kind,
            "release_content_hash": self.release_content_hash,
        }.items() if v is not None}

    @property
    def proof_hash(self) -> str:
        return _sha256_bytes(_canonical(self.to_dict()))


def _guard_preregistered(evidence: GuardEvidence) -> None:
    if not _is_sha256(evidence.preregistration_sha256):
        raise TransitionGuardError(
            "DRAFT -> PREREGISTERED requires the pinned sha256 of the frozen "
            "preregistration document"
        )


def _guard_armed(evidence: GuardEvidence, machine: "ExperimentStateMachine") -> None:
    if evidence.armed_attestation is not True:
        raise TransitionGuardError(
            "PREREGISTERED -> ARMED requires an explicit armed attestation; a "
            "PREREGISTERED, armed:false record (e.g. D2-0005) may not be armed"
        )
    if not _is_sha256(evidence.preregistration_sha256):
        raise TransitionGuardError(
            "PREREGISTERED -> ARMED requires the preregistration document hash"
        )
    pinned = machine.preregistration_sha256
    if pinned is None:
        raise TransitionGuardError(
            "no preregistration hash is pinned on this machine; refusing to arm"
        )
    if evidence.preregistration_sha256 != pinned:
        raise TransitionGuardError(
            "preregistration hash drift: presented "
            f"{evidence.preregistration_sha256} != pinned {pinned}; the "
            "preregistration must be byte-identical at arming time"
        )


def _guard_running(evidence: GuardEvidence, freeze_manifest_path: Path | None) -> None:
    """ARMED -> RUNNING: freeze manifest present and hash-verified."""
    if freeze_manifest_path is None:
        raise TransitionGuardError(
            "ARMED -> RUNNING requires a freeze manifest path"
        )
    path = Path(freeze_manifest_path)
    if not path.is_file():
        raise TransitionGuardError(f"freeze manifest not found: {path}")
    manifest = json.loads(path.read_text())
    entries = manifest.get("entries") if isinstance(manifest, dict) else None
    if not isinstance(entries, dict) or not entries:
        raise TransitionGuardError(
            f"freeze manifest {path} has no 'entries' mapping of relpath->sha256"
        )
    base = path.parent
    bad = []
    for rel, digest in sorted(entries.items()):
        if not _is_sha256(digest):
            bad.append(f"{rel}: not a 64-hex digest")
            continue
        target = base / rel
        if not target.is_file():
            bad.append(f"{rel}: missing")
        elif hash_file(target) != digest:
            bad.append(f"{rel}: hash mismatch")
    if bad:
        raise TransitionGuardError(
            "freeze manifest failed verification: " + "; ".join(bad)
        )
    if evidence.freeze_manifest_sha256 != _sha256_bytes(path.read_bytes()):
        raise TransitionGuardError(
            "freeze manifest content hash does not match the guard evidence"
        )


def _guard_evidence_sealed(evidence: GuardEvidence, sealed_path: Path | None) -> None:
    """RUNNING -> EVIDENCE_SEALED: sealed evidence hash verification."""
    if sealed_path is None:
        raise TransitionGuardError(
            "RUNNING -> EVIDENCE_SEALED requires a sealed evidence artifact path"
        )
    path = Path(sealed_path)
    if not path.is_file():
        raise TransitionGuardError(f"sealed evidence not found: {path}")
    actual = _sha256_bytes(path.read_bytes())
    if not _is_sha256(evidence.sealed_evidence_sha256):
        raise TransitionGuardError(
            "guard evidence must pin the expected sealed evidence sha256"
        )
    if actual != evidence.sealed_evidence_sha256:
        raise TransitionGuardError(
            f"sealed evidence hash mismatch: on-disk {actual} != pinned "
            f"{evidence.sealed_evidence_sha256}; refusing to seal tampered evidence"
        )


def _guard_closed(
    evidence: GuardEvidence,
    outcome_artifact_path: Path | None,
    failure_json_path: Path | None,
) -> None:
    """EVIDENCE_SEALED -> CLOSED: decision region OR infra FAILURE.json."""
    has_outcome = outcome_artifact_path is not None and Path(outcome_artifact_path).is_file()
    has_failure = failure_json_path is not None and Path(failure_json_path).is_file()
    if has_outcome and has_failure:
        raise TransitionGuardError(
            "both a decision-region outcome artifact and FAILURE.json were "
            "presented: closure is ambiguous (fail closed), matching the "
            "outcome-never-observed criterion of the interpretation policy"
        )
    if not has_outcome and not has_failure:
        raise TransitionGuardError(
            "EVIDENCE_SEALED -> CLOSED requires a decision-region outcome "
            "artifact or an infrastructure FAILURE.json"
        )
    if has_outcome:
        path = Path(outcome_artifact_path)
        outcome = json.loads(path.read_text())
        region = outcome.get("decision_region") if isinstance(outcome, dict) else None
        if region not in DECISION_REGION_BRANCHES:
            raise TransitionGuardError(
                f"decision_region {region!r} is not one of the preregistered "
                f"regions {sorted(DECISION_REGION_BRANCHES)} (fail closed)"
            )
        actual = _sha256_bytes(path.read_bytes())
        if evidence.closure_artifact_sha256 != actual or evidence.closure_kind != "decision_region":
            raise TransitionGuardError(
                "outcome artifact hash/kind does not match the guard evidence"
            )
        return
    path = Path(failure_json_path)
    failure = json.loads(path.read_text())
    for required in ("failure_stage", "failure_reason", "detected_utc", "invalidates"):
        if required not in failure:
            raise TransitionGuardError(
                f"FAILURE.json missing required field {required!r}"
            )
    category = (failure.get("classification") or {}).get("category")
    if category != INFRASTRUCTURE_FAILURE_CATEGORY:
        raise TransitionGuardError(
            f"FAILURE.json category {category!r} is not "
            f"{INFRASTRUCTURE_FAILURE_CATEGORY!r}: a scientific failure record "
            "cannot close an experiment as infrastructure failure"
        )
    actual = _sha256_bytes(path.read_bytes())
    if (
        evidence.closure_artifact_sha256 != actual
        or evidence.closure_kind != "infrastructure_failure"
    ):
        raise TransitionGuardError(
            "FAILURE.json hash/kind does not match the guard evidence"
        )


def _guard_published(evidence: GuardEvidence, release_dir: Path | None) -> None:
    """CLOSED -> PUBLISHED: release verification via release_format."""
    if release_dir is None:
        raise TransitionGuardError("CLOSED -> PUBLISHED requires a release directory")
    try:
        result = verify_release(Path(release_dir))
    except ValueError as exc:
        raise TransitionGuardError(f"release is not verifiable: {exc}") from exc
    if not result.ok:
        raise TransitionGuardError(
            "release fails verification (tampered="
            f"{result.tampered}, missing={result.missing}, extra={result.extra}); "
            "refusing to publish an unverifiable release"
        )
    if not _is_sha256(evidence.release_content_hash):
        raise TransitionGuardError(
            "guard evidence must pin the release content hash"
        )


# ---------------------------------------------------------------------------
# Failure record (orthogonal to the lifecycle)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InfrastructureFailureRecord:
    """An infrastructure-failure record attached at any state.

    This is NOT a terminal scientific state: it records that infrastructure
    (not the hypothesis) failed, which stages it invalidates, and that no
    outcome was observed. It never advances the lifecycle by itself.
    """

    failure_stage: str
    failure_reason: str
    detected_utc: str
    invalidates: tuple[str, ...]
    attached_at_state: State
    outcome_observed: bool = False

    def validate(self) -> None:
        if not self.failure_stage:
            raise StateMachineError("failure_stage is required")
        if not self.failure_reason:
            raise StateMachineError("failure_reason is required")
        if not self.detected_utc:
            raise StateMachineError("detected_utc is required")
        if self.outcome_observed:
            raise StateMachineError(
                "an infrastructure failure record with an observed outcome is a "
                "contradiction: a scientific failure must close via a decision "
                "region, never via the infrastructure channel"
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "category": INFRASTRUCTURE_FAILURE_CATEGORY,
            "failure_stage": self.failure_stage,
            "failure_reason": self.failure_reason,
            "detected_utc": self.detected_utc,
            "invalidates": list(self.invalidates),
            "attached_at_state": self.attached_at_state.value,
            "outcome_observed": self.outcome_observed,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InfrastructureFailureRecord":
        record = cls(
            failure_stage=payload["failure_stage"],
            failure_reason=payload["failure_reason"],
            detected_utc=payload["detected_utc"],
            invalidates=tuple(payload.get("invalidates", ())),
            attached_at_state=State(payload["attached_at_state"]),
            outcome_observed=bool(payload.get("outcome_observed", False)),
        )
        record.validate()
        return record


# ---------------------------------------------------------------------------
# Append-only sha-chained journal
# ---------------------------------------------------------------------------

def _entry_hash(entry: dict[str, Any]) -> str:
    payload = {k: v for k, v in entry.items() if k != "entry_sha256"}
    return _sha256_bytes(_canonical(payload))


def make_journal_entry(
    *,
    seq: int,
    event: str,
    from_state: str | None,
    to_state: str | None,
    created_utc: str,
    detail: str,
    guard_proof: str | None,
    failure_record: dict[str, Any] | None,
    prev_sha256: str,
) -> dict[str, Any]:
    entry = {
        "seq": seq,
        "event": event,  # "transition" | "infrastructure_failure"
        "from_state": from_state,
        "to_state": to_state,
        "created_utc": created_utc,
        "detail": detail,
        "guard_proof": guard_proof,
        "failure_record": failure_record,
        "prev_sha256": prev_sha256,
    }
    entry["entry_sha256"] = _entry_hash(entry)
    return entry


def verify_journal(journal: dict[str, Any]) -> None:
    """Fail closed unless the journal's sha chain is intact.

    Detects edits to any entry, reordering, truncation masked by rewriting
    seq numbers, and genesis replacement.
    """
    require_schema_version(journal, SCHEMA_VERSION, label="state machine journal")
    if journal.get("schema_id") != JOURNAL_SCHEMA_ID:
        raise JournalTamperError(
            f"schema_id {journal.get('schema_id')!r} is not {JOURNAL_SCHEMA_ID!r}"
        )
    entries = journal.get("entries")
    if not isinstance(entries, list):
        raise JournalTamperError("journal has no entries list")
    prev = journal.get("genesis_sha256")
    if not _is_sha256(prev):
        raise JournalTamperError("journal genesis hash missing or malformed")
    for i, entry in enumerate(entries):
        if entry.get("seq") != i:
            raise JournalTamperError(f"entry {i}: seq mismatch")
        if entry.get("prev_sha256") != prev:
            raise JournalTamperError(
                f"entry {i}: prev_sha256 does not chain from the previous entry"
            )
        if entry.get("entry_sha256") != _entry_hash(entry):
            raise JournalTamperError(
                f"entry {i}: entry hash mismatch (content was edited)"
            )
        prev = entry["entry_sha256"]


def genesis_hash(experiment_label: str) -> str:
    return _sha256_bytes(_canonical({"genesis": experiment_label}))


# ---------------------------------------------------------------------------
# The machine
# ---------------------------------------------------------------------------

class ExperimentStateMachine:
    """Fail-closed experiment lifecycle machine with a sha-chained journal.

    Construct with ``experiment_label`` (free-form; synthetic-only in tests)
    and optionally an initial ``state`` plus ``preregistration_sha256`` when
    adopting an existing record's position (see :func:`state_for_lock_status`).
    The journal is in-memory plus optional mirroring to ``journal_path`` on
    every append (atomic write; the file is always a complete journal).
    """

    def __init__(
        self,
        *,
        experiment_label: str,
        state: State = State.DRAFT,
        preregistration_sha256: str | None = None,
        journal_path: Path | None = None,
        entries: list[dict[str, Any]] | None = None,
        failures: list[InfrastructureFailureRecord] | None = None,
        evidence_class: str = EVIDENCE_CLASS,
    ) -> None:
        if preregistration_sha256 is not None and not _is_sha256(preregistration_sha256):
            raise StateMachineError("preregistration_sha256 must be a 64-hex digest")
        self.experiment_label = experiment_label
        self.state = state
        self.preregistration_sha256 = preregistration_sha256
        self.journal_path = Path(journal_path) if journal_path else None
        self.entries: list[dict[str, Any]] = list(entries or [])
        self.failures: list[InfrastructureFailureRecord] = list(failures or [])
        self.evidence_class = evidence_class
        if self.journal_path and self.journal_path.exists():
            on_disk = json.loads(self.journal_path.read_text())
            verify_journal(on_disk)
            if _canonical(on_disk["entries"]) != _canonical(self.entries):
                raise JournalTamperError(
                    "in-memory entries diverge from the on-disk journal"
                )

    # -- journal plumbing ----------------------------------------------------

    def _prev_sha(self) -> str:
        if self.entries:
            return self.entries[-1]["entry_sha256"]
        return genesis_hash(self.experiment_label)

    def _append(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)
        if self.journal_path:
            journal = self.to_journal()
            blob = _canonical(journal) + b"\n"
            tmp = self.journal_path.with_suffix(".tmp")
            tmp.write_bytes(blob)
            tmp.replace(self.journal_path)

    def to_journal(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "schema_id": JOURNAL_SCHEMA_ID,
            "experiment_label": self.experiment_label,
            "evidence_class": self.evidence_class,
            "genesis_sha256": genesis_hash(self.experiment_label),
            "current_state": self.state.value,
            "entries": list(self.entries),
        }

    # -- failure records (orthogonal) ----------------------------------------

    def attach_infrastructure_failure(
        self,
        *,
        failure_stage: str,
        failure_reason: str,
        detected_utc: str,
        invalidates: tuple[str, ...] = (),
    ) -> InfrastructureFailureRecord:
        """Attach an infra failure record at the CURRENT state.

        Legal at every state, including PUBLISHED (a post-publication infra
        finding is still recorded, never rewritten into the science). The
        lifecycle state does not change.
        """
        record = InfrastructureFailureRecord(
            failure_stage=failure_stage,
            failure_reason=failure_reason,
            detected_utc=detected_utc,
            invalidates=tuple(invalidates),
            attached_at_state=self.state,
        )
        record.validate()
        entry = make_journal_entry(
            seq=len(self.entries),
            event="infrastructure_failure",
            from_state=self.state.value,
            to_state=self.state.value,
            created_utc=detected_utc,
            detail=failure_reason,
            guard_proof=None,
            failure_record=record.to_dict(),
            prev_sha256=self._prev_sha(),
        )
        self.failures.append(record)
        self._append(entry)
        return record

    # -- transitions ----------------------------------------------------------

    def transition(
        self,
        target: State,
        *,
        created_utc: str,
        evidence: GuardEvidence | None = None,
        detail: str = "",
        freeze_manifest_path: Path | None = None,
        sealed_evidence_path: Path | None = None,
        outcome_artifact_path: Path | None = None,
        failure_json_path: Path | None = None,
        release_dir: Path | None = None,
    ) -> None:
        """Attempt ``self.state -> target``. Illegal transitions and guard
        failures raise (fail closed); nothing is journaled on failure."""
        if not isinstance(target, State):
            raise IllegalTransitionError(f"unknown target state: {target!r}")
        if (self.state, target) not in TRANSITIONS:
            raise IllegalTransitionError(
                f"illegal transition {self.state.value} -> {target.value}; "
                "the lifecycle is strictly ordered "
                "(DRAFT->PREREGISTERED->ARMED->RUNNING->EVIDENCE_SEALED->CLOSED->PUBLISHED)"
            )
        evidence = evidence or GuardEvidence()
        if target is State.PREREGISTERED:
            _guard_preregistered(evidence)
        elif target is State.ARMED:
            _guard_armed(evidence, self)
        elif target is State.RUNNING:
            _guard_running(evidence, freeze_manifest_path)
        elif target is State.EVIDENCE_SEALED:
            _guard_evidence_sealed(evidence, sealed_evidence_path)
        elif target is State.CLOSED:
            _guard_closed(evidence, outcome_artifact_path, failure_json_path)
        elif target is State.PUBLISHED:
            _guard_published(evidence, release_dir)
        else:  # pragma: no cover - transition table is exhaustive
            raise IllegalTransitionError(f"no guard implemented for {target.value}")

        if target is State.PREREGISTERED:
            self.preregistration_sha256 = evidence.preregistration_sha256

        entry = make_journal_entry(
            seq=len(self.entries),
            event="transition",
            from_state=self.state.value,
            to_state=target.value,
            created_utc=created_utc,
            detail=detail,
            guard_proof=evidence.proof_hash,
            failure_record=None,
            prev_sha256=self._prev_sha(),
        )
        self.state = target
        self._append(entry)

    # -- adoption / wiring -----------------------------------------------------


def state_for_lock_status(record: dict[str, Any]) -> State:
    """Map a generations/*.json record onto a lifecycle state (read-only).

    ``lock_status`` drives the mapping; an ``armed: false`` flag caps the
    state at PREREGISTERED even if a caller claims otherwise, so D2-0005's
    ``PREREGISTERED, armed:false`` can never be read as ARMED. Unknown lock
    statuses fail closed.
    """
    lock_status = record.get("lock_status")
    if lock_status not in LOCK_STATUS_TO_STATE:
        raise StateMachineError(
            f"unknown lock_status {lock_status!r}; refusing to guess a state"
        )
    state = LOCK_STATUS_TO_STATE[lock_status]
    if record.get("armed") is False and state not in (State.DRAFT, State.PREREGISTERED):
        raise StateMachineError(
            "record declares armed:false but a post-PREREGISTERED lock_status; "
            "contradictory record, failing closed"
        )
    if state in (State.DRAFT, State.PREREGISTERED):
        return state
    if record.get("armed") is not True:
        # No explicit armed attestation: fail closed at PREREGISTERED rather
        # than promote silently.
        raise StateMachineError(
            f"lock_status {lock_status!r} implies ARMED or beyond but the record "
            "carries no explicit armed:true attestation"
        )
    return state


def replay_journal(journal: dict[str, Any]) -> ExperimentStateMachine:
    """Deterministically reconstruct a machine from a journal.

    Re-verifies the sha chain and re-checks every transition against the
    legal transition table (guards are not re-run; each entry pins the
    ``guard_proof`` hash of evidence verified at append time). Identical
    journals replay to identical machines.
    """
    verify_journal(journal)
    machine = ExperimentStateMachine(
        experiment_label=journal["experiment_label"],
        evidence_class=journal.get("evidence_class", EVIDENCE_CLASS),
    )
    for entry in journal["entries"]:
        if entry["event"] == "infrastructure_failure":
            record = InfrastructureFailureRecord.from_dict(entry["failure_record"])
            if record.attached_at_state != machine.state:
                raise JournalTamperError(
                    f"entry {entry['seq']}: failure attached at "
                    f"{record.attached_at_state.value} but replay is at "
                    f"{machine.state.value}"
                )
            machine.failures.append(record)
            machine.entries.append(dict(entry))
            continue
        if entry["event"] != "transition":
            raise JournalTamperError(f"entry {entry['seq']}: unknown event")
        target = State(entry["to_state"])
        if entry["from_state"] != machine.state.value:
            raise JournalTamperError(
                f"entry {entry['seq']}: from_state {entry['from_state']!r} does "
                f"not match replay state {machine.state.value!r}"
            )
        if (machine.state, target) not in TRANSITIONS:
            raise JournalTamperError(
                f"entry {entry['seq']}: illegal transition in journal "
                f"({entry['from_state']} -> {entry['to_state']})"
            )
        if not _is_sha256(entry.get("guard_proof")):
            raise JournalTamperError(
                f"entry {entry['seq']}: transition without a guard proof hash"
            )
        if target is State.PREREGISTERED:
            # The pinned preregistration hash cannot be recovered from the
            # proof hash (one-way); replay records that arming was gated.
            machine.preregistration_sha256 = None
        machine.state = target
        machine.entries.append(dict(entry))
    return machine

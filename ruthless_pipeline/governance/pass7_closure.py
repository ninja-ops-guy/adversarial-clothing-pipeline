"""Pass 7 closure helpers for end-to-end adaptive CTM governance rehearsals.

These helpers are prospective and evidence-class neutral. They do not read held-out
outcomes, alter frozen D2 artifacts, or make physical-efficacy claims.
"""
from __future__ import annotations

from dataclasses import dataclass

from .adaptive import EvidenceSeal, FrozenPolicy, propose_next_wave_policy, require_policy_frozen_before_sampling
from .bridge_overlap import RegimeDecision, require_pooling_legal
from .chaos import ChaosArchive, ChaosEvent
from .ledger import GovernanceEventType, GovernanceLedger
from .state import GovernanceStateMachine, InvariantConflict


class Pass7ClosureError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClosureReport:
    source_wave_id: str
    target_wave_id: str
    source_seal_id: str
    policy_hash: str
    regime_decision: RegimeDecision
    ledger_events: int
    chaos_original_failures: int
    chaos_rescreens: int
    chaos_promotions: int


def record_policy_freeze(
    *,
    ledger: GovernanceLedger,
    experiment_id: str,
    event_id: str,
    actor: str,
    created_at: str,
    policy: FrozenPolicy,
) -> None:
    ledger.append(
        event_id=event_id,
        experiment_id=experiment_id,
        event_type=GovernanceEventType.SEAL,
        actor=actor,
        created_at=created_at,
        payload={
            "artifact_type": "FROZEN_NEXT_WAVE_POLICY",
            "source_wave_id": policy.source_wave_id,
            "target_wave_id": policy.target_wave_id,
            "source_seal_id": policy.source_seal_id,
            "policy_hash": policy.policy_hash,
        },
    )


def record_chaos_event(
    *,
    ledger: GovernanceLedger,
    experiment_id: str,
    event_id: str,
    actor: str,
    created_at: str,
    event: ChaosEvent,
) -> None:
    ledger.append(
        event_id=event_id,
        experiment_id=experiment_id,
        event_type=GovernanceEventType.RESCREEN,
        actor=actor,
        created_at=created_at,
        payload={
            "chaos_event_type": event.event_type,
            "candidate_id": event.candidate_id,
            "source_candidate_id": event.source_candidate_id,
            "new_status": event.new_status.value if event.new_status is not None else None,
            "reason_code": event.reason_code,
        },
    )


def close_adaptive_cycle(
    *,
    prior: EvidenceSeal,
    target_wave_id: str,
    policy_payload: dict,
    regime_decision: RegimeDecision,
    current_wave_outcomes: dict | None = None,
    chaos_archive: ChaosArchive | None = None,
) -> FrozenPolicy:
    """Close the adaptation decision before target-wave sampling begins."""
    policy = propose_next_wave_policy(
        prior=prior,
        target_wave_id=target_wave_id,
        policy=policy_payload,
        current_wave_outcomes=current_wave_outcomes,
    )
    require_policy_frozen_before_sampling(policy, target_wave_id)
    require_pooling_legal(regime_decision)
    if chaos_archive is not None:
        report = chaos_archive.yield_report()
        if report["original_failures"] < 0:
            raise Pass7ClosureError("invalid chaos archive accounting")
    return policy


def rehearse_required_halt(
    *,
    machine: GovernanceStateMachine,
    conflict: InvariantConflict,
    event_id: str,
) -> None:
    """Exercise the mandatory fail-closed HALT path for an invariant conflict."""
    machine.halt_for_conflict(conflict, event_id=event_id)
    if machine.halt_record != conflict:
        raise Pass7ClosureError("HALT rehearsal did not preserve conflict record")


def build_closure_report(
    *,
    policy: FrozenPolicy,
    regime_decision: RegimeDecision,
    ledger: GovernanceLedger,
    chaos_archive: ChaosArchive,
) -> ClosureReport:
    ledger.verify()
    chaos = chaos_archive.yield_report()
    return ClosureReport(
        source_wave_id=policy.source_wave_id,
        target_wave_id=policy.target_wave_id,
        source_seal_id=policy.source_seal_id,
        policy_hash=policy.policy_hash,
        regime_decision=regime_decision,
        ledger_events=len(ledger.events),
        chaos_original_failures=chaos["original_failures"],
        chaos_rescreens=chaos["rescreens"],
        chaos_promotions=chaos["promotions"],
    )

import pytest

from ruthless_pipeline.governance.adaptive import AdaptiveGovernanceError, EvidenceSeal
from ruthless_pipeline.governance.bridge_overlap import BridgeGovernanceError, RegimeDecision
from ruthless_pipeline.governance.chaos import ChaosArchive
from ruthless_pipeline.governance.ids import GovernanceId, IdKind
from ruthless_pipeline.governance.ledger import GovernanceLedger
from ruthless_pipeline.governance.pass7_closure import (
    build_closure_report,
    close_adaptive_cycle,
    record_chaos_event,
    record_policy_freeze,
    rehearse_required_halt,
)
from ruthless_pipeline.governance.state import GovernanceStateMachine, InvariantConflict, ExperimentState


def _gid(kind: IdKind, value: str) -> str:
    return str(GovernanceId(kind, value))


def test_sealed_prior_wave_closes_into_frozen_next_wave_policy():
    prior = EvidenceSeal("WAVE-N", "SEAL-001", "a" * 64)
    policy = close_adaptive_cycle(
        prior=prior,
        target_wave_id="WAVE-N1",
        policy_payload={"sampler": "projected-hashing", "seed": 17},
        regime_decision=RegimeDecision.COMPARABLE,
    )
    assert policy.target_wave_id == "WAVE-N1"
    assert len(policy.policy_hash) == 64


def test_unsealed_prior_wave_cannot_drive_adaptation():
    prior = EvidenceSeal("WAVE-N", "SEAL-001", "a" * 64, state="RUNNING")
    with pytest.raises(AdaptiveGovernanceError):
        close_adaptive_cycle(
            prior=prior,
            target_wave_id="WAVE-N1",
            policy_payload={},
            regime_decision=RegimeDecision.COMPARABLE,
        )


def test_current_wave_outcome_leakage_is_rejected():
    prior = EvidenceSeal("WAVE-N", "SEAL-001", "a" * 64)
    with pytest.raises(AdaptiveGovernanceError):
        close_adaptive_cycle(
            prior=prior,
            target_wave_id="WAVE-N1",
            policy_payload={},
            regime_decision=RegimeDecision.COMPARABLE,
            current_wave_outcomes={"held_out_score": 0.9},
        )


def test_regime_reset_forbids_default_pooling():
    prior = EvidenceSeal("WAVE-N", "SEAL-001", "a" * 64)
    with pytest.raises(BridgeGovernanceError):
        close_adaptive_cycle(
            prior=prior,
            target_wave_id="WAVE-N1",
            policy_payload={},
            regime_decision=RegimeDecision.REGIME_RESET,
        )


def test_policy_and_chaos_events_are_append_only_ledger_records():
    ledger = GovernanceLedger()
    exp = _gid(IdKind.EXPERIMENT, "PASS7-CLOSURE")
    policy = close_adaptive_cycle(
        prior=EvidenceSeal("WAVE-N", "SEAL-001", "b" * 64),
        target_wave_id="WAVE-N1",
        policy_payload={"lane": "exact"},
        regime_decision=RegimeDecision.COMPARABLE,
    )
    record_policy_freeze(
        ledger=ledger,
        experiment_id=exp,
        event_id=_gid(IdKind.EVENT, "POLICY-FREEZE"),
        actor="test",
        created_at="2026-09-10T20:30:00Z",
        policy=policy,
    )
    archive = ChaosArchive()
    archive.add_failure("CHAOS-001", "SIMULATION_ONLY:PHYSICAL_GATE")
    ev = archive.rescreen("CHAOS-001", admissible=False, reason_code="SIMULATION_ONLY:STILL_INADMISSIBLE")
    record_chaos_event(
        ledger=ledger,
        experiment_id=exp,
        event_id=_gid(IdKind.EVENT, "CHAOS-RESCREEN"),
        actor="test",
        created_at="2026-09-10T20:31:00Z",
        event=ev,
    )
    report = build_closure_report(
        policy=policy,
        regime_decision=RegimeDecision.COMPARABLE,
        ledger=ledger,
        chaos_archive=archive,
    )
    assert report.ledger_events == 2
    assert report.chaos_original_failures == 1
    assert report.chaos_rescreens == 1


def test_required_halt_rehearsal_preserves_conflict_record():
    ledger = GovernanceLedger()
    exp = _gid(IdKind.EXPERIMENT, "PASS7-HALT")
    machine = GovernanceStateMachine(experiment_id=exp, ledger=ledger, actor="test")
    conflict = InvariantConflict(
        invariant_ids=("LAW-4",),
        affected_ids=("WAVE-N1",),
        discovered_at="2026-09-10T20:32:00Z",
        evidence_status="NOT_ADMISSIBLE",
        data_collection_occurred=False,
        required_governance_decision="HALT_AND_REVIEW",
    )
    rehearse_required_halt(
        machine=machine,
        conflict=conflict,
        event_id=_gid(IdKind.EVENT, "MANDATORY-HALT"),
    )
    assert machine.state is ExperimentState.HALTED
    assert ledger.events[-1].event_type == "HALT"


def test_original_chaos_failure_survives_rescreen_and_promotion():
    archive = ChaosArchive()
    archive.add_failure("CHAOS-002", "SIMULATION_ONLY:INITIAL")
    archive.rescreen("CHAOS-002", admissible=True, reason_code="PHYSICAL_GATE:PASS")
    archive.promote_to_hypothesis("CHAOS-002", physically_admissible=True)
    report = archive.yield_report()
    assert report["original_failures"] == 1
    assert report["rescreens"] == 1
    assert report["promotions"] == 1

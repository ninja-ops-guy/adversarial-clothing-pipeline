from __future__ import annotations

import hashlib

import pytest

from ruthless_pipeline.ctm.intake import CTMIntakeError, accept_governed_cohort
from ruthless_pipeline.governance.adaptive import (
    AdaptiveGovernanceError,
    EvidenceSeal,
    freeze_allocation_policy,
    propose_next_wave_policy,
    require_policy_frozen_before_sampling,
)
from ruthless_pipeline.governance.bridge_overlap import RegimeDecision
from ruthless_pipeline.governance.chaos import (
    ChaosArchive,
    ChaosGovernanceError,
    ChaosStatus,
)
from ruthless_pipeline.governance.ctm_comparison import (
    CTMComparisonGovernanceError,
    CohortComparisonContext,
    ComparisonMode,
    PipelineMigrationClass,
    assess_ctm_comparison,
    require_ctm_comparison_eligible,
)
from ruthless_pipeline.governance.ledger import GovernanceLedger
from ruthless_pipeline.governance.seal import seal_cohort
from ruthless_pipeline.governance.state import (
    ExperimentState,
    GovernanceStateMachine,
    InvariantConflict,
)


def _legacy_manifest(*, cohort: str, constraint: str, seed: int) -> tuple[dict, dict[str, bytes]]:
    artifact = f"specimen:{cohort}".encode()
    artifacts = {"specimen.bin": artifact}
    return (
        {
            "cohort_id": cohort,
            "experiment_id": "RAC-EXP-PASS7-CERT",
            "constraint_id": constraint,
            "code_commit": "pass7-fixture",
            "seed": seed,
            "diagnostic_threshold_hash": "d" * 64,
            "specimen_ids": [f"{cohort}-S1"],
            "artifacts": {
                "specimen.bin": hashlib.sha256(artifact).hexdigest(),
            },
        },
        artifacts,
    )


def _context(
    *,
    cohort: str,
    seal: str,
    constraint: str,
    pipeline: str = "RAC-PIPE-001",
    version: str = "1.0.0",
) -> CohortComparisonContext:
    return CohortComparisonContext(
        cohort_id=cohort,
        seal_id=seal,
        constraint_set_id=constraint,
        pipeline_id=pipeline,
        pipeline_version=version,
    )


def test_empty_current_wave_outcome_container_is_rejected() -> None:
    prior = EvidenceSeal("WAVE-N", "RAC-SEAL-N", "a" * 64)
    with pytest.raises(AdaptiveGovernanceError, match="current-wave"):
        propose_next_wave_policy(
            prior=prior,
            target_wave_id="WAVE-N+1",
            policy={},
            current_wave_outcomes={},
        )


def test_allocation_policy_is_frozen_and_hash_bound_to_prior_evidence() -> None:
    prior = EvidenceSeal("WAVE-N", "RAC-SEAL-N", "a" * 64)
    frozen = freeze_allocation_policy(
        prior=prior,
        target_wave_id="WAVE-N+1",
        constrained_fraction=0.78,
        chaos_fraction=0.22,
        version="alloc-v1",
        stopping_rule="stop at preregistered sample cap or precision target",
        reallocation_rule="adapt only from a sealed prior CTM wave",
        policy={"sampler_lane": "stratified"},
    )
    require_policy_frozen_before_sampling(frozen, "WAVE-N+1")
    assert frozen.source_evidence_hash == "a" * 64
    assert frozen.allocation is not None
    assert frozen.allocation.chaos_fraction == pytest.approx(0.22)
    assert len(frozen.policy_hash) == 64


def test_invalid_allocation_cannot_be_preregistered() -> None:
    prior = EvidenceSeal("WAVE-N", "RAC-SEAL-N", "a" * 64)
    with pytest.raises(AdaptiveGovernanceError, match="must equal 1"):
        freeze_allocation_policy(
            prior=prior,
            target_wave_id="WAVE-N+1",
            constrained_fraction=0.8,
            chaos_fraction=0.3,
            version="alloc-v1",
            stopping_rule="frozen",
            reallocation_rule="next sealed wave only",
        )


def test_constraint_change_requires_overlap_analysis() -> None:
    left = _context(cohort="C-A", seal="S-A", constraint="CS-A")
    right = _context(cohort="C-B", seal="S-B", constraint="CS-B")
    with pytest.raises(CTMComparisonGovernanceError, match="overlap analysis"):
        assess_ctm_comparison(left, right)


def test_pipeline_change_requires_explicit_migration_classification() -> None:
    left = _context(cohort="C-A", seal="S-A", constraint="CS-A")
    right = _context(
        cohort="C-B",
        seal="S-B",
        constraint="CS-A",
        pipeline="RAC-PIPE-002",
    )
    with pytest.raises(CTMComparisonGovernanceError, match="classification"):
        assess_ctm_comparison(left, right)


def test_bridge_required_comparison_is_explicit_and_eligible() -> None:
    left = _context(cohort="C-A", seal="S-A", constraint="CS-A")
    right = _context(cohort="C-B", seal="S-B", constraint="CS-B")
    decision = assess_ctm_comparison(
        left,
        right,
        regime_decision=RegimeDecision.BRIDGE_REQUIRED,
        overlap_analysis_id="RAC-OVERLAP-001",
        bridge_cohort_id="RAC-COHORT-BRIDGE-001",
    )
    assert decision.mode is ComparisonMode.BRIDGED
    assert require_ctm_comparison_eligible(decision) is decision


def test_regime_reset_cannot_enter_default_ctm_comparison() -> None:
    left = _context(cohort="C-A", seal="S-A", constraint="CS-A")
    right = _context(cohort="C-B", seal="S-B", constraint="CS-B")
    decision = assess_ctm_comparison(
        left,
        right,
        regime_decision=RegimeDecision.REGIME_RESET,
        overlap_analysis_id="RAC-OVERLAP-RESET",
    )
    assert decision.mode is ComparisonMode.SEPARATE_REGIME
    assert not decision.eligible
    with pytest.raises(CTMComparisonGovernanceError, match="denied"):
        require_ctm_comparison_eligible(decision)


def test_bridged_pipeline_change_requires_bridge_cohort() -> None:
    left = _context(cohort="C-A", seal="S-A", constraint="CS-A")
    right = _context(
        cohort="C-B",
        seal="S-B",
        constraint="CS-A",
        pipeline="RAC-PIPE-002",
    )
    with pytest.raises(CTMComparisonGovernanceError, match="bridge_cohort_id"):
        assess_ctm_comparison(
            left,
            right,
            pipeline_migration=PipelineMigrationClass.BRIDGED,
        )


def test_latest_chaos_rescreen_controls_promotion() -> None:
    archive = ChaosArchive()
    archive.add_failure("C-1", "PRINTABILITY")
    archive.rescreen("C-1", admissible=True, reason_code="NEW_PRINTER")
    archive.rescreen("C-1", admissible=False, reason_code="SEAM_DISTORTION")
    assert archive.current_status("C-1") is ChaosStatus.SIMULATION_ONLY
    with pytest.raises(ChaosGovernanceError, match="latest re-screen"):
        archive.promote_to_hypothesis("C-1", physically_admissible=True)


def test_chaos_reports_admissibility_and_gate_bias_without_dropping_failures() -> None:
    archive = ChaosArchive()
    archive.add_failure(
        "C-A",
        "PRINTABILITY",
        generator_class="diffusion",
        topology_class="fragmented",
        spectral_class="high-frequency",
    )
    archive.add_failure(
        "C-B",
        "DEFORMATION",
        generator_class="diffusion",
        topology_class="fragmented",
        spectral_class="mid-frequency",
    )
    archive.add_failure(
        "C-C",
        "SEAM_SAFETY",
        generator_class="procedural",
        topology_class="connected",
        spectral_class="mid-frequency",
    )
    archive.rescreen("C-A", admissible=True, reason_code="CAPABILITY_CHANGED")
    archive.rescreen("C-B", admissible=False, reason_code="STILL_DEFORMS")

    report = archive.admissibility_report()
    assert report["archived"] == 3
    assert report["admissible"] == 1
    assert report["simulation_only"] == 1
    assert report["never_rescreened_failed"] == 1
    assert report["admissibility_rate"] == pytest.approx(1 / 3)

    bias = archive.gate_bias_report("generator_class")
    assert bias["diffusion"]["archived"] == 2
    assert bias["diffusion"]["admissibility_rate"] == pytest.approx(0.5)
    assert bias["procedural"]["admissibility_rate"] == 0.0


def test_pass7_end_to_end_exit_gate_with_halt_and_chaos_rescreen() -> None:
    # constraints -> cohort -> seal -> CTM
    manifest_n, artifacts_n = _legacy_manifest(
        cohort="RAC-COHORT-P7-N",
        constraint="CS-OLD",
        seed=17,
    )
    seal_n = seal_cohort(manifest_n, artifacts_n)
    assert accept_governed_cohort(seal_n, manifest_n, artifacts_n) is seal_n

    with pytest.raises(CTMIntakeError, match="unsealed"):
        accept_governed_cohort(None, manifest_n, artifacts_n)

    # sealed CTM result -> frozen next-wave adaptation
    evidence = EvidenceSeal(
        wave_id="WAVE-N",
        seal_id=seal_n.seal_id,
        evidence_hash=seal_n.seal_hash,
    )
    next_policy = freeze_allocation_policy(
        prior=evidence,
        target_wave_id="WAVE-N+1",
        constrained_fraction=0.75,
        chaos_fraction=0.25,
        version="alloc-pass7-exit-v1",
        stopping_rule="stop at preregistered cap",
        reallocation_rule="change only after next sealed CTM result",
        policy={"target_distribution": "stratified"},
    )
    require_policy_frozen_before_sampling(next_policy, "WAVE-N+1")

    # constraint migration -> overlap/bridge -> next cohort
    manifest_np1, artifacts_np1 = _legacy_manifest(
        cohort="RAC-COHORT-P7-NP1",
        constraint="CS-NEW",
        seed=18,
    )
    seal_np1 = seal_cohort(manifest_np1, artifacts_np1)
    assert accept_governed_cohort(seal_np1, manifest_np1, artifacts_np1) is seal_np1

    comparison = assess_ctm_comparison(
        _context(
            cohort=seal_n.cohort_id,
            seal=seal_n.seal_id,
            constraint=seal_n.constraint_id,
        ),
        _context(
            cohort=seal_np1.cohort_id,
            seal=seal_np1.seal_id,
            constraint=seal_np1.constraint_id,
        ),
        regime_decision=RegimeDecision.BRIDGE_REQUIRED,
        overlap_analysis_id="RAC-OVERLAP-P7-001",
        bridge_cohort_id="RAC-COHORT-P7-BRIDGE",
    )
    require_ctm_comparison_eligible(comparison)
    assert comparison.mode is ComparisonMode.BRIDGED

    # Intentionally trigger Law-7 HALT through the real state machine.
    ledger = GovernanceLedger()
    machine = GovernanceStateMachine(
        experiment_id="RAC-EXP-PASS7-CERT",
        ledger=ledger,
        actor="pass7-certification",
    )
    machine.transition(
        ExperimentState.PREFLIGHT,
        event_id="RAC-GOV-EVT-P7-001",
        created_at="2026-09-10T20:30:00Z",
    )
    conflict = InvariantConflict(
        invariant_ids=("LAW-7",),
        affected_ids=("RAC-EXP-PASS7-CERT",),
        discovered_at="2026-09-10T20:30:01Z",
        evidence_status="PRE_RESULT",
        data_collection_occurred=False,
        required_governance_decision="resolve temporal-firewall conflict",
    )
    machine.halt_for_conflict(conflict, event_id="RAC-GOV-EVT-P7-HALT")
    assert machine.state is ExperimentState.HALTED
    assert ledger.verify()

    # Chaos failure remains archived through resurrection to a new hypothesis.
    chaos = ChaosArchive()
    chaos.add_failure(
        "CHAOS-P7-001",
        "SIMULATION_ONLY",
        generator_class="procedural",
    )
    chaos.rescreen(
        "CHAOS-P7-001",
        admissible=True,
        reason_code="MANUFACTURING_CAPABILITY_CHANGED",
    )
    promoted = chaos.promote_to_hypothesis(
        "CHAOS-P7-001",
        physically_admissible=True,
    )
    assert promoted.source_candidate_id == "CHAOS-P7-001"
    assert chaos.candidates["CHAOS-P7-001"].original_status is ChaosStatus.FAILED

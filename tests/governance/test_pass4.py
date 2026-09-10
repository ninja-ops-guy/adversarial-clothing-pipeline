"""Governance Pass 4: sentinel, calibration, bridge, and overlap tests."""

from __future__ import annotations

from hashlib import sha256

import pytest

from ruthless_pipeline.governance.bridge import (
    BridgeGovernanceError,
    ConstraintBridgeCohort,
    validate_common_support,
)
from ruthless_pipeline.governance.overlap import (
    CountEstimate,
    MaterialityPolicy,
    OverlapAnalysis,
    OverlapGovernanceError,
    RegimeDecision,
    RegimeDecisionPolicy,
    decide_regime,
    estimate_bidirectional_overlap,
    estimate_policy_overlap,
    estimate_stratified_support,
    require_overlap_analysis_for_migration,
    support_overlap_from_counts,
)
from ruthless_pipeline.governance.seal import seal_cohort
from ruthless_pipeline.governance.sentinel import (
    CalibrationState,
    EvaluationPipeline,
    PipelineBridgePlan,
    PreprocessingMode,
    SentinelGovernanceError,
    SentinelRegistry,
    create_sentinel,
    pipeline_change_requires_bridge,
    validate_blind_sentinel_evaluation,
    validate_pipeline_transition,
)

H_A = "a" * 64
H_B = "b" * 64
H_C = "c" * 64
H_D = "d" * 64


def _sealed_source():
    data = b"sentinel-source"
    digest = sha256(data).hexdigest()
    manifest = {
        "cohort_id": "RAC-COH-SOURCE01",
        "experiment_id": "RAC-EXP-SOURCE01",
        "constraint_id": "RAC-CST-OLD0001",
        "code_commit": "a" * 40,
        "seed": 17,
        "diagnostic_threshold_hash": H_B,
        "specimen_ids": ["S1", "S2", "S3", "S4"],
        "artifacts": {"source.bin": digest},
    }
    return manifest, seal_cohort(manifest, {"source.bin": data})


def _sentinel():
    manifest, seal = _sealed_source()
    return create_sentinel(
        sentinel_id="RAC-SEN-WAVE0001",
        source_wave_id="WAVE-N",
        source_seal=seal,
        cohort_manifest=manifest,
        specimen_ids=("S1", "S3"),
        selection_seed=99,
        selection_policy_hash=H_C,
    )


def _pipeline(
    pipeline_id: str,
    *,
    mode: PreprocessingMode = PreprocessingMode.STATELESS,
    calibration_id: str | None = None,
    calibration_hash: str | None = None,
    detector_hash: str = H_B,
    prior_outcome_access: bool = False,
):
    return EvaluationPipeline(
        pipeline_id=pipeline_id,
        software_version="1.0.0",
        code_hash=H_A,
        detector_hash=detector_hash,
        preprocessing_hash=H_C,
        random_seed=123,
        preprocessing_mode=mode,
        calibration_id=calibration_id,
        calibration_state_hash=calibration_hash,
        prior_outcome_access=prior_outcome_access,
    )


def test_sentinel_is_fixed_at_wave_seal_and_cannot_be_resampled():
    sentinel = _sentinel()
    registry = SentinelRegistry()
    registry.register(sentinel)
    manifest, seal = _sealed_source()
    replacement = create_sentinel(
        sentinel_id="RAC-SEN-WAVE0002",
        source_wave_id="WAVE-N",
        source_seal=seal,
        cohort_manifest=manifest,
        specimen_ids=("S2", "S4"),
        selection_seed=100,
        selection_policy_hash=H_D,
    )
    with pytest.raises(SentinelGovernanceError, match="resampling is forbidden"):
        registry.register(replacement)


def test_sentinel_must_be_subset_of_sealed_source_cohort():
    manifest, seal = _sealed_source()
    with pytest.raises(SentinelGovernanceError, match="subset"):
        create_sentinel(
            sentinel_id="RAC-SEN-WAVE0001",
            source_wave_id="WAVE-N",
            source_seal=seal,
            cohort_manifest=manifest,
            specimen_ids=("S1", "NOT-IN-COHORT"),
            selection_seed=99,
            selection_policy_hash=H_C,
        )


def test_blind_sentinel_refuses_prior_outcome_access():
    sentinel = _sentinel()
    pipeline = _pipeline("RAC-PIP-PIPE0001", prior_outcome_access=True)
    with pytest.raises(SentinelGovernanceError, match="prior-wave outcomes"):
        validate_blind_sentinel_evaluation(sentinel, pipeline)


def test_calibrated_pipeline_requires_disjoint_frozen_calibration_set():
    sentinel = _sentinel()
    calibration = CalibrationState(
        calibration_id="RAC-CAL-CAL0001",
        member_ids=("CAL-1", "CAL-2"),
        state_hash=H_D,
        source_manifest_hash=H_A,
        random_seed=22,
    )
    pipeline = _pipeline(
        "RAC-PIP-PIPE0001",
        mode=PreprocessingMode.CALIBRATED,
        calibration_id=calibration.calibration_id,
        calibration_hash=calibration.state_hash,
    )
    validate_blind_sentinel_evaluation(
        sentinel,
        pipeline,
        calibration=calibration,
        bridge_ids=("BRIDGE-1",),
        treatment_ids=("TREAT-1",),
        heldout_ids=("HOLD-1",),
    )
    contaminated = CalibrationState(
        calibration_id="RAC-CAL-CAL0001",
        member_ids=("CAL-1", "S1"),
        state_hash=H_D,
        source_manifest_hash=H_A,
        random_seed=22,
    )
    with pytest.raises(SentinelGovernanceError, match="overlaps"):
        validate_blind_sentinel_evaluation(sentinel, pipeline, calibration=contaminated)


def test_calibration_state_cannot_consume_outcome_labels():
    calibration = CalibrationState(
        calibration_id="RAC-CAL-CAL0001",
        member_ids=("CAL-1",),
        state_hash=H_D,
        source_manifest_hash=H_A,
        random_seed=22,
        outcome_labels_consumed=True,
    )
    with pytest.raises(SentinelGovernanceError, match="outcome labels"):
        calibration.validate()


def test_pipeline_change_requires_paired_bridge_on_same_sentinel():
    sentinel = _sentinel()
    old = _pipeline("RAC-PIP-PIPE0001")
    new = _pipeline("RAC-PIP-PIPE0002", detector_hash=H_D)
    assert pipeline_change_requires_bridge(old, new)
    with pytest.raises(SentinelGovernanceError, match="requires an explicit pipeline bridge"):
        validate_pipeline_transition(old, new, sentinel=sentinel, bridge=None)
    bridge = PipelineBridgePlan(
        bridge_id="RAC-BRG-PIPE0001",
        sentinel_id=sentinel.sentinel_id,
        old_pipeline_id=old.pipeline_id,
        new_pipeline_id=new.pipeline_id,
    )
    validate_pipeline_transition(old, new, sentinel=sentinel, bridge=bridge)


def test_constraint_bridge_requires_common_support():
    bridge = ConstraintBridgeCohort(
        bridge_id="RAC-BRG-CST00001",
        old_constraint_id="RAC-CST-OLD0001",
        new_constraint_id="RAC-CST-NEW0001",
        specimen_ids=("A", "B"),
        sampling_manifest_id="RAC-SMP-BRIDGE01",
        source_policy="intersection-sampler-v1",
    )
    validate_common_support(
        bridge,
        {"A": 5, "B": 7},
        old_feasible=lambda x: x <= 10,
        new_feasible=lambda x: x >= 5,
    )
    with pytest.raises(BridgeGovernanceError, match="F\\(old\\)"):
        validate_common_support(
            bridge,
            {"A": 5, "B": 3},
            old_feasible=lambda x: x <= 10,
            new_feasible=lambda x: x >= 5,
        )


def test_bidirectional_overlap_retains_confidence_intervals():
    estimate = estimate_bidirectional_overlap(
        list(range(1, 11)),
        list(range(5, 15)),
        old_feasible=lambda x: x <= 10,
        new_feasible=lambda x: x >= 5,
    )
    assert estimate.old_to_new.estimate == pytest.approx(0.6)
    assert estimate.new_to_old.estimate == pytest.approx(0.6)
    assert estimate.support_overlap.lower < estimate.support_overlap.estimate < estimate.support_overlap.upper
    assert estimate.to_dict()["support_overlap"]["confidence"] == 0.95


def test_projected_count_overlap_propagates_count_uncertainty():
    estimate = support_overlap_from_counts(
        CountEstimate(1000, 900, 1100, "ApproxMC"),
        CountEstimate(800, 720, 880, "ApproxMC"),
        CountEstimate(600, 530, 670, "ApproxMC"),
    )
    assert estimate.estimate == pytest.approx(0.75)
    assert estimate.lower < estimate.estimate < estimate.upper
    assert "ApproxMC" in estimate.method


def test_hypothesis_named_rare_stratum_is_material():
    old_labels = ["COMMON"] * 100 + ["RARE"]
    new_labels = ["COMMON"] * 100 + ["RARE"]
    policy = MaterialityPolicy(mass_threshold=0.05, hypothesis_named_strata=frozenset({"RARE"}))
    assert "RARE" in policy.material_strata(old_labels, new_labels)


def test_migration_without_overlap_analysis_fails_law4():
    with pytest.raises(OverlapGovernanceError, match="Law 4"):
        require_overlap_analysis_for_migration("RAC-CST-OLD0001", "RAC-CST-NEW0001", None)


def test_inadequate_common_support_emits_regime_reset():
    old = [{"x": x, "s": "TARGET"} for x in range(0, 40)]
    new = [{"x": x, "s": "TARGET"} for x in range(35, 75)]
    material = MaterialityPolicy(
        mass_threshold=0.01,
        hypothesis_named_strata=frozenset({"TARGET"}),
    ).material_strata([x["s"] for x in old], [x["s"] for x in new])
    rows = estimate_stratified_support(
        old,
        new,
        old_feasible=lambda item: item["x"] < 40,
        new_feasible=lambda item: item["x"] >= 35,
        stratum_of=lambda item: item["s"],
        material_strata=material,
    )
    policy_overlap = estimate_policy_overlap(
        [x["s"] for x in old],
        [x["s"] for x in new],
        bootstrap_seed=7,
        bootstrap_replicates=100,
    )
    analysis = OverlapAnalysis(
        overlap_id="RAC-OVR-MIG00001",
        old_constraint_id="RAC-CST-OLD0001",
        new_constraint_id="RAC-CST-NEW0001",
        material_strata=tuple(sorted(material)),
        support_by_stratum=rows,
        policy_overlap=policy_overlap,
        method="bidirectional_monte_carlo+stratum_bootstrap",
        assumptions=("source samples are uniform over each feasible regime",),
    )
    require_overlap_analysis_for_migration("RAC-CST-OLD0001", "RAC-CST-NEW0001", analysis)
    decision = decide_regime(
        analysis,
        RegimeDecisionPolicy(min_support_lower_bound=0.50, min_policy_overlap_lower_bound=0.50),
    )
    assert decision is RegimeDecision.REGIME_RESET
    assert analysis.to_dict()["support_by_stratum"][0]["support_overlap"]["confidence"] == 0.95


def test_policy_shift_can_force_regime_reset_even_with_common_support():
    specimens_old = [{"x": i, "s": "A" if i < 35 else "B"} for i in range(40)]
    specimens_new = [{"x": i, "s": "A" if i < 5 else "B"} for i in range(40)]
    material_policy = MaterialityPolicy(mass_threshold=0.05)
    old_labels = [x["s"] for x in specimens_old]
    new_labels = [x["s"] for x in specimens_new]
    material = material_policy.material_strata(old_labels, new_labels)
    rows = estimate_stratified_support(
        specimens_old,
        specimens_new,
        old_feasible=lambda _: True,
        new_feasible=lambda _: True,
        stratum_of=lambda item: item["s"],
        material_strata=material,
    )
    policy_overlap = estimate_policy_overlap(
        old_labels,
        new_labels,
        bootstrap_seed=19,
        bootstrap_replicates=100,
    )
    analysis = OverlapAnalysis(
        overlap_id="RAC-OVR-MIG00002",
        old_constraint_id="RAC-CST-OLD0001",
        new_constraint_id="RAC-CST-NEW0001",
        material_strata=tuple(sorted(material)),
        support_by_stratum=rows,
        policy_overlap=policy_overlap,
        method="fixture",
    )
    assert decide_regime(
        analysis,
        RegimeDecisionPolicy(min_support_lower_bound=0.50, min_policy_overlap_lower_bound=0.60),
    ) is RegimeDecision.REGIME_RESET

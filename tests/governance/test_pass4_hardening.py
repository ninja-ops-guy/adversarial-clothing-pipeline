"""Pass 4 hardening tests for seal-bound sentinels and overlap analysis."""

from hashlib import sha256

import pytest

from ruthless_pipeline.governance.bridge import ConstraintBridgeCohort, ConstraintBridgeError, validate_common_support
from ruthless_pipeline.governance.overlap import (
    CountEstimate,
    DetailedRegimeDecision,
    MaterialityPolicy,
    OverlapAnalysis,
    OverlapGovernanceError,
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

H1 = "a" * 64
H2 = "b" * 64
H3 = "c" * 64
H4 = "d" * 64


def source():
    data = b"source"
    manifest = {
        "cohort_id": "RAC-COH-SOURCE01",
        "experiment_id": "RAC-EXP-SOURCE01",
        "constraint_id": "RAC-CST-OLD0001",
        "code_commit": "a" * 40,
        "seed": 17,
        "diagnostic_threshold_hash": H2,
        "specimen_ids": ["S1", "S2", "S3"],
        "artifacts": {"source.bin": sha256(data).hexdigest()},
    }
    return manifest, seal_cohort(manifest, {"source.bin": data})


def sentinel():
    manifest, seal = source()
    return create_sentinel(
        sentinel_id="RAC-SEN-WAVE001",
        source_wave_id="WAVE-N",
        source_seal=seal,
        cohort_manifest=manifest,
        specimen_ids=("S1", "S2"),
        selection_seed=7,
        selection_policy_hash=H3,
    )


def pipeline(pid, *, detector=H2, mode=PreprocessingMode.STATELESS, cal=None, cal_hash=None, leak=False):
    return EvaluationPipeline(pid, "1.0.0", H1, detector, H3, 11, mode, cal, cal_hash, leak)


def test_sentinel_is_bound_to_sealed_source_and_resampling_is_forbidden():
    s = sentinel()
    reg = SentinelRegistry()
    reg.register(s)
    manifest, seal = source()
    other = create_sentinel(
        sentinel_id="RAC-SEN-WAVE002", source_wave_id="WAVE-N", source_seal=seal,
        cohort_manifest=manifest, specimen_ids=("S3",), selection_seed=8, selection_policy_hash=H4,
    )
    with pytest.raises(SentinelGovernanceError, match="resampling"):
        reg.register(other)


def test_sentinel_rejects_specimen_outside_sealed_cohort():
    manifest, seal = source()
    with pytest.raises(SentinelGovernanceError, match="subset"):
        create_sentinel(
            sentinel_id="RAC-SEN-WAVE001", source_wave_id="WAVE-N", source_seal=seal,
            cohort_manifest=manifest, specimen_ids=("S1", "X"), selection_seed=7, selection_policy_hash=H3,
        )


def test_blind_pipeline_rejects_prior_outcome_access():
    with pytest.raises(SentinelGovernanceError, match="prior-wave"):
        validate_blind_sentinel_evaluation(sentinel(), pipeline("RAC-PIP-PIPE001", leak=True))


def test_calibration_is_disjoint_and_frozen():
    s = sentinel()
    cal = CalibrationState("RAC-CAL-CAL0001", ("C1", "C2"), H4, H1, 22)
    p = pipeline("RAC-PIP-PIPE001", mode=PreprocessingMode.CALIBRATED, cal=cal.calibration_id, cal_hash=cal.state_hash)
    validate_blind_sentinel_evaluation(s, p, calibration=cal, treatment_ids=("T1",), heldout_ids=("H1",))
    contaminated = CalibrationState("RAC-CAL-CAL0002", ("S1",), H4, H1, 22)
    p2 = pipeline("RAC-PIP-PIPE002", mode=PreprocessingMode.CALIBRATED, cal=contaminated.calibration_id, cal_hash=contaminated.state_hash)
    with pytest.raises(SentinelGovernanceError, match="overlaps"):
        validate_blind_sentinel_evaluation(s, p2, calibration=contaminated)


def test_pipeline_change_requires_paired_bridge_on_same_sentinel():
    s = sentinel()
    old = pipeline("RAC-PIP-PIPE001")
    new = pipeline("RAC-PIP-PIPE002", detector=H4)
    assert pipeline_change_requires_bridge(old, new)
    with pytest.raises(SentinelGovernanceError, match="explicit pipeline bridge"):
        validate_pipeline_transition(old, new, sentinel=s, bridge=None)
    bridge = PipelineBridgePlan("RAC-BRG-PIPE001", s.sentinel_id, old.pipeline_id, new.pipeline_id)
    validate_pipeline_transition(old, new, sentinel=s, bridge=bridge)


def test_constraint_bridge_requires_intersection_membership():
    b = ConstraintBridgeCohort("RAC-BRG-CST0001", "RAC-CST-OLD0001", "RAC-CST-NEW0001", ("A", "B"), "RAC-SMP-BRIDGE1", "intersection/v1")
    validate_common_support(b, {"A": 5, "B": 7}, old_feasible=lambda x: x <= 10, new_feasible=lambda x: x >= 5)
    with pytest.raises(ConstraintBridgeError, match="F\\(old\\)"):
        validate_common_support(b, {"A": 5, "B": 3}, old_feasible=lambda x: x <= 10, new_feasible=lambda x: x >= 5)


def test_bidirectional_overlap_carries_confidence_interval():
    e = estimate_bidirectional_overlap(list(range(1, 11)), list(range(5, 15)), old_feasible=lambda x: x <= 10, new_feasible=lambda x: x >= 5)
    assert e.old_to_new.estimate == pytest.approx(0.6)
    assert e.support_overlap.lower < e.support_overlap.estimate < e.support_overlap.upper


def test_count_overlap_propagates_approximate_count_uncertainty():
    e = support_overlap_from_counts(CountEstimate(1000, 900, 1100, "ApproxMC"), CountEstimate(800, 720, 880, "ApproxMC"), CountEstimate(600, 530, 670, "ApproxMC"))
    assert e.estimate == pytest.approx(0.75)
    assert e.lower < e.estimate < e.upper


def test_hypothesis_named_rare_stratum_remains_material():
    p = MaterialityPolicy(0.05, frozenset({"RARE"}))
    assert "RARE" in p.material_strata(["COMMON"] * 100 + ["RARE"], ["COMMON"] * 100 + ["RARE"])


def test_law4_requires_overlap_bound_to_same_constraint_pair():
    with pytest.raises(OverlapGovernanceError, match="Law 4"):
        require_overlap_analysis_for_migration("RAC-CST-OLD0001", "RAC-CST-NEW0001", None)


def test_low_common_support_forces_regime_reset():
    old = [{"x": x, "s": "TARGET"} for x in range(40)]
    new = [{"x": x, "s": "TARGET"} for x in range(35, 75)]
    material = frozenset({"TARGET"})
    rows = estimate_stratified_support(old, new, old_feasible=lambda x: x["x"] < 40, new_feasible=lambda x: x["x"] >= 35, stratum_of=lambda x: x["s"], material_strata=material)
    policy_overlap = estimate_policy_overlap(["TARGET"] * 40, ["TARGET"] * 40, bootstrap_seed=7, bootstrap_replicates=100)
    analysis = OverlapAnalysis("RAC-OVR-MIG0001", "RAC-CST-OLD0001", "RAC-CST-NEW0001", ("TARGET",), rows, policy_overlap, "mc+bootstrap")
    require_overlap_analysis_for_migration("RAC-CST-OLD0001", "RAC-CST-NEW0001", analysis)
    assert decide_regime(analysis, RegimeDecisionPolicy(0.50, 0.50)) is DetailedRegimeDecision.REGIME_RESET


def test_policy_shift_alone_can_force_regime_reset():
    old = [{"s": "A" if i < 35 else "B"} for i in range(40)]
    new = [{"s": "A" if i < 5 else "B"} for i in range(40)]
    labels_old, labels_new = [x["s"] for x in old], [x["s"] for x in new]
    material = MaterialityPolicy(0.05).material_strata(labels_old, labels_new)
    rows = estimate_stratified_support(old, new, old_feasible=lambda _: True, new_feasible=lambda _: True, stratum_of=lambda x: x["s"], material_strata=material)
    po = estimate_policy_overlap(labels_old, labels_new, bootstrap_seed=19, bootstrap_replicates=100)
    analysis = OverlapAnalysis("RAC-OVR-MIG0002", "RAC-CST-OLD0001", "RAC-CST-NEW0001", tuple(sorted(material)), rows, po, "fixture")
    assert decide_regime(analysis, RegimeDecisionPolicy(0.50, 0.60)) is DetailedRegimeDecision.REGIME_RESET

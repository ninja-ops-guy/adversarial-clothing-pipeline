from __future__ import annotations

import pytest

from ruthless_pipeline.governance.bridge_overlap import (
    BridgeGovernanceError,
    OverlapEstimate,
    RegimeDecision,
    SentinelRecord,
    assert_calibration_isolation,
    classify_regime,
    require_blind_re_evaluation,
    require_pooling_legal,
)


def _estimate(**overrides):
    data = dict(
        old_support_fraction=0.90,
        new_support_fraction=0.88,
        policy_overlap=0.80,
        ci_low=0.82,
        ci_high=0.94,
        material_strata_covered=True,
        estimator="bidirectional-monte-carlo/v1",
    )
    data.update(overrides)
    return OverlapEstimate(**data)


def test_sentinel_identity_is_deterministic_and_order_sensitive():
    a = SentinelRecord("W1", ("S1", "S2"), 7, "a" * 64)
    b = SentinelRecord("W1", ("S1", "S2"), 7, "a" * 64)
    c = SentinelRecord("W1", ("S2", "S1"), 7, "a" * 64)
    assert a.sentinel_hash == b.sentinel_hash
    assert a.sentinel_hash != c.sentinel_hash


def test_sentinel_rejects_calibration_overlap():
    with pytest.raises(BridgeGovernanceError):
        SentinelRecord("W1", ("S1",), 7, "a" * 64, ("S1",)).validate()


def test_calibration_is_disjoint_from_all_governed_sets():
    assert_calibration_isolation(
        calibration_ids=("C1",), sentinel_ids=("S1",), bridge_ids=("B1",),
        treatment_ids=("T1",), held_out_ids=("H1",),
    )
    with pytest.raises(BridgeGovernanceError):
        assert_calibration_isolation(
            calibration_ids=("H1",), sentinel_ids=(), bridge_ids=(),
            treatment_ids=(), held_out_ids=("H1",),
        )


def test_prior_outcomes_cannot_initialize_next_wave():
    require_blind_re_evaluation(prior_outcome_ids=("O1",), initialization_input_ids=("CFG",))
    with pytest.raises(BridgeGovernanceError):
        require_blind_re_evaluation(prior_outcome_ids=("O1",), initialization_input_ids=("O1", "CFG"))


def test_overlap_classifies_comparable_bridge_and_reset():
    assert classify_regime(_estimate()) is RegimeDecision.COMPARABLE
    assert classify_regime(_estimate(policy_overlap=0.30)) is RegimeDecision.BRIDGE_REQUIRED
    assert classify_regime(_estimate(ci_low=0.40)) is RegimeDecision.REGIME_RESET
    assert classify_regime(_estimate(material_strata_covered=False)) is RegimeDecision.REGIME_RESET


def test_regime_reset_forbids_naive_pooling():
    require_pooling_legal(RegimeDecision.COMPARABLE)
    with pytest.raises(BridgeGovernanceError):
        require_pooling_legal(RegimeDecision.REGIME_RESET)


def test_invalid_uncertainty_fails_closed():
    with pytest.raises(BridgeGovernanceError):
        classify_regime(_estimate(ci_low=0.9, ci_high=0.8))

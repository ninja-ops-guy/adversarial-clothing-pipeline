"""Tests for the preregistered D2-0005 paired Arm M vs Arm C statistics."""

import json
import math

import pytest

from ruthless_pipeline.certification.paired_arm_statistics import (
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_Z,
    INCONCLUSIVE_WIDTH_MAX,
    PairedArmStatistics,
    bootstrap_paired_difference_interval,
    classify_decision,
    paired_arm_statistics,
    paired_arm_statistics_from_arms,
    to_canonical_json,
    validate_paired_key_sets,
)
from ruthless_pipeline.certification.statistics import wilson_interval


def make_outcomes(n: int, hits_m: int, hits_c: int, overlap: int = 0):
    """Deterministic fixture: units u0..u{n-1} with controlled discordance."""
    outcomes = {}
    for i in range(n):
        m = i < hits_m
        c = i < overlap or (hits_m <= i < hits_m + (hits_c - overlap))
        outcomes[f"model-x|t{i:03d}|0"] = (m, c)
    return outcomes


def test_wilson_intervals_match_hand_computed():
    outcomes = make_outcomes(n=40, hits_m=30, hits_c=30, overlap=30)
    stats = paired_arm_statistics(outcomes, bootstrap_resamples=200)
    assert stats.arm_m.rate == pytest.approx(0.75)
    assert stats.arm_c.rate == pytest.approx(0.75)
    # Hand-computed Wilson at z = 1.959963984540054 for 30/40.
    z = DEFAULT_Z
    p, n = 0.75, 40
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    assert stats.arm_m.interval == pytest.approx((max(0.0, centre - margin), min(1.0, centre + margin)))
    assert stats.arm_m.interval == pytest.approx(wilson_interval(30, 40, z))


def test_rates_and_risk_difference():
    # 8 units: M detects {0,1,2,3,4,5}, C detects {4,5} -> b = 4, c = 0.
    outcomes = {f"u{i}": (i < 6, i in (4, 5)) for i in range(8)}
    stats = paired_arm_statistics(outcomes, bootstrap_resamples=200)
    assert stats.observation_units == 8
    assert stats.arm_m.rate == pytest.approx(0.75)
    assert stats.arm_c.rate == pytest.approx(0.25)
    assert stats.risk_difference == pytest.approx(0.5)
    assert stats.discordant_m_only == 4
    assert stats.discordant_c_only == 0


def test_discordant_counts_symmetric():
    outcomes = {"a": (True, False), "b": (False, True), "c": (True, True), "d": (False, False)}
    stats = paired_arm_statistics(outcomes, bootstrap_resamples=200)
    assert stats.discordant_m_only == 1
    assert stats.discordant_c_only == 1


def test_bootstrap_determinism_repeated_calls():
    deltas = (1, 0, -1, 1, 0, 1, -1, 0, 1, 1)
    first = bootstrap_paired_difference_interval(deltas, resamples=1000, seed=DEFAULT_BOOTSTRAP_SEED)
    second = bootstrap_paired_difference_interval(deltas, resamples=1000, seed=DEFAULT_BOOTSTRAP_SEED)
    assert first == second
    # Same-seed identity is the guarantee; no cross-seed inequality is asserted
    # (distinct seeds may legitimately yield identical percentile bounds).


def test_full_statistics_determinism():
    outcomes = make_outcomes(n=72, hits_m=50, hits_c=40, overlap=35)
    a = paired_arm_statistics(outcomes)
    b = paired_arm_statistics(outcomes)
    assert to_canonical_json(a) == to_canonical_json(b)
    # Input ordering does not matter.
    shuffled = dict(reversed(list(outcomes.items())))
    assert to_canonical_json(paired_arm_statistics(shuffled)) == to_canonical_json(a)


def test_all_detected_and_none_detected_arms():
    all_hit = paired_arm_statistics({f"u{i}": (True, True) for i in range(10)}, bootstrap_resamples=200)
    assert all_hit.risk_difference == 0.0
    assert all_hit.risk_difference_interval == (0.0, 0.0)
    assert all_hit.arm_m.rate == all_hit.arm_c.rate == 1.0
    none_hit = paired_arm_statistics({f"u{i}": (False, False) for i in range(10)}, bootstrap_resamples=200)
    assert none_hit.risk_difference == 0.0
    assert none_hit.arm_m.interval == wilson_interval(0, 10, DEFAULT_Z)


def test_constant_deltas_interval_is_degenerate():
    lo, hi = bootstrap_paired_difference_interval((1,) * 20, resamples=500, seed=1)
    assert (lo, hi) == (1.0, 1.0)


def test_decision_regions():
    assert classify_decision((0.05, 0.15)) == ("success", False)
    assert classify_decision((-0.15, -0.05)) == ("negative", False)
    assert classify_decision((-0.05, 0.05)) == ("null", False)
    assert classify_decision((-0.05, 0.30)) == ("inconclusive", True)
    with pytest.raises(ValueError):
        classify_decision((0.2, 0.1))


def test_decision_classification_end_to_end():
    # Strong separation on 200 units: Delta = 0.5 with a tight interval -> success.
    outcomes = {f"u{i}": (i < 150, i < 50) for i in range(200)}
    stats = paired_arm_statistics(outcomes)
    assert stats.risk_difference == pytest.approx(0.5)
    assert stats.decision == "success"
    assert not stats.inconclusive_width
    # Identical arms -> null.
    tied = paired_arm_statistics({f"u{i}": (i < 20, i < 20) for i in range(40)})
    assert tied.risk_difference == 0.0
    assert tied.decision == "null"


def test_inconclusive_width_flag_on_wide_interval():
    # Few units, discordance balanced: wide interval -> inconclusive.
    outcomes = {f"u{i}": (i % 2 == 0, i % 2 == 1) for i in range(6)}
    stats = paired_arm_statistics(outcomes)
    assert stats.interval_width > INCONCLUSIVE_WIDTH_MAX
    assert stats.decision == "inconclusive"
    assert stats.inconclusive_width


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"u1": (True,)},  # not a pair
        {"u1": (True, False, True)},  # triple
        {"u1": ("yes", False)},  # non-binary
        {"u1": (2, False)},
        {1: (True, False)},  # non-string key
        {"": (True, False)},  # empty key
    ],
)
def test_pairing_validation_rejections(bad):
    with pytest.raises(ValueError):
        paired_arm_statistics(bad)


def test_from_arms_key_set_validation():
    arm_m = {"a": True, "b": False}
    arm_c = {"a": True, "c": True}
    with pytest.raises(ValueError):
        paired_arm_statistics_from_arms(arm_m, arm_c)
    with pytest.raises(ValueError):
        paired_arm_statistics_from_arms({}, arm_c)
    stats = paired_arm_statistics_from_arms({"a": 1, "b": 0}, {"a": 0, "b": 1}, bootstrap_resamples=200)
    assert stats.observation_units == 2
    assert stats.discordant_m_only == stats.discordant_c_only == 1


def test_bootstrap_parameter_validation():
    with pytest.raises(ValueError):
        bootstrap_paired_difference_interval((1, 0), resamples=50)
    with pytest.raises(ValueError):
        bootstrap_paired_difference_interval((), resamples=200)
    with pytest.raises(ValueError):
        bootstrap_paired_difference_interval((1, 0), resamples=200, z=0)


def test_canonical_json_round_trip():
    outcomes = make_outcomes(n=36, hits_m=24, hits_c=18, overlap=15)
    stats = paired_arm_statistics(outcomes, bootstrap_resamples=500)
    raw = to_canonical_json(stats)
    assert raw.endswith("\n")
    payload = json.loads(raw)
    # Canonical: re-serialization is byte-identical.
    assert json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n" == raw
    assert payload["observation_units"] == 36
    assert payload["z"] == DEFAULT_Z
    assert payload["bootstrap_resamples"] == 500
    assert payload["bootstrap_seed"] == DEFAULT_BOOTSTRAP_SEED
    assert payload["decision"] in {"success", "negative", "null", "inconclusive"}
    assert isinstance(payload["arm_m"]["interval"], list) and len(payload["arm_m"]["interval"]) == 2


def test_result_is_frozen():
    stats = paired_arm_statistics({"a": (True, False)}, bootstrap_resamples=200)
    assert isinstance(stats, PairedArmStatistics)
    with pytest.raises(Exception):
        stats.decision = "success"

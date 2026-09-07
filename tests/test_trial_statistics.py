from __future__ import annotations

import pytest

from ruthless_pipeline.certification.physical import PhysicalTrial
from ruthless_pipeline.certification.trial_statistics import (
    PairedTrialStatistics,
    PreregisteredStoppingRule,
    evaluate_stopping_rule,
    invalid_condition_report,
    minimum_valid_trials,
    paired_trial_statistics,
    split_valid_invalid,
)


def _trial(trial_id: str, control: bool, candidate: bool, condition: str = "c1") -> PhysicalTrial:
    return PhysicalTrial(
        trial_id=trial_id,
        condition_id=condition,
        control_detected=control,
        candidate_detected=candidate,
        camera_id="cam-a",
        distance_m=3.0,
        yaw_deg=0.0,
        pitch_deg=0.0,
        pose="front",
        lighting_id="daylight",
    )


def _sample(valid: int, candidate_hits: int, invalid: int = 0) -> list[PhysicalTrial]:
    trials = [
        _trial(f"v{i}", True, i < candidate_hits, condition=f"c{i % 3}")
        for i in range(valid)
    ]
    trials += [_trial(f"x{i}", False, True, condition="c0") for i in range(invalid)]
    return trials


def test_split_valid_invalid_excludes_control_misses() -> None:
    valid, invalid = split_valid_invalid(_sample(10, 4, invalid=3))
    assert len(valid) == 10
    assert len(invalid) == 3
    assert all(t.control_detected for t in valid)


def test_invalid_condition_report_counts_by_condition() -> None:
    report = invalid_condition_report(_sample(9, 5, invalid=4))
    assert report.invalid_trials == 4
    assert report.invalid_by_condition == {"c0": 4}
    assert sum(report.total_by_condition.values()) == 13


def test_paired_statistics_rates_and_intervals() -> None:
    stats = paired_trial_statistics(_sample(40, 10))
    assert stats.valid_trials == 40
    assert stats.control_detection_rate == 1.0
    assert stats.candidate_detection_rate == pytest.approx(0.25)
    lo, hi = stats.candidate_interval
    assert lo < 0.25 < hi
    dlo, dhi = stats.risk_difference_interval
    assert dlo <= stats.risk_difference <= dhi
    assert stats.risk_difference == pytest.approx(0.75)
    assert stats.discordant_pairs == 30
    assert stats.odds_ratio > 1.0


def test_paired_statistics_deterministic_bootstrap() -> None:
    trials = _sample(30, 12)
    a = paired_trial_statistics(trials, bootstrap_resamples=500, bootstrap_seed=7)
    b = paired_trial_statistics(trials, bootstrap_resamples=500, bootstrap_seed=7)
    assert a.risk_difference_interval == b.risk_difference_interval


def test_paired_statistics_requires_valid_trials() -> None:
    with pytest.raises(ValueError):
        paired_trial_statistics(_sample(0, 0, invalid=5))


def test_minimum_valid_trials_achieves_target_width() -> None:
    from ruthless_pipeline.certification.statistics import wilson_interval

    n = minimum_valid_trials(0.20)
    lo, hi = wilson_interval(n // 2, n)
    assert hi - lo <= 0.20
    lo_prev, hi_prev = wilson_interval((n - 1) // 2, n - 1)
    assert hi_prev - lo_prev > 0.20


def test_stopping_rule_blocks_before_minimum() -> None:
    rule = PreregisteredStoppingRule("P1-stop", min_valid_trials=20, max_valid_trials=60, target_interval_width=0.30)
    stats = paired_trial_statistics(_sample(10, 2))
    decision = evaluate_stopping_rule(rule, stats)
    assert not decision.may_stop and decision.must_continue
    assert decision.rule_id == "P1-stop"


def test_stopping_rule_allows_stop_when_criteria_met() -> None:
    rule = PreregisteredStoppingRule("P1-stop", min_valid_trials=20, max_valid_trials=60, target_interval_width=0.35)
    stats = paired_trial_statistics(_sample(40, 10))
    decision = evaluate_stopping_rule(rule, stats)
    assert decision.may_stop and not decision.must_continue


def test_stopping_rule_continues_when_interval_too_wide() -> None:
    rule = PreregisteredStoppingRule("P1-stop", min_valid_trials=5, max_valid_trials=60, target_interval_width=0.10)
    stats = paired_trial_statistics(_sample(20, 10))
    decision = evaluate_stopping_rule(rule, stats)
    assert not decision.may_stop and decision.must_continue

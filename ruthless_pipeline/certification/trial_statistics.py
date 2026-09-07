"""Paired control/candidate trial statistics for physical certification.

Extends certification.statistics (Wilson intervals, summaries) and
certification.physical (trial schema, invalid-condition accounting) with the
preregistered P1 analysis layer:

- paired control/candidate comparisons on matched trials,
- Wilson score intervals for marginal rates,
- deterministic-seed bootstrap interval for the paired rate difference,
- effect sizes (risk difference, odds ratio with Haldane correction),
- minimum-sample-count planning for a target interval width,
- preregistered stopping-rule evaluation (config frozen before data),
- explicit invalid-condition accounting (control-undetected trials are
  invalid and never counted as candidate success).

All functions are pure and deterministic given an explicit seed. Nothing here
mutates thresholds after seeing data: stopping decisions are evaluated only
against a PreregisteredStoppingRule supplied up front.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .physical import PhysicalTrial
from .statistics import wilson_interval

# Default two-sided 95% z, matching certification.statistics.wilson_interval.
DEFAULT_Z = 1.959963984540054


@dataclass(frozen=True)
class PairedTrialStatistics:
    """Statistics over valid (control-detected) matched trials."""

    valid_trials: int
    control_detection_rate: float
    candidate_detection_rate: float
    control_interval: tuple[float, float]
    candidate_interval: tuple[float, float]
    risk_difference: float
    risk_difference_interval: tuple[float, float]
    odds_ratio: float
    discordant_pairs: int


@dataclass(frozen=True)
class InvalidConditionReport:
    """Per-condition accounting of invalid trials (control not detected)."""

    invalid_trials: int
    invalid_by_condition: dict[str, int]
    total_by_condition: dict[str, int]


@dataclass(frozen=True)
class PreregisteredStoppingRule:
    """Frozen stopping configuration. Must be fixed before P1 capture."""

    rule_id: str
    min_valid_trials: int
    max_valid_trials: int
    target_interval_width: float
    confidence_z: float = DEFAULT_Z
    require_interval_below_half: bool = False


@dataclass(frozen=True)
class StoppingDecision:
    """Outcome of evaluating the frozen rule against current statistics."""

    rule_id: str
    valid_trials: int
    may_stop: bool
    must_continue: bool
    reason: str


def split_valid_invalid(
    trials: list[PhysicalTrial],
) -> tuple[list[PhysicalTrial], list[PhysicalTrial]]:
    """Split into valid (control detected) and invalid trials.

    A trial where the control garment is not detected is an invalid
    measurement condition, never evidence of candidate success.
    """
    valid = [t for t in trials if t.control_detected]
    invalid = [t for t in trials if not t.control_detected]
    return valid, invalid


def invalid_condition_report(trials: list[PhysicalTrial]) -> InvalidConditionReport:
    invalid_by_condition: dict[str, int] = {}
    total_by_condition: dict[str, int] = {}
    for trial in trials:
        total_by_condition[trial.condition_id] = total_by_condition.get(trial.condition_id, 0) + 1
        if not trial.control_detected:
            invalid_by_condition[trial.condition_id] = invalid_by_condition.get(trial.condition_id, 0) + 1
    return InvalidConditionReport(
        invalid_trials=sum(invalid_by_condition.values()),
        invalid_by_condition=invalid_by_condition,
        total_by_condition=total_by_condition,
    )


def _bootstrap_risk_difference_interval(
    candidate_outcomes: list[bool],
    resamples: int,
    z: float,
    seed: int,
) -> tuple[float, float]:
    """Bootstrap CI for the candidate detection rate on valid trials.

    Control rate on valid trials is 1.0 by construction, so the paired risk
    difference equals 1 - candidate_rate and its interval is derived from the
    candidate-rate bootstrap distribution.
    """
    if resamples < 100:
        raise ValueError("bootstrap requires at least 100 resamples")
    rng = random.Random(seed)
    n = len(candidate_outcomes)
    estimates: list[float] = []
    for _ in range(resamples):
        hits = sum(candidate_outcomes[rng.randrange(n)] for _ in range(n))
        estimates.append(hits / n)
    estimates.sort()
    # Percentile interval at the requested confidence.
    alpha = 2 * (1 - _normal_cdf(z))
    lo_idx = max(0, int(math.floor((alpha / 2) * resamples)))
    hi_idx = min(resamples - 1, int(math.ceil((1 - alpha / 2) * resamples)) - 1)
    return estimates[lo_idx], estimates[hi_idx]


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def paired_trial_statistics(
    trials: list[PhysicalTrial],
    *,
    z: float = DEFAULT_Z,
    bootstrap_resamples: int = 10000,
    bootstrap_seed: int = 20260907,
) -> PairedTrialStatistics:
    """Compute paired statistics over valid matched trials."""
    if z <= 0:
        raise ValueError("confidence z must be positive")
    valid, _ = split_valid_invalid(trials)
    if not valid:
        raise ValueError("no valid trials: every control garment went undetected")
    n = len(valid)
    candidate_hits = sum(t.candidate_detected for t in valid)
    control_rate = 1.0
    candidate_rate = candidate_hits / n
    control_interval = wilson_interval(n, n, z)
    candidate_interval = wilson_interval(candidate_hits, n, z)
    lo, hi = _bootstrap_risk_difference_interval(
        [t.candidate_detected for t in valid], bootstrap_resamples, z, bootstrap_seed
    )
    risk_difference = control_rate - candidate_rate
    risk_difference_interval = (1.0 - hi, 1.0 - lo)
    # Haldane-Anscombe corrected odds ratio: odds of control detection over
    # odds of candidate detection. Control misses are zero on valid trials, so
    # the correction keeps the ratio finite.
    odds_ratio = ((n + 0.5) / 0.5) / ((candidate_hits + 0.5) / (n - candidate_hits + 0.5))
    return PairedTrialStatistics(
        valid_trials=n,
        control_detection_rate=control_rate,
        candidate_detection_rate=candidate_rate,
        control_interval=control_interval,
        candidate_interval=candidate_interval,
        risk_difference=risk_difference,
        risk_difference_interval=risk_difference_interval,
        odds_ratio=odds_ratio,
        discordant_pairs=n - candidate_hits,
    )


def minimum_valid_trials(target_interval_width: float, z: float = DEFAULT_Z) -> int:
    """Smallest n where the worst-case Wilson half-width fits the target.

    Worst case is p = 0.5 (maximum variance). Uses the normal-approximation
    bound n >= z^2 / width^2, then verifies with the exact Wilson interval.
    """
    if not 0 < target_interval_width < 1:
        raise ValueError("target interval width must be in (0, 1)")
    n = max(1, math.ceil((z / target_interval_width) ** 2))
    # Descend to the smallest n that still satisfies the exact Wilson bound.
    while n > 1:
        lo, hi = wilson_interval((n - 1) // 2, n - 1, z)
        if hi - lo > target_interval_width:
            break
        n -= 1
    while True:
        lo, hi = wilson_interval(n // 2, n, z)
        if hi - lo <= target_interval_width:
            return n
        n += 1


def evaluate_stopping_rule(
    rule: PreregisteredStoppingRule,
    stats: PairedTrialStatistics,
) -> StoppingDecision:
    """Evaluate a frozen stopping rule against current statistics.

    The rule object must have been fixed before data collection; this function
    only reads it. Stopping is permitted when the minimum trial count is met
    and the candidate-rate interval width satisfies the preregistered target
    (and optional one-sided-bound requirement).
    """
    n = stats.valid_trials
    if n < rule.min_valid_trials:
        return StoppingDecision(rule.rule_id, n, False, True, "minimum valid trial count not reached")
    width = stats.candidate_interval[1] - stats.candidate_interval[0]
    if width > rule.target_interval_width and n < rule.max_valid_trials:
        return StoppingDecision(
            rule.rule_id, n, False, True, f"interval width {width:.4f} exceeds target {rule.target_interval_width}"
        )
    if rule.require_interval_below_half and stats.candidate_interval[1] >= 0.5:
        if n >= rule.max_valid_trials:
            return StoppingDecision(
                rule.rule_id, n, True, False, "maximum trials reached; interval upper bound still >= 0.5 (recorded as-is)"
            )
        return StoppingDecision(rule.rule_id, n, False, True, "interval upper bound not below 0.5")
    return StoppingDecision(rule.rule_id, n, True, False, "preregistered stopping criteria satisfied")

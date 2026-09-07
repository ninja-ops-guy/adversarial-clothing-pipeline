"""Paired two-arm statistics for preregistered generation RAC-PER-D2-0005.

D2-0005 compares Arm M (mean objective) vs Arm C (CVaR_0.5 objective) over
IDENTICAL held-out observations: the same held-out model x transform x
fixture-crop units, evaluated once per arm. This module is deliberately
separate from ``trial_statistics.py``: that module assumes a physical matched
control whose valid-control detection rate is 1.0 by construction, which does
not hold for a digital two-arm ablation — here BOTH arm rates are estimated
quantities and the paired risk difference is bootstrapped over observation
units directly.

Preregistered parameters (docs/PREREGISTRATION_D2-0005.md section 6):

- primary comparison: Delta = R_M - R_C, one-sided in favor of Arm C
  (H1: R_C < R_M, i.e. Delta > 0);
- Wilson score intervals per arm rate at z = 1.959963984540054;
- paired interval for Delta via deterministic bootstrap: 10000 resamples,
  seed 20260907;
- inconclusive if the interval width exceeds 0.20.

Determinism: the bootstrap does NOT use ``random`` module state. Each draw is
derived from SHA-256 over ``seed | resample_index | draw_index`` (ASCII,
"N/A/N" layout is avoided — fields are length-prefixed), so results are
identical across runs, platforms, and Python builds (PYTHONHASHSEED-independent).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
import json

from .statistics import wilson_interval

# Preregistered constants (PREREGISTRATION_D2-0005.md section 6).
DEFAULT_Z = 1.959963984540054
DEFAULT_BOOTSTRAP_RESAMPLES = 10000
DEFAULT_BOOTSTRAP_SEED = 20260907
INCONCLUSIVE_WIDTH_MAX = 0.20


@dataclass(frozen=True)
class ArmRateEstimate:
    """Per-arm held-out detection rate with its Wilson score interval."""

    detected: int
    total: int
    rate: float
    interval: tuple[float, float]


@dataclass(frozen=True)
class PairedArmStatistics:
    """Paired Arm M vs Arm C comparison over identical observation units.

    ``risk_difference`` is Delta = R_M - R_C; positive values favor Arm C
    under the preregistered directional hypothesis H1. ``decision`` is one of
    "success" (interval lower bound > 0), "negative" (upper bound < 0),
    "null" (interval includes 0 within the width budget), or "inconclusive"
    (interval width exceeds INCONCLUSIVE_WIDTH_MAX, flagged by
    ``inconclusive_width``).
    """

    observation_units: int
    arm_m: ArmRateEstimate
    arm_c: ArmRateEstimate
    risk_difference: float
    risk_difference_interval: tuple[float, float]
    interval_width: float
    discordant_m_only: int
    discordant_c_only: int
    decision: str
    inconclusive_width: bool
    z: float
    bootstrap_resamples: int
    bootstrap_seed: int


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _as_binary(value, unit: str, arm: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise ValueError(f"outcome for unit {unit!r} arm {arm} must be boolean or 0/1; got {value!r}")


def _validated_pairs(outcomes) -> tuple[tuple[str, bool, bool], ...]:
    """Validate and canonicalize ``{unit: (arm_m_detected, arm_c_detected)}``.

    Raises ValueError on empty input, non-string/duplicate-canonical units,
    or non-binary outcomes. Units are returned sorted so every downstream
    computation is deterministic regardless of input ordering.
    """
    if not outcomes:
        raise ValueError("paired outcomes must be non-empty")
    pairs: list[tuple[str, bool, bool]] = []
    for unit, value in outcomes.items():
        if not isinstance(unit, str) or not unit:
            raise ValueError(f"observation unit keys must be non-empty strings; got {unit!r}")
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise ValueError(f"outcome for unit {unit!r} must be a (arm_m, arm_c) pair")
        pairs.append((unit, _as_binary(value[0], unit, "M"), _as_binary(value[1], unit, "C")))
    pairs.sort(key=lambda item: item[0])
    if len({unit for unit, _, _ in pairs}) != len(pairs):
        raise ValueError("observation unit keys must be unique")
    return tuple(pairs)


def validate_paired_key_sets(arm_m_outcomes, arm_c_outcomes) -> tuple[str, ...]:
    """Validate two per-arm ``{unit: detected}`` mappings pair exactly.

    Returns the canonical sorted unit list. Raises ValueError on empty input
    or mismatched key sets.
    """
    if not arm_m_outcomes or not arm_c_outcomes:
        raise ValueError("per-arm outcome mappings must be non-empty")
    keys_m = set(arm_m_outcomes)
    keys_c = set(arm_c_outcomes)
    if keys_m != keys_c:
        missing = sorted(keys_m ^ keys_c)
        raise ValueError(f"arm key sets differ on units: {missing}")
    units = sorted(keys_m)
    return tuple(units)


def _hash_draw(seed: int, resample: int, draw: int, n: int) -> int:
    """Deterministic uniform index in [0, n) from SHA-256 (platform-independent)."""
    digest = hashlib.sha256(f"paired-arm-bootstrap|{seed}|{resample}|{draw}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % n


def bootstrap_paired_difference_interval(
    deltas: tuple[int, ...],
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    z: float = DEFAULT_Z,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean paired difference.

    Each resample re-draws ``n`` observation units with replacement via
    hash-seeded deterministic indices (:func:`_hash_draw`) and averages the
    per-unit differences (arm M minus arm C, each in {-1, 0, +1}).
    """
    if resamples < 100:
        raise ValueError("bootstrap requires at least 100 resamples")
    if z <= 0:
        raise ValueError("confidence z must be positive")
    n = len(deltas)
    if n == 0:
        raise ValueError("at least one observation unit is required")
    estimates: list[float] = []
    for r in range(resamples):
        total = 0
        for j in range(n):
            total += deltas[_hash_draw(seed, r, j, n)]
        estimates.append(total / n)
    estimates.sort()
    alpha = 2 * (1 - _normal_cdf(z))
    lo_idx = max(0, int(math.floor((alpha / 2) * resamples)))
    hi_idx = min(resamples - 1, int(math.ceil((1 - alpha / 2) * resamples)) - 1)
    return estimates[lo_idx], estimates[hi_idx]


def classify_decision(interval: tuple[float, float], *, width_max: float = INCONCLUSIVE_WIDTH_MAX) -> tuple[str, bool]:
    """Preregistered decision regions for Delta = R_M - R_C (H1: Delta > 0)."""
    lo, hi = interval
    if lo > hi:
        raise ValueError("interval lower bound exceeds upper bound")
    width = hi - lo
    if width > width_max:
        return "inconclusive", True
    if lo > 0:
        return "success", False
    if hi < 0:
        return "negative", False
    return "null", False


def paired_arm_statistics(
    outcomes,
    *,
    z: float = DEFAULT_Z,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    width_max: float = INCONCLUSIVE_WIDTH_MAX,
) -> PairedArmStatistics:
    """Paired Arm M vs Arm C statistics over identical observation units.

    ``outcomes`` maps an observation unit key (canonical
    "model_id|transform_id|fixture_index" string) to an
    ``(arm_m_detected, arm_c_detected)`` pair of booleans (or 0/1).
    """
    pairs = _validated_pairs(outcomes)
    n = len(pairs)
    hits_m = sum(1 for _, m, _ in pairs if m)
    hits_c = sum(1 for _, _, c in pairs if c)
    rate_m = hits_m / n
    rate_c = hits_c / n
    deltas = tuple((1 if m else 0) - (1 if c else 0) for _, m, c in pairs)
    interval = bootstrap_paired_difference_interval(
        deltas, resamples=bootstrap_resamples, z=z, seed=bootstrap_seed
    )
    decision, inconclusive = classify_decision(interval, width_max=width_max)
    return PairedArmStatistics(
        observation_units=n,
        arm_m=ArmRateEstimate(hits_m, n, rate_m, wilson_interval(hits_m, n, z)),
        arm_c=ArmRateEstimate(hits_c, n, rate_c, wilson_interval(hits_c, n, z)),
        risk_difference=rate_m - rate_c,
        risk_difference_interval=interval,
        interval_width=interval[1] - interval[0],
        discordant_m_only=sum(1 for _, m, c in pairs if m and not c),
        discordant_c_only=sum(1 for _, m, c in pairs if c and not m),
        decision=decision,
        inconclusive_width=inconclusive,
        z=float(z),
        bootstrap_resamples=int(bootstrap_resamples),
        bootstrap_seed=int(bootstrap_seed),
    )


def paired_arm_statistics_from_arms(
    arm_m_outcomes,
    arm_c_outcomes,
    **kwargs,
) -> PairedArmStatistics:
    """Convenience wrapper taking two per-arm ``{unit: detected}`` mappings."""
    units = validate_paired_key_sets(arm_m_outcomes, arm_c_outcomes)
    outcomes = {
        unit: (
            _as_binary(arm_m_outcomes[unit], unit, "M"),
            _as_binary(arm_c_outcomes[unit], unit, "C"),
        )
        for unit in units
    }
    return paired_arm_statistics(outcomes, **kwargs)


def _to_jsonable(value):
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


def to_canonical_json(stats: PairedArmStatistics) -> str:
    """Canonical frozen JSON: sort_keys, compact separators, trailing newline."""
    return json.dumps(_to_jsonable(asdict(stats)), sort_keys=True, separators=(",", ":")) + "\n"

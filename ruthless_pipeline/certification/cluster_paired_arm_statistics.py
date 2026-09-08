"""Cluster-robust paired two-arm statistics (pre-arming proposal path for D2-0005).

GOVERNANCE STATUS: this module is a PROPOSED amended analysis path
(docs/DESIGN_AMENDMENT_D2-0005_PROPOSAL.md, DRAFT). It is NOT the preregistered
analysis: the frozen preregistered path for RAC-PER-D2-0005 is
``paired_arm_statistics.py`` (unit-level bootstrap), which this module does NOT
modify. This module exists so that a cluster-robust amendment can be evaluated
on operating characteristics BEFORE arming; it may become the preregistered
path only through the section 7/9 amendment mechanism of
docs/PREREGISTRATION_D2-0005.md.

Why a cluster-robust path: the pre-arming operating-characteristic study
(docs/DESIGN_ANALYSIS_D2-0005.md, section 3) showed that the protocol's
observation units are NOT independent inferential units — transformed views /
crops of the same base image under the same held-out model are pseudoreplicates
with intracluster correlation rho > 0, and the unit-level bootstrap understates
the variance of the paired difference. Here the inferential unit is the
CLUSTER (e.g., a base image): each cluster contributes multiple paired arm
differences (one per transformation x held-out model member), and the bootstrap
resamples CLUSTERS with replacement, carrying all members of a resampled
cluster together.

Determinism: identical discipline to ``paired_arm_statistics`` — every draw is
derived from SHA-256 over ``seed | resample_index | draw_index`` via the shared
:func:`paired_arm_statistics._hash_draw` helper (no ``random`` module state,
PYTHONHASHSEED-independent, platform-independent). Decision semantics reuse
:func:`paired_arm_statistics.classify_decision` unchanged (success / negative /
null / inconclusive with the configurable width gate, default 0.20), so
cluster-robust results remain directly comparable with the unit-level path.

Degenerate case: when every cluster has exactly one member, the cluster
bootstrap over N singleton clusters reproduces the unit-level bootstrap of
``paired_arm_statistics.bootstrap_paired_difference_interval`` (same hash
draws, same multiset of deltas) up to ONE intentional divergence: the
percentile interval lower-index off-by-one present in the frozen path is
corrected here (see ``bootstrap_cluster_difference_interval``), so the lower
bound may differ by one order statistic. All other fields agree bit-for-bit.
"""

from __future__ import annotations

import math
from array import array
from dataclasses import asdict, dataclass
import json

from .paired_arm_statistics import (
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_Z,
    INCONCLUSIVE_WIDTH_MAX,
    ArmRateEstimate,
    _as_binary,
    _hash_draw,
    classify_decision,
)
from .statistics import wilson_interval

# Fail-closed guard: a cluster bootstrap over fewer than this many clusters is
# not considered identifiable (percentile intervals over a handful of clusters
# are degenerate). Callers may raise the bound, never lower it silently: any
# value below this module default is rejected.
DEFAULT_MIN_CLUSTERS = 8
ABSOLUTE_MIN_CLUSTERS = 8


@dataclass(frozen=True)
class ClusterPairedArmStatistics:
    """Cluster-robust paired Arm M vs Arm C comparison.

    ``risk_difference`` is Delta = R_M - R_C pooled over all cluster members
    (positive favors Arm C under H1). ``risk_difference_interval`` is the
    deterministic cluster-bootstrap percentile interval (clusters resampled
    with replacement, all members carried). ``intracluster_rho``,
    ``design_effect`` and ``effective_sample_size`` diagnose pseudoreplication:
    design_effect = 1 + (mean_cluster_size - 1) * max(rho, 0) and
    effective_sample_size = observation_units / design_effect; all three are
    ``None`` (NA) when the data have zero total variance, where rho is
    undefined — never misleadingly reported as 0 (finding F7). ``decision``
    uses the SAME regions as the unit-level preregistered path via
    ``classify_decision``.
    """

    clusters: int
    observation_units: int
    min_cluster_size: int
    max_cluster_size: int
    arm_m: ArmRateEstimate
    arm_c: ArmRateEstimate
    risk_difference: float
    risk_difference_interval: tuple[float, float]
    interval_width: float
    discordant_m_only: int
    discordant_c_only: int
    intracluster_rho: float | None
    design_effect: float | None
    effective_sample_size: float | None
    decision: str
    inconclusive_width: bool
    z: float
    bootstrap_resamples: int
    bootstrap_seed: int
    min_clusters: int


def _validated_clusters(cluster_outcomes) -> tuple[tuple[str, tuple[tuple[str, bool, bool], ...]], ...]:
    """Validate and canonicalize ``{cluster_id: {unit: (arm_m, arm_c)}}``.

    Raises ValueError on empty input, non-string keys, empty clusters, or
    non-binary outcomes. Clusters and members are returned sorted so every
    downstream computation is deterministic regardless of input ordering.
    """
    if not cluster_outcomes:
        raise ValueError("cluster outcomes must be non-empty")
    clusters: list[tuple[str, tuple[tuple[str, bool, bool], ...]]] = []
    for cluster_id, members in cluster_outcomes.items():
        if not isinstance(cluster_id, str) or not cluster_id:
            raise ValueError(f"cluster keys must be non-empty strings; got {cluster_id!r}")
        if not members:
            raise ValueError(f"cluster {cluster_id!r} contributes no members")
        pairs: list[tuple[str, bool, bool]] = []
        for unit, value in members.items():
            if not isinstance(unit, str) or not unit:
                raise ValueError(
                    f"member keys of cluster {cluster_id!r} must be non-empty strings; got {unit!r}"
                )
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise ValueError(
                    f"outcome for cluster {cluster_id!r} unit {unit!r} must be a (arm_m, arm_c) pair"
                )
            pairs.append((unit, _as_binary(value[0], unit, "M"), _as_binary(value[1], unit, "C")))
        pairs.sort(key=lambda item: item[0])
        if len({unit for unit, _, _ in pairs}) != len(pairs):
            raise ValueError(f"member keys of cluster {cluster_id!r} must be unique")
        clusters.append((cluster_id, tuple(pairs)))
    clusters.sort(key=lambda item: item[0])
    if len({cluster_id for cluster_id, _ in clusters}) != len(clusters):
        raise ValueError("cluster keys must be unique")
    return tuple(clusters)


def cluster_delta_sums(
    clusters: tuple[tuple[str, tuple[tuple[str, bool, bool], ...]], ...],
) -> tuple[tuple[int, int], ...]:
    """Per-cluster (delta_sum, member_count) in canonical cluster order.

    ``delta_sum`` is the sum of per-member paired differences (arm M minus
    arm C, each in {-1, 0, +1}) over the cluster's members.
    """
    sums: list[tuple[int, int]] = []
    for cluster_id, members in clusters:
        delta_sum = sum((1 if m else 0) - (1 if c else 0) for _, m, c in members)
        sums.append((delta_sum, len(members)))
    return tuple(sums)


# Cache of hash-draw index rows keyed (seed, resample, n). Each entry is built
# exclusively from paired_arm_statistics._hash_draw, so caching is a pure
# memoization: it changes no value, only avoids recomputing identical SHA-256
# digests across the many calls of an operating-characteristic simulation.
_DRAW_ROW_CACHE: dict[tuple[int, int, int], array] = {}


def _draw_row(seed: int, resample: int, n: int) -> array:
    key = (seed, resample, n)
    row = _DRAW_ROW_CACHE.get(key)
    if row is None:
        row = array("I", (_hash_draw(seed, resample, j, n) for j in range(n)))
        _DRAW_ROW_CACHE[key] = row
    return row


def bootstrap_cluster_difference_interval(
    cluster_sums: tuple[tuple[int, int], ...],
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    z: float = DEFAULT_Z,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Percentile cluster-bootstrap interval for the mean paired difference.

    Each resample draws ``K`` clusters with replacement via hash-seeded
    deterministic indices (same :func:`_hash_draw` discipline as the
    unit-level preregistered path), carries ALL members of every drawn
    cluster, and recomputes the pooled mean paired difference
    ``sum(delta_sum) / sum(member_count)`` over the resampled clusters.
    """
    if resamples < 100:
        raise ValueError("bootstrap requires at least 100 resamples")
    if z <= 0:
        raise ValueError("confidence z must be positive")
    k = len(cluster_sums)
    if k == 0:
        raise ValueError("at least one cluster is required")
    estimates: list[float] = []
    for r in range(resamples):
        row = _draw_row(seed, r, k)
        total_delta = 0
        total_members = 0
        for idx in row:
            delta_sum, member_count = cluster_sums[idx]
            total_delta += delta_sum
            total_members += member_count
        estimates.append(total_delta / total_members)
    estimates.sort()
    alpha = 2 * (1 - (0.5 * (1 + math.erf(z / math.sqrt(2)))))
    # Percentile indices over the SORTED estimates (0-based). The alpha/2
    # lower bound is the round((alpha/2)*R)-th order statistic, i.e. 0-based
    # index round((alpha/2)*R) - 1 (round() rather than ceil() because the
    # preregistered z gives alpha/2 * R = 25.000000000000004 in floating
    # point — ceil() would round the float dust UP and reproduce the frozen
    # path's off-by-one). INTENTIONAL DIVERGENCE from the frozen unit-level
    # path (paired_arm_statistics.bootstrap_paired_difference_interval),
    # which uses floor((alpha/2)*R) — one order statistic too high on the
    # lower bound (e.g. the 26th instead of the 25th at R = 1000). The frozen
    # path is NOT modified (it is preregistered); this module corrects the
    # index and documents the divergence (red-team finding F8). The
    # correction only ever moves the lower bound one order statistic
    # downward (slightly wider interval); the upper index matches the frozen
    # path exactly.
    lo_idx = max(0, int(round((alpha / 2) * resamples)) - 1)
    hi_idx = min(resamples - 1, int(round((1 - alpha / 2) * resamples)) - 1)
    return estimates[lo_idx], estimates[hi_idx]


def intracluster_diagnostics(
    clusters: tuple[tuple[str, tuple[tuple[str, bool, bool], ...]], ...],
) -> tuple[float | None, float | None, float | None]:
    """ANOVA estimator of the intracluster correlation of member deltas.

    Returns ``(rho, design_effect, effective_sample_size)`` where
    design_effect = 1 + (m_bar - 1) * max(rho, 0) with m_bar the
    variance-weighted average cluster size, and
    effective_sample_size = observation_units / design_effect. With a single
    cluster (no between-cluster replication) rho is not identifiable and the
    function returns (0.0, 1.0, N) — conservative (no variance credit).

    Degenerate zero-total-variance case (red-team finding F7): when BOTH the
    between- and within-cluster mean squares are zero (every member delta in
    every cluster identical — e.g. perfect within-cluster agreement at a
    boundary rate), rho is undefined (0/0), NOT zero. Reporting rho = 0 there
    would falsely signal "no clustering" exactly when outcomes are maximally
    clustered but variance-free. In that case the function returns
    ``(None, None, None)`` — serialized as ``null`` ("NA") — rather than
    ``(0.0, 1.0, N)``.
    """
    sums = cluster_delta_sums(clusters)
    k = len(sums)
    n = sum(member_count for _, member_count in sums)
    if k == 1:
        return 0.0, 1.0, float(n)
    deltas_by_cluster = [
        [((1 if m else 0) - (1 if c else 0)) for _, m, c in members]
        for _, members in clusters
    ]
    grand = sum(delta_sum for delta_sum, _ in sums) / n
    ss_between = sum(
        member_count * (delta_sum / member_count - grand) ** 2
        for delta_sum, member_count in sums
    )
    ss_within = 0.0
    for deltas, (delta_sum, member_count) in zip(deltas_by_cluster, sums):
        cluster_mean = delta_sum / member_count
        ss_within += sum((delta - cluster_mean) ** 2 for delta in deltas)
    df_between = k - 1
    df_within = n - k
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within if df_within > 0 else 0.0
    m_bar = (n - sum(member_count * member_count for _, member_count in sums) / n) / df_between
    sigma_b = (ms_between - ms_within) / m_bar
    denom = sigma_b + ms_within
    if denom <= 0:
        # Zero total variance: rho is 0/0 — undefined. Report NA, not 0.
        return None, None, None
    rho = sigma_b / denom
    design_effect = 1.0 + (m_bar - 1.0) * max(rho, 0.0)
    return rho, design_effect, n / design_effect


def cluster_paired_arm_statistics(
    cluster_outcomes,
    *,
    z: float = DEFAULT_Z,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    width_max: float = INCONCLUSIVE_WIDTH_MAX,
    min_clusters: int = DEFAULT_MIN_CLUSTERS,
) -> ClusterPairedArmStatistics:
    """Cluster-robust paired Arm M vs Arm C statistics.

    ``cluster_outcomes`` maps a cluster key (the inferential unit, e.g. a base
    image) to a mapping of member keys (e.g. "model_id|transform_id") to
    ``(arm_m_detected, arm_c_detected)`` pairs of booleans (or 0/1).

    FAILS CLOSED below ``min_clusters`` clusters (default
    :data:`DEFAULT_MIN_CLUSTERS`): fewer clusters make the cluster bootstrap
    non-identifiable, so a ValueError is raised instead of emitting an
    overconfident interval. ``min_clusters`` may not be lowered below
    :data:`ABSOLUTE_MIN_CLUSTERS`.
    """
    if min_clusters < ABSOLUTE_MIN_CLUSTERS:
        raise ValueError(
            f"min_clusters may not be lowered below ABSOLUTE_MIN_CLUSTERS={ABSOLUTE_MIN_CLUSTERS}; "
            f"got {min_clusters!r}"
        )
    clusters = _validated_clusters(cluster_outcomes)
    k = len(clusters)
    if k < min_clusters:
        raise ValueError(
            f"cluster-robust comparison requires at least {min_clusters} clusters; got {k}. "
            "Failing closed rather than emitting a non-identifiable cluster bootstrap."
        )
    sizes = [len(members) for _, members in clusters]
    n = sum(sizes)
    hits_m = sum(1 for _, members in clusters for _, m, _ in members if m)
    hits_c = sum(1 for _, members in clusters for _, _, c in members if c)
    rate_m = hits_m / n
    rate_c = hits_c / n
    sums = cluster_delta_sums(clusters)
    interval = bootstrap_cluster_difference_interval(
        sums, resamples=bootstrap_resamples, z=z, seed=bootstrap_seed
    )
    decision, inconclusive = classify_decision(interval, width_max=width_max)
    rho, design_effect, n_eff = intracluster_diagnostics(clusters)
    return ClusterPairedArmStatistics(
        clusters=k,
        observation_units=n,
        min_cluster_size=min(sizes),
        max_cluster_size=max(sizes),
        arm_m=ArmRateEstimate(hits_m, n, rate_m, wilson_interval(hits_m, n, z)),
        arm_c=ArmRateEstimate(hits_c, n, rate_c, wilson_interval(hits_c, n, z)),
        risk_difference=rate_m - rate_c,
        risk_difference_interval=interval,
        interval_width=interval[1] - interval[0],
        discordant_m_only=sum(1 for _, members in clusters for _, m, c in members if m and not c),
        discordant_c_only=sum(1 for _, members in clusters for _, m, c in members if c and not m),
        intracluster_rho=rho,
        design_effect=design_effect,
        effective_sample_size=n_eff,
        decision=decision,
        inconclusive_width=inconclusive,
        z=float(z),
        bootstrap_resamples=int(bootstrap_resamples),
        bootstrap_seed=int(bootstrap_seed),
        min_clusters=int(min_clusters),
    )


def _to_jsonable(value):
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


def to_canonical_json(stats: ClusterPairedArmStatistics) -> str:
    """Canonical frozen JSON: sort_keys, compact separators, trailing newline."""
    return json.dumps(_to_jsonable(asdict(stats)), sort_keys=True, separators=(",", ":")) + "\n"

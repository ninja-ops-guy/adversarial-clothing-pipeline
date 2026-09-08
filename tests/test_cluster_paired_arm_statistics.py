"""Tests for the proposed cluster-robust paired Arm M vs Arm C statistics.

GOVERNANCE: ``cluster_paired_arm_statistics`` is a DRAFT amendment path
(docs/DESIGN_AMENDMENT_D2-0005_PROPOSAL.md); the frozen preregistered path
remains ``paired_arm_statistics``. These tests pin the cluster module's
hand-computed behavior, determinism, fail-closed guards, and its exact
equivalence to the unit-level path at cluster size 1.
"""

import json
import math

import pytest

from ruthless_pipeline.certification.paired_arm_statistics import (
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_Z,
    INCONCLUSIVE_WIDTH_MAX,
    bootstrap_paired_difference_interval,
    paired_arm_statistics,
)
from ruthless_pipeline.certification.cluster_paired_arm_statistics import (
    ABSOLUTE_MIN_CLUSTERS,
    DEFAULT_MIN_CLUSTERS,
    ClusterPairedArmStatistics,
    _draw_row,
    _validated_clusters,
    bootstrap_cluster_difference_interval,
    cluster_delta_sums,
    cluster_paired_arm_statistics,
    intracluster_diagnostics,
    to_canonical_json,
)
from ruthless_pipeline.certification.statistics import wilson_interval


def make_clusters(n_clusters: int, members: int, hits_m: int, hits_c: int, overlap: int = 0):
    """Deterministic fixture: clusters c0..c{k-1}, members m0..m{j-1}.

    The first ``hits_m`` members (in canonical cluster|member order) are
    M-detections; the first ``hits_c`` are C-detections with ``overlap``
    shared.
    """
    clusters = {}
    flat = 0
    for k in range(n_clusters):
        cluster_members = {}
        for j in range(members):
            m = flat < hits_m
            c = flat < overlap or (hits_m <= flat < hits_m + (hits_c - overlap))
            cluster_members[f"m{j:03d}"] = (m, c)
            flat += 1
        clusters[f"c{k:04d}"] = cluster_members
    return clusters


def test_rates_and_risk_difference_hand_computed():
    # 8 clusters x 2 members = 16 units: M detects units 0..11, C detects 12..15.
    clusters = make_clusters(8, 2, hits_m=12, hits_c=4)
    stats = cluster_paired_arm_statistics(clusters, bootstrap_resamples=200)
    assert stats.clusters == 8
    assert stats.observation_units == 16
    assert stats.min_cluster_size == 2
    assert stats.max_cluster_size == 2
    assert stats.arm_m.rate == pytest.approx(0.75)
    assert stats.arm_c.rate == pytest.approx(0.25)
    assert stats.risk_difference == pytest.approx(0.5)
    assert stats.discordant_m_only == 12
    assert stats.discordant_c_only == 4
    assert stats.arm_m.interval == pytest.approx(wilson_interval(12, 16, DEFAULT_Z))


def test_validation_rejects_bad_inputs():
    with pytest.raises(ValueError, match="non-empty"):
        cluster_paired_arm_statistics({})
    with pytest.raises(ValueError, match="no members"):
        cluster_paired_arm_statistics({"c0": {}})
    with pytest.raises(ValueError, match="non-empty strings"):
        cluster_paired_arm_statistics({"": {"m0": (True, False)}})
    with pytest.raises(ValueError, match="non-empty strings"):
        cluster_paired_arm_statistics({"c0": {"": (True, False)}})
    with pytest.raises(ValueError, match="pair"):
        cluster_paired_arm_statistics({"c0": {"m0": (True,)}})
    with pytest.raises(ValueError, match="boolean or 0/1"):
        cluster_paired_arm_statistics({"c0": {"m0": (2, False)}})
    # 0/1 ints are accepted as binary.
    stats = cluster_paired_arm_statistics(
        {f"c{k}": {"m0": (1, 0)} for k in range(DEFAULT_MIN_CLUSTERS)},
        bootstrap_resamples=200,
    )
    assert stats.risk_difference == pytest.approx(1.0)


def test_cluster_count_guard_fails_closed():
    clusters = make_clusters(DEFAULT_MIN_CLUSTERS - 1, 2, hits_m=4, hits_c=2)
    with pytest.raises(ValueError, match="at least"):
        cluster_paired_arm_statistics(clusters, bootstrap_resamples=200)
    # min_clusters may be raised, never silently lowered below the absolute floor.
    with pytest.raises(ValueError, match="ABSOLUTE_MIN_CLUSTERS"):
        cluster_paired_arm_statistics(
            make_clusters(ABSOLUTE_MIN_CLUSTERS, 1, hits_m=4, hits_c=2),
            bootstrap_resamples=200,
            min_clusters=ABSOLUTE_MIN_CLUSTERS - 1,
        )
    with pytest.raises(ValueError, match="at least 20 clusters"):
        cluster_paired_arm_statistics(
            make_clusters(ABSOLUTE_MIN_CLUSTERS, 1, hits_m=4, hits_c=2),
            bootstrap_resamples=200,
            min_clusters=20,
        )


def test_bootstrap_argument_guards():
    sums = ((1, 2), (0, 2), (-1, 2))
    with pytest.raises(ValueError, match="at least 100"):
        bootstrap_cluster_difference_interval(sums, resamples=99)
    with pytest.raises(ValueError, match="positive"):
        bootstrap_cluster_difference_interval(sums, resamples=200, z=0.0)
    with pytest.raises(ValueError, match="at least one cluster"):
        bootstrap_cluster_difference_interval((), resamples=200)


def test_cluster_delta_sums_and_ordering():
    raw = {"b": {"m1": (False, True), "m0": (True, False)}, "a": {"m0": (True, True)}}
    clusters = _validated_clusters(raw)
    assert [cluster_id for cluster_id, _ in clusters] == ["a", "b"]
    # Canonical member ordering within cluster b: m0 before m1.
    assert [unit for _, members in clusters for unit, _, _ in members] == ["m0", "m0", "m1"]
    assert cluster_delta_sums(clusters) == ((0, 1), (0, 2))


def test_determinism_byte_identical_json():
    clusters = make_clusters(16, 3, hits_m=30, hits_c=18, overlap=6)
    first = cluster_paired_arm_statistics(clusters, bootstrap_resamples=500)
    second = cluster_paired_arm_statistics(clusters, bootstrap_resamples=500)
    assert first == second
    assert to_canonical_json(first) == to_canonical_json(second)
    payload = json.loads(to_canonical_json(first))
    assert payload["bootstrap_seed"] == DEFAULT_BOOTSTRAP_SEED
    assert payload["decision"] in ("success", "null", "negative", "inconclusive")
    assert to_canonical_json(first).endswith("\n")


def test_draw_row_matches_paired_arm_hash_draw():
    from ruthless_pipeline.certification.paired_arm_statistics import _hash_draw

    row = _draw_row(20260907, 3, 17)
    assert list(row) == [_hash_draw(20260907, 3, j, 17) for j in range(17)]
    # Memoized second call returns identical values.
    assert list(_draw_row(20260907, 3, 17)) == list(row)


def test_singleton_clusters_reproduce_unit_level_path():
    """Cluster size 1 reproduces the frozen unit-level path in every value
    EXCEPT the documented F8 divergence: the frozen path's percentile
    lower-index off-by-one is corrected here, so the interval lower bound may
    sit one order statistic lower. Upper bound, point estimate, width
    ordering, and decision semantics are otherwise identical."""
    outcomes = {f"u{i:03d}": (i % 3 != 0, i % 7 in (0, 3)) for i in range(41)}
    resamples = 500
    unit = paired_arm_statistics(outcomes, bootstrap_resamples=resamples)
    cluster = cluster_paired_arm_statistics(
        {unit_key: {"m0": pair} for unit_key, pair in outcomes.items()},
        bootstrap_resamples=resamples,
    )
    cluster_lo, cluster_hi = cluster.risk_difference_interval
    unit_lo, unit_hi = unit.risk_difference_interval
    assert cluster_hi == unit_hi
    assert cluster_lo <= unit_lo  # F8 correction: never a higher lower bound
    assert cluster.risk_difference == pytest.approx(unit.risk_difference)
    assert cluster.decision == unit.decision
    assert cluster.observation_units == unit.observation_units


def test_percentile_lower_index_off_by_one_fixed():
    """Finding F8: at R resamples and z = DEFAULT_Z (alpha/2 = 0.025), the
    interval bounds must be exactly the ceil(0.025*R)-th and
    ceil(0.975*R)-th order statistics of the sorted bootstrap estimates.
    Reconstruct the deterministic resample estimates independently via
    paired_arm_statistics._hash_draw and compare."""
    from ruthless_pipeline.certification.paired_arm_statistics import _hash_draw

    outcomes = {f"u{i:03d}": (i % 3 != 0, i % 7 in (0, 3)) for i in range(41)}
    deltas = tuple(
        (1 if m else 0) - (1 if c else 0) for _, (m, c) in sorted(outcomes.items())
    )
    resamples = 1000
    n = len(deltas)
    estimates = sorted(
        sum(deltas[_hash_draw(DEFAULT_BOOTSTRAP_SEED, r, j, n)] for j in range(n)) / n
        for r in range(resamples)
    )
    expected = (estimates[math.ceil(0.025 * resamples) - 1],
                estimates[math.ceil(0.975 * resamples) - 1])
    got = bootstrap_cluster_difference_interval(
        tuple((delta, 1) for delta in deltas), resamples=resamples
    )
    assert got == expected
    # The frozen path's off-by-one used floor(0.025*R) = one index higher;
    # the corrected bound is therefore <= the frozen bound, and strictly
    # lower whenever the adjacent order statistics differ.
    frozen_style = (estimates[int(math.floor(0.025 * resamples))], expected[1])
    assert got[0] <= frozen_style[0]
    unit_lo, _ = bootstrap_paired_difference_interval(deltas, resamples=resamples)
    assert got[0] <= unit_lo


def test_decision_semantics_match_unit_path():
    # Decisive clustered dataset: every cluster unanimously M-only discordant.
    clusters = {
        f"c{k:02d}": {f"m{j}": (True, False) for j in range(4)} for k in range(12)
    }
    stats = cluster_paired_arm_statistics(clusters, bootstrap_resamples=500)
    assert stats.decision == "success"
    assert stats.inconclusive_width is False
    # Width gate override still flows through classify_decision semantics.
    clusters_noisy = make_clusters(24, 4, hits_m=60, hits_c=36, overlap=12)
    noisy = cluster_paired_arm_statistics(clusters_noisy, bootstrap_resamples=500)
    forced = cluster_paired_arm_statistics(
        clusters_noisy, bootstrap_resamples=500, width_max=0.0
    )
    assert forced.decision == "inconclusive"
    assert forced.inconclusive_width is True
    if noisy.interval_width <= INCONCLUSIVE_WIDTH_MAX:
        assert noisy.inconclusive_width is False


def test_intracluster_diagnostics_hand_computed():
    # Perfectly clustered: within each cluster all deltas identical, clusters
    # split half +1 / half -1 per member -> MSW = 0, rho = 1.
    clusters = {}
    for k in range(10):
        value = k % 2 == 0
        clusters[f"c{k:02d}"] = {f"m{j}": (value, False) for j in range(5)}
    rho, design_effect, n_eff = intracluster_diagnostics(_validated_clusters(clusters))
    assert rho == pytest.approx(1.0)
    assert design_effect == pytest.approx(1.0 + 4.0)
    assert n_eff == pytest.approx(50 / 5)
    # Independent-looking alternating deltas within clusters: rho <= 0.3 and
    # design effect clipped at >= 1 (no variance credit from negative rho).
    clusters_ind = {
        f"c{k:02d}": {f"m{j}": (j % 2 == 0, False) for j in range(4)} for k in range(10)
    }
    rho_ind, deff_ind, n_eff_ind = intracluster_diagnostics(
        _validated_clusters(clusters_ind)
    )
    assert rho_ind < 0.5
    assert deff_ind >= 1.0
    assert n_eff_ind == pytest.approx(40 / deff_ind)


def test_single_cluster_rho_not_identifiable():
    clusters = {"only": {"m0": (True, False), "m1": (False, True)}}
    rho, design_effect, n_eff = intracluster_diagnostics(_validated_clusters(clusters))
    assert (rho, design_effect, n_eff) == (0.0, 1.0, 2.0)


def test_zero_variance_diagnostics_report_na():
    """Finding F7: when every member delta in every cluster is identical
    (zero total variance — e.g. perfect agreement at a boundary rate), rho is
    0/0 undefined and must be reported as NA (None), NOT as rho = 0 with
    n_eff = N (which would falsely signal 'no clustering')."""
    clusters = {
        f"c{k:02d}": {f"m{j}": (True, False) for j in range(4)} for k in range(10)
    }
    rho, design_effect, n_eff = intracluster_diagnostics(_validated_clusters(clusters))
    assert (rho, design_effect, n_eff) == (None, None, None)
    stats = cluster_paired_arm_statistics(clusters, bootstrap_resamples=200)
    assert stats.intracluster_rho is None
    assert stats.design_effect is None
    assert stats.effective_sample_size is None
    payload = json.loads(to_canonical_json(stats))
    assert payload["intracluster_rho"] is None  # serialized as null ("NA")
    # Sanity: the same all-+1 dataset still yields a decisive SUCCESS with a
    # degenerate zero-width interval — only the DIAGNOSTIC is NA.
    assert stats.decision == "success"
    # Contrast: zero WITHIN-cluster variance but nonzero between-cluster
    # variance is rho = 1 (identifiable), not NA.
    mixed = {}
    for k in range(10):
        value = k % 2 == 0
        mixed[f"c{k:02d}"] = {f"m{j}": (value, False) for j in range(4)}
    rho_mixed, _, _ = intracluster_diagnostics(_validated_clusters(mixed))
    assert rho_mixed == pytest.approx(1.0)


def test_cluster_bootstrap_widens_under_correlation():
    """Positively clustered data must give a wider cluster CI than unit CI."""
    # 12 clusters x 6 members; within a cluster all members share one state.
    clusters = {}
    for k in range(12):
        state = k % 4  # 0: both, 1: M-only, 2: C-only, 3: neither
        pair = [(True, True), (True, False), (False, True), (False, False)][state]
        clusters[f"c{k:02d}"] = {f"m{j}": pair for j in range(6)}
    resamples = 500
    cluster_stats = cluster_paired_arm_statistics(clusters, bootstrap_resamples=resamples)
    flat_outcomes = {
        f"{cid}|{mid}": pair for cid, members in clusters.items() for mid, pair in members.items()
    }
    unit_stats = paired_arm_statistics(flat_outcomes, bootstrap_resamples=resamples)
    assert cluster_stats.interval_width > unit_stats.interval_width
    assert cluster_stats.intracluster_rho > 0.5
    assert cluster_stats.effective_sample_size < cluster_stats.observation_units / 2


def test_unbalanced_clusters_pooled_ratio_estimator():
    clusters = {
        "big": {f"m{j}": (True, False) for j in range(5)},   # delta_sum +5, size 5
        "small0": {"m0": (False, True)},                      # delta_sum -1, size 1
        "small1": {"m0": (True, True)},                       # delta_sum  0, size 1
    }
    sums = cluster_delta_sums(_validated_clusters(clusters))
    assert sorted(sums) == [(-1, 1), (0, 1), (5, 5)]
    # Resample size 3 over these clusters: pooled mean = sum(delta)/sum(size).
    interval = bootstrap_cluster_difference_interval(sums, resamples=200)
    lo, hi = interval
    assert lo <= 4 / 7 <= hi  # point estimate is (+5 -1 +0)/(5+1+1)
    assert lo >= -1.0 and hi <= 1.0


def test_stats_type_and_frozen_fields():
    clusters = make_clusters(10, 2, hits_m=12, hits_c=6)
    stats = cluster_paired_arm_statistics(clusters, bootstrap_resamples=200)
    assert isinstance(stats, ClusterPairedArmStatistics)
    with pytest.raises(Exception):
        stats.decision = "null"  # frozen dataclass
    assert stats.min_clusters == DEFAULT_MIN_CLUSTERS
    assert math.isfinite(stats.intracluster_rho)

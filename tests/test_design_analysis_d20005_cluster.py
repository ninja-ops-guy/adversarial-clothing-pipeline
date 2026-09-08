"""Tests for the D2-0005 cluster-aware pre-arming design-analysis simulation.

Covers: determinism (byte-identical artifact), generator validation (Delta /
icc / counts), joint-model marginals, intracluster-correlation structure of
the DGP (including the F1-corrected property that the REALIZED pairwise
correlation matches the LABELED icc parameter), probability normalization per
cell, equivalence-up-to-documented-divergence of the simulation's unit-level
path with the frozen preregistered analysis on simulated datasets,
false-success control at Delta <= 0, and coverage sanity at large cluster
counts.
"""

from __future__ import annotations

import json
import math

import pytest

from ruthless_pipeline.certification.paired_arm_statistics import (
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_Z,
    INCONCLUSIVE_WIDTH_MAX,
    paired_arm_statistics,
)
from ruthless_pipeline.certification.cluster_paired_arm_statistics import (
    DEFAULT_MIN_CLUSTERS,
    cluster_paired_arm_statistics,
)
from scripts.design_analysis_d20005_cluster import (
    DATASETS_PER_CELL,
    DECISIONS,
    GRID_BOOTSTRAP_RESAMPLES,
    MEMBERS_PER_CLUSTER,
    SIM_SEED,
    _classify_both_paths,
    draw_clustered_dataset,
    joint_probabilities,
    render_markdown_table,
    run_grid,
    simulate_cell,
    to_canonical_json,
)


def _small_grid(monkeypatch):
    """Shrink the grid so run_grid() stays fast under test."""
    monkeypatch.setattr("scripts.design_analysis_d20005_cluster.GRID_DELTAS", (0.0, 0.2))
    monkeypatch.setattr("scripts.design_analysis_d20005_cluster.GRID_ICCS", (0.0, 0.25))
    monkeypatch.setattr("scripts.design_analysis_d20005_cluster.GRID_CLUSTER_COUNTS", (8,))
    monkeypatch.setattr("scripts.design_analysis_d20005_cluster.MEMBERS_PER_CLUSTER", 2)
    monkeypatch.setattr("scripts.design_analysis_d20005_cluster.SWEEP_MEMBER_COUNTS", (2,))
    monkeypatch.setattr(
        "scripts.design_analysis_d20005_cluster.CONFIRMATION_CLUSTER_COUNTS", (8,)
    )
    monkeypatch.setattr("scripts.design_analysis_d20005_cluster.DATASETS_PER_CELL", 15)
    monkeypatch.setattr("scripts.design_analysis_d20005_cluster.GRID_BOOTSTRAP_RESAMPLES", 100)
    monkeypatch.setattr(
        "scripts.design_analysis_d20005_cluster.DEFAULT_BOOTSTRAP_RESAMPLES", 100
    )


def test_run_grid_is_byte_identical_across_runs(monkeypatch):
    _small_grid(monkeypatch)
    first = to_canonical_json(run_grid())
    second = to_canonical_json(run_grid())
    assert first == second
    assert first.endswith("\n")
    assert json.dumps(json.loads(first), sort_keys=True, separators=(",", ":")) + "\n" == first


def test_run_specs_worker_count_independent():
    """Determinism attestation: the process pool (workers=2) must return
    byte-identical cell results to serial execution (workers=1), with cell
    order preserved."""
    from scripts.design_analysis_d20005_cluster import _run_specs

    specs = [(0.2, 0.25, 8, 2, 100), (0.0, 0.0, 8, 3, 100), (-0.1, 0.5, 8, 2, 100)]
    serial, serial_excluded = _run_specs(specs, workers=1)
    parallel, parallel_excluded = _run_specs(specs, workers=2)
    assert to_canonical_json({"c": serial}) == to_canonical_json({"c": parallel})
    assert serial_excluded == parallel_excluded == []


def test_canonical_json_formatting():
    payload = {"b": 1, "a": {"d": [1, 2], "c": "x"}}
    assert to_canonical_json(payload) == '{"a":{"c":"x","d":[1,2]},"b":1}\n'


def test_generator_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        joint_probabilities(1.5)
    with pytest.raises(ValueError):
        joint_probabilities(float("nan"))
    with pytest.raises(ValueError):
        draw_clustered_dataset(0.9, 0.5, 36, 6, 0)  # rate_c = -0.4: infeasible
    with pytest.raises(ValueError):
        draw_clustered_dataset(0.1, -0.1, 36, 6, 0)
    with pytest.raises(ValueError):
        draw_clustered_dataset(0.1, 1.5, 36, 6, 0)
    with pytest.raises(ValueError):
        draw_clustered_dataset(0.1, 0.5, 0, 6, 0)
    with pytest.raises(ValueError):
        draw_clustered_dataset(0.1, 0.5, 36, 0, 0)
    with pytest.raises(ValueError):
        draw_clustered_dataset(0.1, 0.5, 3.5, 6, 0)
    with pytest.raises(ValueError):
        simulate_cell(0.1, 0.5, 36, 6, datasets=0, resamples=100)
    with pytest.raises(ValueError):
        simulate_cell(0.1, 0.5, 36, 6, datasets=2, resamples=99)


def test_joint_model_marginals_match_delta():
    for delta in (-0.1, 0.0, 0.2, 0.3):
        p_both, p_m_only, p_c_only, p_neither = joint_probabilities(delta)
        assert p_both + p_m_only + p_c_only + p_neither == pytest.approx(1.0)
        assert p_both + p_m_only == pytest.approx(0.5)
        assert p_both + p_c_only == pytest.approx(0.5 - delta)
        assert p_m_only - p_c_only == pytest.approx(delta)


def test_draw_dataset_deterministic_and_shaped():
    first = draw_clustered_dataset(0.2, 0.5, 24, 4, 3, SIM_SEED)
    second = draw_clustered_dataset(0.2, 0.5, 24, 4, 3, SIM_SEED)
    assert first == second
    assert len(first) == 24
    assert all(len(members) == 4 for members in first.values())
    other = draw_clustered_dataset(0.2, 0.5, 24, 4, 4, SIM_SEED)
    assert other != first


def test_intracluster_correlation_structure():
    """At icc = 1 all members of a cluster share one joint state; at icc = 0
    the within-cluster agreement rate matches independent pairing."""
    perfect = draw_clustered_dataset(0.2, 1.0, 24, 6, 0)
    for members in perfect.values():
        assert len(set(members.values())) == 1
    # icc = 0: expected agreement between two independent draws under the
    # symmetric joint model at Delta = 0.2 (p_M = 0.5, p_C = 0.3).
    p_both, p_m_only, p_c_only, p_neither = joint_probabilities(0.2)
    expected_agree = p_both**2 + p_m_only**2 + p_c_only**2 + p_neither**2
    independent = draw_clustered_dataset(0.2, 0.0, 60, 8, 0)
    agree = total = 0
    for members in independent.values():
        states = list(members.values())
        for i in range(len(states)):
            for j in range(i + 1, len(states)):
                total += 1
                agree += states[i] == states[j]
    assert agree / total == pytest.approx(expected_agree, abs=0.05)


def _mean_pairwise_delta_corr(dataset: dict) -> float:
    """Empirical Pearson correlation of member deltas over all intra-cluster
    pairs of one drawn dataset (member delta = arm_m - arm_c in {-1,0,+1})."""
    pairs = []
    for members in dataset.values():
        deltas = [(1 if m else 0) - (1 if c else 0) for m, c in members.values()]
        for i in range(len(deltas)):
            for j in range(i + 1, len(deltas)):
                pairs.append((deltas[i], deltas[j]))
    n = len(pairs)
    sx = sum(p[0] for p in pairs)
    sy = sum(p[1] for p in pairs)
    sxx = sum(p[0] * p[0] for p in pairs)
    syy = sum(p[1] * p[1] for p in pairs)
    sxy = sum(p[0] * p[1] for p in pairs)
    cov = sxy / n - (sx / n) * (sy / n)
    var_x = sxx / n - (sx / n) ** 2
    var_y = syy / n - (sy / n) ** 2
    if var_x <= 0 or var_y <= 0:
        return float("nan")
    return cov / math.sqrt(var_x * var_y)


def test_realized_icc_matches_labeled_parameter():
    """Finding F1: the labeled parameter of the corrected DGP must BE the
    realized intracluster correlation. Measure the empirical pairwise
    correlation of member deltas over many clusters and assert it matches the
    labeled icc within tolerance at several grid points."""
    for icc in (0.0, 0.1, 0.25, 0.5, 0.7):
        corrs = []
        for dataset_index in range(12):
            dataset = draw_clustered_dataset(0.0, icc, 60, 6, dataset_index)
            value = _mean_pairwise_delta_corr(dataset)
            if not math.isnan(value):
                corrs.append(value)
        realized = sum(corrs) / len(corrs)
        assert realized == pytest.approx(icc, abs=0.05), (icc, realized)


def test_probabilities_sum_to_one_per_cell():
    for delta in (-0.1, 0.0, 0.3):
        for rho in (0.0, 0.8):
            cell = simulate_cell(delta, rho, 24, 2, datasets=12, resamples=100)
            assert cell["datasets"] == 12
            for path in ("cluster", "unit"):
                block = cell["analyses"][path]
                total = (
                    block["p_success"]
                    + block["p_null"]
                    + block["p_negative"]
                    + block["p_inconclusive"]
                )
                assert total == pytest.approx(1.0)
                assert 0.0 <= block["coverage"] <= 1.0
    assert set(DECISIONS) == {"success", "null", "negative", "inconclusive"}


def test_cell_simulation_deterministic():
    first = simulate_cell(0.1, 0.5, 24, 2, datasets=10, resamples=100)
    second = simulate_cell(0.1, 0.5, 24, 2, datasets=10, resamples=100)
    assert first == second


def test_simulation_uses_real_analysis_paths():
    """The cluster path must BE cluster_paired_arm_statistics, and the unit
    path must classify exactly as the frozen paired_arm_statistics does. The
    interval may differ from the frozen path ONLY by the documented F8
    lower-index correction (lower bound at most one order statistic lower;
    upper bound identical)."""
    for dataset_index in range(4):
        for delta, icc in ((0.2, 0.25), (0.0, 0.1), (-0.1, 0.7)):
            dataset = draw_clustered_dataset(delta, icc, 24, 3, dataset_index)
            both = _classify_both_paths(dataset, 200)
            reference_cluster = cluster_paired_arm_statistics(
                dataset, bootstrap_resamples=200, min_clusters=DEFAULT_MIN_CLUSTERS
            )
            assert both["cluster"] == reference_cluster
            flat_outcomes = {
                f"{cid}|{mid}": pair
                for cid, members in dataset.items()
                for mid, pair in members.items()
            }
            reference_unit = paired_arm_statistics(
                flat_outcomes,
                z=DEFAULT_Z,
                bootstrap_resamples=200,
                bootstrap_seed=DEFAULT_BOOTSTRAP_SEED,
                width_max=INCONCLUSIVE_WIDTH_MAX,
            )
            sim_lo, sim_hi = both["unit"].risk_difference_interval
            ref_lo, ref_hi = reference_unit.risk_difference_interval
            assert sim_hi == ref_hi  # upper index unchanged by the F8 fix
            assert sim_lo <= ref_lo  # corrected lower bound never higher
            assert both["unit"].decision == reference_unit.decision


def test_false_success_control_at_null_and_reversed():
    """P(SUCCESS) at Delta_true <= 0 must stay near the 97.5% one-sided level
    for the CLUSTER path, even under strong clustering. (The unit path is
    known-invalid under icc > 0 — quantifying that failure is the point of
    the study, so no bound is asserted for it here.)"""
    for delta in (0.0, -0.1):
        cell = simulate_cell(delta, 0.5, 36, 4, datasets=100, resamples=200)
        assert cell["analyses"]["cluster"]["p_success"] <= 0.08, delta


def test_cluster_path_dominates_unit_path_under_correlation():
    """Under rho > 0 the unit path must report systematically narrower CIs
    (it understates clustered variance); the cluster path must not."""
    cell = simulate_cell(0.2, 0.8, 36, 6, datasets=40, resamples=200)
    cluster = cell["analyses"]["cluster"]
    unit = cell["analyses"]["unit"]
    assert unit["mean_interval_width"] < cluster["mean_interval_width"]
    assert unit["coverage"] <= cluster["coverage"] + 1e-9


def test_coverage_sanity_at_large_cluster_count():
    """At large K the cluster path's CI must cover the true Delta at roughly
    the nominal 95% level (loose Monte Carlo bounds)."""
    cell = simulate_cell(0.2, 0.5, 144, 2, datasets=60, resamples=200)
    coverage = cell["analyses"]["cluster"]["coverage"]
    assert coverage >= 0.80


def test_grid_defaults_are_documented_constants():
    assert SIM_SEED == 20261209
    assert DATASETS_PER_CELL >= 200
    assert MEMBERS_PER_CLUSTER >= 2
    assert 100 <= GRID_BOOTSTRAP_RESAMPLES <= 10000
    assert DEFAULT_MIN_CLUSTERS >= 8


def test_render_markdown_table_contains_blocks(monkeypatch):
    _small_grid(monkeypatch)
    payload = run_grid()
    table = render_markdown_table(payload)
    assert "Main grid" in table
    assert "Members-per-cluster sweep" in table
    assert "Confirmation block" in table
    assert "+0.2" in table
    assert "CLUSTER P(SUCCESS)" in table

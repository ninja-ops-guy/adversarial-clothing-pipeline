"""Tests for the D2-0005 pre-arming design-analysis simulation driver.

Covers: determinism (same seeds -> byte-identical results artifact),
generator validation (rejects invalid Delta / n / structure), probability
normalization per cell, and — critically — that the simulation classifies
through the PREREGISTERED decision path (paired_arm_statistics), not a
reimplementation of the decision regions.
"""

from __future__ import annotations

import json

import pytest

from ruthless_pipeline.certification.paired_arm_statistics import (
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_Z,
    INCONCLUSIVE_WIDTH_MAX,
    bootstrap_paired_difference_interval,
    classify_decision,
    paired_arm_statistics,
)
from scripts.design_analysis_d20005 import (
    DATASETS_PER_CELL,
    DECISIONS,
    GRID_BOOTSTRAP_RESAMPLES,
    SIM_SEED,
    _deltas_from_counts,
    _IntervalCache,
    draw_dataset,
    joint_probabilities,
    render_markdown_table,
    run_grid,
    simulate_cell,
    to_canonical_json,
)


def _small_grid(monkeypatch):
    """Shrink the grid so run_grid() stays fast under test."""
    monkeypatch.setattr("scripts.design_analysis_d20005.GRID_DELTAS", (0.0, 0.2))
    monkeypatch.setattr("scripts.design_analysis_d20005.GRID_STRUCTURES", ("symmetric",))
    monkeypatch.setattr("scripts.design_analysis_d20005.GRID_UNIT_COUNTS", (36,))
    monkeypatch.setattr("scripts.design_analysis_d20005.CONFIRMATION_STRUCTURES", ("symmetric",))
    monkeypatch.setattr("scripts.design_analysis_d20005.CONFIRMATION_UNIT_COUNTS", (36,))
    monkeypatch.setattr("scripts.design_analysis_d20005.DATASETS_PER_CELL", 20)
    monkeypatch.setattr("scripts.design_analysis_d20005.GRID_BOOTSTRAP_RESAMPLES", 100)
    monkeypatch.setattr("scripts.design_analysis_d20005.DEFAULT_BOOTSTRAP_RESAMPLES", 100)


def test_run_grid_is_byte_identical_across_runs(monkeypatch):
    _small_grid(monkeypatch)
    first = to_canonical_json(run_grid())
    second = to_canonical_json(run_grid())
    assert first == second
    assert first.endswith("\n")
    # Canonical JSON: sorted keys and compact separators round-trip exactly.
    assert json.dumps(json.loads(first), sort_keys=True, separators=(",", ":")) + "\n" == first


def test_canonical_json_formatting():
    payload = {"b": 1, "a": {"d": [1, 2], "c": "x"}}
    text = to_canonical_json(payload)
    assert text == '{"a":{"c":"x","d":[1,2]},"b":1}\n'


def test_generator_rejects_invalid_delta():
    with pytest.raises(ValueError):
        joint_probabilities(1.5, "symmetric")
    with pytest.raises(ValueError):
        joint_probabilities(float("nan"), "symmetric")
    with pytest.raises(ValueError):
        draw_dataset(0.9, "sparse", 36, 0)  # rate_c = 0.3 - 0.9 < 0: infeasible
    with pytest.raises(ValueError):
        simulate_cell(0.5, "sparse", 36, datasets=2, resamples=100)  # infeasible cell


def test_generator_rejects_invalid_structure_and_n():
    with pytest.raises(ValueError):
        joint_probabilities(0.1, "unknown-structure")
    with pytest.raises(ValueError):
        draw_dataset(0.1, "symmetric", 0, 0)
    with pytest.raises(ValueError):
        draw_dataset(0.1, "symmetric", -5, 0)
    with pytest.raises(ValueError):
        draw_dataset(0.1, "symmetric", 3.5, 0)


def test_joint_model_marginals_match_delta():
    for structure in ("symmetric", "m_dominated", "sparse"):
        for delta in (-0.1, 0.0, 0.2):
            model = joint_probabilities(delta, structure)
            total = model.p_both + model.p_m_only + model.p_c_only + model.p_neither
            assert total == pytest.approx(1.0)
            assert model.p_both + model.p_m_only == pytest.approx(model.rate_m)
            assert model.p_both + model.p_c_only == pytest.approx(model.rate_c)
            assert model.rate_m - model.rate_c == pytest.approx(delta)
            assert model.p_m_only - model.p_c_only == pytest.approx(delta)


def test_m_dominated_structure_is_nested():
    model = joint_probabilities(0.2, "m_dominated")
    assert model.p_c_only == pytest.approx(0.0)
    model = joint_probabilities(-0.1, "m_dominated")
    assert model.p_m_only == pytest.approx(0.0)


def test_draw_dataset_deterministic_and_counts_sum():
    first = draw_dataset(0.2, "symmetric", 72, 3, SIM_SEED)
    second = draw_dataset(0.2, "symmetric", 72, 3, SIM_SEED)
    assert first == second
    assert sum(first) == 72
    other = draw_dataset(0.2, "symmetric", 72, 4, SIM_SEED)
    assert other != first or draw_dataset(0.2, "symmetric", 72, 5, SIM_SEED) != first


def test_probabilities_sum_to_one_per_cell():
    for delta in (-0.1, 0.0, 0.3):
        for structure in ("symmetric", "m_dominated", "sparse"):
            cell = simulate_cell(delta, structure, 36, datasets=25, resamples=100)
            total = (
                cell["p_success"] + cell["p_null"] + cell["p_negative"] + cell["p_inconclusive"]
            )
            assert total == pytest.approx(1.0)
            assert cell["datasets"] == 25
            assert set(DECISIONS) == {"success", "null", "negative", "inconclusive"}


def test_cell_simulation_deterministic():
    first = simulate_cell(0.1, "symmetric", 36, datasets=20, resamples=100)
    second = simulate_cell(0.1, "symmetric", 36, datasets=20, resamples=100)
    assert first == second


def test_simulation_uses_preregistered_decision_path():
    """Every simulated dataset must classify exactly as paired_arm_statistics does.

    The driver must not reimplement the preregistered decision regions: the
    interval it classifies is the module's bootstrap interval over the same
    deltas, and the decision matches paired_arm_statistics(...).decision with
    preregistered defaults (z, bootstrap seed, width gate).
    """
    cache = _IntervalCache()
    for dataset_index in range(5):
        for delta, structure in ((0.2, "symmetric"), (0.3, "m_dominated"), (0.0, "sparse")):
            n_m_only, n_concordant, n_c_only = draw_dataset(delta, structure, 36, dataset_index)
            deltas = _deltas_from_counts(36, n_m_only, n_concordant, n_c_only)
            interval = cache.interval(36, n_m_only, n_concordant, n_c_only, 100)
            reference_interval = bootstrap_paired_difference_interval(
                deltas, resamples=100, z=DEFAULT_Z, seed=DEFAULT_BOOTSTRAP_SEED
            )
            assert interval == reference_interval
            outcomes = {
                f"sim-model|tform-{i:03d}|fx0": (deltas[i] == 1, deltas[i] == -1)
                for i in range(36)
            }
            reference = paired_arm_statistics(
                outcomes,
                z=DEFAULT_Z,
                bootstrap_resamples=100,
                bootstrap_seed=DEFAULT_BOOTSTRAP_SEED,
                width_max=INCONCLUSIVE_WIDTH_MAX,
            )
            decision, _ = classify_decision(interval, width_max=INCONCLUSIVE_WIDTH_MAX)
            assert decision == reference.decision
            assert reference.observation_units == 36
            assert reference.discordant_m_only == n_m_only
            assert reference.discordant_c_only == n_c_only


def test_decision_regions_are_preregistered_values():
    # The driver classifies with the module's classify_decision at the
    # preregistered width gate; spot-check the frozen regions directly.
    assert classify_decision((0.05, 0.15), width_max=INCONCLUSIVE_WIDTH_MAX) == ("success", False)
    assert classify_decision((-0.15, -0.05), width_max=INCONCLUSIVE_WIDTH_MAX) == (
        "negative",
        False,
    )
    assert classify_decision((-0.05, 0.10), width_max=INCONCLUSIVE_WIDTH_MAX) == ("null", False)
    assert classify_decision((0.05, 0.30), width_max=INCONCLUSIVE_WIDTH_MAX) == (
        "inconclusive",
        True,
    )


def test_grid_defaults_are_documented_constants():
    assert SIM_SEED == 20261204
    assert DATASETS_PER_CELL >= 500
    assert 100 <= GRID_BOOTSTRAP_RESAMPLES <= 10000


def test_render_markdown_table_contains_cells(monkeypatch):
    _small_grid(monkeypatch)
    payload = run_grid()
    table = render_markdown_table(payload)
    assert "| Delta_true | discordance | n |" in table
    assert "+0.2" in table
    assert "Confirmation block" in table

"""SW-15 tests: simulator benchmark & sensitivity harness (synthetic only)."""
from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.future_evidence.benchmark import (
    BenchmarkConfig,
    TickCounter,
    benchmark_table,
    run_config_benchmark,
)
from ruthless_pipeline.future_evidence.errors import (
    FutureEvidenceError,
    ReservedFieldError,
)


def stable_sim(params, seed, ticker):
    """Deterministic synthetic 'deformation': smooth in parameters."""
    rng = np.random.default_rng(seed)
    base = rng.standard_normal(8)
    ticker.tick(10)
    return base * params["stiffness"] + params["damping"]


def unstable_sim(params, seed, ticker):
    """Synthetic 'physics' config that explodes for large stiffness."""
    ticker.tick(5)
    k = params["stiffness"]
    if k > 1.0:
        return np.array([np.inf, np.nan])
    return np.array([k, params["damping"]])


def cfg(config_id="CFG-A", family="deformation", stiffness=0.5):
    return BenchmarkConfig(
        config_id=config_id,
        family=family,
        parameters={"stiffness": stiffness, "damping": 0.1},
        seed=42,
    )


def test_benchmark_row_deterministic_and_computational_only():
    row = run_config_benchmark(cfg(), stable_sim)
    assert row["deterministic"] is True
    assert row["numerically_stable"] is True
    assert row["runtime_units"] == 10
    assert row["memory_bytes"] == 64
    assert row["evidence_class"] == "synthetic_pipeline_validation_only"
    assert row["empirical_validity"] == "unassessed_no_measured_channel"
    assert row["measured_predictive_validity"] is None
    assert row["row_id"].startswith("RAC-SBEN-")


def test_table_is_deterministic():
    rows = [
        run_config_benchmark(cfg("CFG-A"), stable_sim),
        run_config_benchmark(cfg("CFG-B"), stable_sim),
    ]
    t1 = benchmark_table(rows)
    t2 = benchmark_table(list(reversed(rows)))
    assert t1 == t2
    assert t1["ranks_physical_fidelity"] is False
    assert t1["ranking_basis"] == "computational_quality_only"


def test_identifies_unstable_region():
    row = run_config_benchmark(cfg("CFG-UNSTABLE", "physics", 2.0), unstable_sim)
    assert row["numerically_stable"] is False
    table = benchmark_table([row])
    assert table["unstable_config_ids"] == ["CFG-UNSTABLE"]


def test_sensitivity_finite_difference():
    row = run_config_benchmark(cfg(), stable_sim)
    assert row["output_sensitivity"]["damping"] == pytest.approx(1.0)
    assert row["output_sensitivity"]["stiffness"] > 0.0


def test_reserved_measured_field_refused():
    bad = BenchmarkConfig(
        config_id="CFG-X",
        family="deformation",
        parameters={"stiffness": 0.5, "damping": 0.1},
        seed=1,
        measured_predictive_validity={"metric_name": "m", "value": 0.9},
    )
    with pytest.raises(ReservedFieldError):
        run_config_benchmark(bad, stable_sim)


def test_unknown_family_refused():
    bad = BenchmarkConfig(
        config_id="CFG-X",
        family="not-a-family",
        parameters={"a": 1.0},
        seed=1,
    )
    with pytest.raises(FutureEvidenceError):
        run_config_benchmark(bad, stable_sim)


def test_nondeterminism_detected():
    counter = {"n": 0}

    def noisy(params, seed, ticker):
        counter["n"] += 1
        ticker.tick(3)
        return np.array([params["stiffness"] + counter["n"]])

    row = run_config_benchmark(cfg("CFG-NOISY"), noisy)
    assert row["deterministic"] is False
    assert row["output_sha256"] is None


def test_tick_counter_rejects_nonpositive():
    with pytest.raises(FutureEvidenceError):
        TickCounter().tick(0)

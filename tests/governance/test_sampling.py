"""Tests for Governance Pass 6 sampling and diagnostics."""
from __future__ import annotations

import pytest

from ruthless_pipeline.governance.sampling import (
    BackendTelemetry,
    DiagnosticPolicy,
    RepresentativenessState,
    SamplerLane,
    SamplingGovernanceError,
    SamplingRequest,
    SamplingResult,
    diagnose,
    require_confirmatory_eligible,
    select_backend,
)


def request(**overrides):
    values = dict(
        target_distribution="uniform_over_feasible_projection",
        sample_count=3,
        seed=7,
        semantic_projection=("x",),
        material_strata=("rare",),
    )
    values.update(overrides)
    return SamplingRequest(**values)


def result(**overrides):
    values = dict(
        lane=SamplerLane.EXACT,
        samples=({"x": 0}, {"x": 1}, {"x": 2}),
        target_distribution="uniform_over_feasible_projection",
        achieved_distribution="exact_uniform",
        backend_version="fixture/1",
    )
    values.update(overrides)
    return SamplingResult(**values)


def policy(**overrides):
    values = dict(
        version="diag/1",
        minimum_material_strata_coverage=1.0,
        maximum_duplicate_fraction=0.34,
        minimum_effective_sample_size=2.0,
        minimum_support_coverage=0.9,
    )
    values.update(overrides)
    return DiagnosticPolicy(**values)


def test_samples_cannot_contain_auxiliary_variables():
    bad = result(samples=({"x": 0, "aux": 1}, {"x": 1}, {"x": 2}))
    with pytest.raises(SamplingGovernanceError, match="non-semantic"):
        bad.validate(request())


def test_exact_small_fixture_selected_by_versioned_policy():
    selected = select_backend(
        BackendTelemetry(variable_count=8, constraint_count=4, independent_support_size=4),
        selector_version="selector/1",
        exact_max_variables=10,
        hashing_max_support=100,
    )
    assert selected.selected is SamplerLane.EXACT
    assert selected.selector_version == "selector/1"


def test_selector_thresholds_are_inputs_not_constants():
    telemetry = BackendTelemetry(variable_count=20, constraint_count=5, independent_support_size=5)
    one = select_backend(telemetry, selector_version="selector/a", exact_max_variables=25, hashing_max_support=10)
    two = select_backend(telemetry, selector_version="selector/b", exact_max_variables=10, hashing_max_support=10)
    assert one.selected is SamplerLane.EXACT
    assert two.selected is SamplerLane.PROJECTED_HASHING


def test_diagnostics_retain_model_count_uncertainty():
    bundle = diagnose(
        request(), result(), policy=policy(), observed_material_strata=("rare",),
        support_coverage=1.0, approximate_model_count=100.0,
        approximate_model_count_interval=(80.0, 125.0),
    )
    assert bundle.approximate_model_count_interval == (80.0, 125.0)
    assert bundle.state is RepresentativenessState.ELIGIBLE


def test_missing_material_stratum_blocks_confirmatory_inference():
    bundle = diagnose(request(), result(), policy=policy(), observed_material_strata=(), support_coverage=1.0)
    assert bundle.state is RepresentativenessState.LOW_REPRESENTATIVENESS
    assert "MATERIAL_STRATA_COVERAGE" in bundle.reasons
    with pytest.raises(SamplingGovernanceError, match="confirmatory inference denied"):
        require_confirmatory_eligible(bundle)


def test_duplicate_concentration_is_detected():
    repeated = result(samples=({"x": 1}, {"x": 1}, {"x": 1}))
    bundle = diagnose(request(), repeated, policy=policy(), observed_material_strata=("rare",), support_coverage=1.0)
    assert "DUPLICATE_CONCENTRATION" in bundle.reasons


def test_low_ess_from_importance_weights_is_detected():
    weighted = result(weights=(1.0, 0.0, 0.0))
    bundle = diagnose(request(), weighted, policy=policy(), observed_material_strata=("rare",), support_coverage=1.0)
    assert "LOW_ESS" in bundle.reasons


def test_degraded_backend_never_silently_becomes_confirmatory():
    degraded = result(lane=SamplerLane.DEGRADED)
    bundle = diagnose(request(), degraded, policy=policy(), observed_material_strata=("rare",), support_coverage=1.0)
    assert bundle.state is RepresentativenessState.LOW_REPRESENTATIVENESS
    assert "DEGRADED_BACKEND" in bundle.reasons


def test_invalid_uncertainty_interval_fails_closed():
    with pytest.raises(SamplingGovernanceError, match="model-count interval"):
        diagnose(
            request(), result(), policy=policy(), observed_material_strata=("rare",), support_coverage=1.0,
            approximate_model_count=100.0, approximate_model_count_interval=(120.0, 80.0),
        )

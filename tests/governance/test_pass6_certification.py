"""Pass 6 certification tests for projected sampling, routing, and diagnostics."""
from __future__ import annotations

import pytest

from ruthless_pipeline.governance.sampling import (
    BackendTelemetry,
    DiagnosticPolicy,
    ExactProjectedPopulationBackend,
    PopulationIdentity,
    RepresentativenessState,
    SamplerLane,
    SamplingGovernanceError,
    SamplingRequest,
    SamplingResult,
    build_sampling_manifest,
    diagnose,
    require_confirmatory_eligible,
)
from ruthless_pipeline.governance.sampling_diagnostics import (
    exact_distribution_diagnostics,
    repeated_seed_instability,
)
from ruthless_pipeline.governance.sampling_routing import (
    EmpiricalLaneModel,
    select_backend_empirical,
)
from ruthless_pipeline.governance.validators import validate_manifest


SEMANTIC_HASH = "a" * 64


def population_identity(**overrides):
    values = dict(
        constraint_set_id="RAC-CS-PASS6-001",
        constraint_version="1.0.0",
        semantic_hash=SEMANTIC_HASH,
        projection_version="genome/1",
        semantic_projection=("x", "y"),
        independent_support=("x",),
    )
    values.update(overrides)
    return PopulationIdentity(**values)


def request(**overrides):
    values = dict(
        target_distribution="uniform_over_feasible_projection",
        sample_count=4,
        seed=17,
        semantic_projection=("x", "y"),
        population=population_identity(),
    )
    values.update(overrides)
    return SamplingRequest(**values)


def exact_population():
    return (
        {"x": 0, "y": 0},
        {"x": 0, "y": 1},
        {"x": 1, "y": 0},
        {"x": 1, "y": 1},
    )


def policy(**overrides):
    values = dict(
        version="diag/pass6-1",
        minimum_material_strata_coverage=1.0,
        maximum_duplicate_fraction=0.25,
        minimum_effective_sample_size=2.0,
        minimum_support_coverage=0.9,
        maximum_total_variation=0.20,
        maximum_marginal_error=0.20,
        maximum_pairwise_error=0.20,
    )
    values.update(overrides)
    return DiagnosticPolicy(**values)


def manual_result(samples, **overrides):
    values = dict(
        lane=SamplerLane.PROJECTED_HASHING,
        samples=tuple(samples),
        target_distribution="uniform_over_feasible_projection",
        achieved_distribution="estimated_near_uniform",
        backend_id="fixture.hashing",
        backend_version="1.0",
    )
    values.update(overrides)
    return SamplingResult(**values)


def test_population_identity_keeps_full_projection_distinct_from_independent_support():
    identity = population_identity()
    identity.validate()
    assert identity.semantic_projection == ("x", "y")
    assert identity.independent_support == ("x",)
    assert len(identity.identity_hash) == 64


def test_independent_support_cannot_redefine_scientific_population():
    bad = population_identity(independent_support=("x", "aux"))
    with pytest.raises(SamplingGovernanceError, match="subset of the full"):
        bad.validate()


def test_request_projection_must_match_population_projection_exactly():
    bad = request(semantic_projection=("x",))
    with pytest.raises(SamplingGovernanceError, match="full scientific population"):
        bad.validate()


def test_result_must_contain_every_semantic_variable_and_no_auxiliary_variables():
    missing = manual_result(
        ({"x": 0}, {"x": 0}, {"x": 1}, {"x": 1})
    )
    with pytest.raises(SamplingGovernanceError, match="missing semantic"):
        missing.validate(request())

    extra = manual_result(
        (
            {"x": 0, "y": 0, "aux": 1},
            {"x": 0, "y": 1},
            {"x": 1, "y": 0},
            {"x": 1, "y": 1},
        )
    )
    with pytest.raises(SamplingGovernanceError, match="non-semantic"):
        extra.validate(request())


def test_first_sat_witness_is_explicitly_rejected_as_sampling_distribution():
    bad = manual_result(exact_population(), achieved_distribution="first_sat_witness")
    with pytest.raises(SamplingGovernanceError, match="not scientific samples"):
        bad.validate(request())


def test_exact_backend_samples_known_projected_population_without_branch_bias():
    backend = ExactProjectedPopulationBackend(exact_population(), version="1.2")
    sampled = backend.sample(request())
    assert sampled.lane is SamplerLane.EXACT
    assert sampled.population_size == 4
    assert {tuple(sorted(item.items())) for item in sampled.samples} == {
        tuple(sorted(item.items())) for item in exact_population()
    }
    assert sampled.achieved_distribution == "exact_uniform_without_replacement"


def test_exact_backend_is_seed_deterministic_without_treating_order_as_population():
    backend = ExactProjectedPopulationBackend(exact_population())
    one = backend.sample(request(sample_count=2, seed=99))
    two = backend.sample(request(sample_count=2, seed=99))
    assert one.samples == two.samples


def test_exact_calibration_matches_known_population_when_all_assignments_sampled():
    backend = ExactProjectedPopulationBackend(exact_population())
    sampled = backend.sample(request())
    metrics = exact_distribution_diagnostics(request(), sampled, exact_population())
    assert metrics.total_variation == pytest.approx(0.0)
    assert metrics.maximum_marginal_error == pytest.approx(0.0)
    assert metrics.maximum_pairwise_error == pytest.approx(0.0)


def test_biased_sample_fails_global_and_dependency_diagnostics():
    biased = manual_result(
        (
            {"x": 0, "y": 0},
            {"x": 0, "y": 0},
            {"x": 0, "y": 0},
            {"x": 0, "y": 0},
        )
    )
    metrics = exact_distribution_diagnostics(request(), biased, exact_population())
    bundle = diagnose(
        request(),
        biased,
        policy=policy(),
        observed_material_strata=(),
        support_coverage=1.0,
        calibration=metrics,
    )
    assert bundle.state is RepresentativenessState.LOW_REPRESENTATIVENESS
    assert "GLOBAL_DISTRIBUTION_MISMATCH" in bundle.reasons
    assert "MARGINAL_DISTRIBUTION_MISMATCH" in bundle.reasons
    assert "PAIRWISE_DISTRIBUTION_MISMATCH" in bundle.reasons
    assert bundle.diagnostic_debt > 0


def test_unweighted_independent_draws_do_not_invent_an_ess_metric():
    backend = ExactProjectedPopulationBackend(exact_population())
    sampled = backend.sample(request())
    metrics = exact_distribution_diagnostics(request(), sampled, exact_population())
    bundle = diagnose(
        request(),
        sampled,
        policy=policy(),
        observed_material_strata=(),
        support_coverage=1.0,
        calibration=metrics,
    )
    assert bundle.effective_sample_size is None
    assert "LOW_ESS" not in bundle.reasons


def test_correlated_sampler_without_ess_is_fail_closed():
    correlated = manual_result(exact_population(), correlated_draws=True)
    metrics = exact_distribution_diagnostics(request(), correlated, exact_population())
    bundle = diagnose(
        request(),
        correlated,
        policy=policy(),
        observed_material_strata=(),
        support_coverage=1.0,
        calibration=metrics,
    )
    assert "MISSING_ESS_FOR_CORRELATED_SAMPLER" in bundle.reasons


def test_weighted_sampler_uses_weight_based_ess():
    weighted = manual_result(
        exact_population(),
        weights=(1.0, 0.0, 0.0, 0.0),
    )
    metrics = exact_distribution_diagnostics(request(), weighted, exact_population())
    bundle = diagnose(
        request(),
        weighted,
        policy=policy(),
        observed_material_strata=(),
        support_coverage=1.0,
        calibration=metrics,
    )
    assert bundle.effective_sample_size == pytest.approx(1.0)
    assert "LOW_ESS" in bundle.reasons


def test_repeated_seed_instability_is_measured_on_full_projected_distribution():
    left = manual_result(
        (
            {"x": 0, "y": 0},
            {"x": 0, "y": 0},
            {"x": 0, "y": 0},
            {"x": 0, "y": 0},
        )
    )
    right = manual_result(
        (
            {"x": 1, "y": 1},
            {"x": 1, "y": 1},
            {"x": 1, "y": 1},
            {"x": 1, "y": 1},
        )
    )
    assert repeated_seed_instability(request(), (left, right)) == pytest.approx(1.0)


def test_seed_instability_threshold_can_refuse_confirmatory_release():
    unbiased = manual_result(exact_population())
    metrics = exact_distribution_diagnostics(request(), unbiased, exact_population())
    bundle = diagnose(
        request(),
        unbiased,
        policy=policy(maximum_seed_instability=0.10),
        observed_material_strata=(),
        support_coverage=1.0,
        calibration=metrics,
        repeated_seed_instability=0.75,
    )
    assert "REPEATED_SEED_INSTABILITY" in bundle.reasons
    with pytest.raises(SamplingGovernanceError, match="confirmatory inference denied"):
        require_confirmatory_eligible(bundle)


def test_degraded_lane_always_carries_confirmatory_debt():
    degraded = manual_result(exact_population(), lane=SamplerLane.DEGRADED)
    metrics = exact_distribution_diagnostics(request(), degraded, exact_population())
    bundle = diagnose(
        request(),
        degraded,
        policy=policy(),
        observed_material_strata=(),
        support_coverage=1.0,
        calibration=metrics,
    )
    assert "DEGRADED_BACKEND" in bundle.reasons
    assert dict(bundle.debt_components)["DEGRADED_BACKEND"] == pytest.approx(1.0)


def test_model_count_and_constraint_sensitivity_uncertainty_survive_bundle():
    sampled = manual_result(exact_population())
    metrics = exact_distribution_diagnostics(request(), sampled, exact_population())
    bundle = diagnose(
        request(),
        sampled,
        policy=policy(),
        observed_material_strata=(),
        support_coverage=1.0,
        calibration=metrics,
        approximate_model_count=100.0,
        approximate_model_count_interval=(80.0, 125.0),
        constraint_sensitivity={"seam_safe": 0.12},
        constraint_sensitivity_intervals={"seam_safe": (0.08, 0.17)},
    )
    assert bundle.approximate_model_count_interval == (80.0, 125.0)
    assert bundle.constraint_sensitivity_intervals["seam_safe"] == (0.08, 0.17)


def test_sampling_manifest_binds_population_sampler_and_diagnostic_policy():
    backend = ExactProjectedPopulationBackend(exact_population(), version="1.2")
    sampled = backend.sample(request())
    manifest = build_sampling_manifest(
        sampling_id="RAC-SAMP-PASS6-001",
        experiment_id="RAC-EXP-PASS6-001",
        request=request(),
        result=sampled,
        diagnostic_policy=policy(),
    )
    assert manifest["constraint_set_id"] == "RAC-CS-PASS6-001"
    assert manifest["semantic_hash"] == SEMANTIC_HASH
    assert manifest["semantic_projection"] == ["x", "y"]
    assert manifest["independent_support"] == ["x"]
    assert manifest["sampler_lane"] == SamplerLane.EXACT.value
    assert manifest["target_distribution"] == "uniform_over_feasible_projection"
    assert manifest["achieved_distribution"] == "exact_uniform_without_replacement"
    assert manifest["diagnostic_threshold_hash"] == policy().threshold_hash
    assert validate_manifest("sampling_manifest", manifest) is True


def test_diagnostic_policy_change_changes_manifest_binding():
    backend = ExactProjectedPopulationBackend(exact_population())
    sampled = backend.sample(request())
    first_policy = policy(maximum_total_variation=0.20)
    second_policy = policy(maximum_total_variation=0.10)
    first = build_sampling_manifest(
        sampling_id="RAC-SAMP-PASS6-001",
        experiment_id="RAC-EXP-PASS6-001",
        request=request(),
        result=sampled,
        diagnostic_policy=first_policy,
    )
    second = build_sampling_manifest(
        sampling_id="RAC-SAMP-PASS6-001",
        experiment_id="RAC-EXP-PASS6-001",
        request=request(),
        result=sampled,
        diagnostic_policy=second_policy,
    )
    assert first["diagnostic_threshold_hash"] != second["diagnostic_threshold_hash"]


def test_empirical_router_uses_frozen_calibrated_coefficients_not_width_constants():
    telemetry = BackendTelemetry(
        variable_count=100,
        constraint_count=200,
        independent_support_size=40,
        treewidth_estimate=75,
        graph_density=0.2,
    )
    models = (
        EmpiricalLaneModel(
            lane=SamplerLane.EXACT,
            model_version="fit/1",
            intercept=5.0,
            coefficients={"variable_count": 0.01},
            confidence=0.9,
            training_observations=50,
        ),
        EmpiricalLaneModel(
            lane=SamplerLane.PROJECTED_HASHING,
            model_version="fit/1",
            intercept=1.0,
            coefficients={"independent_support_size": 0.02},
            confidence=0.8,
            training_observations=120,
        ),
        EmpiricalLaneModel(
            lane=SamplerLane.STRATIFIED,
            model_version="fit/1",
            intercept=4.0,
            coefficients={"treewidth_estimate": 0.01},
            confidence=0.7,
            training_observations=40,
        ),
    )
    selected = select_backend_empirical(
        telemetry,
        selector_version="router/1",
        models=models,
    )
    assert selected.selected is SamplerLane.PROJECTED_HASHING
    assert selected.selection_basis == "frozen_empirical_cost_model"
    assert selected.evidence_count == 120
    assert (
        selected.lane_scores[SamplerLane.PROJECTED_HASHING.value]
        < selected.lane_scores[SamplerLane.EXACT.value]
    )


def test_empirical_router_rejects_unregistered_features():
    model = EmpiricalLaneModel(
        lane=SamplerLane.EXACT,
        model_version="fit/1",
        intercept=1.0,
        coefficients={"adversarial_efficacy": 1.0},
        confidence=0.8,
        training_observations=10,
    )
    with pytest.raises(SamplingGovernanceError, match="unsupported empirical routing"):
        model.validate()

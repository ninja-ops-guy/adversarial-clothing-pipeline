from __future__ import annotations

from dataclasses import replace
import json

import pytest

from ruthless_pipeline.governance.constraints import (
    ConstraintImpact,
    ConstraintSet,
    ConstraintSetRegistry,
)
from ruthless_pipeline.governance.ledger import GovernanceLedger
from ruthless_pipeline.governance.pass6_exit import (
    LaneCapability,
    LaneInventoryEntry,
    Pass6ExitError,
    run_pass6_exit_sequence,
    seal_pass6_backend_run,
)
from ruthless_pipeline.governance.sampling import (
    DiagnosticPolicy,
    ExactProjectedPopulationBackend,
    ExternalSamplerReply,
    PopulationIdentity,
    ProjectedSamplerAdapter,
    RepresentativenessState,
    SamplerLane,
    SamplingGovernanceError,
    SamplingRequest,
)
from ruthless_pipeline.governance.state import (
    ExperimentState,
    GovernanceStateMachine,
)


EXPERIMENT_ID = "RAC-EXP-PASS6EXIT001"
CONSTRAINT_ID = "RAC-CS-PASS6EXIT001"
PIPELINE_ID = "RAC-PIPE-PASS6EXIT001"
CALIBRATION_ID = "RAC-CAL-PASS6EXIT001"
POPULATION = (
    {"x": 0, "y": 0},
    {"x": 0, "y": 1},
    {"x": 1, "y": 0},
    {"x": 1, "y": 1},
)


def _request() -> SamplingRequest:
    population = PopulationIdentity(
        constraint_set_id=CONSTRAINT_ID,
        constraint_version="v1",
        semantic_hash="a" * 64,
        projection_version="RAC-PG-1.0",
        semantic_projection=("x", "y"),
        independent_support=("x",),
    )
    return SamplingRequest(
        target_distribution="uniform_over_feasible_projection",
        sample_count=4,
        seed=20260910,
        semantic_projection=("x", "y"),
        material_strata=("A", "B"),
        population=population,
        with_replacement=False,
    )


def _policy() -> DiagnosticPolicy:
    return DiagnosticPolicy(
        version="pass6-exit-policy-v1",
        minimum_material_strata_coverage=1.0,
        maximum_duplicate_fraction=0.25,
        minimum_effective_sample_size=2.0,
        minimum_support_coverage=0.75,
        maximum_total_variation=0.25,
        maximum_marginal_error=0.25,
        maximum_pairwise_error=0.25,
        maximum_seed_instability=0.25,
        require_exact_calibration_when_available=True,
        require_external_sampler_test=True,
    )


def _good_reply(request):
    del request
    return ExternalSamplerReply(
        samples=POPULATION,
        achieved_distribution="validated_external_near_uniform",
        population_size=4,
    )


def _biased_reply(request):
    del request
    return ExternalSamplerReply(
        samples=tuple({"x": 1, "y": 1} for _ in range(4)),
        achieved_distribution="importance_weighted_biased_proposal",
        weights=(10.0, 1.0, 1.0, 1.0),
        population_size=4,
    )


def _backends():
    return {
        SamplerLane.EXACT: ExactProjectedPopulationBackend(POPULATION),
        SamplerLane.PROJECTED_HASHING: ProjectedSamplerAdapter(
            lane=SamplerLane.PROJECTED_HASHING,
            sampler=_good_reply,
            backend_id="fixture.projected-hashing",
            version="1",
        ),
        SamplerLane.STRATIFIED: ProjectedSamplerAdapter(
            lane=SamplerLane.STRATIFIED,
            sampler=_good_reply,
            backend_id="fixture.stratified",
            version="1",
        ),
        SamplerLane.DEGRADED: ProjectedSamplerAdapter(
            lane=SamplerLane.DEGRADED,
            sampler=_biased_reply,
            backend_id="fixture.degraded-proposal",
            version="1",
        ),
    }


def _inventory():
    return (
        LaneInventoryEntry(SamplerLane.EXACT, LaneCapability.BUILTIN_PRODUCTION, "ExactProjectedPopulationBackend"),
        LaneInventoryEntry(SamplerLane.PROJECTED_HASHING, LaneCapability.EXTERNAL_ADAPTER_PRODUCTION, "ProjectedSamplerAdapter + external hashing engine"),
        LaneInventoryEntry(SamplerLane.STRATIFIED, LaneCapability.EXTERNAL_ADAPTER_PRODUCTION, "ProjectedSamplerAdapter + external stratified engine"),
        LaneInventoryEntry(SamplerLane.DEGRADED, LaneCapability.EXTERNAL_ADAPTER_PRODUCTION, "ProjectedSamplerAdapter + proposal/rejection/importance engine"),
    )


def _run():
    return run_pass6_exit_sequence(
        experiment_id=EXPERIMENT_ID,
        request=_request(),
        backends=_backends(),
        sampling_ids={
            SamplerLane.EXACT: "RAC-SAMP-PASS6EXACT",
            SamplerLane.PROJECTED_HASHING: "RAC-SAMP-PASS6HASH",
            SamplerLane.STRATIFIED: "RAC-SAMP-PASS6STRAT",
            SamplerLane.DEGRADED: "RAC-SAMP-PASS6DEGRADED",
        },
        inventory=_inventory(),
        diagnostic_policy=_policy(),
        exact_population=POPULATION,
        observed_material_strata={lane: ("A", "B") for lane in SamplerLane},
        support_coverage={lane: 1.0 for lane in SamplerLane},
        repeated_seed_instability={
            SamplerLane.EXACT: 0.0,
            SamplerLane.PROJECTED_HASHING: 0.0,
            SamplerLane.STRATIFIED: 0.0,
            SamplerLane.DEGRADED: 0.75,
        },
        approximate_model_count=4.0,
        approximate_model_count_interval=(3.5, 4.5),
        constraint_sensitivity={"c1": 0.10},
        constraint_sensitivity_intervals={"c1": (0.05, 0.15)},
    )


def _registry() -> ConstraintSetRegistry:
    registry = ConstraintSetRegistry()
    registry.add(
        ConstraintSet(
            constraint_id=CONSTRAINT_ID,
            parent_id=None,
            semantic_hash="a" * 64,
            rules_hash="b" * 64,
            encoder_hash="c" * 64,
            projection_version="RAC-PG-1.0",
            software_version="1.0.0",
            impact=ConstraintImpact.NONE,
            encoder_version="0.4.2",
        )
    )
    return registry


def _preflight_machine():
    ledger = GovernanceLedger()
    machine = GovernanceStateMachine(experiment_id=EXPERIMENT_ID, ledger=ledger, actor="pass6-exit")
    machine.transition(
        ExperimentState.PREFLIGHT,
        event_id="RAC-GOV-EVT-PASS6PREFLIGHT",
        created_at="2026-09-10T22:00:00Z",
    )
    return machine, ledger


def test_pass6_exit_runs_every_available_lane_and_refuses_biased_degraded_sampler():
    record = _run()
    assert {run.lane for run in record.runs} == set(SamplerLane)
    by_lane = {run.lane: run for run in record.runs}
    assert by_lane[SamplerLane.EXACT].confirmatory_eligible is True
    assert by_lane[SamplerLane.PROJECTED_HASHING].confirmatory_eligible is True
    assert by_lane[SamplerLane.STRATIFIED].confirmatory_eligible is True
    assert by_lane[SamplerLane.DEGRADED].confirmatory_eligible is False
    assert by_lane[SamplerLane.DEGRADED].diagnostics.state is RepresentativenessState.LOW_REPRESENTATIVENESS
    assert "DEGRADED_BACKEND" in by_lane[SamplerLane.DEGRADED].diagnostics.reasons


def test_pass6_exit_serialization_retains_count_and_sensitivity_uncertainty():
    payload = json.loads(json.dumps(_run().to_dict(), sort_keys=True))
    for run in payload["runs"]:
        assert run["diagnostics"]["approximate_model_count_interval"] == [3.5, 4.5]
        assert run["diagnostics"]["constraint_sensitivity_intervals"]["c1"] == [0.05, 0.15]


def test_pass6_eligible_run_seals_with_exact_diagnostic_policy_hash():
    record = _run()
    exact = next(run for run in record.runs if run.lane is SamplerLane.EXACT)
    machine, ledger = _preflight_machine()
    artifacts = {"cohort/pass6-exit.json": b'{"fixture":"pass6"}'}
    seal = seal_pass6_backend_run(
        exact,
        diagnostic_policy=_policy(),
        cohort_id="RAC-COHORT-PASS6EXIT001",
        specimen_ids=("S1", "S2", "S3", "S4"),
        artifact_bytes=artifacts,
        constraint_registry=_registry(),
        registered_pipeline_ids=(PIPELINE_ID,),
        registered_calibration_ids=(CALIBRATION_ID,),
        code_commit="a" * 40,
        code_version="pass6-exit/1",
        pipeline_id=PIPELINE_ID,
        pipeline_version="fixture-pipeline/1",
        calibration_id=CALIBRATION_ID,
        calibration_version="fixture-calibration/1",
        state_machine=machine,
        seal_event_id="RAC-GOV-EVT-PASS6SEAL001",
        created_at="2026-09-10T22:01:00Z",
    )
    assert seal.state == "SEALED"
    assert seal.diagnostic_threshold_hash == _policy().threshold_hash
    assert machine.state is ExperimentState.SEALED
    assert ledger.verify() is True


def test_pass6_post_manifest_threshold_change_invalidates_would_be_seal():
    record = _run()
    exact = next(run for run in record.runs if run.lane is SamplerLane.EXACT)
    changed = replace(_policy(), maximum_duplicate_fraction=0.10, version="pass6-exit-policy-v2")
    machine, _ = _preflight_machine()
    with pytest.raises(Pass6ExitError, match="changed after sampling manifest"):
        seal_pass6_backend_run(
            exact,
            diagnostic_policy=changed,
            cohort_id="RAC-COHORT-PASS6EXIT002",
            specimen_ids=("S1", "S2", "S3", "S4"),
            artifact_bytes={"cohort/pass6-exit.json": b'{}'},
            constraint_registry=_registry(),
            registered_pipeline_ids=(PIPELINE_ID,),
            registered_calibration_ids=(CALIBRATION_ID,),
            code_commit="a" * 40,
            code_version="pass6-exit/1",
            pipeline_id=PIPELINE_ID,
            pipeline_version="fixture-pipeline/1",
            calibration_id=CALIBRATION_ID,
            calibration_version="fixture-calibration/1",
            state_machine=machine,
            seal_event_id="RAC-GOV-EVT-PASS6SEAL002",
        )


def test_pass6_external_adapter_cannot_leak_auxiliary_variables_or_first_witness():
    request = _request()
    leaking = ProjectedSamplerAdapter(
        lane=SamplerLane.PROJECTED_HASHING,
        sampler=lambda request: ExternalSamplerReply(
            samples=tuple({"x": 0, "y": 0, "aux": 1} for _ in range(4)),
            achieved_distribution="near_uniform",
        ),
        backend_id="fixture.leaking",
        version="1",
    )
    with pytest.raises(SamplingGovernanceError, match="non-semantic variables"):
        leaking.sample(request)

    first_witness = ProjectedSamplerAdapter(
        lane=SamplerLane.PROJECTED_HASHING,
        sampler=lambda request: ExternalSamplerReply(
            samples=tuple({"x": 0, "y": 0} for _ in range(4)),
            achieved_distribution="first_sat_witness",
        ),
        backend_id="fixture.first-witness",
        version="1",
    )
    with pytest.raises(SamplingGovernanceError, match="not scientific samples"):
        first_witness.sample(request)

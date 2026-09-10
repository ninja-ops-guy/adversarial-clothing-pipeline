"""Pass 6 tests for replaceable external sampler lanes."""
from __future__ import annotations

import pytest

from ruthless_pipeline.governance.sampling import (
    ExternalSamplerReply,
    PopulationIdentity,
    ProjectedSamplerAdapter,
    SamplerLane,
    SamplingGovernanceError,
    SamplingRequest,
)


POPULATION = PopulationIdentity(
    constraint_set_id="RAC-CS-PASS6-EXT-001",
    constraint_version="1.0.0",
    semantic_hash="b" * 64,
    projection_version="genome/1",
    semantic_projection=("x", "y"),
    independent_support=("x",),
)


def request() -> SamplingRequest:
    return SamplingRequest(
        target_distribution="uniform_over_feasible_projection",
        sample_count=3,
        seed=41,
        semantic_projection=("x", "y"),
        population=POPULATION,
    )


def fixture_reply(achieved_distribution: str) -> ExternalSamplerReply:
    return ExternalSamplerReply(
        samples=(
            {"x": 0, "y": 0},
            {"x": 0, "y": 1},
            {"x": 1, "y": 0},
        ),
        achieved_distribution=achieved_distribution,
    )


@pytest.mark.parametrize(
    ("lane", "distribution"),
    (
        (SamplerLane.PROJECTED_HASHING, "estimated_near_uniform"),
        (SamplerLane.STRATIFIED, "preregistered_stratified"),
        (SamplerLane.DEGRADED, "proposal_rejection_importance"),
    ),
)
def test_external_lanes_share_one_projection_and_provenance_contract(
    lane: SamplerLane,
    distribution: str,
):
    adapter = ProjectedSamplerAdapter(
        lane=lane,
        sampler=lambda _: fixture_reply(distribution),
        backend_id=f"fixture.{lane.value}",
        version="1.0",
    )
    sampled = adapter.sample(request())
    assert sampled.lane is lane
    assert sampled.backend_id == f"fixture.{lane.value}"
    assert sampled.backend_version == "1.0"
    assert sampled.achieved_distribution == distribution
    assert all(set(sample) == {"x", "y"} for sample in sampled.samples)


def test_external_adapter_rejects_auxiliary_variable_leakage():
    def bad_sampler(_):
        return ExternalSamplerReply(
            samples=(
                {"x": 0, "y": 0, "aux": 1},
                {"x": 0, "y": 1},
                {"x": 1, "y": 0},
            ),
            achieved_distribution="estimated_near_uniform",
        )

    adapter = ProjectedSamplerAdapter(
        lane=SamplerLane.PROJECTED_HASHING,
        sampler=bad_sampler,
        backend_id="fixture.bad-aux",
        version="1.0",
    )
    with pytest.raises(SamplingGovernanceError, match="non-semantic"):
        adapter.sample(request())


def test_external_adapter_rejects_wrong_sample_count():
    def bad_sampler(_):
        return ExternalSamplerReply(
            samples=({"x": 0, "y": 0},),
            achieved_distribution="preregistered_stratified",
        )

    adapter = ProjectedSamplerAdapter(
        lane=SamplerLane.STRATIFIED,
        sampler=bad_sampler,
        backend_id="fixture.bad-count",
        version="1.0",
    )
    with pytest.raises(SamplingGovernanceError, match="sample count"):
        adapter.sample(request())


def test_external_adapter_rejects_untyped_backend_reply():
    adapter = ProjectedSamplerAdapter(
        lane=SamplerLane.PROJECTED_HASHING,
        sampler=lambda _: {"samples": []},
        backend_id="fixture.untyped",
        version="1.0",
    )
    with pytest.raises(SamplingGovernanceError, match="ExternalSamplerReply"):
        adapter.sample(request())


def test_external_adapter_cannot_label_first_solver_model_as_sampling_distribution():
    adapter = ProjectedSamplerAdapter(
        lane=SamplerLane.PROJECTED_HASHING,
        sampler=lambda _: fixture_reply("first_sat_witness"),
        backend_id="fixture.first-model",
        version="1.0",
    )
    with pytest.raises(SamplingGovernanceError, match="not scientific samples"):
        adapter.sample(request())

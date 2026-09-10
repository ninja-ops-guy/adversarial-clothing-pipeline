"""Tests for SPEC-16 external-cohort adapter (lane D)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.channel import ChannelRecord
from ruthless_pipeline.ctm.external_cohort import (
    CHANNEL_COMPLETENESS_FIELDS,
    COHORTS,
    EVIDENCE_CLASS,
    EXTERNAL_OBSERVATION_SCHEMA_VERSION,
    ExternalCohortError,
    ExternalObservation,
    advtshirt_1k_provenance,
    build_analysis_pool,
    claim_ceiling,
    fabrication_delta,
    promote_to_controlled_efficacy,
    require_secondary_only,
)

GENOME_SHA = "c" * 64
GENOME_SHA2 = "d" * 64

COMPLETE_UNKNOWN = {f: "unknown" for f in CHANNEL_COMPLETENESS_FIELDS}
COMPLETE_KNOWN = {f: "known" for f in CHANNEL_COMPLETENESS_FIELDS}


def _obs(**overrides):
    kwargs = dict(
        artifact_ref="advtshirt-1k/images/0001.jpg",
        dataset=advtshirt_1k_provenance(),
        genome_measurement_sha256=GENOME_SHA,
        channel_completeness=dict(COMPLETE_UNKNOWN),
    )
    kwargs.update(overrides)
    return ExternalObservation(**kwargs)


def _genome(seed=1.0):
    return {
        "spectral": {"energy": seed, "peak": seed * 2},
        "topology": {"components": int(seed)},
        "color": {"entropy": seed / 2},
        "geometry": {"bbox": [0, 0, seed, seed]},
    }


# -- positive -----------------------------------------------------------------

def test_observation_roundtrip_schema_and_determinism():
    obs = _obs()
    obs.validate_against_schema()
    assert ExternalObservation.from_dict(obs.to_dict()) == obs
    assert obs.observation_sha256() == _obs().observation_sha256()
    assert obs.observation_id.startswith("RAC-CTM-EXT-")


def test_evidence_class_and_cohort_are_fixed():
    obs = _obs()
    assert obs.evidence_class == "external_physical_observation"
    assert obs.cohort == "external_fabricated"
    require_secondary_only(obs)


def test_claim_ceiling_defaults_to_exploratory():
    assert claim_ceiling(_obs()) == "EXPLORATORY"


def test_claim_ceiling_rises_only_with_independent_ctm_channel():
    obs = _obs(channel_completeness=dict(COMPLETE_KNOWN))
    channel = ChannelRecord(
        channel_id="phys-1",
        tier="physical",
        camera_model="sony-imx500",
        isp_pipeline_id="sony-imx500-default-v3",
    )
    assert claim_ceiling(obs, ctm_channel=channel) == "PHYSICAL_SINGLE_CHANNEL"
    # incomplete channel completeness caps at EXPLORATORY even with a channel
    obs2 = _obs()
    assert claim_ceiling(obs2, ctm_channel=channel) == "EXPLORATORY"


def test_fabrication_delta_routes_through_compare():
    obs = _obs()
    delta = fabrication_delta(_genome(1.0), _genome(2.0), observation=obs)
    assert delta["kind"] == "external_fabrication_delta"
    assert delta["claim_state"] == "EXPLORATORY"
    assert delta["physical_efficacy_claimed"] is False
    assert delta["overall_distance"] > 0
    same = fabrication_delta(_genome(1.0), _genome(1.0), observation=obs)
    assert same["identical"] is True


def test_declared_stratified_pool_ok():
    pool = build_analysis_pool(
        [("digital_master", {"g": 1}), ("external_fabricated", _obs().to_dict())],
        cohort_term_declared=True,
    )
    assert pool["cohorts"] == ["digital_master", "external_fabricated"]
    assert pool["claim_ceiling"] == "EXPLORATORY"
    assert pool["physical_efficacy_claimed"] is False


def test_single_cohort_pool_ok_without_term():
    pool = build_analysis_pool([("external_fabricated", _obs().to_dict())])
    assert pool["cohorts"] == ["external_fabricated"]


# -- negative / fail-closed ----------------------------------------------------

def test_promotion_to_controlled_efficacy_always_refused():
    with pytest.raises(ExternalCohortError):
        promote_to_controlled_efficacy(_obs())
    # even with fully known channel metadata
    with pytest.raises(ExternalCohortError):
        promote_to_controlled_efficacy(_obs(channel_completeness=dict(COMPLETE_KNOWN)))


def test_silent_mixed_pool_refused():
    with pytest.raises(ExternalCohortError):
        build_analysis_pool(
            [("digital_master", {"g": 1}), ("external_fabricated", _obs().to_dict())]
        )


def test_unknown_cohort_refused():
    with pytest.raises(ExternalCohortError):
        build_analysis_pool([("mystery", {})])


def test_empty_pool_refused():
    with pytest.raises(ExternalCohortError):
        build_analysis_pool([])


def test_missing_channel_completeness_field_fails_closed():
    bad = {k: v for k, v in COMPLETE_UNKNOWN.items() if k != "lighting"}
    with pytest.raises(ExternalCohortError):
        _obs(channel_completeness=bad)


def test_invalid_channel_completeness_value_fails_closed():
    with pytest.raises(ExternalCohortError):
        _obs(channel_completeness={**COMPLETE_UNKNOWN, "camera": "guessed"})


def test_extra_channel_completeness_field_fails_closed():
    with pytest.raises(ExternalCohortError):
        _obs(channel_completeness={**COMPLETE_UNKNOWN, "lens": "known"})


def test_primary_evidence_class_assertion_refused():
    payload = _obs().to_dict()
    payload["evidence_class"] = "experimental_print_specimen"
    with pytest.raises(ExternalCohortError):
        ExternalObservation.from_dict(payload)


def test_asserted_observation_id_mismatch_refused():
    payload = _obs().to_dict()
    payload["observation_id"] = "RAC-CTM-EXT-0000000000000000"
    with pytest.raises(ExternalCohortError):
        ExternalObservation.from_dict(payload)


def test_missing_genome_sha_fails_closed():
    with pytest.raises(ExternalCohortError):
        _obs(genome_measurement_sha256="")
    with pytest.raises(ExternalCohortError):
        _obs(genome_measurement_sha256="C" * 64)  # uppercase


def test_missing_provenance_fails_closed():
    with pytest.raises(ExternalCohortError):
        _obs(dataset=advtshirt_1k_provenance().__class__(
            dataset_name="", version="v", source_paper_ref="p",
            license="l", registered_utc="2026-04-01"))


def test_bad_schema_version_fails_closed():
    with pytest.raises(ExternalCohortError):
        _obs(schema_version="rac-ctm-external-observation/0.9")


def test_version_and_constants():
    assert EXTERNAL_OBSERVATION_SCHEMA_VERSION == "rac-ctm-external-observation/1.0"
    assert EVIDENCE_CLASS == "external_physical_observation"
    assert COHORTS == frozenset({"digital_master", "external_fabricated"})
    assert GENOME_SHA != GENOME_SHA2

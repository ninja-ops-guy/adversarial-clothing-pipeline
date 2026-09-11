"""Tests for the D2-0007 Stage-0 landmark-free wiring smoke test.

Coverage: determinism (same seeds → same hashes across two runs),
landmark-free assertion, registry-sourced generators, provenance
completeness (required fields, hashes verify by regeneration),
exposure-ledger entries, EXPLORATORY claim state, fail-closed tamper
rejection, and smoke-summary schema/shape validation.

Nothing here measures efficacy; the scoring surface is a synthetic
development fixture (hypothesis-screening infrastructure, never evidence).
"""

from __future__ import annotations

import copy
import json

import pytest

from ruthless_pipeline.certification.observation_medium import (
    IMAGE_COMPOSITE,
    verify_annotation,
)
from ruthless_pipeline.governance.evaluation_exposure import (
    EXPOSURE_SCHEMA_VERSION,
)
from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from ruthless_pipeline.patterns import P0_GENERATORS
from ruthless_pipeline.patterns.wiring import (
    SMOKE_GENERATORS,
    SMOKE_SCHEMA_VERSION,
    SMOKE_SEEDS,
    WiringSmokeError,
    build_smoke_registry,
    run_wiring_smoke,
    verify_smoke_summary,
)

REQUIRED_SUMMARY_FIELDS = (
    "schema_version",
    "smoke_id",
    "generation_id",
    "stage",
    "generators",
    "seeds",
    "landmark_free",
    "candidates",
    "exposure_ledger_sha256",
    "provenance",
    "boundaries",
    "verdict",
    "summary_sha256",
)

REQUIRED_CANDIDATE_FIELDS = (
    "candidate_id",
    "pattern_sha256",
    "generator",
    "generator_version",
    "provenance_hash",
    "params",
    "evidence_class",
    "physical_efficacy_claimed",
    "claim_state",
    "landmark_free",
    "seed",
)


@pytest.fixture(scope="module")
def summary():
    return run_wiring_smoke()


# --- determinism -------------------------------------------------------------

def test_same_seeds_same_hashes_across_two_runs():
    a = run_wiring_smoke()
    b = run_wiring_smoke()
    assert a["summary_sha256"] == b["summary_sha256"]
    assert canonical_json(a) == canonical_json(b)
    assert a["exposure_ledger_sha256"] == b["exposure_ledger_sha256"]
    hashes_a = [c["candidate"]["pattern_sha256"] for c in a["candidates"]]
    hashes_b = [c["candidate"]["pattern_sha256"] for c in b["candidates"]]
    assert hashes_a == hashes_b


# --- registry-sourced generators ----------------------------------------------

def test_generators_come_from_registry_over_p0(summary):
    registry = build_smoke_registry()
    names_in_registry = {key.split("@", 1)[0] for key in registry.generators}
    assert names_in_registry == {cls().name if isinstance(cls, type) else cls.name
                                 for cls in P0_GENERATORS}
    for entry in summary["generators"]:
        assert entry["source"] == "P0_GENERATORS via GeneratorRegistry"
        instance = registry.get(entry["name"])
        assert instance.version == entry["version"]
    assert tuple(g["name"] for g in summary["generators"]) == SMOKE_GENERATORS


# --- landmark-free assertion ---------------------------------------------------

def test_no_landmarks_supplied_and_recorded(summary):
    assert summary["landmark_free"] is True
    for entry in summary["candidates"]:
        cand = entry["candidate"]
        assert cand["landmark_free"] is True
        mg = cand["params"]["mask_geometry"]
        assert "landmarks" not in mg
        assert "bboxes" not in mg


def test_feature_collage_core_path_taken_without_landmarks(summary):
    """FeatureCollage's eye-overlap block is a try/except MissingLandmarksError
    enhancement; with no landmarks supplied the anchor-independent core is the
    path taken — asserted via landmark_free provenance on its candidates."""
    collage = [e for e in summary["candidates"]
               if e["candidate"]["generator"] == "feature_collage"]
    assert collage, "feature_collage candidates missing"
    for entry in collage:
        assert entry["candidate"]["landmark_free"] is True
        assert not entry["candidate"]["params"]["mask_geometry"]


# --- provenance completeness ---------------------------------------------------

def test_candidate_required_fields_and_claim_state(summary):
    for entry in summary["candidates"]:
        cand = entry["candidate"]
        for field in REQUIRED_CANDIDATE_FIELDS:
            assert cand.get(field) is not None, f"missing {field}"
        assert cand["claim_state"] == "EXPLORATORY"
        assert cand["physical_efficacy_claimed"] is False
        assert cand["evidence_class"] == "digital_candidate"
        assert len(cand["pattern_sha256"]) == 64
        assert len(cand["provenance_hash"]) == 64
        assert cand["seed"] in SMOKE_SEEDS


def test_hashes_verify_by_regeneration(summary):
    verify_smoke_summary(summary)  # raises on any mismatch


def test_observation_medium_synthetic_and_verified(summary):
    for entry in summary["candidates"]:
        annotation = entry["observation_medium"]
        verify_annotation(annotation)
        assert annotation["observation_medium"] == IMAGE_COMPOSITE
        assert annotation["physical_efficacy_claimed"] is False


def test_transfer_records_stay_synthetic(summary):
    for entry in summary["candidates"]:
        record = entry["transfer_record"]
        assert record["evidence_class"] == "synthetic_pipeline_validation_only"
        assert record["physical_efficacy_claimed"] is False


# --- exposure ledger -----------------------------------------------------------

def test_exposure_ledger_entries_written(summary):
    assert len(summary["exposure_ledger_sha256"]) == 64
    events = [e["exposure_event"] for e in summary["candidates"]]
    assert len(events) == len(SMOKE_GENERATORS) * len(SMOKE_SEEDS)
    ids = [e["event_id"] for e in events]
    assert len(set(ids)) == len(ids)
    for event in events:
        assert event["schema_version"] == EXPOSURE_SCHEMA_VERSION
        assert event["output_class"] == "surrogate_evaluation"
        assert event["decision_influenced"] is False
        assert len(event["output_hash"]) == 64
        assert event["output_hash"] == (
            sha256_bytes(canonical_json(
                next(c for c in summary["candidates"]
                     if c["exposure_event"]["event_id"] == event["event_id"]
                     )["evaluation"]["detector_response"])))


def test_evaluation_surface_is_development_fixture_not_evidence(summary):
    for entry in summary["candidates"]:
        ev = entry["evaluation"]
        assert ev["surface"] == "development_synthetic_fixture"
        assert "not_evidence" in ev["surface_role"]
        assert ev["efficacy_measured"] is False
        assert ev["model_id"].startswith("SMOKE-DEV-FIXTURE")


# --- smoke summary schema/shape -------------------------------------------------

def test_summary_schema_shape_and_verdict(summary):
    for field in REQUIRED_SUMMARY_FIELDS:
        assert field in summary, f"missing summary field {field}"
    assert summary["schema_version"] == SMOKE_SCHEMA_VERSION
    assert summary["verdict"] == "PASS"
    assert summary["generation_id"] == "RAC-PER-D2-0007"
    assert len(summary["summary_sha256"]) == 64
    assert summary["provenance"]["nodes"]
    assert summary["provenance"]["edges"]
    boundaries = summary["boundaries"]
    assert boundaries["d2_0005_touched"] is False
    assert boundaries["d2_0005_armed"] is False
    assert boundaries["heldout_accessed"] is False
    assert boundaries["d2_0004_rerun"] is False
    assert boundaries["thresholds_changed"] is False
    assert boundaries["efficacy_claimed"] is False


# --- fail-closed behavior --------------------------------------------------------

def test_tampered_provenance_hash_rejected(summary):
    bad = copy.deepcopy(summary)
    bad["candidates"][0]["candidate"]["provenance_hash"] = "0" * 64
    with pytest.raises(WiringSmokeError):
        verify_smoke_summary(bad)


def test_tampered_pattern_hash_rejected(summary):
    bad = copy.deepcopy(summary)
    bad["candidates"][1]["candidate"]["pattern_sha256"] = "f" * 64
    with pytest.raises(WiringSmokeError):
        verify_smoke_summary(bad)


def test_tampered_summary_body_rejected(summary):
    bad = copy.deepcopy(summary)
    bad["seeds"] = [1, 2]
    with pytest.raises(WiringSmokeError, match="summary_sha256"):
        verify_smoke_summary(bad)


def test_tampered_exposure_pin_rejected(summary):
    bad = copy.deepcopy(summary)
    bad["candidates"][0]["exposure_event"]["output_hash"] = "a" * 64
    with pytest.raises(WiringSmokeError):
        verify_smoke_summary(bad)


def test_claim_state_escalation_rejected(summary):
    bad = copy.deepcopy(summary)
    bad["candidates"][0]["candidate"]["claim_state"] = "CONFIRMED"
    with pytest.raises(WiringSmokeError):
        verify_smoke_summary(bad)


def test_committed_artifact_matches_regeneration():
    """The committed smoke summary artifact regenerates byte-for-byte."""
    from pathlib import Path

    path = (Path(__file__).resolve().parents[1]
            / "artifacts" / "d2007_wiring_smoke" / "smoke_summary.json")
    assert path.is_file(), "committed smoke summary missing"
    committed = json.loads(path.read_text())
    assert committed["verdict"] == "PASS"
    verify_smoke_summary(committed)
    assert committed["summary_sha256"] == run_wiring_smoke()["summary_sha256"]

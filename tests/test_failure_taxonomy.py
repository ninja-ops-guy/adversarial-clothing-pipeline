"""Tests for ruthless_pipeline.certification.failure_taxonomy."""

from __future__ import annotations

import pytest

from ruthless_pipeline.certification.failure_taxonomy import (
    FailureAtlas,
    FailureCategory,
    FailureRecord,
    FailureSignal,
    classify_failure,
)

KW = dict(experiment_id="EXP-1", generation_id="GEN-1",
          record_id="FR-test0000001", created_utc="2026-01-01T00:00:00.000000Z")


def test_optimization_failure():
    rec = classify_failure(
        {"baseline_detection_rate": 0.90, "surrogate_detection_rate": 0.89}, **KW)
    assert rec.category is FailureCategory.OPTIMIZATION_FAILURE
    assert rec.confidence == "high"
    assert any(s.name == "surrogate_detection_rate" for s in rec.signals)


def test_surrogate_overfit_same_family():
    rec = classify_failure(
        {"baseline_detection_rate": 0.90, "surrogate_detection_rate": 0.40,
         "heldout_detection_rate": 0.85, "heldout_same_family": True}, **KW)
    assert rec.category is FailureCategory.SURROGATE_OVERFIT
    assert {s.name for s in rec.signals} == {
        "surrogate_suppression", "heldout_detection_rate"}


def test_cross_architecture_transfer_failure():
    rec = classify_failure(
        {"baseline_detection_rate": 0.90, "surrogate_detection_rate": 0.40,
         "heldout_detection_rate": 0.85, "heldout_same_family": False}, **KW)
    assert rec.category is FailureCategory.CROSS_ARCHITECTURE_TRANSFER_FAILURE


def test_transformation_fragility():
    rec = classify_failure(
        {"transformation_rates": {"front": 0.1, "side": 0.2, "far": 0.6}}, **KW)
    assert rec.category is FailureCategory.TRANSFORMATION_FRAGILITY
    assert rec.signals[0].value == pytest.approx(0.5)


def test_statistical_inconclusive():
    rec = classify_failure(
        {"wilson_interval": (0.1, 0.5), "effect_direction_consistent": True}, **KW)
    assert rec.category is FailureCategory.STATISTICAL_INCONCLUSIVE
    # Inconsistent direction must not fire.
    rec2 = classify_failure(
        {"wilson_interval": (0.1, 0.5), "effect_direction_consistent": False}, **KW)
    assert rec2.category is FailureCategory.UNCLASSIFIED


def test_measurement_signal_categories():
    assert classify_failure({"delta_e": 9.0}, **KW).category is (
        FailureCategory.MANUFACTURING_LOSS)
    assert classify_failure({"scale_error": 0.05}, **KW).category is (
        FailureCategory.MANUFACTURING_LOSS)
    assert classify_failure({"isp_margin_loss": 0.30}, **KW).category is (
        FailureCategory.CAMERA_ISP_LOSS)
    assert classify_failure({"deformation_score_drop": 0.40}, **KW).category is (
        FailureCategory.DEFORMATION_FAILURE)
    assert classify_failure({"coverage_entropy": 0.30}, **KW).category is (
        FailureCategory.COVERAGE_FAILURE)


def test_unclassified():
    rec = classify_failure({}, **KW)
    assert rec.category is FailureCategory.UNCLASSIFIED
    assert rec.confidence == "low"
    assert rec.signals == ()


def test_priority_resolution_records_all_matches():
    # Fires OPTIMIZATION_FAILURE, TRANSFORMATION_FRAGILITY and CAMERA_ISP_LOSS;
    # priority order puts OPTIMIZATION_FAILURE first.
    rec = classify_failure(
        {"baseline_detection_rate": 0.9, "surrogate_detection_rate": 0.9,
         "transformation_rates": [0.1, 0.9], "isp_margin_loss": 0.5}, **KW)
    assert rec.category is FailureCategory.OPTIMIZATION_FAILURE
    assert rec.confidence == "medium"
    names = {s.name for s in rec.signals}
    assert {"surrogate_detection_rate", "transformation_spread",
            "isp_margin_loss"} <= names
    assert "also matched" in rec.explanation


def _atlas_with_records():
    atlas = FailureAtlas()
    atlas.add(classify_failure({}, experiment_id="E1", generation_id="G1",
                               record_id="FR-1", created_utc=KW["created_utc"]))
    atlas.add(classify_failure({"delta_e": 9.0}, experiment_id="E2",
                               generation_id="G1", record_id="FR-2",
                               created_utc=KW["created_utc"]))
    atlas.add(classify_failure({}, experiment_id="E3", generation_id="G2",
                               record_id="FR-3", created_utc=KW["created_utc"]))
    return atlas


def test_atlas_add_lookup_summary():
    atlas = _atlas_with_records()
    assert len(atlas.by_generation("G1")) == 2
    assert len(atlas.by_category(FailureCategory.UNCLASSIFIED)) == 2
    summary = atlas.summary()
    assert summary["unclassified"] == 2
    assert summary["manufacturing_loss"] == 1
    assert summary["optimization_failure"] == 0
    with pytest.raises(ValueError):
        atlas.by_generation("")


def test_atlas_json_round_trip():
    atlas = _atlas_with_records()
    restored = FailureAtlas.from_json(atlas.to_json())
    assert restored.to_json() == atlas.to_json()
    assert [r.record_sha256() for r in restored.records] == [
        r.record_sha256() for r in atlas.records]


def test_hash_stability_and_validation():
    rec1 = classify_failure({"delta_e": 9.0}, **KW)
    rec2 = classify_failure({"delta_e": 9.0}, **KW)
    assert rec1.record_sha256() == rec2.record_sha256()
    assert len(rec1.record_sha256()) == 64
    with pytest.raises(ValueError):
        FailureRecord(
            record_id="", experiment_id="E", generation_id="G",
            category=FailureCategory.UNCLASSIFIED, signals=(), confidence="low",
            explanation="x", created_utc="t").validate()
    with pytest.raises(ValueError):
        FailureSignal(name="", value=1.0, detail="d").validate()

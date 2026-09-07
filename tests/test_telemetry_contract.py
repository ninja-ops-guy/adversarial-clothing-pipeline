"""Tests for the D2-0005 optimization telemetry contract."""

from __future__ import annotations

import hashlib
import json

import pytest

from ruthless_pipeline.certification import telemetry_contract as tc


CANDIDATE_HASH = hashlib.sha256(b"candidate-pattern-bytes").hexdigest()
OTHER_HASH = hashlib.sha256(b"other-candidate").hexdigest()
CAL_SHA = hashlib.sha256(b"calibration-profile").hexdigest()

SURROGATE_RATES = {
    "yolov8n-person": 0.12,
    "yolov5s-person": 0.18,
    "detr-resnet50": 0.09,
}


def make_optimizer_config() -> tc.OptimizerConfig:
    return tc.OptimizerConfig(
        optimizer_id="adaptive-surrogate-search-v2",
        seed=20270115,
        max_evaluations=500,
        hyperparameters={"population": 32, "mutation_rate": 0.15},
    )


def make_pre(**overrides) -> tc.PreHeldOutTelemetry:
    kwargs = dict(
        candidate_sha256=CANDIDATE_HASH,
        generation_id="RAC-PER-D2-0005",
        recorded_utc="2027-01-15T00:00:00Z",
        surrogate_mean_detection_rate=0.13,
        surrogate_worst_case_detection_rate=0.18,
        per_surrogate_detection_rates=dict(SURROGATE_RATES),
        cross_model_disagreement=tc.cross_model_disagreement(SURROGATE_RATES),
        transformation_sweep_variance=0.004,
        spectral_band_energy={"low": 0.31, "mid": 0.52, "high": 0.17},
        pattern_fidelity=0.93,
        printability=0.88,
        objective_trajectory={
            "initial": 0.62,
            "final": 0.14,
            "best": 0.13,
            "evaluations": 500,
        },
        coverage_metrics={"patch_coverage": 0.41, "coverage_entropy": 0.72},
        optimizer_config=make_optimizer_config(),
        calibration_profile=tc.CalibrationProfileRef("RAC-PCP-1.1-3", CAL_SHA),
    )
    kwargs.update(overrides)
    return tc.PreHeldOutTelemetry(**kwargs)


def make_outcome(**overrides) -> tc.HeldOutOutcome:
    kwargs = dict(
        candidate_sha256=CANDIDATE_HASH,
        heldout_detection_rates={
            "fasterrcnn_resnet50_fpn_v2": 0.21,
            "maskrcnn_resnet50_fpn_v2": 0.19,
        },
        verdict="PASS",
        recorded_utc="2027-01-20T00:00:00Z",
        benchmark_run_id="RAC-BENCH-D2-0005-001",
    )
    kwargs.update(overrides)
    return tc.HeldOutOutcome(**kwargs)


def make_record() -> tc.TelemetryRecord:
    return tc.TelemetryRecord(pre=make_pre())


# --- schema validation ---


def test_valid_record_passes_validation():
    make_record().validate()


def test_null_calibration_profile_allowed_pre_production():
    pre = make_pre(calibration_profile=None)
    tc.TelemetryRecord(pre=pre).validate()


def test_json_schema_document_is_valid_and_matches_record():
    assert tc.JSON_SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(tc.JSON_SCHEMA)
    jsonschema.validate(make_record().to_dict(), tc.JSON_SCHEMA)
    bad = make_record().to_dict()
    bad["pre"]["candidate_sha256"] = "not-a-hash"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, tc.JSON_SCHEMA)


def test_round_trip_json():
    record = make_record().append_outcome(make_outcome())
    restored = tc.TelemetryRecord.from_json(record.to_json())
    assert restored.to_dict() == record.to_dict()
    assert restored.frozen_sha256() == record.frozen_sha256()


# --- frozen-hash stability ---


def test_frozen_hash_stable_across_outcome_append():
    record = make_record()
    before = record.frozen_sha256()
    with_outcome = record.append_outcome(make_outcome())
    assert with_outcome.frozen_sha256() == before
    assert len(before) == 64
    int(before, 16)


def test_frozen_hash_detects_retroactive_edit():
    record = make_record()
    tampered = tc.TelemetryRecord(
        pre=make_pre(surrogate_mean_detection_rate=0.99)
    )
    assert tampered.frozen_sha256() != record.frozen_sha256()


def test_append_outcome_returns_new_record_original_untouched():
    record = make_record()
    updated = record.append_outcome(make_outcome())
    assert record.outcome is None
    assert updated.outcome is not None
    assert updated is not record


# --- append-only enforcement / candidate mismatch ---


def test_append_outcome_twice_rejected():
    record = make_record().append_outcome(make_outcome())
    with pytest.raises(ValueError, match="append-only"):
        record.append_outcome(make_outcome())


def test_append_outcome_candidate_hash_mismatch_rejected():
    with pytest.raises(ValueError, match="different candidate hash"):
        make_record().append_outcome(make_outcome(candidate_sha256=OTHER_HASH))


def test_record_with_mismatched_attached_outcome_rejected():
    record = tc.TelemetryRecord(
        pre=make_pre(), outcome=make_outcome(candidate_sha256=OTHER_HASH)
    )
    with pytest.raises(ValueError, match="different candidate hash"):
        record.validate()


# --- disagreement / variance computation sanity ---


def test_cross_model_disagreement_values():
    result = tc.cross_model_disagreement({"a": 0.0, "b": 1.0})
    assert result["mean"] == pytest.approx(0.5)
    assert result["variance"] == pytest.approx(0.25)
    assert result["spread"] == pytest.approx(1.0)
    assert result["max_pairwise_delta"] == pytest.approx(1.0)
    assert result["model_count"] == pytest.approx(2.0)


def test_cross_model_disagreement_requires_two_models():
    with pytest.raises(ValueError, match="at least 2"):
        tc.cross_model_disagreement({"only": 0.5})


def test_inconsistent_disagreement_rejected():
    bad = dict(tc.cross_model_disagreement(SURROGATE_RATES))
    bad["variance"] = 0.99
    with pytest.raises(ValueError, match="cross_model_disagreement"):
        make_pre(cross_model_disagreement=bad).validate()


# --- malformed field rejection ---


@pytest.mark.parametrize(
    "overrides, match",
    [
        ({"candidate_sha256": "abc123"}, "64-hex"),
        ({"generation_id": "D2-0005"}, "RAC-PER-D2"),
        ({"contract_version": "0.9"}, "contract_version"),
        ({"recorded_utc": ""}, "recorded_utc"),
        ({"surrogate_mean_detection_rate": 1.5}, "\\[0, 1\\]"),
        ({"surrogate_worst_case_detection_rate": -0.1}, "\\[0, 1\\]"),
        ({"per_surrogate_detection_rates": {"only": 0.5}}, "at least 2"),
        ({"transformation_sweep_variance": -0.5}, "non-negative"),
        ({"spectral_band_energy": {}}, "spectral_band_energy"),
        ({"spectral_band_energy": {"low": -1.0}}, "non-negative"),
        ({"pattern_fidelity": 2.0}, "\\[0, 1\\]"),
        ({"printability": float("nan")}, "\\[0, 1\\]"),
        ({"objective_trajectory": {"initial": 0.5}}, "objective_trajectory"),
        ({"coverage_metrics": {"patch_coverage": 0.4}}, "coverage_entropy"),
        ({"coverage_metrics": {"coverage_entropy": -0.2}}, "non-negative"),
        (
            {"calibration_profile": tc.CalibrationProfileRef("BAD-ID", CAL_SHA)},
            "RAC-PCP",
        ),
        (
            {"calibration_profile": tc.CalibrationProfileRef("RAC-PCP-1.1-3", "zz")},
            "64-hex",
        ),
    ],
)
def test_malformed_pre_fields_rejected(overrides, match):
    with pytest.raises(ValueError, match=match):
        make_pre(**overrides).validate()


@pytest.mark.parametrize(
    "overrides, match",
    [
        ({"candidate_sha256": "nope"}, "64-hex"),
        ({"heldout_detection_rates": {}}, "must not be empty"),
        ({"heldout_detection_rates": {"m": 1.2}}, "\\[0, 1\\]"),
        ({"verdict": "MAYBE"}, "verdict"),
        ({"recorded_utc": ""}, "recorded_utc"),
        ({"benchmark_run_id": ""}, "benchmark_run_id"),
    ],
)
def test_malformed_outcome_fields_rejected(overrides, match):
    with pytest.raises(ValueError, match=match):
        make_outcome(**overrides).validate()


def test_malformed_optimizer_config_rejected():
    with pytest.raises(ValueError, match="max_evaluations"):
        make_pre(
            optimizer_config=tc.OptimizerConfig("opt", 1, 0)
        ).validate()
    with pytest.raises(ValueError, match="seed"):
        make_pre(
            optimizer_config=tc.OptimizerConfig("opt", True, 10)
        ).validate()


def test_frozen_hash_matches_manual_sha256():
    record = make_record()
    manual = hashlib.sha256(record.frozen_canonical_json()).hexdigest()
    assert record.frozen_sha256() == manual

from __future__ import annotations

import pytest

from ruthless_pipeline.patterns.d2007_smoke import (
    D2007SmokeGateError,
    HELDOUT_MODEL_SET_ID,
    SURROGATE_MODEL_SET_ID,
    SurrogateScoreResult,
    build_landmark_free_candidate,
    run_landmark_free_smoke,
)

SURROGATES = (
    "yolov8n",
    "fasterrcnn_mobilenet_v3_320",
    "detr_resnet50",
    "ssdlite320_mobilenet_v3",
    "retinanet_resnet50_fpn_v2",
    "fcos_resnet50_fpn",
)


def _passing_scorer(image, candidate):
    assert image.shape == (128, 96, 3)
    assert candidate["generator"] == "feature_collage"
    assert "landmarks" not in candidate["params"]["mask_geometry"]
    return SurrogateScoreResult(
        model_set_id=SURROGATE_MODEL_SET_ID,
        per_surrogate_detection_rates={model: 0.75 for model in SURROGATES},
        invalid_condition_fraction=0.0,
        heldout_access=False,
    )


def test_build_candidate_is_landmark_free_and_exploratory():
    _, candidate = build_landmark_free_candidate()
    assert candidate["generator"] == "feature_collage"
    assert "landmarks" not in candidate["params"]["mask_geometry"]
    assert candidate["claim_state"] == "EXPLORATORY"
    assert candidate["physical_efficacy_claimed"] is False


def test_smoke_runs_fixture_candidate_surrogate_telemetry_path():
    telemetry = run_landmark_free_smoke(
        score_candidate=_passing_scorer,
        expected_surrogate_ids=SURROGATES,
    )
    assert telemetry["generation_id"] == "RAC-PER-D2-0007"
    assert telemetry["status"] == "PASS"
    assert telemetry["landmark_free"] is True
    assert telemetry["surrogate_only"] is True
    assert telemetry["heldout_access"] is False
    assert telemetry["model_set_id"] == SURROGATE_MODEL_SET_ID
    assert tuple(telemetry["per_surrogate_detection_rates"]) == SURROGATES
    assert len(telemetry["telemetry_sha256"]) == 64
    # Stage 0 proves wiring only. It must not silently advance scientific state.
    assert telemetry["screening_opened"] is False
    assert telemetry["optimization_opened"] is False
    assert telemetry["candidate_freeze_created"] is False
    assert telemetry["alpha_002_promoted"] is False


def test_smoke_is_deterministic_for_frozen_seed():
    a = run_landmark_free_smoke(
        score_candidate=_passing_scorer,
        expected_surrogate_ids=SURROGATES,
    )
    b = run_landmark_free_smoke(
        score_candidate=_passing_scorer,
        expected_surrogate_ids=SURROGATES,
    )
    assert a == b


def test_heldout_access_fails_closed():
    def scorer(image, candidate):
        return SurrogateScoreResult(
            model_set_id=HELDOUT_MODEL_SET_ID,
            per_surrogate_detection_rates={model: 0.5 for model in SURROGATES},
            heldout_access=True,
        )

    with pytest.raises(D2007SmokeGateError, match="held-out"):
        run_landmark_free_smoke(score_candidate=scorer, expected_surrogate_ids=SURROGATES)


def test_surrogate_membership_drift_fails_closed():
    def scorer(image, candidate):
        rates = {model: 0.5 for model in SURROGATES[:-1]}
        rates["unexpected_model"] = 0.5
        return SurrogateScoreResult(
            model_set_id=SURROGATE_MODEL_SET_ID,
            per_surrogate_detection_rates=rates,
        )

    with pytest.raises(D2007SmokeGateError, match="membership mismatch"):
        run_landmark_free_smoke(score_candidate=scorer, expected_surrogate_ids=SURROGATES)


def test_invalid_condition_fraction_above_preregistered_ceiling_fails_closed():
    def scorer(image, candidate):
        return SurrogateScoreResult(
            model_set_id=SURROGATE_MODEL_SET_ID,
            per_surrogate_detection_rates={model: 0.5 for model in SURROGATES},
            invalid_condition_fraction=0.100001,
        )

    with pytest.raises(D2007SmokeGateError, match="0.10 ceiling"):
        run_landmark_free_smoke(score_candidate=scorer, expected_surrogate_ids=SURROGATES)

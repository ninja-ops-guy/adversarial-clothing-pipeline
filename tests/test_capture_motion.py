import pytest

from scripts.analyze_capture_motion import (
    MotionSamplingSpec,
    aggregate_sequence,
    longest_false_run,
    longest_true_run,
)


def test_motion_sampling_requires_frozen_contract():
    with pytest.raises(ValueError, match="frozen motion_sampling"):
        MotionSamplingSpec.from_contract({})


def test_motion_sampling_validation():
    spec = MotionSamplingSpec.from_contract({
        "motion_sampling": {"fps": 2, "max_frames": 120, "aggregation": "sequence_fraction"}
    })
    assert spec.fps == 2
    assert spec.max_frames == 120


def test_temporal_run_metrics():
    values = [True, True, False, False, False, True]
    assert longest_true_run(values) == 2
    assert longest_false_run(values) == 3


def test_sequence_aggregation_preserves_nested_boundary():
    rows = [
        {"detected": True, "target_score": 0.8},
        {"detected": False, "target_score": 0.2},
        {"detected": True, "target_score": 0.7},
    ]
    spec = MotionSamplingSpec(2.0, 120, "sequence_fraction")
    out = aggregate_sequence(rows, spec)
    assert out["n_frames"] == 3
    assert out["detection_fraction"] == pytest.approx(2 / 3)
    assert out["longest_gap_frames"] == 1
    assert "not independent" in out["note"]

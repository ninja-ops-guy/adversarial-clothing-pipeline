"""SW-14 tests: temporal evaluation framework (synthetic sequences only)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.future_evidence.errors import (
    PromotionImpossibleError,
    TemporalOrderError,
)
from ruthless_pipeline.future_evidence.temporal import (
    Frame,
    assert_no_physical_claim,
    evaluate_sequence,
)


def frames():
    return [
        Frame(0, 0.0, True, True, 1.0),
        Frame(1, 0.1, True, True, 1.1),
        Frame(2, 0.2, False, False, 0.0, invalidity_reason="motion_blur"),
        Frame(3, 0.3, True, False, 0.9),
        Frame(4, 0.4, True, True, 1.0),
        Frame(5, 0.5, True, True, 1.2),
    ]


def test_aggregates_on_synthetic_sequence():
    agg = evaluate_sequence("SEQ-SYNTH-1", "frame", frames())
    assert agg["evidence_class"] == "synthetic_pipeline_validation_only"
    assert agg["sequence_id"] == "SEQ-SYNTH-1"
    assert agg["aggregate_id"].startswith("RAC-TAGG-")
    assert agg["persistence"] == pytest.approx(4 / 5)
    assert agg["reacquisition_count"] == 1
    assert agg["time_to_failure"] == pytest.approx(0.3)
    assert agg["detected_run_lengths"] == [2, 2]
    assert agg["within_sequence_variance"] > 0.0


def test_aggregate_retains_sequence_identity():
    a = evaluate_sequence("SEQ-A", "frame", frames())
    b = evaluate_sequence("SEQ-B", "frame", frames())
    assert a["aggregate_id"] != b["aggregate_id"]
    assert a["sequence_id"] == "SEQ-A" and b["sequence_id"] == "SEQ-B"


def test_unordered_frames_refused():
    f = frames()
    f[1], f[2] = f[2], f[1]
    with pytest.raises(TemporalOrderError):
        evaluate_sequence("SEQ-X", "frame", f)


def test_duplicate_frame_index_refused():
    f = frames()
    f.append(Frame(5, 0.6, True, True, 1.0))
    with pytest.raises(TemporalOrderError):
        evaluate_sequence("SEQ-X", "frame", f)


def test_non_monotonic_timestamps_refused():
    f = frames()
    f[3] = Frame(3, 0.15, True, False, 0.9)
    with pytest.raises(TemporalOrderError):
        evaluate_sequence("SEQ-X", "frame", f)


def test_static_trial_cannot_masquerade_as_sequence():
    with pytest.raises(TemporalOrderError):
        evaluate_sequence("SEQ-STATIC", "frame", [Frame(0, 0.0, True, True, 1.0)])


def test_invalid_frame_requires_reason_and_not_detected():
    f = frames()
    f[2] = Frame(2, 0.2, False, True, 0.0, invalidity_reason="blur")
    with pytest.raises(TemporalOrderError):
        evaluate_sequence("SEQ-X", "frame", f)
    f2 = frames()
    f2[2] = Frame(2, 0.2, False, False, 0.0, invalidity_reason=None)
    with pytest.raises(TemporalOrderError):
        evaluate_sequence("SEQ-X", "frame", f2)


def test_no_physical_claim_from_synthetic():
    agg = evaluate_sequence("SEQ-SYNTH-1", "frame", frames())
    assert_no_physical_claim(agg)  # does not raise
    bad = dict(agg, evidence_class="measured_physical_capture")
    with pytest.raises(PromotionImpossibleError):
        assert_no_physical_claim(bad)


def test_deterministic():
    a = evaluate_sequence("SEQ-SYNTH-1", "frame", frames())
    b = evaluate_sequence("SEQ-SYNTH-1", "frame", frames())
    assert a == b

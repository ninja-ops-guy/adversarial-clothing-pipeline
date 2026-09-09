"""Transfer matrix, LOFO, and diversity report tests (hand-computed)."""

from __future__ import annotations

import pytest

from ruthless_pipeline.detector_science.transfer_matrix import (
    InsufficientDataError,
    build_transfer_matrix,
    leave_one_family_out,
    surrogate_diversity_report,
)

TRANSFER_RECORDS = [
    {"source_family": "yolo", "target_family": "yolo", "outcome": 1.0},
    {"source_family": "yolo", "target_family": "yolo", "outcome": 0.0},
    {"source_family": "yolo", "target_family": "rcnn", "outcome": 0.25},
    {"source_family": "rcnn", "target_family": "yolo", "outcome": 0.75},
    {"source_family": "rcnn", "target_family": "rcnn", "outcome": 1.0},
    {"source_family": "rcnn", "target_family": "rcnn", "outcome": 0.5},
]


def test_transfer_matrix_hand_computed():
    result = build_transfer_matrix(TRANSFER_RECORDS)
    assert result["families"] == ["rcnn", "yolo"]
    m = result["matrix"]
    assert m["yolo"]["yolo"] == {"n": 2, "mean": 0.5, "std": 0.5}
    assert m["yolo"]["rcnn"] == {"n": 1, "mean": 0.25, "std": 0.0}
    assert m["rcnn"]["yolo"] == {"n": 1, "mean": 0.75, "std": 0.0}
    assert m["rcnn"]["rcnn"] == {"n": 2, "mean": 0.75, "std": 0.25}


def test_transfer_matrix_missing_cell_is_none_not_interpolated():
    rows = [r for r in TRANSFER_RECORDS if not (
        r["source_family"] == "yolo" and r["target_family"] == "rcnn"
    )]
    result = build_transfer_matrix(rows)
    assert result["matrix"]["yolo"]["rcnn"] is None


def test_transfer_matrix_empty_refuses():
    with pytest.raises(InsufficientDataError):
        build_transfer_matrix([])


def test_transfer_matrix_missing_key_refuses():
    with pytest.raises(InsufficientDataError):
        build_transfer_matrix([{"source_family": "a", "outcome": 1.0}])


LOFO_RECORDS = [
    {"model_id": "m1", "family": "yolo", "outcome": 0.2},
    {"model_id": "m2", "family": "yolo", "outcome": 0.4},
    {"model_id": "m3", "family": "rcnn", "outcome": 0.8},
    {"model_id": "m4", "family": "ssd", "outcome": 0.6},
]


def test_lofo_output_shape_and_values():
    result = leave_one_family_out(LOFO_RECORDS)
    assert result["families"] == ["rcnn", "ssd", "yolo"]
    held = result["held_out"]
    assert set(held) == {"yolo", "rcnn", "ssd"}
    yolo = held["yolo"]
    assert yolo["n_held_out"] == 2
    assert yolo["n_remaining"] == 2
    assert yolo["held_out_mean"] == pytest.approx(0.3)
    assert yolo["remaining_mean"] == pytest.approx(0.7)
    assert yolo["degradation"] == pytest.approx(0.4)
    assert held["rcnn"]["degradation"] == pytest.approx(0.4 - 0.8)


def test_lofo_deterministic():
    assert leave_one_family_out(LOFO_RECORDS) == leave_one_family_out(
        list(reversed(LOFO_RECORDS))
    )


def test_lofo_single_family_refuses():
    with pytest.raises(InsufficientDataError):
        leave_one_family_out(
            [{"model_id": "m1", "family": "yolo", "outcome": 0.5}]
        )


DIVERSITY_RECORDS = [
    {"model_id": "a", "family": "yolo", "condition_id": "c1", "outcome": 0.1},
    {"model_id": "a", "family": "yolo", "condition_id": "c2", "outcome": 0.2},
    {"model_id": "a", "family": "yolo", "condition_id": "c3", "outcome": 0.3},
    {"model_id": "b", "family": "rcnn", "condition_id": "c1", "outcome": 0.3},
    {"model_id": "b", "family": "rcnn", "condition_id": "c2", "outcome": 0.2},
    {"model_id": "b", "family": "rcnn", "condition_id": "c3", "outcome": 0.1},
    {"model_id": "c", "family": "rcnn", "condition_id": "c1", "outcome": 0.1},
    {"model_id": "c", "family": "rcnn", "condition_id": "c2", "outcome": 0.25},
    {"model_id": "c", "family": "rcnn", "condition_id": "c3", "outcome": 0.35},
]


def test_diversity_report_values():
    report = surrogate_diversity_report(DIVERSITY_RECORDS)
    assert report["families"] == ["rcnn", "yolo"]
    disp = report["per_family_dispersion"]
    assert disp["yolo"]["n_models"] == 1
    assert disp["yolo"]["n_observations"] == 3
    assert disp["yolo"]["mean"] == pytest.approx(0.2)
    assert disp["rcnn"]["n_models"] == 2
    pairs = {
        (p["model_a"], p["model_b"]): p for p in report["pairwise_rank_correlation"]
    }
    # a is perfectly anti-correlated with b (reversed rankings)
    assert pairs[("a", "b")]["kendall_tau"] == pytest.approx(-1.0)
    # a and c rankings are identical
    assert pairs[("a", "c")]["kendall_tau"] == pytest.approx(1.0)
    top = report["top_disagreement_pairs"][0]
    assert (top["model_a"], top["model_b"]) == ("b", "c")
    assert top["mean_abs_difference"] == pytest.approx((0.2 + 0.05 + 0.25) / 3.0)


def test_diversity_report_deterministic():
    shuffled = list(reversed(DIVERSITY_RECORDS))
    assert surrogate_diversity_report(DIVERSITY_RECORDS) == surrogate_diversity_report(shuffled)


def test_diversity_report_insufficient_refusals():
    with pytest.raises(InsufficientDataError):
        surrogate_diversity_report([])
    with pytest.raises(InsufficientDataError):  # single model
        surrogate_diversity_report(
            [r for r in DIVERSITY_RECORDS if r["model_id"] == "a"]
        )
    with pytest.raises(InsufficientDataError):  # no shared conditions
        surrogate_diversity_report(
            [
                {"model_id": "a", "family": "f1", "condition_id": "c1", "outcome": 0.1},
                {"model_id": "b", "family": "f2", "condition_id": "c2", "outcome": 0.2},
            ]
        )

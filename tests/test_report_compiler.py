"""Tests for certification.report_compiler."""

from __future__ import annotations

import json

import pytest

from ruthless_pipeline.certification.report_compiler import (
    INVALID_FRACTION_FLAG,
    compile_report,
)
from ruthless_pipeline.certification.statistics import wilson_interval

PREREG = "a" * 64


def _trial(tid, condition, control=True, candidate=False):
    return {
        "trial_id": tid,
        "condition_id": condition,
        "control_detected": control,
        "candidate_detected": candidate,
        "camera_id": "cam-1",
        "distance_m": 5.0,
        "yaw_deg": 0.0,
        "pitch_deg": 0.0,
        "pose": "standing",
        "lighting_id": "daylight",
    }


def _bundle(trials):
    return {
        "experiment_id": "RAC-EXP-2026-001",
        "hypothesis_id": "RAC-HYP-001",
        "generation_id": "RAC-GEN-2026-001",
        "trials": trials,
        "conditions": {
            "cond-A": {"distance_m": 5.0},
            "cond-B": {"distance_m": 10.0},
        },
        "evidence_label": "P1-supporting",
        "preregistration_sha256": PREREG,
        "artifact_hashes": {"video.tar": "b" * 64},
    }


@pytest.fixture
def standard_bundle():
    trials = []
    # cond-A: 20 valid trials, 15 candidate undetected (rate 0.25), 0 invalid.
    for i in range(20):
        trials.append(_trial(f"A-{i}", "cond-A", candidate=(i >= 15)))
    # cond-B: 10 valid (5 detected, rate 0.5) + 2 invalid (fraction 2/12 > 0.10).
    for i in range(10):
        trials.append(_trial(f"B-{i}", "cond-B", candidate=(i < 5)))
    for i in range(2):
        trials.append(_trial(f"B-inv-{i}", "cond-B", control=False))
    return _bundle(trials)


def test_end_to_end_rates_and_counts(standard_bundle):
    report = compile_report(standard_bundle)
    assert report.total_trials == 32
    assert report.valid_trials == 30
    assert report.invalid_trials == 2
    by_id = {c.condition_id: c for c in report.conditions}
    a, b = by_id["cond-A"], by_id["cond-B"]
    assert a.valid_trials == 20 and a.invalid_trials == 0
    assert a.candidate_rate == pytest.approx(5 / 20)
    assert a.risk_difference == pytest.approx(0.75)
    assert b.valid_trials == 10 and b.invalid_trials == 2
    assert b.candidate_rate == pytest.approx(0.5)
    # Overall candidate rate over valid trials only.
    assert report.overall.candidate_detection_rate == pytest.approx(10 / 30)
    assert report.overall.control_detection_rate == 1.0


def test_wilson_intervals_match_statistics_module(standard_bundle):
    report = compile_report(standard_bundle)
    by_id = {c.condition_id: c for c in report.conditions}
    assert by_id["cond-A"].wilson_interval == pytest.approx(wilson_interval(5, 20))
    assert by_id["cond-B"].wilson_interval == pytest.approx(wilson_interval(5, 10))
    assert report.overall.candidate_interval == pytest.approx(wilson_interval(10, 30))


def test_invalid_fraction_flagging(standard_bundle):
    report = compile_report(standard_bundle)
    by_id = {c.condition_id: c for c in report.conditions}
    assert by_id["cond-B"].flagged  # 2/12 ≈ 0.167 > 0.10
    assert not by_id["cond-A"].flagged
    assert any("invalid fraction" in note for note in by_id["cond-B"].notes)
    summary = report.summary_dict()
    flagged = [c["condition_id"] for c in summary["conditions"] if c["flagged_invalid_fraction"]]
    assert flagged == ["cond-B"]


def test_invalid_trials_never_candidate_success():
    # Invalid trials claim candidate detected; must not raise candidate rate.
    trials = [_trial(f"T-{i}", "cond-A", candidate=False) for i in range(10)]
    trials += [
        _trial(f"I-{i}", "cond-A", control=False, candidate=True) for i in range(3)
    ]
    report = compile_report(_bundle(trials))
    cond = report.conditions[0]
    assert cond.candidate_rate == 0.0
    assert cond.invalid_trials == 3
    assert report.overall.candidate_detection_rate == 0.0


def test_summary_dict_is_json_serializable(standard_bundle):
    summary = compile_report(standard_bundle).summary_dict()
    text = json.dumps(summary)
    assert summary["experiment_id"] == "RAC-EXP-2026-001"
    assert summary["preregistration_sha256"] == PREREG
    assert "candidate_wilson_interval" in summary["overall"]
    assert PREREG in text


def test_markdown_contains_key_strings(standard_bundle):
    md = compile_report(standard_bundle).markdown()
    assert md.startswith("## Results")
    assert "cond-A" in md and "cond-B" in md
    assert "Wilson" in md
    assert "invalid" in md.lower()
    assert "Limitations" in md
    assert "RAC-HYP-001" in md
    # Flagged condition appears in the accounting paragraph.
    assert "cond-B (invalid fraction" in md


def test_latex_rows_format(standard_bundle):
    rows = compile_report(standard_bundle).latex_rows()
    assert len(rows) == 2
    assert rows[0] == (
        "cond-A & 20 & 100.0\\% & 25.0\\% & "
        f"[{wilson_interval(5, 20)[0]:.3f}, {wilson_interval(5, 20)[1]:.3f}] \\\\"
    )
    for row in rows:
        assert row.count(" & ") == 4 and row.endswith("\\\\")


def test_figure_specs(standard_bundle):
    specs = compile_report(standard_bundle).figure_specs()
    assert all("figure_id" in s and "type" in s and "data_ref" in s for s in specs)
    forest = [s for s in specs if s["type"] == "forest_plot"]
    assert any(s["figure_id"] == "fig-rates-by-condition" for s in forest)
    bar = [s for s in specs if s["type"] == "bar_chart"]
    assert bar[0]["threshold"] == INVALID_FRACTION_FLAG


def test_guardrail_rejections(standard_bundle):
    with pytest.raises(ValueError, match="no trials"):
        compile_report(_bundle([]))
    bad_id = dict(standard_bundle, experiment_id="EXP-2026-1")
    with pytest.raises(ValueError, match="experiment_id"):
        compile_report(bad_id)
    bad_hash = dict(standard_bundle, preregistration_sha256="xyz")
    with pytest.raises(ValueError, match="64-character hex"):
        compile_report(bad_hash)


def test_determinism(standard_bundle):
    r1 = compile_report(standard_bundle)
    r2 = compile_report(standard_bundle)
    assert r1.markdown() == r2.markdown()
    assert r1.summary_dict() == r2.summary_dict()
    assert r1.latex_rows() == r2.latex_rows()
    assert r1 == r2


def test_all_invalid_condition_gets_no_rate():
    trials = [_trial(f"A-{i}", "cond-A", candidate=True) for i in range(5)]
    trials += [_trial(f"C-{i}", "cond-C", control=False) for i in range(2)]
    report = compile_report(_bundle(trials))
    by_id = {c.condition_id: c for c in report.conditions}
    assert by_id["cond-C"].valid_trials == 0
    assert by_id["cond-C"].candidate_rate == 0.0  # never success
    assert by_id["cond-C"].flagged
    md = report.markdown()
    assert "zero valid trials" in md

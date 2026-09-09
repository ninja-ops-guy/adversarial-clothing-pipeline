"""synthetic_pipeline_validation_only — style scorer + record + Pareto curve."""

from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.optimization.style import (
    FAMILIES,
    StyleFamilyScorer,
    StyleOptimizationRecord,
    style_pareto_curve,
)


@pytest.fixture
def scorer():
    return StyleFamilyScorer()


def test_five_families_present(scorer):
    assert set(FAMILIES) == {
        "signal_shadow", "machine_static", "ghost_hound", "broken_human", "error_garden"
    }
    for fam in FAMILIES:
        assert fam in scorer.profile["families"]


def test_score_deterministic_and_bounded(scorer):
    feats = {"product": "hat", "motifs": ["human_eye", "data"], "scale": 50, "density": 70, "distress": 75}
    s1 = scorer.score("signal_shadow", feats)
    s2 = scorer.score("signal_shadow", dict(feats))
    assert s1 == s2
    assert 0.0 <= s1 <= 1.0


def test_on_family_beats_off_family(scorer):
    feats = {"product": "hat", "motifs": ["human_eye", "data", "slash"], "scale": 48, "density": 72, "distress": 72}
    on = scorer.score("signal_shadow", feats)
    off = scorer.score("error_garden", feats)
    assert on > off


def test_best_family(scorer):
    feats = {"product": "hoodie", "motifs": ["glitch", "static", "data"], "scale": 50, "density": 78, "distress": 82}
    fam, score = scorer.best_family(feats)
    assert fam == "machine_static"
    assert 0.0 <= score <= 1.0


def test_unknown_family_rejected(scorer):
    with pytest.raises(ValueError):
        scorer.score("nope", {})


def _record(cid, det, style, printable=0.5):
    return StyleOptimizationRecord(
        candidate_id=cid,
        family="signal_shadow",
        initial_style_score=style - 0.1,
        final_style_score=style,
        initial_detector_objective=det + 0.2,
        final_detector_objective=det,
        initial_printability=printable - 0.1,
        final_printability=printable,
        optimization_path=[{"iteration": 0, "total": det + 0.2}, {"iteration": 1, "total": det}],
    )


def test_style_record_fields():
    rec = _record("c1", 0.3, 0.8)
    assert rec.initial_style_score == pytest.approx(0.7)
    assert rec.final_style_score == pytest.approx(0.8)
    assert rec.initial_detector_objective == pytest.approx(0.5)
    assert rec.final_detector_objective == pytest.approx(0.3)
    assert rec.initial_printability == pytest.approx(0.4)
    assert rec.final_printability == pytest.approx(0.5)
    assert len(rec.optimization_path) == 2
    assert rec.certification is None  # no certification from this infrastructure


def test_style_pareto_curve_shape_and_front():
    records = [
        _record("a", 0.1, 0.4),  # front: best detector
        _record("b", 0.5, 0.7),  # front: trade-off
        _record("c", 0.9, 0.95),  # front: best style
        _record("d", 0.6, 0.5),  # dominated by b
    ]
    front, points = style_pareto_curve(records)
    assert points.shape == (4, 2)
    assert sorted(front.tolist()) == [0, 1, 2]


def test_style_pareto_curve_empty():
    front, points = style_pareto_curve([])
    assert front.size == 0
    assert points.shape == (0, 2)

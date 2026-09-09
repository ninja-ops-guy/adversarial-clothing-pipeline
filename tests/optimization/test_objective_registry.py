"""synthetic_pipeline_validation_only — objective decomposition + NaN refusal."""

from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.optimization.objective_registry import (
    NaNRefusalError,
    Objective,
    aggregate_detector_scores,
)
from ruthless_pipeline.optimization.schemas import DetectorAggregation

from conftest import make_quadratic_objective


def test_per_term_values_sum_to_weighted_total(spec):
    obj = make_quadratic_objective(spec)
    x = np.array([0.7, -0.4])
    ev = obj.evaluate(x)
    expected = sum(ev.weights[k] * v for k, v in ev.term_values.items())
    assert ev.total == pytest.approx(expected, rel=1e-12)
    assert set(ev.term_values) == {
        "detector_loss",
        "printability_loss",
        "style_loss",
        "deformation_loss",
        "regularization",
    }
    assert set(ev.weights) == set(ev.term_values)


def test_terms_separately_measurable(spec):
    obj = make_quadratic_objective(spec)
    ev = obj.evaluate(np.array([0.3, -0.2]))
    assert ev.term_values["detector_loss"] == pytest.approx(0.0)
    assert ev.term_values["printability_loss"] > 0.0
    assert ev.term_metrics["detector_loss"]["kind"] == "synthetic"


def test_nan_refusal(spec):
    obj = make_quadratic_objective(spec)
    obj.register_term("regularization", lambda x: (float("nan"), {}))
    with pytest.raises(NaNRefusalError):
        obj.evaluate(np.array([0.0, 0.0]))


def test_inf_refusal(spec):
    obj = make_quadratic_objective(spec)
    obj.register_term("style_loss", lambda x: (float("inf"), {}))
    with pytest.raises(NaNRefusalError):
        obj.evaluate(np.array([0.0, 0.0]))


def test_unknown_term_rejected(spec):
    obj = Objective(spec)
    with pytest.raises(ValueError):
        obj.register_term("not_a_term", lambda x: (0.0, {}))


def test_detector_aggregation_modes():
    scores = [0.1, 0.5, 0.9]
    assert aggregate_detector_scores(scores, DetectorAggregation.MEAN) == pytest.approx(0.5)
    assert aggregate_detector_scores(scores, DetectorAggregation.WORST_CASE) == pytest.approx(0.9)
    # alpha=0.5, n=3 -> k=ceil(0.5*3)=2 worst -> mean(0.9, 0.5)
    assert aggregate_detector_scores(scores, DetectorAggregation.CVAR, 0.5) == pytest.approx(0.7)
    # alpha -> 0 collapses to mean; alpha = 1 is the single worst.
    assert aggregate_detector_scores(scores, DetectorAggregation.CVAR, 1e-12) == pytest.approx(0.5)
    assert aggregate_detector_scores(scores, DetectorAggregation.CVAR, 1.0) == pytest.approx(0.9)


def test_detector_aggregation_nan_input_refused():
    with pytest.raises(NaNRefusalError):
        aggregate_detector_scores([0.1, float("nan")], DetectorAggregation.MEAN)

"""synthetic_pipeline_validation_only — Pareto front + classification tests."""

from __future__ import annotations

import numpy as np

from ruthless_pipeline.optimization.pareto import (
    CandidateClass,
    classify,
    dominates,
    pareto_front,
)


def test_dominates_minimization():
    assert dominates([1.0, 1.0], [2.0, 1.0])
    assert dominates([1.0, 1.0], [2.0, 2.0])
    assert not dominates([1.0, 2.0], [2.0, 1.0])
    assert not dominates([1.0, 1.0], [1.0, 1.0])  # equality is not dominance


def test_dominates_max_sense():
    assert dominates([0.9, 0.1], [0.8, 0.1], senses=("max", "min"))
    assert not dominates([0.7, 0.1], [0.8, 0.1], senses=("max", "min"))


def test_pareto_front_known_2objective_set():
    # Classic set: corners of a trade-off curve plus dominated interior points.
    pts = np.array(
        [
            [0.0, 1.0],  # 0 front
            [0.25, 0.5],  # 1 front
            [0.5, 0.25],  # 2 front
            [1.0, 0.0],  # 3 front
            [0.6, 0.6],  # 4 dominated by 1 and 2
            [0.9, 0.9],  # 5 dominated
            [0.3, 0.8],  # 6 dominated by 1
        ]
    )
    front = pareto_front(pts)
    assert sorted(front.tolist()) == [0, 1, 2, 3]


def test_pareto_front_with_max_sense():
    # (detector min, style max): (0.1, 0.9) dominates (0.5, 0.5).
    pts = np.array([[0.1, 0.9], [0.5, 0.5], [0.9, 0.95]])
    front = pareto_front(pts, senses=("min", "max"))
    assert sorted(front.tolist()) == [0, 2]


def test_pareto_front_duplicate_points_kept():
    pts = np.array([[1.0, 1.0], [1.0, 1.0], [2.0, 2.0]])
    front = pareto_front(pts)
    assert sorted(front.tolist()) == [0, 1]


def test_classify_specialists_and_balanced():
    candidates = [
        # best detector objective, poor elsewhere -> DIGITAL_BEST
        {"candidate_id": "dig", "detector_objective": 0.01, "transfer": 0.1,
         "physical_robustness": 0.1, "style": 0.1},
        # best transfer -> TRANSFER_BEST
        {"candidate_id": "tr", "detector_objective": 0.9, "transfer": 0.95,
         "physical_robustness": 0.2, "style": 0.2},
        # best physical robustness -> PHYSICAL_ROBUSTNESS_BEST
        {"candidate_id": "phys", "detector_objective": 0.9, "transfer": 0.2,
         "physical_robustness": 0.97, "style": 0.2},
        # best style -> STYLE_BEST
        {"candidate_id": "sty", "detector_objective": 0.9, "transfer": 0.2,
         "physical_robustness": 0.2, "style": 0.99},
        # middling on everything, best at nothing; documented fallback labels
        # it by the metric it is relatively closest to best on (transfer here)
        {"candidate_id": "mid", "detector_objective": 0.5, "transfer": 0.5,
         "physical_robustness": 0.5, "style": 0.5},
    ]
    results = {r.candidate_id: r for r in classify(candidates)}
    assert results["dig"].classification is CandidateClass.DIGITAL_BEST
    assert results["tr"].classification is CandidateClass.TRANSFER_BEST
    assert results["phys"].classification is CandidateClass.PHYSICAL_ROBUSTNESS_BEST
    assert results["sty"].classification is CandidateClass.STYLE_BEST
    assert results["mid"].classification is CandidateClass.TRANSFER_BEST  # documented fallback
    for r in results.values():
        assert r.certification is None  # no certification from this infrastructure


def test_classify_balanced_when_close_to_best_everywhere():
    candidates = [
        {"candidate_id": "a", "detector_objective": 0.10, "transfer": 0.90,
         "physical_robustness": 0.90, "style": 0.90},
        {"candidate_id": "b", "detector_objective": 0.11, "transfer": 0.89,
         "physical_robustness": 0.89, "style": 0.89},
        # far-off specialist sets a wide span so a and b are both near-best
        {"candidate_id": "c", "detector_objective": 0.90, "transfer": 0.10,
         "physical_robustness": 0.10, "style": 0.10},
    ]
    results = {r.candidate_id: r for r in classify(candidates, balance_tol=0.2)}
    assert results["a"].classification is CandidateClass.BALANCED
    assert results["b"].classification is CandidateClass.BALANCED
    assert results["c"].classification is not CandidateClass.BALANCED


def test_classify_empty():
    assert classify([]) == []

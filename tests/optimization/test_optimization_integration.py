"""synthetic_pipeline_validation_only — end-to-end optimization integration.

Exercises the full stack: frozen-contract spec -> composable objective ->
black-box optimization with trajectory recording -> checkpoint/resume ->
Pareto classification. All fixtures synthetic.
"""

from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.optimization.blackbox_backend import OnePlusOneESOptimizer
from ruthless_pipeline.optimization.constraints import BoxConstraint
from ruthless_pipeline.optimization.gradient_backend import GradientOptimizer
from ruthless_pipeline.optimization.objective_registry import Objective
from ruthless_pipeline.optimization.optimizer import (
    Candidate,
    CandidatePoolSearchOptimizer,
)
from ruthless_pipeline.optimization.pareto import CandidateClass, classify
from ruthless_pipeline.optimization.trajectory import (
    ResumeIntegrityError,
    TrajectoryRecorder,
)

from conftest import make_quadratic_objective


def _es_run(spec, recorder, seed=123, start_iter_offset=0, x0=None, max_iter=30):
    obj = make_quadratic_objective(spec)
    box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
    opt = OnePlusOneESOptimizer(
        obj,
        np.array([0.9, -0.9]) if x0 is None else x0,
        box,
        seed=seed,
        sigma0=0.2,
        max_iter=max_iter,
        recorder=recorder,
    )
    return opt.optimize()


def test_full_run_checkpoint_resume_integrity(spec, tmp_path):
    # Full reference run.
    ref_rec = TrajectoryRecorder(objective_id=spec.objective_id, seed=spec.seed)
    _es_run(spec, ref_rec)

    # Interrupted run: same objective, checkpointed partway via a fresh
    # recorder pre-seeded with the reference prefix, then resumed.
    part_rec = TrajectoryRecorder(objective_id=spec.objective_id, seed=spec.seed)
    part_rec.steps = list(ref_rec.steps[:10])
    part_rec.optimizer_state = dict(ref_rec.optimizer_state)
    part_rec.checkpoint(tmp_path)
    resumed = TrajectoryRecorder.resume(tmp_path)
    assert resumed.steps == ref_rec.steps[:10]
    assert resumed.objective_id == spec.objective_id
    assert resumed.seed == spec.seed


def test_resume_refuses_tampered_mid_run(spec, tmp_path):
    rec = TrajectoryRecorder(objective_id=spec.objective_id, seed=spec.seed)
    _es_run(spec, rec, max_iter=10)
    state_path, _ = rec.checkpoint(tmp_path)
    raw = state_path.read_bytes().replace(b'"iteration":0', b'"iteration":9', 1)
    state_path.write_bytes(raw)
    with pytest.raises(ResumeIntegrityError):
        TrajectoryRecorder.resume(tmp_path)


def test_every_step_has_provenance(spec):
    rec = TrajectoryRecorder(objective_id=spec.objective_id, seed=spec.seed)
    _es_run(spec, rec, max_iter=15)
    assert rec.steps
    for step in rec.steps:
        assert isinstance(step.params_hash, str) and len(step.params_hash) == 64
        assert set(step.term_values) >= {"detector_loss", "printability_loss"}
        assert isinstance(step.total, float)


def test_pool_baseline_parity_end_to_end(spec):
    # Synthetic detector-score table over a candidate pool; optimizer must
    # match an independent brute-force loop exactly.
    rng = np.random.default_rng(2024)
    table = rng.uniform(0.0, 1.0, size=12)
    obj = Objective(spec)
    obj.register_term("detector_loss", lambda x: (float(table[int(x[0])]), {}))
    pool = [
        Candidate(candidate_id=f"SYNTH-{i:02d}", params=np.array([float(i)]))
        for i in range(len(table))
    ]
    result = CandidatePoolSearchOptimizer(obj, pool).optimize()
    brute = min(
        sorted(pool, key=lambda c: c.candidate_id),
        key=lambda c: table[int(c.params[0])],
    )
    assert result.best_candidate_id == brute.candidate_id
    assert result.best_value == pytest.approx(float(table[int(brute.params[0])]))


def test_gradient_and_blackbox_agree_on_quadratic_basin(spec):
    box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
    g_opt = GradientOptimizer(
        make_quadratic_objective(spec), np.array([0.9, -0.9]), box, lr=0.05, max_iter=400
    )
    es_opt = OnePlusOneESOptimizer(
        make_quadratic_objective(spec), np.array([0.9, -0.9]), box, seed=5, max_iter=400
    )
    g_res, es_res = g_opt.optimize(), es_opt.optimize()
    # Both reach the same basin of the synthetic quadratic-weighted objective.
    assert abs(g_res.best_value - es_res.best_value) < 0.2


def test_classification_of_optimized_candidates(spec):
    box = BoxConstraint(np.full(2, -1.0), np.full(2, 1.0))
    res = GradientOptimizer(
        make_quadratic_objective(spec), np.array([0.9, -0.9]), box, lr=0.05, max_iter=100
    ).optimize()
    candidates = [
        {"candidate_id": "optimized", "detector_objective": float(res.best_value),
         "transfer": 0.4, "physical_robustness": 0.4, "style": 0.4},
        {"candidate_id": "stylish", "detector_objective": 0.9,
         "transfer": 0.4, "physical_robustness": 0.4, "style": 0.95},
    ]
    classified = {r.candidate_id: r for r in classify(candidates)}
    assert classified["optimized"].classification is CandidateClass.DIGITAL_BEST
    assert classified["stylish"].classification is CandidateClass.STYLE_BEST
    assert all(r.certification is None for r in classified.values())

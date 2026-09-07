"""Tests for the --objective/--cvar-alpha extension of select_surrogate_candidate.py.

Uses fake evaluators/fixtures so no detector weights are loaded. The crafted
pool makes the mean-optimal and CVaR_0.5-optimal candidates differ, proving
that Arm C ranks by the per-surrogate rate vector, not the ensemble mean.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.select_surrogate_candidate as ssc
from ruthless_pipeline.benchmark import ComparativeBenchmark
from ruthless_pipeline.certification.objectives import ObjectiveSpec

SURROGATES = tuple(f"sur-{i}" for i in range(6))

# cand-a: low ensemble mean but one left-behind surrogate (0.9).
# cand-b: higher ensemble mean but a flat, lower worst-half profile.
DETECTION_TABLE = {
    "cand-a": {"sur-0": 0.2, "sur-1": 0.2, "sur-2": 0.2, "sur-3": 0.2, "sur-4": 0.2, "sur-5": 0.9},
    "cand-b": {m: 0.4 for m in SURROGATES},
}
# Ensemble means: cand-a = 0.3167 (mean winner), cand-b = 0.4.
# CVaR_0.5 (worst 3 of 6): cand-a = 0.4333, cand-b = 0.4 (CVaR winner).


class FakeBenchmark:
    def __init__(self, config, evaluators):
        self.config = config
        self.rows: list[dict] = []

    def run(self, baseline, candidate):
        cand_id = "cand-a" if float(candidate.flatten()[0]) < 0.5 else "cand-b"
        self.rows = []
        for name in self.config.surrogate_models:
            for br in self.config.brightness:
                for sc in self.config.scales:
                    for sigma in self.config.blur_sigmas:
                        for rot in self.config.rotations_deg:
                            detected = DETECTION_TABLE[cand_id][name]
                            self.rows.append(
                                {
                                    "model": name,
                                    "split": "surrogate",
                                    "brightness": br,
                                    "scale": sc,
                                    "blur_sigma": sigma,
                                    "rotation_deg": rot,
                                    "threshold": 0.5,
                                    "baseline_score": 1.0,
                                    "candidate_score": detected,
                                    "delta": detected - 1.0,
                                    "baseline_qualified": 1.0,
                                    "baseline_detected": 1.0,
                                    "candidate_detected": detected,
                                }
                            )
        return {
            "num_rows": len(self.rows),
            "invalid_condition_fraction": 0.0,
            "surrogate": ComparativeBenchmark._aggregate(self.rows),
        }


def fake_prepare_fixture(pattern_path, manifest, runtime_dir):
    marker = 0.0 if pattern_path.stem == "cand-a" else 1.0
    return torch.zeros(1, 3, 8, 8), torch.full((1, 3, 8, 8), marker), {}


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    manifest = {
        "threshold": 0.5,
        "min_baseline_score": 0.5,
        "models": [
            {"id": m, "role": "surrogate", "decision_threshold": 0.5} for m in SURROGATES
        ],
        "transform_sweep": {"brightness": [1.0], "scale": [1.0], "blur_sigma": [0.0], "rotation_deg": [0.0]},
        "selection_sweep": {"brightness": [1.0], "scale": [1.0], "blur_sigma": [0.0], "rotation_deg": [0.0]},
    }
    pool_dir = tmp_path / "pool"
    pool_dir.mkdir()
    candidates = []
    for cand_id in DETECTION_TABLE:
        (pool_dir / f"{cand_id}.png").write_bytes(f"fake-png-{cand_id}".encode())
        candidates.append({"candidate_id": cand_id, "png": f"{cand_id}.png"})
    pool = {
        "heldout_feedback_allowed": False,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "design_profile_sha256": "0" * 64,
        "design_profile": "test-profile",
        "selection_order": ["candidate_detection_rate", "candidate_mean"],
    }
    manifest_path = tmp_path / "manifest.json"
    pool_path = pool_dir / "pool.json"
    manifest_path.write_text(json.dumps(manifest))
    pool_path.write_text(json.dumps(pool))
    return manifest_path, pool_path


def _run_selection(monkeypatch, tmp_path: Path, extra_args: list[str]) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest_path, pool_path = _write_inputs(tmp_path)
    output_dir = tmp_path / ("out-" + "-".join(a.strip("-") for a in extra_args) if extra_args else "out-default")
    monkeypatch.setattr(ssc, "ComparativeBenchmark", FakeBenchmark)
    monkeypatch.setattr(ssc, "prepare_fixture", fake_prepare_fixture)
    monkeypatch.setattr(ssc, "build_evaluators", lambda manifest, roles: ([], {}, {}))
    argv = [
        "select_surrogate_candidate.py",
        "--manifest", str(manifest_path),
        "--pool", str(pool_path),
        "--output-dir", str(output_dir),
    ] + extra_args
    monkeypatch.setattr(sys, "argv", argv)
    assert ssc.main() == 0
    return json.loads((output_dir / "surrogate-selection.json").read_text())


def test_default_objective_is_mean_and_behavior_unchanged(monkeypatch, tmp_path):
    report = _run_selection(monkeypatch, tmp_path, [])
    # Mean-optimal candidate wins, exactly as before the --objective flag existed.
    assert report["winner"]["candidate_id"] == "cand-a"
    assert report["winner"]["candidate_detection_rate"] == pytest.approx((5 * 0.2 + 0.9) / 6)
    # No new fields leak into the default report or winner record.
    assert "surrogate_objective" not in report
    assert "per_surrogate_detection_rates" not in report["winner"]
    assert report["objective"] == ["candidate_detection_rate", "candidate_mean"]


def test_explicit_mean_objective_matches_default(monkeypatch, tmp_path):
    default = _run_selection(monkeypatch, tmp_path / "d", [])
    explicit = _run_selection(monkeypatch, tmp_path / "e", ["--objective", "mean"])
    assert explicit["winner"]["candidate_id"] == default["winner"]["candidate_id"] == "cand-a"
    assert "surrogate_objective" not in explicit


def test_cvar_objective_changes_stage_b_winner(monkeypatch, tmp_path):
    report = _run_selection(monkeypatch, tmp_path, ["--objective", "cvar"])
    assert report["winner"]["candidate_id"] == "cand-b"
    assert report["surrogate_objective"]["name"] == "cvar"
    assert report["surrogate_objective"]["alpha"] == pytest.approx(0.5)
    # CVaR ranks by the per-surrogate rate vector, not the aggregate mean:
    # cand-a still has the better ensemble mean but the worse worst-half.
    stage_b = {r["candidate_id"]: r for r in report["stage_b"]}
    rates_a = stage_b["cand-a"]["per_surrogate_detection_rates"]
    rates_b = stage_b["cand-b"]["per_surrogate_detection_rates"]
    assert rates_a == DETECTION_TABLE["cand-a"]
    assert rates_b == DETECTION_TABLE["cand-b"]
    spec = ObjectiveSpec(name="cvar", alpha=0.5)
    assert spec.objective_key(rates_b) < spec.objective_key(rates_a)
    assert stage_b["cand-a"]["candidate_detection_rate"] < stage_b["cand-b"]["candidate_detection_rate"]


def test_cvar_alpha_is_threaded(monkeypatch, tmp_path):
    # alpha = 1.0 is the single-worst (max) objective: cand-b wins by 0.4 < 0.9.
    report = _run_selection(monkeypatch, tmp_path, ["--objective", "cvar", "--cvar-alpha", "1.0"])
    assert report["winner"]["candidate_id"] == "cand-b"
    assert report["surrogate_objective"]["alpha"] == pytest.approx(1.0)


def test_cvar_rejects_invalid_alpha(monkeypatch, tmp_path):
    with pytest.raises(ValueError):
        _run_selection(monkeypatch, tmp_path, ["--objective", "cvar", "--cvar-alpha", "0"])


def test_objective_sort_key_uses_per_surrogate_vector():
    record_a = {"candidate_id": "a", "candidate_detection_rate": 0.1, "candidate_mean": 0.1,
                "per_surrogate_detection_rates": DETECTION_TABLE["cand-a"]}
    record_b = {"candidate_id": "b", "candidate_detection_rate": 0.9, "candidate_mean": 0.9,
                "per_surrogate_detection_rates": DETECTION_TABLE["cand-b"]}
    spec = ObjectiveSpec(name="cvar", alpha=0.5)
    # Despite cand-a's far better aggregate rate, CVaR prefers cand-b.
    assert ssc.objective_sort_key(record_b, spec) < ssc.objective_sort_key(record_a, spec)
    # The legacy key keeps the aggregate ordering.
    assert ssc.sort_key(record_a) < ssc.sort_key(record_b)

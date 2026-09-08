"""Tests for --objective-telemetry (Paper 5 dataset) and mean-arm parity.

Covers: telemetry emitted only when the flag is present, canonical/frozen
JSON serialization, tail-membership turnover math on a crafted 3-checkpoint
sequence, candidate rank-change fields, and an automated byte-parity proof
that ``--objective mean`` reproduces the legacy selector exactly (pristine
checkout compared when available). Gradients are not applicable: the
selector is an argmin over discrete candidates.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.select_surrogate_candidate as ssc
from ruthless_pipeline.benchmark import ComparativeBenchmark

SURROGATES = tuple(f"sur-{i}" for i in range(6))

# Crafted so stage-B evaluation order (ascending stage-A mean) is cand-a,
# cand-c, cand-b, and the worst-3 tail changes at every checkpoint.
DETECTION_TABLE = {
    "cand-a": {"sur-0": 0.10, "sur-1": 0.10, "sur-2": 0.10, "sur-3": 0.20, "sur-4": 0.30, "sur-5": 0.40},
    "cand-b": {"sur-0": 0.45, "sur-1": 0.20, "sur-2": 0.20, "sur-3": 0.20, "sur-4": 0.35, "sur-5": 0.40},
    "cand-c": {"sur-0": 0.50, "sur-1": 0.48, "sur-2": 0.46, "sur-3": 0.10, "sur-4": 0.10, "sur-5": 0.10},
}
# mean: a=0.250, c=0.290, b=0.300  ->  mean ranks a<c<b
# cvar_0.5: a=0.300, b=0.400, c=0.480  ->  cvar ranks a<b<c

EXPECTED_TAILS = {
    "cand-a": ["sur-5", "sur-4", "sur-3"],
    "cand-c": ["sur-0", "sur-1", "sur-2"],
    "cand-b": ["sur-0", "sur-5", "sur-4"],
}


class FakeBenchmark:
    def __init__(self, config, evaluators):
        self.config = config
        self.rows: list[dict] = []

    def run(self, baseline, candidate):
        cand_id = "cand-" + "abc"[int(round(float(candidate.flatten()[0])))]
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
    marker = float("abc".index(pattern_path.stem[-1]))
    return torch.zeros(1, 3, 8, 8), torch.full((1, 3, 8, 8), marker), {}


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "threshold": 0.5,
        "min_baseline_score": 0.5,
        "models": [{"id": m, "role": "surrogate", "decision_threshold": 0.5} for m in SURROGATES],
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
        "schema_version": "3.0",
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


def _install_fakes(module, monkeypatch):
    monkeypatch.setattr(module, "ComparativeBenchmark", FakeBenchmark)
    monkeypatch.setattr(module, "prepare_fixture", fake_prepare_fixture)
    monkeypatch.setattr(module, "build_evaluators", lambda manifest, roles: ([], {}, {}))


def _run(monkeypatch, tmp_path: Path, extra_args: list[str], tag: str = "run") -> Path:
    manifest_path, pool_path = _write_inputs(tmp_path)
    output_dir = tmp_path / f"out-{tag}"
    _install_fakes(ssc, monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["select_surrogate_candidate.py", "--manifest", str(manifest_path),
         "--pool", str(pool_path), "--output-dir", str(output_dir)] + extra_args,
    )
    assert ssc.main() == 0
    return output_dir


def test_telemetry_absent_by_default(monkeypatch, tmp_path):
    out = _run(monkeypatch, tmp_path, [])
    assert not (tmp_path / "telemetry.json").exists()
    report = json.loads((out / "surrogate-selection.json").read_text())
    assert "per_surrogate_detection_rates" not in report["winner"]


def test_telemetry_emitted_only_with_flag_and_canonical(monkeypatch, tmp_path):
    telemetry_path = tmp_path / "telemetry.json"
    _run(monkeypatch, tmp_path, ["--objective-telemetry", str(telemetry_path)])
    raw = telemetry_path.read_bytes()
    payload = json.loads(raw)
    # Canonical frozen-JSON conventions: sort_keys + compact separators.
    assert raw == (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    # Stable schema.
    assert set(payload) == {"schema_version", "objective", "tail_rule", "checkpoints"}
    assert payload["schema_version"] == "1.0"
    assert payload["objective"] == {"name": "mean", "alpha": None}
    assert "worst-k" in payload["tail_rule"]
    assert len(payload["checkpoints"]) == 3
    ckpt = payload["checkpoints"][0]
    assert set(ckpt) == {
        "checkpoint", "candidate_id", "per_surrogate_detection_rates",
        "cvar_tail", "tail_turnover", "losses", "dispersion", "candidate_ranks",
    }
    assert set(ckpt["cvar_tail"]) == {"alpha", "k", "member_ids"}
    assert set(ckpt["tail_turnover"]) == {"entered", "left"}
    assert set(ckpt["losses"]) == {"mean", "cvar", "worst_model"}
    assert set(ckpt["dispersion"]) == {"model_count", "mean", "variance", "spread", "max_pairwise_delta"}


def test_telemetry_checkpoints_turnover_and_ranks(monkeypatch, tmp_path):
    telemetry_path = tmp_path / "telemetry.json"
    _run(monkeypatch, tmp_path, ["--objective", "cvar", "--objective-telemetry", str(telemetry_path)])
    payload = json.loads(telemetry_path.read_text())
    assert payload["objective"] == {"name": "cvar", "alpha": 0.5}
    checkpoints = payload["checkpoints"]
    assert [c["candidate_id"] for c in checkpoints] == ["cand-a", "cand-c", "cand-b"]

    # Per-checkpoint rates and worst-k tail membership (alpha = 0.5 -> k = 3).
    for ckpt in checkpoints:
        rates = json.loads(json.dumps(DETECTION_TABLE[ckpt["candidate_id"]]))
        assert ckpt["per_surrogate_detection_rates"] == rates
        assert ckpt["cvar_tail"]["k"] == 3
        assert ckpt["cvar_tail"]["alpha"] == 0.5
        assert ckpt["cvar_tail"]["member_ids"] == EXPECTED_TAILS[ckpt["candidate_id"]]
        assert ckpt["losses"]["worst_model"] == pytest.approx(max(DETECTION_TABLE[ckpt["candidate_id"]].values()))
        assert ckpt["losses"]["mean"] == pytest.approx(
            sum(DETECTION_TABLE[ckpt["candidate_id"]].values()) / 6
        )

    # Tail turnover vs previous checkpoint.
    assert checkpoints[0]["tail_turnover"] == {"entered": ["sur-3", "sur-4", "sur-5"], "left": []}
    assert checkpoints[1]["tail_turnover"] == {
        "entered": ["sur-0", "sur-1", "sur-2"],
        "left": ["sur-3", "sur-4", "sur-5"],
    }
    assert checkpoints[2]["tail_turnover"] == {"entered": ["sur-4", "sur-5"], "left": ["sur-1", "sur-2"]}

    # Candidate rank changes at the final checkpoint (all 3 evaluated).
    ranks = checkpoints[-1]["candidate_ranks"]
    assert set(ranks) == {"cand-a", "cand-b", "cand-c"}
    assert ranks["cand-a"] == {"mean_rank": 1, "cvar_rank": 1, "rank_delta": 0}
    assert ranks["cand-b"] == {"mean_rank": 3, "cvar_rank": 2, "rank_delta": -1}
    assert ranks["cand-c"] == {"mean_rank": 2, "cvar_rank": 3, "rank_delta": 1}
    # Intermediate checkpoints only rank candidates evaluated so far.
    assert set(checkpoints[0]["candidate_ranks"]) == {"cand-a"}
    assert set(checkpoints[1]["candidate_ranks"]) == {"cand-a", "cand-c"}


def test_telemetry_does_not_alter_selection_outputs(monkeypatch, tmp_path):
    plain = _run(monkeypatch, tmp_path / "p", [], tag="plain")
    with_tel_dir = tmp_path / "t"
    with_tel = _run(
        monkeypatch, with_tel_dir,
        ["--objective-telemetry", str(with_tel_dir / "telemetry.json")], tag="tel",
    )
    # candidate-config.json is byte-identical with and without telemetry.
    assert (plain / "candidate-config.json").read_bytes() == (with_tel / "candidate-config.json").read_bytes()


LEGACY_REPORT_KEYS = {
    "schema_version", "selection_boundary", "surrogate_models", "heldout_models_loaded",
    "heldout_feedback_used", "model_state_hashes", "model_provenance", "design_profile",
    "design_profile_sha256", "candidate_count", "objective", "stage_a_policy",
    "stage_b_policy", "top_k", "winner", "stage_a", "stage_b",
}
LEGACY_RECORD_KEYS = {
    "candidate_id", "config", "pattern_path", "pattern_sha256", "baseline_detection_rate",
    "candidate_detection_rate", "candidate_mean", "invalid_condition_fraction",
    "printability_proxy", "art_direction_proxy", "reference_fidelity_score",
    "reference_fidelity_subscores",
}


def test_mean_arm_reproduces_legacy_selector_exactly(monkeypatch, tmp_path):
    out = _run(monkeypatch, tmp_path, ["--objective", "mean"])
    raw_report = (out / "surrogate-selection.json").read_text()
    report = json.loads(raw_report)
    # Exact legacy schema: no added/removed/renamed keys anywhere.
    assert set(report) == LEGACY_REPORT_KEYS
    for record in (*report["stage_a"], *report["stage_b"], report["winner"]):
        assert set(record) == LEGACY_RECORD_KEYS
    # Legacy winner rule: min over stage-B eligible under the legacy sort_key.
    eligible = [r for r in report["stage_b"] if r["invalid_condition_fraction"] <= 0.10]
    assert report["winner"] == min(eligible, key=ssc.sort_key)
    # Canonical legacy serialization round-trips byte-for-byte.
    assert raw_report == json.dumps(report, indent=2, sort_keys=True) + "\n"
    config = json.loads((out / "candidate-config.json").read_text())
    assert config["source_candidate_id"] == report["winner"]["candidate_id"]
    assert config["selection_boundary"] == "SURROGATE_ONLY"


@pytest.mark.skipif(
    not Path(os.environ.get("ACP_PRISTINE_ROOT", "/mnt/agents/acp")).joinpath(
        "scripts/select_surrogate_candidate.py"
    ).exists(),
    reason="pristine checkout not available",
)
def test_mean_arm_byte_identical_to_pristine_checkout(monkeypatch, tmp_path):
    """Strong parity: run the pristine script and the modified script on the
    same fixture and require byte-identical output files."""
    pristine_root = Path(os.environ.get("ACP_PRISTINE_ROOT", "/mnt/agents/acp"))
    spec = importlib.util.spec_from_file_location(
        "ssc_pristine", pristine_root / "scripts/select_surrogate_candidate.py"
    )
    pristine = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    sys.path.insert(0, str(pristine_root))
    try:
        spec.loader.exec_module(pristine)
        manifest_path, pool_path = _write_inputs(tmp_path / "pristine-fixture")
        out_dir = tmp_path / "out-pristine"
        _install_fakes(pristine, monkeypatch)
        monkeypatch.setattr(
            sys, "argv",
            ["select_surrogate_candidate.py", "--manifest", str(manifest_path),
             "--pool", str(pool_path), "--output-dir", str(out_dir)],
        )
        assert pristine.main() == 0
    finally:
        sys.path = saved_path
    modified_out = _run(monkeypatch, tmp_path / "modified-fixture", ["--objective", "mean"], tag="modified")
    for name in ("surrogate-selection.json", "candidate-config.json"):
        pristine_bytes = (out_dir / name).read_text().replace(
            str(tmp_path / "pristine-fixture"), "<FIXTURE>"
        ).replace(str(out_dir), "<OUT>")
        modified_bytes = (modified_out / name).read_text().replace(
            str(tmp_path / "modified-fixture"), "<FIXTURE>"
        ).replace(str(modified_out), "<OUT>")
        assert pristine_bytes == modified_bytes, f"{name} diverged from pristine selector"

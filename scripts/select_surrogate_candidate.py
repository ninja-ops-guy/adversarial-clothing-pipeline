from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.benchmark import BenchmarkConfig, ComparativeBenchmark
from scripts.run_measured_benchmark import build_evaluators, prepare_fixture


def make_config(manifest: dict, surrogate_ids: tuple[str, ...], sweep: dict) -> BenchmarkConfig:
    return BenchmarkConfig(
        threshold=float(manifest.get("threshold", 0.5)),
        thresholds={
            item["id"]: float(item["decision_threshold"])
            for item in manifest["models"]
            if item.get("role") == "surrogate"
        },
        brightness=tuple(float(v) for v in sweep["brightness"]),
        scales=tuple(float(v) for v in sweep["scale"]),
        blur_sigmas=tuple(float(v) for v in sweep["blur_sigma"]),
        rotations_deg=tuple(float(v) for v in sweep.get("rotation_deg", [0.0])),
        surrogate_models=surrogate_ids,
        heldout_models=(),
        min_baseline_score=float(manifest.get("min_baseline_score", 0.5)),
        seed=1337,
        device="cpu",
    )


def evaluate_candidate(
    item: dict,
    *,
    pool_dir: Path,
    manifest: dict,
    output_dir: Path,
    config: BenchmarkConfig,
    evaluators,
) -> dict:
    pattern_path = pool_dir / item["png"]
    runtime = output_dir / f"selection-{item['candidate_id']}"
    baseline, candidate, _ = prepare_fixture(pattern_path, manifest, runtime)
    benchmark = ComparativeBenchmark(config, evaluators)
    summary = benchmark.run(baseline, candidate)
    sur = summary["surrogate"]
    return {
        "candidate_id": item["candidate_id"],
        "config": item,
        "pattern_path": str(pattern_path),
        "pattern_sha256": hashlib.sha256(pattern_path.read_bytes()).hexdigest(),
        "baseline_detection_rate": sur["baseline_detection_rate"],
        "candidate_detection_rate": sur["candidate_detection_rate"],
        "candidate_mean": sur["candidate_mean"],
        "invalid_condition_fraction": summary["invalid_condition_fraction"],
        "printability_proxy": float(item.get("printability_proxy", 0.0)),
        "art_direction_proxy": float(item.get("art_direction_proxy", 0.0)),
    }


def sort_key(record: dict) -> tuple[float, float, float, float, str]:
    """Detector performance dominates; local design proxies only resolve ties."""
    return (
        float(record["candidate_detection_rate"]),
        float(record["candidate_mean"]),
        -float(record.get("printability_proxy", 0.0)),
        -float(record.get("art_direction_proxy", 0.0)),
        str(record["candidate_id"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a print-test candidate using surrogate models only.")
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--pool", default="benchmarks/runtime/pool/pool.json")
    parser.add_argument("--output-dir", default="benchmarks/runtime")
    parser.add_argument("--final-id", default="RAC-PER-D2-0003")
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    pool_path = Path(args.pool)
    pool = json.loads(pool_path.read_text())
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if pool.get("heldout_feedback_allowed") is not False:
        raise SystemExit("candidate pool must explicitly prohibit held-out feedback")
    if int(pool.get("candidate_count", 0)) != len(pool.get("candidates", [])):
        raise SystemExit("candidate pool count does not match candidate records")
    if not pool.get("design_profile_sha256"):
        raise SystemExit("candidate pool missing preregistered design-profile hash")

    evaluators, provenance, state_hashes = build_evaluators(manifest, roles={"surrogate"})
    surrogate_ids = tuple(item["id"] for item in manifest["models"] if item.get("role") == "surrogate")
    if not surrogate_ids:
        raise SystemExit("no surrogate models configured")

    nominal = {"brightness": [1.0], "scale": [1.0], "blur_sigma": [0.0], "rotation_deg": [0.0]}
    nominal_config = make_config(manifest, surrogate_ids, nominal)
    stage_a = [
        evaluate_candidate(
            item,
            pool_dir=pool_path.parent,
            manifest=manifest,
            output_dir=output_dir / "stage-a",
            config=nominal_config,
            evaluators=evaluators,
        )
        for item in pool["candidates"]
    ]
    stage_a_eligible = [r for r in stage_a if r["invalid_condition_fraction"] <= 0.10]
    if not stage_a_eligible:
        raise SystemExit("all candidates invalid during nominal surrogate screening")
    finalists = sorted(stage_a_eligible, key=sort_key)[: max(1, args.top_k)]

    full_sweep = manifest.get("selection_sweep", manifest["transform_sweep"])
    full_config = make_config(manifest, surrogate_ids, full_sweep)
    item_by_id = {item["candidate_id"]: item for item in pool["candidates"]}
    stage_b = [
        evaluate_candidate(
            item_by_id[record["candidate_id"]],
            pool_dir=pool_path.parent,
            manifest=manifest,
            output_dir=output_dir / "stage-b",
            config=full_config,
            evaluators=evaluators,
        )
        for record in finalists
    ]
    stage_b_eligible = [r for r in stage_b if r["invalid_condition_fraction"] <= 0.10]
    if not stage_b_eligible:
        raise SystemExit("all finalists invalid under robust surrogate sweep")
    winner = min(stage_b_eligible, key=sort_key)

    shutil.copyfile(winner["pattern_path"], output_dir / "candidate.png")
    final_config = {
        "schema_version": "3.0",
        **{k: v for k, v in winner["config"].items() if k not in {"png", "candidate_id"}},
        "candidate_id": args.final_id,
        "source_candidate_id": winner["candidate_id"],
        "source": "two-stage surrogate-only Product Studio candidate selection",
        "selection_boundary": "SURROGATE_ONLY",
        "selection_objective": pool.get("selection_order", []),
        "design_profile_sha256": pool["design_profile_sha256"],
    }
    (output_dir / "candidate-config.json").write_text(json.dumps(final_config, indent=2, sort_keys=True) + "\n")

    report = {
        "schema_version": "3.0",
        "selection_boundary": "SURROGATE_ONLY",
        "surrogate_models": list(surrogate_ids),
        "heldout_models_loaded": [],
        "heldout_feedback_used": False,
        "model_state_hashes": state_hashes,
        "model_provenance": provenance,
        "design_profile": pool.get("design_profile"),
        "design_profile_sha256": pool["design_profile_sha256"],
        "candidate_count": pool["candidate_count"],
        "objective": pool.get("selection_order", []),
        "stage_a_policy": nominal,
        "stage_b_policy": full_sweep,
        "top_k": args.top_k,
        "winner": winner,
        "stage_a": stage_a,
        "stage_b": stage_b,
    }
    (output_dir / "surrogate-selection.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"final_id": args.final_id, "winner": winner}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

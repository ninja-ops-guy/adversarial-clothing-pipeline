from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from ruthless_pipeline.benchmark import BenchmarkConfig, ComparativeBenchmark
from scripts.run_measured_benchmark import build_evaluators, prepare_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a D2 candidate using surrogate models only.")
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--pool", default="benchmarks/runtime/pool/pool.json")
    parser.add_argument("--output-dir", default="benchmarks/runtime")
    parser.add_argument("--final-id", default="RAC-PER-D2-0001")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    pool_path = Path(args.pool)
    pool = json.loads(pool_path.read_text())
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    evaluators, provenance, state_hashes = build_evaluators(manifest, roles={"surrogate"})
    surrogate_ids = tuple(item["id"] for item in manifest["models"] if item.get("role") == "surrogate")
    if not surrogate_ids:
        raise SystemExit("no surrogate models configured")

    sweep = manifest["transform_sweep"]
    config = BenchmarkConfig(
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

    records = []
    pool_dir = pool_path.parent
    for item in pool["candidates"]:
        pattern_path = pool_dir / item["png"]
        baseline, candidate, fixture = prepare_fixture(pattern_path, manifest, output_dir / f"selection-{item['candidate_id']}")
        benchmark = ComparativeBenchmark(config, evaluators)
        summary = benchmark.run(baseline, candidate)
        sur = summary["surrogate"]
        records.append({
            "candidate_id": item["candidate_id"],
            "config": item,
            "pattern_path": str(pattern_path),
            "pattern_sha256": __import__("hashlib").sha256(pattern_path.read_bytes()).hexdigest(),
            "baseline_detection_rate": sur["baseline_detection_rate"],
            "candidate_detection_rate": sur["candidate_detection_rate"],
            "candidate_mean": sur["candidate_mean"],
            "invalid_condition_fraction": summary["invalid_condition_fraction"],
        })

    eligible = [r for r in records if r["invalid_condition_fraction"] <= 0.10]
    if not eligible:
        raise SystemExit("all surrogate candidates invalid under baseline qualification")
    winner = min(
        eligible,
        key=lambda r: (
            r["candidate_detection_rate"],
            r["candidate_mean"],
            r["candidate_id"],
        ),
    )

    shutil.copyfile(winner["pattern_path"], output_dir / "candidate.png")
    final_config = {
        "schema_version": "1.0",
        "candidate_id": args.final_id,
        "source_candidate_id": winner["candidate_id"],
        "source": "surrogate-only deterministic candidate selection",
        **{k: v for k, v in winner["config"].items() if k != "png"},
    }
    (output_dir / "candidate-config.json").write_text(json.dumps(final_config, indent=2, sort_keys=True) + "\n")
    report = {
        "schema_version": "1.0",
        "selection_boundary": "SURROGATE_ONLY",
        "surrogate_models": list(surrogate_ids),
        "heldout_models_loaded": [],
        "model_state_hashes": state_hashes,
        "model_provenance": provenance,
        "objective": ["candidate_detection_rate:min", "candidate_mean:min", "candidate_id:lexical"],
        "winner": winner,
        "candidates": records,
    }
    (output_dir / "surrogate-selection.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"final_id": args.final_id, "winner": winner}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

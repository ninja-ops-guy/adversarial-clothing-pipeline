from __future__ import annotations

"""Execute one frozen generator family of D2-0007 Stage-1 motif screening.

This command is deliberately split by generator so CI can evaluate the fixed
8x8 screening budget in parallel.  It constructs PERSON-SUR-v3 evaluators only,
verifies their pinned weight hashes, applies the frozen transform sweep, and
writes eight surrogate-only observations.  It cannot aggregate/promote, build
anchors, optimize, freeze a winner, or touch held-out models.
"""

import argparse
import json
import os
from pathlib import Path
import sys

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.benchmark import ComparativeBenchmark  # noqa: E402
from ruthless_pipeline.patterns.d2007_screening import (  # noqa: E402
    SURROGATE_MODEL_SET_ID,
    build_observation,
    generate_screening_candidate,
    load_json,
    validate_execution_spec,
)
from scripts.run_measured_benchmark import build_evaluators, prepare_fixture  # noqa: E402
from scripts.select_surrogate_candidate import make_config  # noqa: E402


def _model_ids(model_set: dict) -> tuple[str, ...]:
    if model_set.get("model_set_id") != SURROGATE_MODEL_SET_ID:
        raise SystemExit("Stage 1 requires PERSON-SUR-v3")
    if model_set.get("role") != "surrogate":
        raise SystemExit("Stage-1 model set must have role=surrogate")
    ids = tuple(str(value) for value in model_set.get("models", ()))
    if len(ids) != 6 or len(set(ids)) != 6:
        raise SystemExit("PERSON-SUR-v3 must contain exactly six unique models")
    return ids


def _per_model_rates(rows: list[dict], model_ids: tuple[str, ...]) -> tuple[dict[str, float], dict[str, float]]:
    baseline: dict[str, float] = {}
    candidate: dict[str, float] = {}
    for model in model_ids:
        valid = [
            row for row in rows
            if row["model"] == model and row["split"] == "surrogate" and row["baseline_qualified"]
        ]
        if not valid:
            baseline[model] = 0.0
            candidate[model] = 1.0
        else:
            baseline[model] = sum(float(row["baseline_detected"]) for row in valid) / len(valid)
            candidate[model] = sum(float(row["candidate_detected"]) for row in valid) / len(valid)
    return baseline, candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one D2-0007 Stage-1 motif family on PERSON-SUR-v3 only.")
    parser.add_argument("--generator-index", type=int, required=True)
    parser.add_argument("--spec", default="configs/d2007_stage1_screening_v1.json")
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--model-set", default="model_sets/PERSON-SUR-v3.json")
    parser.add_argument("--output-dir", default="benchmarks/runtime/d2-0007/stage1")
    args = parser.parse_args()

    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    spec = load_json(ROOT / args.spec)
    validate_execution_spec(spec, repo_root=ROOT)
    generator_index = int(args.generator_index)
    if not 0 <= generator_index < len(spec["generator_order"]):
        raise SystemExit("generator index outside frozen D2-0007 inventory")

    manifest = load_json(ROOT / args.manifest)
    model_set = load_json(ROOT / args.model_set)
    surrogate_ids = _model_ids(model_set)
    manifest_surrogates = tuple(
        str(item["id"]) for item in manifest["models"] if item.get("role") == "surrogate"
    )
    if manifest_surrogates != surrogate_ids:
        raise SystemExit("PERSON-SUR-v3 order/membership disagrees with benchmark manifest")
    frozen_sweep = spec["screening_fixture"]["transform_sweep"]
    if manifest.get("transform_sweep") != frozen_sweep:
        raise SystemExit("benchmark transform_sweep drifted from D2-0007 Stage-1 execution freeze")
    if manifest.get("fixture", {}).get("name") != spec["screening_fixture"]["fixture_name"]:
        raise SystemExit("screening fixture identity drifted from D2-0007 Stage-1 execution freeze")

    # Critical scientific boundary: instantiate surrogate-role evaluators only.
    evaluators, provenance, state_hashes = build_evaluators(manifest, roles={"surrogate"})
    for item in manifest["models"]:
        if item.get("role") != "surrogate":
            continue
        expected = str(item.get("state_dict_sha256", "")).lower()
        actual = str(state_hashes.get(item["id"], "")).lower()
        if len(expected) != 64 or actual != expected:
            raise SystemExit(f"surrogate model state hash mismatch for {item['id']}")

    config = make_config(manifest, surrogate_ids, frozen_sweep)
    if config.heldout_models:
        raise SystemExit("Stage-1 benchmark config unexpectedly contains held-out models")

    output_dir = ROOT / args.output_dir
    pattern_dir = output_dir / "patterns" / f"g{generator_index}"
    fixture_dir = output_dir / "fixtures" / f"g{generator_index}"
    pattern_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir.mkdir(parents=True, exist_ok=True)

    candidates: list[dict] = []
    observations: list[dict] = []
    fixture_metadata: dict | None = None
    for composition_index in range(int(spec["budget"]["compositions_per_generator"])):
        image, candidate_record = generate_screening_candidate(
            spec,
            generator_index=generator_index,
            composition_index=composition_index,
        )
        pattern_path = pattern_dir / f"c{composition_index}.png"
        Image.fromarray(image.astype("uint8"), "RGB").save(pattern_path)
        baseline, candidate, metadata = prepare_fixture(
            pattern_path,
            manifest,
            fixture_dir / f"c{composition_index}",
        )
        if fixture_metadata is None:
            fixture_metadata = metadata
        benchmark = ComparativeBenchmark(config, evaluators)
        summary = benchmark.run(baseline, candidate)
        baseline_rates, candidate_rates = _per_model_rates(benchmark.rows, surrogate_ids)
        observation = build_observation(
            candidate_record,
            baseline_detection_rates=baseline_rates,
            candidate_detection_rates=candidate_rates,
            invalid_condition_fraction=float(summary["invalid_condition_fraction"]),
        )
        candidates.append(candidate_record)
        observations.append(observation.to_dict())

    result = {
        "schema_version": "rac-d2007-stage1-generator-result/1.0",
        "generation_id": "RAC-PER-D2-0007",
        "stage": "STAGE_1_MOTIF_SCREENING",
        "status": "GENERATOR_COMPLETE",
        "generator_index": generator_index,
        "generator_class": spec["generator_order"][generator_index],
        "model_set_id": SURROGATE_MODEL_SET_ID,
        "heldout_access": False,
        "body_garment_anchor_support_built": False,
        "optimization_opened": False,
        "candidate_freeze_created": False,
        "alpha_002_promoted": False,
        "surrogate_state_hashes": {key: state_hashes[key] for key in sorted(state_hashes)},
        "surrogate_provenance": {key: provenance[key] for key in sorted(provenance)},
        "fixture": fixture_metadata,
        "candidates": candidates,
        "observations": observations,
    }
    output_path = output_dir / f"generator-{generator_index}.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "generator_index": generator_index,
        "generator_class": result["generator_class"],
        "observation_count": len(observations),
        "heldout_access": False,
        "output": str(output_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

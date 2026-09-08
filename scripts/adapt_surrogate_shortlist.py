from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch
from PIL import Image
from torchvision.transforms.functional import pil_to_tensor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.benchmark import BenchmarkConfig, ComparativeBenchmark
from ruthless_pipeline.certification.schema_version import require_schema_version
from ruthless_pipeline.capgen import extract_base_colors, initialize_pattern_logits, render_palette_patch
from scripts.run_measured_benchmark import build_evaluators, prepare_fixture


def to_tensor(path: Path, size: int = 512) -> torch.Tensor:
    image = Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    return pil_to_tensor(image).float().div(255.0).unsqueeze(0)


def save_tensor(tensor: torch.Tensor, path: Path) -> None:
    arr = (
        tensor.detach()
        .cpu()
        .clamp(0, 1)
        .squeeze(0)
        .permute(1, 2, 0)
        .mul(255)
        .round()
        .to(torch.uint8)
        .numpy()
    )
    Image.fromarray(arr).save(path)


def make_config(manifest: dict, surrogate_ids: tuple[str, ...]) -> BenchmarkConfig:
    sweep = manifest.get("selection_sweep", manifest["transform_sweep"])
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


def evaluate(path: Path, manifest: dict, runtime: Path, config: BenchmarkConfig, evaluators) -> dict:
    baseline, candidate, _ = prepare_fixture(path, manifest, runtime)
    bench = ComparativeBenchmark(config, evaluators)
    summary = bench.run(baseline, candidate)["surrogate"]
    return {
        "baseline_detection_rate": summary["baseline_detection_rate"],
        "candidate_detection_rate": summary["candidate_detection_rate"],
        "candidate_mean": summary["candidate_mean"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create environment-adapted variants from a surrogate-selected RAC shortlist."
    )
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--selection", default="benchmarks/runtime/surrogate-selection.json")
    parser.add_argument("--pool", default="benchmarks/runtime/pool/pool.json")
    parser.add_argument("--output-dir", default="benchmarks/runtime/adaptive")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    selection = json.loads(Path(args.selection).read_text())
    require_schema_version(selection, "3.0", label=f"selection report {args.selection}")
    pool_path = Path(args.pool)
    pool = json.loads(pool_path.read_text())
    require_schema_version(pool, "3.0", label=f"candidate pool {pool_path}")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if selection.get("selection_boundary") != "SURROGATE_ONLY":
        raise SystemExit("adaptive stage requires SURROGATE_ONLY selection input")
    if selection.get("heldout_models_loaded") != [] or selection.get("heldout_feedback_used") is not False:
        raise SystemExit("adaptive stage blocked: held-out contamination detected")
    if pool.get("heldout_feedback_allowed") is not False:
        raise SystemExit("adaptive stage blocked: candidate pool allows held-out feedback")

    evaluators, provenance, state_hashes = build_evaluators(manifest, roles={"surrogate"})
    surrogate_ids = tuple(item["id"] for item in manifest["models"] if item.get("role") == "surrogate")
    config = make_config(manifest, surrogate_ids)

    stage_b = sorted(
        selection.get("stage_b", []),
        key=lambda r: (
            float(r["candidate_detection_rate"]),
            float(r["candidate_mean"]),
            -float(r.get("reference_fidelity_score", 0.0)),
        ),
    )[: max(1, args.top_k)]
    if not stage_b:
        raise SystemExit("adaptive stage requires non-empty surrogate finalists")

    # prepare_fixture downloads the documented convenience environment. We use its
    # baseline crops only for palette extraction; no held-out model inference occurs.
    first_path = pool_path.parent / stage_b[0]["config"]["png"]
    env_runtime = output_dir / "environment"
    baseline, _, fixture_meta = prepare_fixture(first_path, manifest, env_runtime)
    environment_images = [baseline]

    pool_by_id = {item["candidate_id"]: item for item in pool["candidates"]}
    records: list[dict] = []
    temperatures = (0.07, 0.10, 0.16)
    blends = (0.70, 0.85, 1.00)

    for finalist in stage_b:
        source_id = finalist["candidate_id"]
        item = pool_by_id[source_id]
        source_path = pool_path.parent / item["png"]
        seed_texture = to_tensor(source_path)
        for colors_k in (3, 4):
            colors = extract_base_colors(
                environment_images,
                num_colors=colors_k,
                max_pixels=20_000,
                iterations=16,
                seed=int(item["seed"]),
            ).to(seed_texture)
            logits = initialize_pattern_logits(seed_texture, colors_k)
            for temperature in temperatures:
                recolored = render_palette_patch(logits, colors, temperature)
                for blend in blends:
                    candidate = seed_texture * (1.0 - blend) + recolored * blend
                    name = f"{source_id}-K{colors_k}-T{str(temperature).replace('.', '')}-B{int(blend*100)}"
                    path = output_dir / f"{name}.png"
                    save_tensor(candidate, path)
                    metrics = evaluate(
                        path,
                        manifest,
                        output_dir / "eval" / name,
                        config,
                        evaluators,
                    )
                    records.append(
                        {
                            "candidate_id": name,
                            "source_candidate_id": source_id,
                            "family": item["family"],
                            "product": item["product"],
                            "seed": item["seed"],
                            "environment_colors": colors_k,
                            "temperature": temperature,
                            "blend": blend,
                            "reference_fidelity_score": item.get("reference_fidelity_score"),
                            "png": path.name,
                            "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            **metrics,
                        }
                    )

    records.sort(
        key=lambda r: (
            float(r["candidate_detection_rate"]),
            float(r["candidate_mean"]),
            -float(r.get("reference_fidelity_score") or 0.0),
            str(r["candidate_id"]),
        )
    )
    winner = records[0]
    report = {
        "schema_version": "1.0",
        "stage": "environment_adaptive_surrogate_only",
        "source_selection": str(Path(args.selection)),
        "surrogate_models": list(surrogate_ids),
        "heldout_models_loaded": [],
        "heldout_feedback_used": False,
        "fixture": fixture_meta,
        "model_provenance": provenance,
        "model_state_hashes": state_hashes,
        "variant_count": len(records),
        "winner": winner,
        "variants": records,
        "next_boundary": "freeze winner, preregister fresh held-out generation before any D2 inference",
    }
    (output_dir / "adaptive-selection.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({"winner": winner, "variant_count": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
from ruthless_pipeline.certification.schema_version import require_schema_version
from ruthless_pipeline.certification.objectives import (
    ObjectiveSpec,
    cvar,
    mean_objective,
    worst_tail_members,
)
from ruthless_pipeline.certification.telemetry_contract import cross_model_disagreement
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


def per_surrogate_detection_rates(rows: list[dict], surrogate_ids: tuple[str, ...]) -> dict[str, float]:
    """Per-surrogate candidate detection rate over valid conditions (1.0 if a surrogate has none)."""
    rates: dict[str, float] = {}
    for model in surrogate_ids:
        valid = [
            r
            for r in rows
            if r["model"] == model and r["split"] == "surrogate" and r["baseline_qualified"]
        ]
        rates[model] = (
            sum(float(r["candidate_detected"]) for r in valid) / len(valid) if valid else 1.0
        )
    return rates


def evaluate_candidate(
    item: dict,
    *,
    pool_dir: Path,
    manifest: dict,
    output_dir: Path,
    config: BenchmarkConfig,
    evaluators,
    include_per_surrogate: bool = False,
) -> dict:
    pattern_path = pool_dir / item["png"]
    runtime = output_dir / f"selection-{item['candidate_id']}"
    baseline, candidate, _ = prepare_fixture(pattern_path, manifest, runtime)
    benchmark = ComparativeBenchmark(config, evaluators)
    summary = benchmark.run(baseline, candidate)
    sur = summary["surrogate"]
    record = {
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
        "reference_fidelity_score": float(item.get("reference_fidelity_score") or 0.0),
        "reference_fidelity_subscores": item.get("reference_fidelity_subscores"),
    }
    if include_per_surrogate:
        record["per_surrogate_detection_rates"] = per_surrogate_detection_rates(
            benchmark.rows, config.surrogate_models
        )
    return record


def sort_key(record: dict) -> tuple[float, float, float, float, float, str]:
    """Detector performance dominates; reference fidelity is the first creative tie-break."""
    return (
        float(record["candidate_detection_rate"]),
        float(record["candidate_mean"]),
        -float(record.get("reference_fidelity_score", 0.0)),
        -float(record.get("printability_proxy", 0.0)),
        -float(record.get("art_direction_proxy", 0.0)),
        str(record["candidate_id"]),
    )


def objective_sort_key(record: dict, objective: ObjectiveSpec) -> tuple[float, float, float, float, float, str]:
    """``sort_key`` with the primary key replaced by the preregistered objective over per-surrogate rates."""
    return (
        objective.objective_key(record["per_surrogate_detection_rates"]),
    ) + sort_key(record)[1:]


def _objective_ranks(entries: list[tuple[str, dict[str, float]]], keyfn) -> dict[str, int]:
    """1-based ranks (lowest loss = rank 1), ties broken by candidate id."""
    order = sorted(entries, key=lambda entry: (keyfn(entry[1]), entry[0]))
    return {candidate_id: rank for rank, (candidate_id, _) in enumerate(order, start=1)}


def build_objective_telemetry(
    stage_b: list[dict], *, objective: ObjectiveSpec, alpha: float
) -> dict:
    """Per-checkpoint objective telemetry over the stage-B evaluation sequence.

    Each stage-B evaluation is one optimization checkpoint. ``alpha`` is the
    worst-k analysis level (the arm's CVaR alpha; 0.5 under the mean arm).
    """
    checkpoints: list[dict] = []
    previous_tail: tuple[str, ...] = ()
    evaluated: list[tuple[str, dict[str, float]]] = []
    for index, record in enumerate(stage_b):
        rates = record["per_surrogate_detection_rates"]
        tail = worst_tail_members(rates, alpha)
        entered = sorted(set(tail) - set(previous_tail))
        left = sorted(set(previous_tail) - set(tail)) if previous_tail else []
        evaluated.append((str(record["candidate_id"]), rates))
        mean_ranks = _objective_ranks(evaluated, lambda r: mean_objective(list(r.values())))
        cvar_ranks = _objective_ranks(evaluated, lambda r: cvar(list(r.values()), alpha))
        checkpoints.append(
            {
                "checkpoint": index,
                "candidate_id": str(record["candidate_id"]),
                "per_surrogate_detection_rates": {k: float(v) for k, v in sorted(rates.items())},
                "cvar_tail": {"alpha": float(alpha), "k": len(tail), "member_ids": list(tail)},
                "tail_turnover": {"entered": entered, "left": left},
                "losses": {
                    "mean": mean_objective(list(rates.values())),
                    "cvar": cvar(list(rates.values()), alpha),
                    "worst_model": max(float(v) for v in rates.values()),
                },
                "dispersion": cross_model_disagreement(rates),
                "candidate_ranks": {
                    candidate_id: {
                        "mean_rank": mean_ranks[candidate_id],
                        "cvar_rank": cvar_ranks[candidate_id],
                        "rank_delta": cvar_ranks[candidate_id] - mean_ranks[candidate_id],
                    }
                    for candidate_id, _ in evaluated
                },
            }
        )
        previous_tail = tail
    return {
        "schema_version": "1.0",
        "objective": {"name": objective.name, "alpha": objective.alpha},
        "tail_rule": "worst-k tail: k = max(1, ceil((1 - alpha) * n)) highest per-surrogate rates",
        "checkpoints": checkpoints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a print-test candidate using surrogate models only.")
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--pool", default="benchmarks/runtime/pool/pool.json")
    parser.add_argument("--output-dir", default="benchmarks/runtime")
    parser.add_argument("--final-id", default="RAC-PER-D2-0004")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--objective", choices=("mean", "cvar"), default="mean")
    parser.add_argument("--cvar-alpha", type=float, default=0.5)
    parser.add_argument(
        "--objective-telemetry",
        default=None,
        help="optional path for per-checkpoint objective telemetry JSON (opt-in; omitted by default)",
    )
    args = parser.parse_args()

    objective = ObjectiveSpec(
        name=args.objective,
        alpha=args.cvar_alpha if args.objective == "cvar" else None,
    )
    objective.validate()

    manifest = json.loads(Path(args.manifest).read_text())
    pool_path = Path(args.pool)
    pool = json.loads(pool_path.read_text())
    require_schema_version(pool, "3.0", label=f"candidate pool {pool_path}")
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
            include_per_surrogate=objective.name == "cvar" or args.objective_telemetry is not None,
        )
        for record in finalists
    ]
    stage_b_eligible = [r for r in stage_b if r["invalid_condition_fraction"] <= 0.10]
    if not stage_b_eligible:
        raise SystemExit("all finalists invalid under robust surrogate sweep")
    if objective.name == "cvar":
        winner = min(stage_b_eligible, key=lambda record: objective_sort_key(record, objective))
    else:
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
    if objective.name == "cvar":
        report["surrogate_objective"] = {
            "name": objective.name,
            "alpha": objective.alpha,
            "definition": "CVaR_alpha of per-surrogate detection rates: mean of the worst "
            "max(1, ceil((1 - alpha) * n)) surrogates (D2-0005 Arm C)",
        }
    (output_dir / "surrogate-selection.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.objective_telemetry is not None:
        telemetry = build_objective_telemetry(stage_b, objective=objective, alpha=float(args.cvar_alpha))
        telemetry_path = Path(args.objective_telemetry)
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        telemetry_path.write_text(json.dumps(telemetry, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"final_id": args.final_id, "winner": winner}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

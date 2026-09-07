from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.physical import PhysicalTrial, summarize_physical_trials
from scripts.run_measured_benchmark import build_evaluators, image_tensor


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def resolve_capture(captures: Path, manifest_dir: Path, value: str) -> Path:
    requested = Path(value)
    candidates = [captures / requested.name, manifest_dir / requested]
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    raise FileNotFoundError(f"missing capture: {value}")


def aggregate(rows: list[dict]) -> dict:
    valid = [r for r in rows if r["baseline_qualified"]]
    if not rows:
        return {"n": 0, "valid_n": 0}
    if not valid:
        return {
            "n": len(rows),
            "valid_n": 0,
            "baseline_detection_rate": 0.0,
            "candidate_detection_rate": 1.0,
            "invalid_condition_fraction": 1.0,
        }
    baseline_hits = sum(int(r["baseline_detected"]) for r in valid)
    candidate_hits = sum(int(r["candidate_detected"]) for r in valid)
    return {
        "n": len(rows),
        "valid_n": len(valid),
        "baseline_mean": sum(float(r["baseline_score"]) for r in valid) / len(valid),
        "candidate_mean": sum(float(r["candidate_score"]) for r in valid) / len(valid),
        "baseline_detection_rate": baseline_hits / len(valid),
        "candidate_detection_rate": candidate_hits / len(valid),
        "invalid_condition_fraction": (len(rows) - len(valid)) / len(rows),
        "baseline_detection_rate_ci95": wilson_interval(baseline_hits, len(valid)),
        "candidate_detection_rate_ci95": wilson_interval(candidate_hits, len(valid)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate matched physical control/candidate captures with the frozen detector ensemble.")
    parser.add_argument("--trial-manifest", required=True)
    parser.add_argument("--captures", required=True)
    parser.add_argument("--model-manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--cert-protocol", default="protocols/RAC-PERSON-DETECT-1.1.json")
    parser.add_argument("--output", default="physical-results.json")
    args = parser.parse_args()

    trial_manifest_path = Path(args.trial_manifest)
    capture_root = Path(args.captures)
    model_manifest_path = Path(args.model_manifest)
    protocol_path = Path(args.cert_protocol)
    trial_manifest = json.loads(trial_manifest_path.read_text())
    model_manifest = json.loads(model_manifest_path.read_text())
    protocol = json.loads(protocol_path.read_text())

    camera_id = str(trial_manifest.get("camera_id", "")).strip()
    if not camera_id or camera_id == "SET_BEFORE_EVALUATION":
        raise SystemExit("trial manifest camera_id must be set to the real capture device before evaluation")
    trials = list(trial_manifest.get("trials", []))
    expected = int(trial_manifest.get("expected_pair_count", len(trials)))
    if not trials or len(trials) != expected:
        raise SystemExit("trial manifest pair count is incomplete")

    evaluators, provenance, state_hashes = build_evaluators(model_manifest)
    evaluator_by_name = {e.name: e for e in evaluators}
    thresholds = {item["id"]: float(item["decision_threshold"]) for item in model_manifest["models"]}
    min_baseline_score = float(model_manifest.get("min_baseline_score", 0.5))
    model_roles = {item["id"]: item.get("role", "unknown") for item in model_manifest["models"]}

    tensor_cache: dict[str, torch.Tensor] = {}
    hash_cache: dict[str, str] = {}

    def load(path: Path) -> torch.Tensor:
        key = str(path.resolve())
        if key not in tensor_cache:
            tensor_cache[key] = image_tensor(Image.open(path).convert("RGB"))
            hash_cache[key] = sha256(path)
        return tensor_cache[key]

    rows: list[dict] = []
    manifest_dir = trial_manifest_path.parent
    for trial in trials:
        control_path = resolve_capture(capture_root, manifest_dir, str(trial["control_file"]))
        candidate_path = resolve_capture(capture_root, manifest_dir, str(trial["candidate_file"]))
        control = load(control_path).unsqueeze(0)
        candidate = load(candidate_path).unsqueeze(0)
        for model_id in thresholds:
            evaluator = evaluator_by_name[model_id]
            with torch.no_grad():
                control_score = float(evaluator.score(control).reshape(-1)[0].item())
                candidate_score = float(evaluator.score(candidate).reshape(-1)[0].item())
            threshold = thresholds[model_id]
            qualified = control_score >= min_baseline_score
            rows.append(
                {
                    "trial_id": trial["trial_id"],
                    "condition_id": trial["condition_id"],
                    "model": model_id,
                    "model_role": model_roles[model_id],
                    "threshold": threshold,
                    "baseline_score": control_score,
                    "candidate_score": candidate_score,
                    "baseline_qualified": qualified,
                    "baseline_detected": control_score >= threshold,
                    "candidate_detected": (candidate_score >= threshold) if qualified else None,
                    "camera_id": camera_id,
                    "distance_m": float(trial["distance_m"]),
                    "yaw_deg": float(trial["yaw_deg"]),
                    "pitch_deg": float(trial["pitch_deg"]),
                    "pose": str(trial["pose"]),
                    "lighting_id": str(trial["lighting_id"]),
                    "wash_state": str(trial.get("wash_state", "W0")),
                    "control_file": str(control_path),
                    "candidate_file": str(candidate_path),
                    "control_sha256": hash_cache[str(control_path.resolve())],
                    "candidate_sha256": hash_cache[str(candidate_path.resolve())],
                }
            )

    by_model: dict[str, list[dict]] = defaultdict(list)
    by_trial: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_model[row["model"]].append(row)
        by_trial[row["trial_id"]].append(row)

    model_summary = {model: aggregate(group) for model, group in by_model.items()}
    conservative_trials: list[PhysicalTrial] = []
    for trial in trials:
        group = by_trial[trial["trial_id"]]
        control_detected = all(bool(r["baseline_qualified"] and r["baseline_detected"]) for r in group)
        candidate_detected = any(bool(r["candidate_detected"]) for r in group if r["baseline_qualified"])
        conservative_trials.append(
            PhysicalTrial(
                trial_id=str(trial["trial_id"]),
                condition_id=str(trial["condition_id"]),
                control_detected=control_detected,
                candidate_detected=candidate_detected,
                camera_id=camera_id,
                distance_m=float(trial["distance_m"]),
                yaw_deg=float(trial["yaw_deg"]),
                pitch_deg=float(trial["pitch_deg"]),
                pose=str(trial["pose"]),
                lighting_id=str(trial["lighting_id"]),
                wash_state=str(trial.get("wash_state", "W0")),
            )
        )

    physical = summarize_physical_trials(conservative_trials)
    invalid_fraction = physical.invalid_trials / physical.total_trials
    relative_reduction = (
        0.0
        if physical.control_detection_rate <= 0
        else (physical.control_detection_rate - physical.candidate_detection_rate) / physical.control_detection_rate
    )
    criteria = protocol["criteria"]
    criteria_pass = (
        physical.control_detection_rate >= float(criteria["min_baseline_detection_rate"])
        and physical.candidate_detection_rate <= float(criteria["max_candidate_detection_rate"])
        and relative_reduction >= float(criteria["min_relative_reduction"])
        and invalid_fraction <= float(criteria["max_invalid_condition_fraction"])
    )

    output = {
        "schema_version": "1.0",
        "status": "measured_physical",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_id": trial_manifest["candidate_id"],
        "candidate_artifact_sha256": trial_manifest["candidate_artifact_sha256"],
        "trial_manifest_sha256": sha256(trial_manifest_path),
        "model_manifest_sha256": sha256(model_manifest_path),
        "protocol_sha256": sha256(protocol_path),
        "camera_id": camera_id,
        "pair_count": len(trials),
        "model_count": len(evaluators),
        "model_state_hashes": state_hashes,
        "model_provenance": provenance,
        "model_summary": model_summary,
        "physical_summary": {
            "total_trials": physical.total_trials,
            "valid_trials": physical.valid_trials,
            "invalid_trials": physical.invalid_trials,
            "control_detection_rate": physical.control_detection_rate,
            "candidate_detection_rate": physical.candidate_detection_rate,
            "invalid_condition_fraction": invalid_fraction,
            "relative_detection_reduction": relative_reduction,
            "criteria_pass": criteria_pass,
            "decision_basis": "conservative ensemble: control must be detected by every frozen model; candidate counts detected if any frozen model detects it",
        },
        "rows": rows,
        "evidence_scope": "physical_matched_capture",
        "rac_p1_review_eligible": criteria_pass,
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    csv_path = output_path.with_suffix(".csv")
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"output": str(output_path), "physical_summary": output["physical_summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

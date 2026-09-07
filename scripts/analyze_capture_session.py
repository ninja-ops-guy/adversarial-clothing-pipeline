from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_measured_benchmark import build_evaluators
from scripts.validate_capture_session import load_session, verify_capture_hashes


class CaptureEvaluator(Protocol):
    name: str
    def score(self, images: torch.Tensor) -> torch.Tensor: ...


@dataclass(frozen=True)
class FrameRecord:
    arm: str
    capture_id: str
    path: str
    timestamp: str | None
    condition: str | None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def load_contract(session: dict[str, Any]) -> dict[str, Any]:
    contract = session.get("analysis_contract")
    if not isinstance(contract, dict):
        raise ValueError("sealed session is missing analysis_contract")
    if contract.get("identity_mode", "disabled") != "disabled":
        raise ValueError("identity matching is not supported by this runner; use a separately approved closed-set protocol")
    models = contract.get("models")
    thresholds = contract.get("thresholds")
    if not isinstance(models, list) or not models:
        raise ValueError("analysis_contract.models must be a non-empty frozen list")
    if len(set(map(str, models))) != len(models):
        raise ValueError("analysis_contract contains duplicate model IDs")
    if not isinstance(thresholds, dict):
        raise ValueError("analysis_contract.thresholds must be an object")
    for model_id in models:
        if model_id not in thresholds:
            raise ValueError(f"missing frozen threshold for {model_id}")
        value = float(thresholds[model_id])
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"invalid threshold for {model_id}")
    return contract


def image_tensor(path: Path) -> torch.Tensor:
    with Image.open(path) as image:
        arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1)


def collect_stills(session_path: Path, session: dict[str, Any]) -> list[tuple[FrameRecord, torch.Tensor]]:
    rows: list[tuple[FrameRecord, torch.Tensor]] = []
    root = session_path.parent
    for arm in ("control", "candidate"):
        for record in session.get("captures", {}).get(arm, {}).get("stills", []):
            rel = str(record["path"])
            rows.append((
                FrameRecord(arm, str(record.get("id", rel)), rel, record.get("timestamp"), record.get("condition")),
                image_tensor(root / rel),
            ))
    if not rows:
        raise ValueError("session contains no still captures")
    return rows


def _model_manifest(root: Path, model_id: str) -> dict[str, Any]:
    path = root / "model_manifests" / f"{model_id}.json"
    if not path.is_file():
        raise ValueError(f"missing frozen model manifest: {model_id}")
    payload = json.loads(path.read_text())
    if payload.get("model_id") != model_id:
        raise ValueError(f"model manifest ID mismatch: {model_id}")
    return payload


def verify_model_contracts(root: Path, benchmark_manifest: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    by_id = {str(item["id"]): item for item in benchmark_manifest["models"]}
    verified: dict[str, Any] = {}
    for model_id in map(str, contract["models"]):
        if model_id not in by_id:
            raise ValueError(f"model not present in frozen benchmark manifest: {model_id}")
        item = by_id[model_id]
        frozen = _model_manifest(root, model_id)
        expected_hash = str(item.get("state_dict_sha256", "")).lower()
        if frozen.get("weights_sha256") != expected_hash:
            raise ValueError(f"model hash contract mismatch: {model_id}")
        threshold = float(contract["thresholds"][model_id])
        if threshold != float(item["decision_threshold"]) or threshold != float(frozen["decision_threshold"]):
            raise ValueError(f"threshold contract mismatch: {model_id}")
        verified[model_id] = {
            "display_name": item["display_name"],
            "framework": item["framework"],
            "model_ref": item["model_ref"],
            "weights_sha256": expected_hash,
            "decision_threshold": threshold,
            "preprocessing": frozen.get("preprocessing", {}),
        }
    return verified


def analyze_stills(
    records: list[tuple[FrameRecord, torch.Tensor]],
    evaluators: list[CaptureEvaluator],
    thresholds: dict[str, float],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    images = torch.stack([image for _, image in records])
    predictions: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    for evaluator in evaluators:
        start = time.perf_counter()
        if hasattr(evaluator, "predict"):
            batch = evaluator.predict(images)
            target_scores = batch.target_scores.detach().cpu()
            boxes = [x.detach().cpu() for x in batch.boxes]
            labels = [x.detach().cpu() for x in batch.labels]
            scores = [x.detach().cpu() for x in batch.scores]
        else:
            target_scores = evaluator.score(images).detach().cpu()
            boxes = [torch.empty((0, 4)) for _ in records]
            labels = [torch.empty((0,), dtype=torch.int64) for _ in records]
            scores = [torch.empty((0,)) for _ in records]
        latency_ms = (time.perf_counter() - start) * 1000
        threshold = float(thresholds[evaluator.name])
        model_rows = []
        for i, (record, _) in enumerate(records):
            target = float(target_scores[i])
            detections = []
            for box, label, score in zip(boxes[i].tolist(), labels[i].tolist(), scores[i].tolist()):
                detections.append({"box_xyxy": box, "label": int(label), "score": float(score)})
            row = {
                "model_id": evaluator.name,
                "arm": record.arm,
                "capture_id": record.capture_id,
                "path": record.path,
                "timestamp": record.timestamp,
                "condition": record.condition,
                "target_score": target,
                "threshold": threshold,
                "detected": target >= threshold,
                "detections": detections,
            }
            predictions.append(row)
            model_rows.append(row)
        for arm in ("control", "candidate"):
            arm_rows = [row for row in model_rows if row["arm"] == arm]
            summaries.setdefault(evaluator.name, {})[arm] = {
                "n_stills": len(arm_rows),
                "detection_rate": sum(row["detected"] for row in arm_rows) / len(arm_rows) if arm_rows else None,
                "mean_target_score": sum(row["target_score"] for row in arm_rows) / len(arm_rows) if arm_rows else None,
            }
        summaries[evaluator.name]["batch_inference_ms"] = latency_ms
    return predictions, summaries


def derive_pair_outcome(predictions: list[dict[str, Any]], model_ids: list[str]) -> dict[str, Any]:
    by_model: dict[str, dict[str, list[bool]]] = {m: {"control": [], "candidate": []} for m in model_ids}
    for row in predictions:
        by_model[row["model_id"]][row["arm"]].append(bool(row["detected"]))
    model_outcomes = {}
    for model_id, arms in by_model.items():
        control = any(arms["control"])
        candidate = any(arms["candidate"])
        model_outcomes[model_id] = {
            "control_detected": control,
            "candidate_detected": candidate,
            "valid": control,
            "invalid_reason": None if control else "control_not_detected",
        }
    valid = [v for v in model_outcomes.values() if v["valid"]]
    return {
        "model_outcomes": model_outcomes,
        "valid_model_count": len(valid),
        "invalid_model_count": len(model_outcomes) - len(valid),
        "control_detected_all_valid_models": bool(valid) and all(v["control_detected"] for v in valid),
        "candidate_detected_rate_valid_models": (
            sum(v["candidate_detected"] for v in valid) / len(valid) if valid else None
        ),
        "note": "Model-level summary only. Frames/stills are nested observations, not independent physical trials.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a frozen authorized person-detection ensemble on a sealed RAC Capture Lab session.")
    parser.add_argument("session_json")
    parser.add_argument("--benchmark-manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--output", default=None)
    parser.add_argument("--allow-unsealed", action="store_true", help="Development only; output is ineligible for physical evidence.")\n    parser.add_argument("--include-motion", action="store_true", help="Extract and analyze videos using the frozen motion_sampling contract.")\n    parser.add_argument("--motion-work-dir", default=None)
    args = parser.parse_args()

    session_path = Path(args.session_json).resolve()
    session = load_session(session_path)
    if not session.get("sealed") and not args.allow_unsealed:
        raise SystemExit("analysis blocked: session must be sealed")
    if session.get("evidence_class") == "physical_garment_p1" and not session.get("calibration_pass"):
        raise SystemExit("analysis blocked: P1 session calibration gate did not pass")
    failures = verify_capture_hashes(session_path, session)
    if failures:
        raise SystemExit("capture integrity failure: " + "; ".join(failures))

    contract = load_contract(session)
    benchmark_path = (ROOT / args.benchmark_manifest).resolve()
    benchmark_manifest = json.loads(benchmark_path.read_text())
    verified = verify_model_contracts(ROOT, benchmark_manifest, contract)

    requested = set(map(str, contract["models"]))
    evaluators, provenance, state_hashes = build_evaluators(benchmark_manifest)
    evaluators = [e for e in evaluators if e.name in requested]
    if {e.name for e in evaluators} != requested:
        raise SystemExit("failed to load every frozen model in analysis contract")
    for model_id in requested:
        if state_hashes[model_id] != verified[model_id]["weights_sha256"]:
            raise SystemExit(f"loaded model hash mismatch: {model_id}")

    records = collect_stills(session_path, session)
    predictions, summaries = analyze_stills(records, evaluators, {k: float(v) for k, v in contract["thresholds"].items()})
    pair = derive_pair_outcome(predictions, list(map(str, contract["models"])))\n\n    motion_predictions: list[dict[str, Any]] = []\n    motion_sequences: dict[str, Any] = {}\n    has_motion = any(session.get("captures", {}).get(arm, {}).get("videos", []) for arm in ("control", "candidate"))\n    if args.include_motion and has_motion:\n        from scripts.analyze_capture_motion import analyze_motion\n        work_dir = Path(args.motion_work_dir) if args.motion_work_dir else session_path.parent / ".rac-motion-frames"\n        motion_predictions, motion_sequences = analyze_motion(\n            session_path, session, contract, evaluators,\n            {k: float(v) for k, v in contract["thresholds"].items()}, work_dir\n        )

    result = {
        "schema_version": "1.0",
        "status": "measured_local_capture",
        "evidence_scope": session["evidence_class"],
        "session_id": session["session_id"],
        "experiment_id": session["experiment_id"],
        "session_freeze_sha256": session.get("freeze_sha256"),
        "capture_hash_verification": "PASS",
        "analysis_contract_sha256": canonical_sha256(contract),
        "benchmark_manifest_sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest(),
        "runner": {"python": sys.version.split()[0], "torch": torch.__version__, "platform": platform.platform()},
        "models": verified,
        "runtime_provenance": provenance,
        "predictions": predictions,
        "model_summaries": summaries,
        "paired_summary": pair,\n        "motion": {\n            "requested": bool(args.include_motion),\n            "source_videos_present": has_motion,\n            "predictions": motion_predictions,\n            "sequences": motion_sequences,\n        },
        "identity_mode": "disabled",
        "limitations": [
            "This runner performs person-detection analysis only.",\n            "Motion frames are deterministically sampled under the frozen motion_sampling contract when --include-motion is used.",
            "Still/frame outputs are nested observations and are not independent physical trials.",
            "Printed-flat prototype results are not RAC-P1 garment evidence.",
            "Results apply only to the frozen models, thresholds, preprocessing, captures, and conditions recorded here.",
        ],
    }
    result["result_sha256"] = canonical_sha256(result)
    output = Path(args.output) if args.output else session_path.with_name(session_path.stem.replace("-session", "") + "-inference.json")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "result_sha256": result["result_sha256"], "paired_summary": pair}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

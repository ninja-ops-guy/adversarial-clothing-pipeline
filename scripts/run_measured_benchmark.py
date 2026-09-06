from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from torchvision import __version__ as torchvision_version
from torchvision.models.detection import (
    FasterRCNN_MobileNet_V3_Large_320_FPN_Weights,
    SSDLite320_MobileNet_V3_Large_Weights,
    fasterrcnn_mobilenet_v3_large_320_fpn,
    ssdlite320_mobilenet_v3_large,
)
from torchvision.transforms.functional import pil_to_tensor, to_pil_image

from ruthless_pipeline.benchmark import BenchmarkConfig, ComparativeBenchmark
from ruthless_pipeline.evaluators import TorchvisionDetectionEvaluator


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_state_dict(model: torch.nn.Module) -> str:
    """Stable hash over parameter/buffer names, dtypes, shapes, and raw tensor bytes."""
    h = hashlib.sha256()
    state = model.state_dict()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        h.update(name.encode("utf-8"))
        h.update(str(tensor.dtype).encode("ascii"))
        h.update(str(tuple(tensor.shape)).encode("ascii"))
        h.update(tensor.numpy().tobytes())
    return h.hexdigest()


def download(url: str, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Ruthless-Adversarial-Clothing-Benchmark/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, dst.open("wb") as fh:
        fh.write(response.read())
    return dst


def image_tensor(image: Image.Image) -> torch.Tensor:
    return pil_to_tensor(image.convert("RGB")).float().div(255.0)


def prepare_fixture(pattern_path: Path, manifest: dict[str, Any], runtime_dir: Path) -> tuple[torch.Tensor, torch.Tensor, dict[str, Any]]:
    fixture = manifest["fixture"]
    source_path = runtime_dir / "source-zidane.jpg"
    download(fixture["source_url"], source_path)

    source = Image.open(source_path).convert("RGB")
    pattern = Image.open(pattern_path).convert("RGB")
    size = int(fixture.get("image_size", 320))

    # Two fixed crops isolate each player from the public convenience fixture. The patch ROI is
    # deliberately fixed and documented so the benchmark is deterministic and does not use a
    # measured detector to choose its own evaluation region.
    specs = [
        {
            "name": "left-player",
            "crop": (0.00, 0.00, 0.57, 1.00),
            "patch_roi": (0.22, 0.34, 0.80, 0.88),
        },
        {
            "name": "right-player",
            "crop": (0.43, 0.00, 1.00, 1.00),
            "patch_roi": (0.18, 0.30, 0.78, 0.88),
        },
    ]

    baseline_images: list[torch.Tensor] = []
    candidate_images: list[torch.Tensor] = []
    sample_records: list[dict[str, Any]] = []
    fixture_dir = runtime_dir / "fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)

    w, h = source.size
    for spec in specs:
        cx1, cy1, cx2, cy2 = spec["crop"]
        crop_box = (
            int(round(cx1 * w)),
            int(round(cy1 * h)),
            int(round(cx2 * w)),
            int(round(cy2 * h)),
        )
        baseline = source.crop(crop_box).resize((size, size), Image.Resampling.LANCZOS)

        rx1, ry1, rx2, ry2 = spec["patch_roi"]
        patch_box = (
            int(round(rx1 * size)),
            int(round(ry1 * size)),
            int(round(rx2 * size)),
            int(round(ry2 * size)),
        )
        candidate = baseline.copy()
        patch = pattern.resize((patch_box[2] - patch_box[0], patch_box[3] - patch_box[1]), Image.Resampling.BICUBIC)
        candidate.paste(patch, patch_box)

        baseline_path = fixture_dir / f"{spec['name']}-baseline.png"
        candidate_path = fixture_dir / f"{spec['name']}-candidate.png"
        baseline.save(baseline_path)
        candidate.save(candidate_path)

        baseline_images.append(image_tensor(baseline))
        candidate_images.append(image_tensor(candidate))
        sample_records.append(
            {
                "name": spec["name"],
                "crop_normalized": list(spec["crop"]),
                "patch_roi_normalized": list(spec["patch_roi"]),
                "baseline_sha256": sha256_file(baseline_path),
                "candidate_sha256": sha256_file(candidate_path),
            }
        )

    metadata = {
        "name": fixture["name"],
        "source_url": fixture["source_url"],
        "source_sha256": sha256_file(source_path),
        "sample_count": len(sample_records),
        "image_size": size,
        "samples": sample_records,
        "note": fixture["note"],
    }
    return torch.stack(baseline_images), torch.stack(candidate_images), metadata


class UltralyticsPersonEvaluator:
    def __init__(self, name: str, model_ref: str, class_id: int = 0) -> None:
        import ultralytics
        from ultralytics import YOLO

        self.name = name
        self.class_id = class_id
        self.package_version = ultralytics.__version__
        self.model_ref = model_ref
        self.model = YOLO(model_ref)

    def score(self, images: torch.Tensor) -> torch.Tensor:
        arrays = [
            (img.detach().cpu().clamp(0, 1).permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
            for img in images
        ]
        results = self.model.predict(source=arrays, imgsz=320, conf=0.001, verbose=False, device="cpu")
        scores: list[float] = []
        for result in results:
            boxes = result.boxes
            if boxes is None or boxes.cls.numel() == 0:
                scores.append(0.0)
                continue
            mask = boxes.cls.to(torch.int64) == self.class_id
            selected = boxes.conf[mask]
            scores.append(float(selected.max().item()) if selected.numel() else 0.0)
        return torch.tensor(scores, dtype=torch.float32, device=images.device)


class DETRPersonEvaluator:
    def __init__(self, name: str, model_ref: str, class_name: str = "person") -> None:
        import transformers
        from transformers import AutoImageProcessor, DetrForObjectDetection

        self.name = name
        self.model_ref = model_ref
        self.package_version = transformers.__version__
        self.device = torch.device("cpu")
        self.processor = AutoImageProcessor.from_pretrained(model_ref)
        self.model = DetrForObjectDetection.from_pretrained(model_ref).to(self.device).eval()
        for parameter in self.model.parameters():
            parameter.requires_grad_(False)

        id2label = {int(k): str(v) for k, v in self.model.config.id2label.items()}
        target = class_name.strip().lower()
        matches = [idx for idx, label in id2label.items() if label.strip().lower() == target]
        if not matches:
            raise ValueError(f"Could not resolve DETR class {class_name!r}; available labels include {list(id2label.values())[:10]}")
        self.class_id = matches[0]

    def score(self, images: torch.Tensor) -> torch.Tensor:
        pil_images = [to_pil_image(img.detach().cpu().clamp(0, 1)) for img in images]
        inputs = self.processor(images=pil_images, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
        probabilities = outputs.logits.softmax(-1)[..., self.class_id]
        return probabilities.max(dim=1).values.to(images.device)


def build_evaluators(manifest: dict[str, Any]) -> tuple[list[Any], dict[str, dict[str, Any]], dict[str, str]]:
    evaluators: list[Any] = []
    provenance: dict[str, dict[str, Any]] = {}
    state_hashes: dict[str, str] = {}

    for item in manifest["models"]:
        model_id = item["id"]
        if model_id == "yolov8n":
            evaluator = UltralyticsPersonEvaluator(model_id, item["model_ref"], int(item["person_class"]))
            provenance[model_id] = {
                "display_name": item["display_name"],
                "framework": item["framework"],
                "model_ref": item["model_ref"],
                "framework_version": evaluator.package_version,
            }
        elif model_id == "detr_resnet50":
            evaluator = DETRPersonEvaluator(model_id, item["model_ref"], str(item["person_class"]))
            provenance[model_id] = {
                "display_name": item["display_name"],
                "framework": item["framework"],
                "model_ref": item["model_ref"],
                "framework_version": evaluator.package_version,
            }
        elif model_id == "fasterrcnn_mobilenet_v3_320":
            weights = FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.DEFAULT
            model = fasterrcnn_mobilenet_v3_large_320_fpn(weights=weights)
            evaluator = TorchvisionDetectionEvaluator(name=model_id, model=model, class_label=int(item["person_class"]), device="cpu")
            provenance[model_id] = {
                "display_name": item["display_name"],
                "framework": item["framework"],
                "model_ref": str(weights),
                "framework_version": torchvision_version,
            }
        elif model_id == "ssdlite320_mobilenet_v3":
            weights = SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
            model = ssdlite320_mobilenet_v3_large(weights=weights)
            evaluator = TorchvisionDetectionEvaluator(name=model_id, model=model, class_label=int(item["person_class"]), device="cpu")
            provenance[model_id] = {
                "display_name": item["display_name"],
                "framework": item["framework"],
                "model_ref": str(weights),
                "framework_version": torchvision_version,
            }
        else:
            raise ValueError(f"Unsupported model id in manifest: {model_id}")
        state_hashes[model_id] = sha256_state_dict(evaluator.model)
        evaluators.append(evaluator)

    return evaluators, provenance, state_hashes


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    n = len(rows)
    baseline_mean = sum(float(row["baseline_score"]) for row in rows) / n
    candidate_mean = sum(float(row["candidate_score"]) for row in rows) / n
    baseline_rate = sum(float(row["baseline_detected"]) for row in rows) / n
    candidate_rate = sum(float(row["candidate_detected"]) for row in rows) / n
    relative_suppression = None
    if baseline_rate > 0:
        relative_suppression = (baseline_rate - candidate_rate) / baseline_rate
    confidence_reduction = None
    if baseline_mean > 0:
        confidence_reduction = (baseline_mean - candidate_mean) / baseline_mean
    return {
        "n": n,
        "baseline_mean_confidence": baseline_mean,
        "candidate_mean_confidence": candidate_mean,
        "baseline_detection_rate": baseline_rate,
        "candidate_detection_rate": candidate_rate,
        "absolute_detection_reduction": baseline_rate - candidate_rate,
        "relative_detection_suppression": relative_suppression,
        "relative_confidence_reduction": confidence_reduction,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run measured detector inference for the Pattern Lab canonical candidate")
    parser.add_argument("--manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--candidate", default="benchmarks/runtime/candidate.png")
    parser.add_argument("--candidate-config", default="benchmarks/runtime/candidate-config.json")
    parser.add_argument("--output", default="benchmark-results.json")
    parser.add_argument("--runtime-dir", default="benchmarks/runtime")
    args = parser.parse_args()

    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    manifest_path = ROOT / args.manifest
    candidate_path = ROOT / args.candidate
    candidate_config_path = ROOT / args.candidate_config
    output_path = ROOT / args.output
    runtime_dir = ROOT / args.runtime_dir
    runtime_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text())
    candidate_config = json.loads(candidate_config_path.read_text())
    baseline, candidate, fixture_metadata = prepare_fixture(candidate_path, manifest, runtime_dir)

    evaluators, model_provenance, state_hashes = build_evaluators(manifest)
    sweep = manifest["transform_sweep"]
    surrogate_ids = tuple(item["id"] for item in manifest["models"] if item.get("role") == "surrogate")
    heldout_ids = tuple(item["id"] for item in manifest["models"] if item.get("role") == "heldout")
    if not surrogate_ids or not heldout_ids:
        raise ValueError("manifest must define non-empty surrogate and heldout model roles")

    lock_proposal = {
        "schema_version": "1.0",
        "generated_from_commit": os.getenv("GITHUB_SHA", "local"),
        "models": {
            item["id"]: {
                "state_dict_sha256": state_hashes[item["id"]],
                "display_name": item["display_name"],
                "framework": item["framework"],
                "model_ref": item["model_ref"],
                "role": item["role"],
                "decision_threshold": float(item["decision_threshold"]),
            }
            for item in manifest["models"]
        },
    }
    (runtime_dir / "model-lock-proposal.json").write_text(json.dumps(lock_proposal, indent=2, sort_keys=True) + "\n")

    mismatches = []
    for item in manifest["models"]:
        expected = str(item.get("state_dict_sha256", "")).lower()
        actual = state_hashes[item["id"]]
        if len(expected) != 64:
            mismatches.append(f"{item['id']}: no preregistered state_dict_sha256")
        elif expected != actual:
            mismatches.append(f"{item['id']}: state_dict hash mismatch")
    locked = not mismatches

    config = BenchmarkConfig(
        threshold=float(manifest.get("threshold", 0.5)),
        thresholds={item["id"]: float(item["decision_threshold"]) for item in manifest["models"]},
        brightness=tuple(float(v) for v in sweep["brightness"]),
        scales=tuple(float(v) for v in sweep["scale"]),
        blur_sigmas=tuple(float(v) for v in sweep["blur_sigma"]),
        rotations_deg=tuple(float(v) for v in sweep.get("rotation_deg", [0.0])),
        surrogate_models=surrogate_ids,
        heldout_models=heldout_ids,
        min_baseline_score=float(manifest.get("min_baseline_score", 0.5)),
        seed=1337,
        device="cpu",
    )
    benchmark = ComparativeBenchmark(config, evaluators)
    summary = benchmark.run(baseline, candidate)

    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in benchmark.rows:
        by_model[str(row["model"])].append(row)

    model_results: dict[str, Any] = {}
    model_ids = surrogate_ids + heldout_ids
    manifest_by_id = {item["id"]: item for item in manifest["models"]}
    for model_id in model_ids:
        model_results[model_id] = {
            **model_provenance[model_id],
            "role": manifest_by_id[model_id]["role"],
            "decision_threshold": float(manifest_by_id[model_id]["decision_threshold"]),
            "state_dict_sha256": state_hashes[model_id],
            "preregistered_hash_match": (
                str(manifest_by_id[model_id].get("state_dict_sha256", "")).lower() == state_hashes[model_id]
            ),
            **aggregate([row for row in by_model[model_id] if row["baseline_qualified"]]),
        }

    all_aggregate = aggregate(list(benchmark.rows))
    generated_at = datetime.now(timezone.utc).isoformat()
    result = {
        "schema_version": "1.0",
        "status": "measured_locked" if locked else "measured_unlocked",
        "certification_eligible": locked,
        "lock_failures": mismatches,
        "evidence_scope": "digital_ci_convenience_fixture",
        "generated_at": generated_at,
        "source_commit": os.getenv("GITHUB_SHA", "local"),
        "runner": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "platform": platform.platform(),
            "device": "cpu",
        },
        "candidate": {
            "config": candidate_config,
            "sha256": sha256_file(candidate_path),
            "source": "Pattern Lab browser canvas",
        },
        "fixture": fixture_metadata,
        "benchmark": {
            "default_threshold": config.threshold,
            "thresholds": config.thresholds,
            "surrogate_models": list(config.surrogate_models),
            "heldout_models": list(config.heldout_models),
            "brightness": list(config.brightness),
            "scale": list(config.scales),
            "blur_sigma": list(config.blur_sigmas),
            "conditions_per_model": len(config.brightness) * len(config.scales) * len(config.blur_sigmas),
            "raw_row_count": len(benchmark.rows),
            "comparative_summary": summary,
        },
        "models": model_results,
        "aggregate": all_aggregate,
        "model_lock": lock_proposal,
        "caveats": [
            "D2 certification eligibility requires all detector state hashes to have been preregistered before this run.",
            "These are measured model-inference results for a two-crop digital convenience fixture, not a physical garment test.",
            "The pattern is digitally pasted into fixed torso-like ROIs; fabric drape, pose diversity, camera distance, and print processes are not represented by this CI fixture.",
            "The benchmark reports only the named model versions in this run and must not be generalized to untested surveillance systems.",
            "A physical or protocol-certified claim requires the repository's separate certification evidence process.",
        ],
        "rows": benchmark.rows,
    }

    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    csv_path = runtime_dir / "benchmark-rows.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(benchmark.rows[0].keys()))
        writer.writeheader()
        writer.writerows(benchmark.rows)

    print(json.dumps({
        "output": str(output_path),
        "candidate_sha256": result["candidate"]["sha256"],
        "raw_rows": len(benchmark.rows),
        "aggregate": all_aggregate,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

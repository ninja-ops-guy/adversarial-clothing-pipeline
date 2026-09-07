from __future__ import annotations

import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import torch

from scripts.analyze_capture_session import CaptureEvaluator, FrameRecord, analyze_stills, image_tensor


@dataclass(frozen=True)
class MotionSamplingSpec:
    fps: float = 2.0
    max_frames: int = 120
    aggregation: str = "sequence_fraction"\n    sequence_detection_threshold: float = 0.5

    @classmethod
    def from_contract(cls, contract: dict[str, Any]) -> "MotionSamplingSpec":
        raw = contract.get("motion_sampling")
        if not isinstance(raw, dict):
            raise ValueError("motion captures require a frozen motion_sampling contract")
        spec = cls(
            fps=float(raw.get("fps", 0)),
            max_frames=int(raw.get("max_frames", 0)),
            aggregation=str(raw.get("aggregation", "")),\n            sequence_detection_threshold=float(raw.get("sequence_detection_threshold", 0.5)),
        )
        if not math.isfinite(spec.fps) or spec.fps <= 0 or spec.fps > 30:
            raise ValueError("motion_sampling.fps must be finite and in (0,30]")
        if not 1 <= spec.max_frames <= 10000:
            raise ValueError("motion_sampling.max_frames must be in [1,10000]")
        if not math.isfinite(spec.sequence_detection_threshold) or not 0 <= spec.sequence_detection_threshold <= 1:\n            raise ValueError("motion_sampling.sequence_detection_threshold must be in [0,1]")\n        if spec.aggregation not in {"sequence_fraction", "any_detected", "majority_detected"}:
            raise ValueError("unsupported motion_sampling.aggregation")
        return spec


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} is required for motion analysis")
    return path


def probe_duration(path: Path) -> float:
    proc = subprocess.run(
        [_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    duration = float(json.loads(proc.stdout)["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError(f"invalid video duration: {path}")
    return duration


def extract_frames(video: Path, output_dir: Path, spec: MotionSamplingSpec) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(video)
    expected = min(spec.max_frames, max(1, int(math.ceil(duration * spec.fps))))
    pattern = output_dir / "frame-%06d.jpg"
    subprocess.run(
        [
            _tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
            "-vf", f"fps={spec.fps}", "-frames:v", str(expected), "-q:v", "2", str(pattern),
        ],
        check=True,
    )
    frames = sorted(output_dir.glob("frame-*.jpg"))
    if not frames:
        raise RuntimeError(f"ffmpeg produced no frames for {video}")
    return frames[: spec.max_frames]


def longest_true_run(values: list[bool]) -> int:
    best = current = 0
    for value in values:
        current = current + 1 if value else 0
        best = max(best, current)
    return best


def longest_false_run(values: list[bool]) -> int:
    return longest_true_run([not value for value in values])


def aggregate_sequence(rows: list[dict[str, Any]], spec: MotionSamplingSpec) -> dict[str, Any]:
    detected = [bool(row["detected"]) for row in rows]
    scores = [float(row["target_score"]) for row in rows]
    fraction = sum(detected) / len(detected) if detected else None
    if spec.aggregation == "any_detected":
        outcome = any(detected)
    elif spec.aggregation == "majority_detected":
        outcome = bool(detected) and fraction >= 0.5
    else:
        outcome = fraction
    return {
        "n_frames": len(rows),
        "detection_fraction": fraction,
        "mean_target_score": sum(scores) / len(scores) if scores else None,
        "max_target_score": max(scores) if scores else None,
        "longest_detected_run_frames": longest_true_run(detected),
        "longest_gap_frames": longest_false_run(detected),
        "aggregation": spec.aggregation,
        "sequence_outcome": outcome,\n        "sequence_detected": (fraction >= spec.sequence_detection_threshold) if fraction is not None else None,\n        "sequence_detection_threshold": spec.sequence_detection_threshold,
        "note": "Frames are nested within this sequence and are not independent inferential units.",
    }


def analyze_motion(
    session_path: Path,
    session: dict[str, Any],
    contract: dict[str, Any],
    evaluators: list[CaptureEvaluator],
    thresholds: dict[str, float],
    work_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = MotionSamplingSpec.from_contract(contract)
    all_predictions: list[dict[str, Any]] = []
    sequences: dict[str, Any] = {}
    root = session_path.parent

    for arm in ("control", "candidate"):
        for record in session.get("captures", {}).get(arm, {}).get("videos", []):
            capture_id = str(record.get("id", record["path"]))
            video = root / str(record["path"])
            frames = extract_frames(video, work_dir / arm / capture_id, spec)
            analyzed = [
                (
                    FrameRecord(
                        arm=arm,
                        capture_id=f"{capture_id}:frame:{index:06d}",
                        path=str(frame),
                        timestamp=record.get("timestamp"),
                        condition=record.get("condition"),
                    ),
                    image_tensor(frame),
                )
                for index, frame in enumerate(frames, start=1)
            ]
            rows, _ = analyze_stills(analyzed, evaluators, thresholds)
            all_predictions.extend(rows)
            sequences[capture_id] = {
                "arm": arm,
                "source_path": str(record["path"]),
                "source_sha256": record.get("sha256"),
                "sampling": {"fps": spec.fps, "max_frames": spec.max_frames, "aggregation": spec.aggregation, "sequence_detection_threshold": spec.sequence_detection_threshold},
                "models": {},
            }
            for evaluator in evaluators:
                model_rows = [row for row in rows if row["model_id"] == evaluator.name]
                sequences[capture_id]["models"][evaluator.name] = aggregate_sequence(model_rows, spec)

    return all_predictions, sequences

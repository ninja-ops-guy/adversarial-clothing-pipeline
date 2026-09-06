from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Protocol

import torch
import torch.nn.functional as F

from .common import atomic_json_dump, ensure_dir, resolve_device, seed_everything, validate_image_tensor


class Evaluator(Protocol):
    name: str
    def score(self, images: torch.Tensor) -> torch.Tensor: ...


@dataclass
class CallableEvaluator:
    name: str
    fn: Callable[[torch.Tensor], torch.Tensor]

    def score(self, images: torch.Tensor) -> torch.Tensor:
        out = self.fn(images)
        if not isinstance(out, torch.Tensor):
            out = torch.as_tensor(out, device=images.device, dtype=torch.float32)
        return out.float().reshape(-1)


@dataclass
class BenchmarkConfig:
    threshold: float = 0.5
    thresholds: dict[str, float] | None = None
    brightness: tuple[float, ...] = (0.7, 1.0, 1.3)
    scales: tuple[float, ...] = (0.65, 1.0, 1.35)
    blur_sigmas: tuple[float, ...] = (0.0, 0.8, 1.6)
    rotations_deg: tuple[float, ...] = (0.0,)
    surrogate_models: tuple[str, ...] = ()
    heldout_models: tuple[str, ...] = ()
    min_baseline_score: float = 0.5
    seed: int = 1337
    device: str = "auto"


class ComparativeBenchmark:
    """Held-out benchmark with baseline qualification and invalid-condition accounting."""

    def __init__(self, config: BenchmarkConfig, evaluators: Iterable[Evaluator]):
        seed_everything(config.seed)
        self.config = config
        self.device = resolve_device(config.device)
        self.evaluators = {e.name: e for e in evaluators}
        missing = [n for n in (*config.surrogate_models, *config.heldout_models) if n not in self.evaluators]
        if missing:
            raise ValueError(f"Missing evaluators: {missing}")
        self.rows: list[dict] = []

    @staticmethod
    def _gaussian_blur(x: torch.Tensor, sigma: float) -> torch.Tensor:
        if sigma <= 0:
            return x
        radius = max(1, int(round(3 * sigma)))
        coords = torch.arange(-radius, radius + 1, device=x.device, dtype=x.dtype)
        kernel = torch.exp(-(coords**2) / (2 * sigma * sigma))
        kernel = kernel / kernel.sum()
        kx = kernel.view(1, 1, 1, -1).repeat(x.shape[1], 1, 1, 1)
        ky = kernel.view(1, 1, -1, 1).repeat(x.shape[1], 1, 1, 1)
        x = F.conv2d(x, kx, padding=(0, radius), groups=x.shape[1])
        return F.conv2d(x, ky, padding=(radius, 0), groups=x.shape[1])

    @staticmethod
    def _rotate(x: torch.Tensor, degrees: float) -> torch.Tensor:
        if degrees == 0:
            return x
        angle = torch.tensor(degrees * torch.pi / 180.0, device=x.device, dtype=x.dtype)
        c, s = torch.cos(angle), torch.sin(angle)
        theta = torch.zeros((x.shape[0], 2, 3), device=x.device, dtype=x.dtype)
        theta[:, 0, 0] = c
        theta[:, 0, 1] = -s
        theta[:, 1, 0] = s
        theta[:, 1, 1] = c
        grid = F.affine_grid(theta, x.size(), align_corners=False)
        return F.grid_sample(x, grid, mode="bilinear", padding_mode="border", align_corners=False)

    def _transform(self, x: torch.Tensor, brightness: float, scale: float, sigma: float, rotation: float) -> torch.Tensor:
        _, _, h, w = x.shape
        y = (x * brightness).clamp(0, 1)
        if scale != 1.0:
            nh, nw = max(16, int(round(h * scale))), max(16, int(round(w * scale)))
            y = F.interpolate(y, size=(nh, nw), mode="bilinear", align_corners=False)
            y = F.interpolate(y, size=(h, w), mode="bilinear", align_corners=False)
        y = self._gaussian_blur(y, sigma)
        return self._rotate(y, rotation)

    def _threshold(self, model: str) -> float:
        return (self.config.thresholds or {}).get(model, self.config.threshold)

    def run(self, baseline: torch.Tensor, candidate: torch.Tensor) -> dict:
        validate_image_tensor(baseline)
        validate_image_tensor(candidate)
        baseline = baseline.to(self.device)
        candidate = candidate.to(self.device)
        if baseline.shape != candidate.shape:
            raise ValueError("baseline and candidate must have the same shape")
        self.rows.clear()
        names = self.config.surrogate_models + self.config.heldout_models or tuple(self.evaluators.keys())
        for name in names:
            evaluator = self.evaluators[name]
            split = "heldout" if name in self.config.heldout_models else "surrogate"
            threshold = self._threshold(name)
            for br in self.config.brightness:
                for sc in self.config.scales:
                    for sigma in self.config.blur_sigmas:
                        for rotation in self.config.rotations_deg:
                            bimg = self._transform(baseline, br, sc, sigma, rotation)
                            cimg = self._transform(candidate, br, sc, sigma, rotation)
                            with torch.no_grad():
                                bs = evaluator.score(bimg).mean().item()
                                cs = evaluator.score(cimg).mean().item()
                            valid = bs >= self.config.min_baseline_score
                            self.rows.append({
                                "model": name,
                                "split": split,
                                "brightness": br,
                                "scale": sc,
                                "blur_sigma": sigma,
                                "rotation_deg": rotation,
                                "threshold": threshold,
                                "baseline_score": bs,
                                "candidate_score": cs,
                                "delta": cs - bs,
                                "baseline_qualified": float(valid),
                                "baseline_detected": float(bs >= threshold),
                                "candidate_detected": float(cs >= threshold) if valid else None,
                            })
        return self.summary()

    @staticmethod
    def _aggregate(rows: list[dict]) -> dict:
        if not rows:
            return {"n": 0}
        valid = [r for r in rows if r["baseline_qualified"]]
        if not valid:
            return {"n": len(rows), "valid_n": 0, "baseline_detection_rate": 0.0, "candidate_detection_rate": 1.0}
        return {
            "n": len(rows),
            "valid_n": len(valid),
            "baseline_mean": sum(r["baseline_score"] for r in valid) / len(valid),
            "candidate_mean": sum(r["candidate_score"] for r in valid) / len(valid),
            "mean_delta": sum(r["delta"] for r in valid) / len(valid),
            "baseline_detection_rate": sum(r["baseline_detected"] for r in valid) / len(valid),
            "candidate_detection_rate": sum(float(r["candidate_detected"]) for r in valid) / len(valid),
        }

    def summary(self) -> dict:
        if not self.rows:
            return {"num_rows": 0}
        invalid = sum(1 for r in self.rows if not r["baseline_qualified"])
        return {
            "num_rows": len(self.rows),
            "invalid_condition_fraction": invalid / len(self.rows),
            "all": self._aggregate(self.rows),
            "surrogate": self._aggregate([r for r in self.rows if r["split"] == "surrogate"]),
            "heldout": self._aggregate([r for r in self.rows if r["split"] == "heldout"]),
        }

    def save(self, output_dir: str | Path, name: str = "benchmark") -> tuple[Path, Path]:
        output_dir = ensure_dir(output_dir)
        csv_path = output_dir / f"{name}.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.rows[0].keys()) if self.rows else ["model"])
            writer.writeheader()
            writer.writerows(self.rows)
        json_path = output_dir / f"{name}.json"
        atomic_json_dump(json_path, {"config": asdict(self.config), "summary": self.summary(), "rows": self.rows})
        return csv_path, json_path

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional, Protocol

import torch
import torch.nn.functional as F

from .common import atomic_json_dump, ensure_dir, resolve_device, seed_everything, validate_image_tensor


class Evaluator(Protocol):
    name: str
    def score(self, images: torch.Tensor) -> torch.Tensor: ...  # lower = less reliable classification


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
    brightness: tuple[float, ...] = (0.7, 1.0, 1.3)
    scales: tuple[float, ...] = (0.65, 1.0, 1.35)
    blur_sigmas: tuple[float, ...] = (0.0, 0.8, 1.6)
    surrogate_models: tuple[str, ...] = ()
    heldout_models: tuple[str, ...] = ()
    seed: int = 1337
    device: str = "auto"


class ComparativeBenchmark:
    """Held-out, transformation-aware benchmark for owned/authorized evaluators.

    Reports raw confidence and thresholded detection rates for baseline vs candidate.
    It does not infer claims for untested commercial systems.
    """

    def __init__(self, config: BenchmarkConfig, evaluators: Iterable[Evaluator]):
        seed_everything(config.seed)
        self.config = config
        self.device = resolve_device(config.device)
        self.evaluators = {e.name: e for e in evaluators}
        missing = [n for n in (*config.surrogate_models,*config.heldout_models) if n not in self.evaluators]
        if missing:
            raise ValueError(f"Missing evaluators: {missing}")
        self.rows: list[dict] = []

    @staticmethod
    def _gaussian_blur(x: torch.Tensor, sigma: float) -> torch.Tensor:
        if sigma <= 0:
            return x
        radius = max(1, int(round(3*sigma)))
        coords = torch.arange(-radius, radius+1, device=x.device, dtype=x.dtype)
        kernel = torch.exp(-(coords**2)/(2*sigma*sigma)); kernel = kernel/kernel.sum()
        kx = kernel.view(1,1,1,-1).repeat(x.shape[1],1,1,1)
        ky = kernel.view(1,1,-1,1).repeat(x.shape[1],1,1,1)
        x = F.conv2d(x, kx, padding=(0,radius), groups=x.shape[1])
        x = F.conv2d(x, ky, padding=(radius,0), groups=x.shape[1])
        return x

    def _transform(self, x: torch.Tensor, brightness: float, scale: float, sigma: float) -> torch.Tensor:
        b,c,h,w = x.shape
        y = (x * brightness).clamp(0,1)
        if scale != 1.0:
            nh,nw = max(16,int(round(h*scale))), max(16,int(round(w*scale)))
            y = F.interpolate(y, size=(nh,nw), mode="bilinear", align_corners=False)
            y = F.interpolate(y, size=(h,w), mode="bilinear", align_corners=False)
        y = self._gaussian_blur(y, sigma)
        return y

    def run(self, baseline: torch.Tensor, candidate: torch.Tensor) -> dict:
        validate_image_tensor(baseline); validate_image_tensor(candidate)
        baseline = baseline.to(self.device); candidate = candidate.to(self.device)
        if baseline.shape != candidate.shape:
            raise ValueError("baseline and candidate must have the same shape")
        self.rows.clear()
        names = self.config.surrogate_models + self.config.heldout_models
        if not names:
            names = tuple(self.evaluators.keys())
        for name in names:
            evaluator = self.evaluators[name]
            split = "heldout" if name in self.config.heldout_models else "surrogate"
            for br in self.config.brightness:
                for sc in self.config.scales:
                    for sigma in self.config.blur_sigmas:
                        bimg = self._transform(baseline, br, sc, sigma)
                        cimg = self._transform(candidate, br, sc, sigma)
                        with torch.no_grad():
                            bs = evaluator.score(bimg).mean().item()
                            cs = evaluator.score(cimg).mean().item()
                        self.rows.append({
                            "model":name,"split":split,"brightness":br,"scale":sc,"blur_sigma":sigma,
                            "baseline_score":bs,"candidate_score":cs,"delta":cs-bs,
                            "baseline_detected":float(bs >= self.config.threshold),
                            "candidate_detected":float(cs >= self.config.threshold),
                        })
        return self.summary()

    def summary(self) -> dict:
        if not self.rows:
            return {"num_rows":0}
        def agg(rows: list[dict]) -> dict:
            if not rows: return {"n":0}
            n=len(rows)
            return {
                "n":n,
                "baseline_mean":sum(r["baseline_score"] for r in rows)/n,
                "candidate_mean":sum(r["candidate_score"] for r in rows)/n,
                "mean_delta":sum(r["delta"] for r in rows)/n,
                "baseline_detection_rate":sum(r["baseline_detected"] for r in rows)/n,
                "candidate_detection_rate":sum(r["candidate_detected"] for r in rows)/n,
            }
        return {
            "num_rows":len(self.rows),
            "all":agg(self.rows),
            "surrogate":agg([r for r in self.rows if r["split"]=="surrogate"]),
            "heldout":agg([r for r in self.rows if r["split"]=="heldout"]),
        }

    def save(self, output_dir: str | Path, name: str = "benchmark") -> tuple[Path,Path]:
        output_dir = ensure_dir(output_dir)
        csv_path = output_dir / f"{name}.csv"
        with open(csv_path,"w",newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.rows[0].keys()) if self.rows else ["model"])
            writer.writeheader(); writer.writerows(self.rows)
        json_path = output_dir / f"{name}.json"
        atomic_json_dump(json_path, {"config":asdict(self.config),"summary":self.summary(),"rows":self.rows})
        return csv_path,json_path

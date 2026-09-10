"""Barrier 3 thin coordinator: compose the existing six-stage engine.

Classification (per the execution survey): CAN_COMPOSE_EXISTING_ENGINE = YES.
Every stage already exposes a deterministic, contract-validated entrypoint;
this module only wires them together and pins provenance/hashes:

    Optimization V3        ruthless_pipeline.optimization.optimizer
                           CandidatePoolSearchOptimizer + Objective (frozen
                           schemas/optimization_objective.schema.json)
    EOT                    ruthless_pipeline.transformations.distribution
                           TransformationDistributionSpec + Sampler (frozen
                           schemas/transformation_distribution.schema.json)
    Detector Science       ruthless_pipeline.detector_science.adapters
                           SyntheticDetectionAdapter (capabilities-guarded)
    Pareto / Style         ruthless_pipeline.optimization.pareto.classify +
                           optimization.style.StyleFamilyScorer
    Printability           ruthless_pipeline.physical_transfer.printability
                           .printability_loss
    Physical Transfer      ruthless_pipeline.physical_transfer.transfer_record
                           .emit (synthetic_generator=True forces
                           synthetic_pipeline_validation_only)

Guarantees:

- single-process, seed-controlled: every stochastic value derives from
  ``config.master_seed`` via sha256 sub-seed chaining; no wall-clock, no
  uuid, no hidden entropy in any scientific artifact;
- hash-pinned: every stage artifact carries the sha256 of its canonical
  JSON payload plus the sha256 of its upstream inputs;
- replayable: ``verify_replay`` compares two runs field-by-field
  (runtime-environment.json is the only excluded, non-scientific file);
- synthetic-only: the physical transfer record is forced to
  evidence_class ``synthetic_pipeline_validation_only`` and
  physical_efficacy_claimed stays False. This coordinator can never touch
  held-out models, D2-0004/D2-0005 surfaces, or measured evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from ruthless_pipeline.detector_science.adapters import SyntheticDetectionAdapter
from ruthless_pipeline.optimization.objective_registry import (
    Objective,
    aggregate_detector_scores,
)
from ruthless_pipeline.optimization.optimizer import (
    Candidate,
    CandidatePoolSearchOptimizer,
)
from ruthless_pipeline.optimization.pareto import classify
from ruthless_pipeline.optimization.schemas import DetectorAggregation, ObjectiveSpec
from ruthless_pipeline.optimization.style import FAMILIES, StyleFamilyScorer
from ruthless_pipeline.optimization.trajectory import TrajectoryRecorder
from ruthless_pipeline.physical_transfer.printability import printability_loss
from ruthless_pipeline.physical_transfer.transfer_record import (
    SYNTHETIC,
    emit as emit_transfer_record,
)
from ruthless_pipeline.transformations.distribution import (
    Sampler,
    TransformationDistributionSpec,
)

COORDINATOR_VERSION = "1.0.0"
RUN_ID = "RAC-BARRIER3-SYNTHETIC-001"

# Files excluded from scientific replay equivalence (non-scientific metadata).
REPLAY_EXCLUDED_FILES = ("runtime-environment.json",)

# Verification overlays derived from the pinned artifacts (not stage outputs):
# excluded from the pinning requirement and from replay equivalence.
OVERLAY_FILES = ("replay-report.json", "barrier3-report.json")

# Synthetic detector ensemble used by the integration proof. These are not
# real models; they exist so the composed path exercises the same contracts.
SYNTHETIC_DETECTORS = (
    {"model_id": "rac-synthetic-detector-0", "model_family": "synthetic-family"},
    {"model_id": "rac-synthetic-detector-1", "model_family": "synthetic-family"},
    {"model_id": "rac-synthetic-detector-2", "model_family": "synthetic-family"},
)


class Barrier3Error(RuntimeError):
    """Raised on any integrity violation in the integrated path. Never
    silently recovered from."""


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def _u01(*parts: Any) -> float:
    """Deterministic uniform in [0, 1) from arbitrary key material."""
    digest = hashlib.sha256(
        "|".join(str(p) for p in parts).encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def derive_seed(master_seed: int, purpose: str) -> int:
    return int.from_bytes(
        hashlib.sha256(f"barrier3|{purpose}|{int(master_seed)}".encode()).digest()[:4],
        "big",
    )


@dataclass(frozen=True)
class Barrier3Config:
    """Fully seed-controlled configuration of one integration run."""

    master_seed: int = 20260910
    n_candidates: int = 8
    candidate_shape: tuple[int, int, int] = (32, 32, 3)
    n_eot_samples: int = 6
    aggregation: str = "CVAR"
    alpha: float = 0.5
    lambda_print: float = 0.2
    lambda_style: float = 0.2
    lambda_reg: float = 0.01
    n_detectors: int = 3

    def __post_init__(self) -> None:
        if self.n_candidates < 2:
            raise Barrier3Error("n_candidates must be >= 2")
        if self.n_eot_samples < 1:
            raise Barrier3Error("n_eot_samples must be >= 1")
        if self.aggregation == "CVAR" and not 0.0 < self.alpha <= 1.0:
            raise Barrier3Error("CVaR alpha must be in (0, 1]")
        if self.n_detectors != len(SYNTHETIC_DETECTORS):
            raise Barrier3Error(
                "n_detectors must match the pinned synthetic ensemble size "
                f"({len(SYNTHETIC_DETECTORS)})"
            )

    def to_dict(self) -> dict:
        return {
            "master_seed": self.master_seed,
            "n_candidates": self.n_candidates,
            "candidate_shape": list(self.candidate_shape),
            "n_eot_samples": self.n_eot_samples,
            "aggregation": self.aggregation,
            "alpha": self.alpha,
            "lambda_print": self.lambda_print,
            "lambda_style": self.lambda_style,
            "lambda_reg": self.lambda_reg,
            "n_detectors": self.n_detectors,
            "coordinator_version": COORDINATOR_VERSION,
        }

    def sha256(self) -> str:
        return sha256_obj(self.to_dict())


# ---------------------------------------------------------------------------
# Synthetic inputs (all derived from master_seed; no external/fabricated data)
# ---------------------------------------------------------------------------


def make_candidate_pool(config: Barrier3Config) -> list[Candidate]:
    """Deterministic synthetic candidate images in [0, 1]."""
    rng = np.random.default_rng(derive_seed(config.master_seed, "pool"))
    pool = []
    for i in range(config.n_candidates):
        params = rng.uniform(0.05, 0.95, size=config.candidate_shape)
        pool.append(
            Candidate(
                candidate_id=f"b3-cand-{i:03d}",
                params=np.asarray(params, dtype=float),
                metadata={"origin": "synthetic_generator"},
            )
        )
    return pool


def make_eot_spec(config: Barrier3Config) -> TransformationDistributionSpec:
    """Small but schema-complete EOT distribution over all four groups."""
    u = lambda lo, hi: {"type": "uniform", "params": {"min": lo, "max": hi}}  # noqa: E731
    manifest = {
        "geometry": {
            "scale": u(0.8, 1.2),
            "camera_distance": u(1.5, 3.5),
            "perspective": u(0.0, 0.1),
            "yaw": u(-25.0, 25.0),
            "pitch": u(-15.0, 15.0),
            "roll": u(-10.0, 10.0),
            "translation": u(-0.15, 0.15),
        },
        "imaging": {
            "blur": u(0.0, 2.0),
            "resize_interpolation": {"type": "choice", "params": {"values": ["bilinear", "nearest"]}},
            "compression": u(0.0, 0.4),
            "exposure": u(-0.2, 0.2),
            "contrast": u(-0.15, 0.15),
        },
        "garment": {
            "stretch": u(0.0, 0.15),
            "wrinkle": u(0.0, 0.4),
            "fold": u(0.0, 0.3),
            "bend": u(0.0, 0.3),
            "partial_occlusion": u(0.0, 0.2),
        },
        "print_capture": {
            "gamut_mapping": {"type": "choice", "params": {"values": ["clip", "compress"]}},
            "resolution_loss": u(0.0, 0.3),
        },
    }
    return TransformationDistributionSpec(
        distribution_id="RAC-BARRIER3-EOT-SYNTHETIC",
        parameter_manifest=manifest,
        seed=derive_seed(config.master_seed, "eot"),
    )


def make_objective_spec(config: Barrier3Config) -> ObjectiveSpec:
    return ObjectiveSpec.from_dict(
        {
            "schema_version": "1.0",
            "objective_id": "RAC-BARRIER3-SYNTHETIC-OBJECTIVE",
            "seed": derive_seed(config.master_seed, "objective"),
            "terms": {
                "detector_loss": {
                    "aggregation": config.aggregation,
                    **({"alpha": config.alpha} if config.aggregation == "CVAR" else {}),
                    "log_separately": True,
                },
                "printability_loss": {"lambda_print": config.lambda_print, "log_separately": True},
                "style_loss": {"lambda_style": config.lambda_style, "log_separately": True},
                "regularization": {"lambda_reg": config.lambda_reg, "log_separately": True},
            },
            "future_generations_only": True,
        }
    )


def make_production_profile(config: Barrier3Config) -> dict:
    """Synthetic printability profile (assumed, not vendor-measured)."""
    return {
        "profile_id": "rac-barrier3-synthetic-print",
        "version": 1,
        "vendor": "synthetic",
        "source": "assumed",
        "created": "2026-09-10",
        "gamut": {"rgb_min": [0.05, 0.05, 0.05], "rgb_max": [0.95, 0.95, 0.95]},
        "min_feature_mm": 0.5,
        "dpi": 150,
        "mtf_cutoff_cycles_per_mm": 1.0,
        "panel": {"width_mm": 300.0, "height_mm": 300.0, "bleed_mm": 3.0, "safe_area_mm": 10.0},
    }


# ---------------------------------------------------------------------------
# Detector science stage (synthetic detectors through the real adapter)
# ---------------------------------------------------------------------------


def _detector_confidence(detector_id: str, cand_key: str, sample_index: int, params: np.ndarray) -> float:
    """Structured deterministic confidence in (0, 1).

    Each synthetic detector prefers a characteristic luminance; the EOT
    sample perturbs the response. Fully reproducible from the key material.
    """
    preferred = 0.15 + 0.7 * _u01("preferred-luminance", detector_id)
    luminance = float(np.mean(params))
    affinity = 1.0 - abs(luminance - preferred)
    eot_factor = 0.75 + 0.25 * _u01("eot-response", detector_id, cand_key, sample_index)
    confidence = affinity * eot_factor
    if not math.isfinite(confidence):
        raise Barrier3Error(f"non-finite confidence for {detector_id}")
    return float(min(max(confidence, 1e-6), 1.0 - 1e-6))


def run_detector_stage(
    pool: Sequence[Candidate],
    config: Barrier3Config,
    sampler: Sampler,
) -> dict:
    """Per-candidate, per-detector EOT-mean confidence via the real
    SyntheticDetectionAdapter (fabrication guard active)."""
    adapter = SyntheticDetectionAdapter()
    table: dict[str, dict[str, float]] = {}
    for cand in pool:
        cand_key = sha256_text(np.ascontiguousarray(cand.params).tobytes().hex())
        per_detector: dict[str, float] = {}
        for det in SYNTHETIC_DETECTORS:
            confidences = []
            for s in range(config.n_eot_samples):
                sampler.sample(s)  # consume the pinned sample (reproducibility contract)
                conf = _detector_confidence(det["model_id"], cand_key, s, cand.params)
                # Route through the real adapter so the response contract and
                # anti-fabrication guard are exercised on the integrated path.
                response = adapter.adapt(
                    {"boxes": [[0.0, 0.0, 1.0, 1.0]], "scores": [conf], "labels": [1]},
                    model_id=det["model_id"],
                    model_family=det["model_family"],
                    condition_id=f"eot-{s}",
                    decision_threshold=0.5,
                )
                confidences.append(float(response.confidence))
            per_detector[det["model_id"]] = float(np.mean(confidences))
        table[cand.candidate_id] = per_detector
    return table


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------


@dataclass
class StageRecord:
    stage: str
    input_source: str
    input_sha256: str
    configuration: dict
    seed: int
    version: str
    output_sha256: str
    upstream: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "input_source": self.input_source,
            "input_sha256": self.input_sha256,
            "configuration": self.configuration,
            "seed": self.seed,
            "version": self.version,
            "output_sha256": self.output_sha256,
            "upstream": list(self.upstream),
        }


def _write_json(path: Path, payload: Any) -> str:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_text(text)


def _style_features(cand: Candidate, profile: Mapping) -> dict:
    """Deterministic style features from candidate content + profile universe."""
    all_motifs = sorted({m for fam in profile.get("families", {}).values() for m in fam.get("motifs", [])})
    cand_key = sha256_text(np.ascontiguousarray(cand.params).tobytes().hex())
    motifs = [m for m in all_motifs if _u01("motif", cand_key, m) < 0.5]
    arr = cand.params
    gx = np.abs(np.diff(arr.mean(axis=2), axis=1)).mean() if arr.ndim == 3 else 0.0
    products = sorted({p for fam in profile.get("families", {}).values() for p in fam.get("products", [])})
    return {
        "motifs": motifs,
        "product": products[0] if products else "unknown",
        "scale": float(arr.mean() * 100.0),
        "density": float(arr.std() * 100.0),
        "distress": float(gx * 100.0),
    }


def run_barrier3(config: Barrier3Config, out_dir: str | Path) -> dict:
    """Execute the integrated six-stage pipeline and write the artifact set.

    Returns the run manifest dict. Raises Barrier3Error (or the underlying
    stage's own fail-closed error) on any integrity violation.
    """
    out = Path(out_dir)
    stage_dir = out / "stage-artifacts"
    stage_dir.mkdir(parents=True, exist_ok=True)

    stages: list[StageRecord] = []
    artifact_hashes: dict[str, str] = {}

    # --- inputs: configuration + pool (both seed-derived) -------------------
    pool = make_candidate_pool(config)
    pool_pin = sha256_obj(
        {c.candidate_id: sha256_text(np.ascontiguousarray(c.params).tobytes().hex()) for c in pool}
    )
    input_hashes = {
        "config_sha256": config.sha256(),
        "candidate_pool_sha256": pool_pin,
        "frozen_contracts": {
            "optimization_objective": "schemas/optimization_objective.schema.json",
            "transformation_distribution": "schemas/transformation_distribution.schema.json",
            "detector_response": "schemas/detector_response.schema.json",
            "physical_transfer_record": "schemas/physical_transfer_record.schema.json",
        },
        "evidence_boundaries": {
            "held_out_models_accessed": False,
            "d2_0004_evidence_touched": False,
            "d2_0005_armed": False,
        },
    }
    artifact_hashes["input-hashes.json"] = _write_json(out / "input-hashes.json", input_hashes)

    # --- stage 2 spec + stage 1 objective need each other; build both -------
    eot_spec = make_eot_spec(config)
    eot_spec.validate()
    sampler = Sampler(eot_spec)
    objective_spec = make_objective_spec(config)
    profile = make_production_profile(config)
    scorer = StyleFamilyScorer(profile_path=None)

    detector_table = run_detector_stage(pool, config, sampler)

    aggregation = DetectorAggregation(config.aggregation)
    detector_losses = {
        cid: aggregate_detector_scores(
            {k: 1.0 - v for k, v in per_det.items()}, aggregation, config.alpha
        )
        for cid, per_det in detector_table.items()
    }

    params_cand_ids = {
        sha256_text(np.ascontiguousarray(c.params).tobytes().hex()): c.candidate_id for c in pool
    }

    def detector_term(params: np.ndarray) -> tuple[float, dict]:
        key = sha256_text(np.ascontiguousarray(params).tobytes().hex())
        cand_id = params_cand_ids[key]
        return detector_losses[cand_id], {"per_detector": detector_table[cand_id]}

    printability_cache: dict[str, Any] = {}

    def printability_term(params: np.ndarray) -> tuple[float, dict]:
        key = sha256_text(np.ascontiguousarray(params).tobytes().hex())
        cand_id = params_cand_ids[key]
        loss = printability_loss(np.asarray(params, dtype=float), profile)
        printability_cache[cand_id] = loss
        return loss.value, {"partial": loss.partial, "components": list(loss.components)}

    style_cache: dict[str, float] = {}

    def style_term(params: np.ndarray) -> tuple[float, dict]:
        key = sha256_text(np.ascontiguousarray(params).tobytes().hex())
        cand_id = params_cand_ids[key]
        cand = next(c for c in pool if c.candidate_id == cand_id)
        features = _style_features(cand, scorer.profile)
        family, score = scorer.best_family(features)
        style_cache[cand_id] = score
        return 1.0 - score, {"family": family, "style_score": score}

    def reg_term(params: np.ndarray) -> tuple[float, dict]:
        return float(np.mean(np.square(np.asarray(params, dtype=float)))), {}

    objective = Objective(objective_spec)
    objective.register_term("detector_loss", detector_term)
    objective.register_term("printability_loss", printability_term)
    objective.register_term("style_loss", style_term)
    objective.register_term("regularization", reg_term)

    # --- stage 1: Optimization V3 -------------------------------------------
    recorder = TrajectoryRecorder()
    optimizer = CandidatePoolSearchOptimizer(objective, pool, recorder=recorder)
    result = optimizer.optimize()
    stage1_payload = {
        "stage": "optimization_v3",
        "objective_id": objective_spec.objective_id,
        "objective_sha256": sha256_obj(objective_spec.raw),
        "n_evaluations": result.n_evaluations,
        "best_candidate_id": result.best_candidate_id,
        "best_value": result.best_value,
        "per_candidate_total": {c.candidate_id: objective.evaluate(c.params).total for c in pool},
    }
    h = _write_json(stage_dir / "stage1-optimization.json", stage1_payload)
    artifact_hashes["stage-artifacts/stage1-optimization.json"] = h
    stages.append(
        StageRecord(
            stage="optimization_v3",
            input_source="make_candidate_pool(master_seed)",
            input_sha256=pool_pin,
            configuration={"objective": objective_spec.raw, "optimizer": "CandidatePoolSearchOptimizer"},
            seed=objective_spec.seed,
            version=COORDINATOR_VERSION,
            output_sha256=h,
            upstream=["input-hashes.json"],
        )
    )

    # --- stage 2: EOT ---------------------------------------------------------
    samples = [sampler.sample(s) for s in range(config.n_eot_samples)]
    stage2_payload = {
        "stage": "eot",
        "distribution_id": eot_spec.distribution_id,
        "manifest_sha256": eot_spec.manifest_sha256,
        "seed": eot_spec.seed,
        "n_samples": config.n_eot_samples,
        "samples_sha256": sha256_obj(samples),
    }
    h = _write_json(stage_dir / "stage2-eot.json", stage2_payload)
    artifact_hashes["stage-artifacts/stage2-eot.json"] = h
    stages.append(
        StageRecord(
            stage="eot",
            input_source="make_eot_spec(master_seed)",
            input_sha256=eot_spec.manifest_sha256,
            configuration=eot_spec.to_dict()["parameter_manifest"],
            seed=eot_spec.seed,
            version=COORDINATOR_VERSION,
            output_sha256=h,
            upstream=["input-hashes.json"],
        )
    )

    # --- stage 3: Detector Science --------------------------------------------
    stage3_payload = {
        "stage": "detector_science",
        "adapter": SyntheticDetectionAdapter().adapter_ref,
        "detectors": list(SYNTHETIC_DETECTORS),
        "aggregation": config.aggregation,
        "alpha": config.alpha if config.aggregation == "CVAR" else None,
        "per_candidate_detector_confidence": detector_table,
        "detector_loss": detector_losses,
    }
    h = _write_json(stage_dir / "stage3-detector-science.json", stage3_payload)
    artifact_hashes["stage-artifacts/stage3-detector-science.json"] = h
    stages.append(
        StageRecord(
            stage="detector_science",
            input_source="stage1 pool x stage2 eot samples",
            input_sha256=sha256_obj({"pool": pool_pin, "eot": stage2_payload["samples_sha256"]}),
            configuration={"detectors": [d["model_id"] for d in SYNTHETIC_DETECTORS]},
            seed=derive_seed(config.master_seed, "detector"),
            version=SyntheticDetectionAdapter.ADAPTER_VERSION,
            output_sha256=h,
            upstream=["stage-artifacts/stage1-optimization.json", "stage-artifacts/stage2-eot.json"],
        )
    )

    # --- stage 4: Pareto / Style ----------------------------------------------
    metrics_rows = []
    for c in pool:
        cid = c.candidate_id
        transfer = float(np.mean(list(detector_table[cid].values())))
        metrics_rows.append(
            {
                "candidate_id": cid,
                "detector_objective": stage1_payload["per_candidate_total"][cid],
                "transfer": transfer,
                "physical_robustness": 1.0 - printability_cache[cid].value,
                "style": style_cache[cid],
            }
        )
    classified = classify(metrics_rows)
    stage4_payload = {
        "stage": "pareto_style",
        "classifications": [
            {"candidate_id": r.candidate_id, "classification": r.classification.value, "metrics": dict(r.metrics)}
            for r in classified
        ],
    }
    h = _write_json(stage_dir / "stage4-pareto-style.json", stage4_payload)
    artifact_hashes["stage-artifacts/stage4-pareto-style.json"] = h
    stages.append(
        StageRecord(
            stage="pareto_style",
            input_source="stage1 totals + stage3 confidence + style features",
            input_sha256=sha256_obj(metrics_rows),
            configuration={"balance_tol": 0.1, "families": list(FAMILIES)},
            seed=derive_seed(config.master_seed, "pareto"),
            version=COORDINATOR_VERSION,
            output_sha256=h,
            upstream=["stage-artifacts/stage1-optimization.json", "stage-artifacts/stage3-detector-science.json"],
        )
    )

    # --- stage 5: Printability --------------------------------------------------
    stage5_payload = {
        "stage": "printability",
        "profile": {k: v for k, v in profile.items()},
        "per_candidate": {
            cid: {
                "value": printability_cache[cid].value,
                "partial": printability_cache[cid].partial,
                "available_components": printability_cache[cid].available_components,
                "unavailable_components": printability_cache[cid].unavailable_components,
            }
            for cid in [c.candidate_id for c in pool]
        },
    }
    h = _write_json(stage_dir / "stage5-printability.json", stage5_payload)
    artifact_hashes["stage-artifacts/stage5-printability.json"] = h
    stages.append(
        StageRecord(
            stage="printability",
            input_source="candidate artwork arrays",
            input_sha256=pool_pin,
            configuration={"profile_id": profile["profile_id"], "profile_version": profile["version"]},
            seed=derive_seed(config.master_seed, "printability"),
            version=COORDINATOR_VERSION,
            output_sha256=h,
            upstream=["stage-artifacts/stage1-optimization.json"],
        )
    )

    # --- stage 6: Physical Transfer (synthetic record, fail-closed class) -------
    winner = next(c for c in pool if c.candidate_id == result.best_candidate_id)
    artwork_bytes = np.ascontiguousarray(winner.params).tobytes()
    record = emit_transfer_record(
        artwork=artwork_bytes,
        template=canonical_json(profile).encode(),
        mapping=canonical_json({"winner": winner.candidate_id}).encode(),
        captured_frame=artwork_bytes,
        garment_sku="SYNTHETIC-BARRIER3",
        fabric="synthetic",
        print_process="synthetic",
        capture_id="synthetic-capture-b3",
        camera="synthetic",
        lighting="synthetic",
        pose="synthetic",
        view="synthetic",
        synthetic_generator=True,
        record_id=f"ptr-b3-{sha256_text(artwork_bytes.hex())[:16]}",
    )
    if record["evidence_class"] != SYNTHETIC or record["physical_efficacy_claimed"]:
        raise Barrier3Error("physical transfer record violated the synthetic evidence boundary")
    stage6_payload = {"stage": "physical_transfer", "record": record}
    h = _write_json(stage_dir / "stage6-physical-transfer.json", stage6_payload)
    artifact_hashes["stage-artifacts/stage6-physical-transfer.json"] = h
    stages.append(
        StageRecord(
            stage="physical_transfer",
            input_source="stage1 winner artwork (synthetic)",
            input_sha256=record["artwork_sha256"],
            configuration={"synthetic_generator": True, "evidence_class": SYNTHETIC},
            seed=derive_seed(config.master_seed, "physical_transfer"),
            version=record["schema_version"],
            output_sha256=h,
            upstream=["stage-artifacts/stage1-optimization.json", "stage-artifacts/stage5-printability.json"],
        )
    )

    # --- telemetry ---------------------------------------------------------------
    telemetry = {
        "run_id": RUN_ID,
        "objective_id": objective_spec.objective_id,
        "evaluations": [
            {
                "iteration": e.iteration,
                "params_hash": e.params_hash,
                "term_values": dict(e.term_values),
                "total": e.total,
            }
            for e in recorder.steps
        ],
        "detector_loss_dispersion": {
            cid: {
                "min": min(per_det.values()),
                "max": max(per_det.values()),
                "mean": float(np.mean(list(per_det.values()))),
            }
            for cid, per_det in detector_table.items()
        },
        "tail": {
            "aggregation": config.aggregation,
            "alpha": config.alpha if config.aggregation == "CVAR" else None,
            "worst_candidate": max(detector_losses, key=detector_losses.get),
            "best_candidate": min(detector_losses, key=detector_losses.get),
        },
    }
    artifact_hashes["objective-telemetry.json"] = _write_json(out / "objective-telemetry.json", telemetry)

    # --- provenance ----------------------------------------------------------------
    provenance = {
        "run_id": RUN_ID,
        "edges": [
            {"from": u, "to": s.stage, "kind": "stage_input"} for s in stages for u in s.upstream
        ],
        "stages": [s.to_dict() for s in stages],
    }
    artifact_hashes["provenance.json"] = _write_json(out / "provenance.json", provenance)

    # --- runtime environment (excluded from scientific equivalence) ----------------
    runtime = {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "coordinator_version": COORDINATOR_VERSION,
        "note": "non-scientific metadata; excluded from replay equivalence",
    }
    _write_json(out / "runtime-environment.json", runtime)

    # --- run manifest -----------------------------------------------------------------
    manifest = {
        "run_id": RUN_ID,
        "coordinator_version": COORDINATOR_VERSION,
        "config": config.to_dict(),
        "config_sha256": config.sha256(),
        "stages": [s.to_dict() for s in stages],
        "best_candidate_id": result.best_candidate_id,
        "best_value": result.best_value,
        "evidence_class": SYNTHETIC,
        "physical_efficacy_claimed": False,
        "held_out_models_accessed": False,
        "d2_0004_modified": False,
        "d2_0005_armed": False,
        "artifact_hashes": artifact_hashes,
    }
    artifact_hashes["run-manifest.json"] = _write_json(out / "run-manifest.json", manifest)

    # --- hashes.sha256 over everything written so far ----------------------------------
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(out).as_posix()}")
    (out / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return manifest


# ---------------------------------------------------------------------------
# Verification: artifact integrity, provenance, deterministic replay
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_artifact_hashes(out_dir: str | Path) -> list[str]:
    """Recompute every artifact hash; returns list of violations (empty = OK)."""
    out = Path(out_dir)
    violations: list[str] = []
    sums = (out / "hashes.sha256").read_text(encoding="utf-8").splitlines()
    recorded = {}
    for line in sums:
        digest, _, rel = line.partition("  ")
        recorded[rel] = digest
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rel = path.relative_to(out).as_posix()
            if rel not in recorded:
                if rel in OVERLAY_FILES:
                    continue  # verification overlay, derived from pinned artifacts
                violations.append(f"{rel}: not pinned in hashes.sha256")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != recorded[rel]:
                violations.append(f"{rel}: hash mismatch (corrupt or tampered artifact)")
    for rel in recorded:
        if not (out / rel).exists():
            violations.append(f"{rel}: pinned artifact missing")
    manifest = _load_json(out / "run-manifest.json")
    for rel, digest in manifest["artifact_hashes"].items():
        path = out / rel
        if not path.exists():
            violations.append(f"{rel}: manifest-pinned artifact missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            violations.append(f"{rel}: manifest hash mismatch")
    return violations


def verify_provenance(out_dir: str | Path) -> list[str]:
    """Every stage output hash must match its artifact; lineage must be acyclic
    and reference existing artifacts."""
    out = Path(out_dir)
    violations: list[str] = []
    provenance = _load_json(out / "provenance.json")
    stages = {s["stage"]: s for s in provenance["stages"]}
    expected_order = [
        "optimization_v3",
        "eot",
        "detector_science",
        "pareto_style",
        "printability",
        "physical_transfer",
    ]
    if list(stages) != expected_order:
        violations.append(f"stage set/order mismatch: {list(stages)}")
    artifact_by_stage = {
        "optimization_v3": "stage-artifacts/stage1-optimization.json",
        "eot": "stage-artifacts/stage2-eot.json",
        "detector_science": "stage-artifacts/stage3-detector-science.json",
        "pareto_style": "stage-artifacts/stage4-pareto-style.json",
        "printability": "stage-artifacts/stage5-printability.json",
        "physical_transfer": "stage-artifacts/stage6-physical-transfer.json",
    }
    for stage, rel in artifact_by_stage.items():
        path = out / rel
        if not path.exists():
            violations.append(f"{stage}: artifact {rel} missing (silent stage skip)")
            continue
        if sha256_text(path.read_text(encoding="utf-8")) != stages[stage]["output_sha256"]:
            violations.append(f"{stage}: output hash does not match artifact {rel}")
        for up in stages[stage]["upstream"]:
            if not (out / up).exists():
                violations.append(f"{stage}: broken provenance edge to missing {up}")
    return violations


def _equivalence_view(out_dir: Path) -> dict:
    """Scientific-equivalence projection: every pinned file except the
    explicitly excluded non-scientific metadata."""
    view: dict[str, str] = {}
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(out_dir).as_posix()
        if rel in REPLAY_EXCLUDED_FILES or rel in OVERLAY_FILES or rel == "hashes.sha256":
            continue
        view[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return view


def verify_replay(dir_a: str | Path, dir_b: str | Path) -> dict:
    """Compare two runs for deterministic replay.

    Compares input hashes, configuration hashes, seeds, stage outputs,
    objective telemetry, provenance, and artifact hashes. Any unexpected
    deterministic drift is a FAIL; only REPLAY_EXCLUDED_FILES metadata may
    differ.
    """
    a, b = Path(dir_a), Path(dir_b)
    view_a, view_b = _equivalence_view(a), _equivalence_view(b)
    mismatches = [rel for rel in sorted(set(view_a) | set(view_b)) if view_a.get(rel) != view_b.get(rel)]
    manifest_a, manifest_b = _load_json(a / "run-manifest.json"), _load_json(b / "run-manifest.json")
    seeds_a = [s["seed"] for s in manifest_a["stages"]]
    seeds_b = [s["seed"] for s in manifest_b["stages"]]
    report = {
        "replay_equivalent": not mismatches and seeds_a == seeds_b,
        "mismatched_artifacts": mismatches,
        "config_sha256": [manifest_a["config_sha256"], manifest_b["config_sha256"]],
        "stage_seeds_equal": seeds_a == seeds_b,
        "excluded_from_equivalence": list(REPLAY_EXCLUDED_FILES),
        "verdict": "PASS" if not mismatches and seeds_a == seeds_b else "FAIL",
    }
    return report


def write_replay_report(report: dict, out_dir: str | Path) -> None:
    _write_json(Path(out_dir) / "replay-report.json", report)


def write_barrier3_report(out_dir: str | Path) -> dict:
    """Final gate report for one Barrier 3 run directory."""
    out = Path(out_dir)
    hash_violations = verify_artifact_hashes(out)
    prov_violations = verify_provenance(out)
    replay = _load_json(out / "replay-report.json") if (out / "replay-report.json").exists() else None
    manifest = _load_json(out / "run-manifest.json")
    closed = (
        not hash_violations
        and not prov_violations
        and replay is not None
        and replay["replay_equivalent"]
    )
    report = {
        "run_id": manifest["run_id"],
        "artifact_integrity": "PASS" if not hash_violations else "FAIL",
        "artifact_violations": hash_violations,
        "provenance": "PASS" if not prov_violations else "FAIL",
        "provenance_violations": prov_violations,
        "deterministic_replay": (replay or {}).get("verdict", "NOT_EXECUTED"),
        "scientific_boundaries": {
            "d2_0004_modified": manifest["d2_0004_modified"],
            "d2_0005_armed": manifest["d2_0005_armed"],
            "held_out_models_accessed": manifest["held_out_models_accessed"],
            "physical_efficacy_claimed": manifest["physical_efficacy_claimed"],
            "evidence_class": manifest["evidence_class"],
        },
        "barrier3_closed": closed,
    }
    _write_json(out / "barrier3-report.json", report)
    return report

"""Barrier 3 integrated deterministic rehearsal.

Synthetic integration proof for the six-stage future-generation engine:
Optimization V3 -> EOT -> Detector Science -> Pareto/Style -> Printability
-> Physical Transfer.

Governance: this module does NOT arm or execute D2-0005, changes no
preregistered value, never loads or scores the held-out model set, and never
produces physical-efficacy evidence.  Frozen D2-0005 values are REFERENCED
from ``docs/D2-0005_FREEZE_CANDIDATE.json`` (and its pinned seed config),
never restated as new literals, moved, or changed.  Held-out identity/hash
values are used only as immutable references; the held-out model-set file is
never opened.  Every emitted record is synthetic_pipeline_validation_only.

The coordinator is deliberately thin: each stage invokes the existing public
API and emits a canonical, hash-bound record.  Journal/resume semantics mirror
rehearsal_d20005.py and fail closed on changed intermediate bytes.  An
executable acceptance gate (``run_acceptance_gate``) hard-fails unless every
Barrier 3 gate criterion holds.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np

from ruthless_pipeline.detector_science.adapters import SyntheticDetectionAdapter
from ruthless_pipeline.optimization.objective_registry import Objective
from ruthless_pipeline.optimization.optimizer import Candidate, CandidatePoolSearchOptimizer
from ruthless_pipeline.optimization.pareto import pareto_front
from ruthless_pipeline.optimization.schemas import ObjectiveSpec
from ruthless_pipeline.optimization.style import StyleFamilyScorer, StyleOptimizationRecord, style_pareto_curve
from ruthless_pipeline.physical_transfer.printability import printability_loss
from ruthless_pipeline.physical_transfer.production_profiles import (
    ProfileIntegrityError,
    compute_sha256 as profile_content_sha256,
    validate_profile,
    verify_integrity as verify_profile_integrity,
)
from ruthless_pipeline.physical_transfer.transfer_record import emit as emit_transfer_record
from ruthless_pipeline.transformations.distribution import (
    REPRODUCIBILITY_NOTE,
    Sampler,
    TransformationDistributionSpec,
)
from ruthless_pipeline.certification import provenance_graph as pg
from ruthless_pipeline.certification.release_format import ReleaseManifest, verify_release

EVIDENCE_CLASS = "synthetic_pipeline_validation_only"
SCHEMA_VERSION = "1.0"
SCHEMA_ID = "barrier3-run-manifest"
GENERATION_ID = "RAC-PER-D2-0005"
DEFAULT_CREATED_UTC = "2026-01-01T00:00:00Z"
RESULT_LINE = "RESULT: synthetic_pipeline_validation_only — Barrier 3 integration proof; not RAC evidence"
MOCK_DETECTOR_LABEL = "MOCK-DETECTOR-SYNTHETIC-NOT-A-MODEL"

SURROGATE_SET_ID = "PERSON-SUR-v3"
SURROGATE_SET_SHA256 = "2f06c19e9e51f3f607b04b499760ab7f470f4b6e18f9c834013fb0a06a5d8876"
HELDOUT_SET_ID = "PERSON-HO-v3"
HELDOUT_SET_SHA256 = "ad1127659a5615871ff320056415dd3c8e8b6a27acef7c6a3bcc4a96e713495e"
HELDOUT_SET_PATH = "model_sets/PERSON-HO-v3.json"
SURROGATE_SET_PATH = "model_sets/PERSON-SUR-v3.json"

FREEZE_CANDIDATE_PATH = "docs/D2-0005_FREEZE_CANDIDATE.json"
FREEZE_SEEDS_PATH = "ruthless_pipeline/certification/config/d20005_freeze/seeds.json"
RUNTIME_LOCK_PATH = "benchmarks/runtime_lock.json"
DESIGN_PROFILE_PATH = "design_profiles/ruthless_reference_v1.json"
PRODUCTION_PROFILE_ID = "barrier3-production"
PRODUCTION_PROFILE_VERSION = 1
# Pinned versioned production profile, deliberately outside the frozen
# design_profiles/ surface (see docs/BARRIER3_REHEARSAL.md §1).
PRODUCTION_PROFILE_PATH = (
    f"ruthless_pipeline/certification/config/barrier3/"
    f"{PRODUCTION_PROFILE_ID}__v{PRODUCTION_PROFILE_VERSION}.json"
)

STAGES = (
    "optimization",
    "eot",
    "detector_science",
    "pareto_style",
    "printability",
    "physical_transfer",
)

#: Per-stage output directories inside the run package.
STAGE_DIRS = {
    "optimization": "optimization",
    "eot": "eot",
    "detector_science": "detector-science",
    "pareto_style": "pareto",
    "printability": "printability",
    "physical_transfer": "physical-transfer",
}

#: Upstream stage(s) each stage must demonstrably consume.
UPSTREAM = {
    "optimization": (),
    "eot": ("optimization",),
    "detector_science": ("eot",),
    "pareto_style": ("optimization", "detector_science"),
    "printability": ("eot",),
    "physical_transfer": ("eot", "detector_science"),
}

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _REPO_ROOT / "schemas" / "barrier3_run_manifest.schema.json"

HASHES_FILE = "hashes.sha256"
RELEASE_MANIFEST = "MANIFEST.json"
JOURNAL_FILE = "rehearsal_journal.json"
REPORT_FILE = "rehearsal-report.json"


class Barrier3Error(RuntimeError):
    """Base fail-closed Barrier 3 error."""


class RehearsalCrash(Barrier3Error):
    """Deliberately injected crash after a named stage."""


class ResumeIntegrityError(Barrier3Error):
    """A completed stage no longer matches its journaled hash."""


class HeldoutAccessRefusal(Barrier3Error):
    """Barrier 3 refuses any attempt to use held-out material beyond identity/hash."""


class PromotionRefusedError(Barrier3Error):
    """Synthetic Barrier 3 output may never be promoted to measured evidence."""


class AcceptanceGateError(Barrier3Error):
    """One or more Barrier 3 acceptance-gate criteria failed."""


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = _canonical(payload) + b"\n"
    path.write_bytes(blob)
    return _sha256_bytes(blob)


def _label(payload: dict) -> dict:
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload["evidence_class"] = EVIDENCE_CLASS
    payload["rac_evidence_eligible"] = False
    payload["physical_efficacy_claimed"] = False
    return payload


def _stage_seed(run_id: str, root_seed: int, stage_id: str, stable_context: Any) -> int:
    material = "|".join(
        [run_id, str(int(root_seed)), stage_id, _canonical(stable_context).decode("utf-8")]
    )
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def _unit_interval(key: str) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _git_head(repo_root: Path = _REPO_ROOT) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
    ).strip()


def load_run_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


def load_frozen_parameters(repo_root: str | Path = _REPO_ROOT) -> dict:
    """REFERENCE the frozen D2-0005 values from their pinned records.

    Values are read from docs/D2-0005_FREEZE_CANDIDATE.json and its pinned
    freeze-seeds config; they are never restated here as new literals, never
    moved, and never changed.
    """
    repo_root = Path(repo_root)
    freeze = json.loads((repo_root / FREEZE_CANDIDATE_PATH).read_text())
    params = freeze["analysis_implementation"]["parameters"]
    design = freeze["design_point"]
    seeds = json.loads((repo_root / FREEZE_SEEDS_PATH).read_text())["seeds"]
    return {
        "candidate_pool_seed": params["candidate_pool_seed"],
        "bootstrap_seed": params["bootstrap_seed"],
        "design_simulation_seed": seeds["design_simulation_seed"],
        "cvar_alpha": params["cvar_alpha"],
        "z": params["z"],
        "bootstrap_resamples": params["bootstrap_resamples"],
        "width_gate": params["width_gate"],
        "min_clusters": params["min_clusters"],
        "design_min_clusters": design["min_clusters_K"],
        "members_per_cluster": design["members_per_cluster"],
        "icc_gate": design["icc_gate"],
        "confirmatory_floor_delta": design["confirmatory_floor_delta"],
    }


#: Frozen D2-0005 values, referenced from the freeze-candidate records.
FROZEN_PARAMETERS = load_frozen_parameters()


def validate_run_manifest(manifest: dict) -> dict:
    jsonschema.validate(instance=manifest, schema=load_run_schema())
    if manifest["expected_stage_order"] != list(STAGES):
        raise Barrier3Error("stage order differs from frozen Barrier 3 order")
    if manifest["model_identity_refs"]["heldout_access"] != "identity_hash_only":
        raise HeldoutAccessRefusal("held-out access must remain identity_hash_only")
    if manifest["arm_ref"]["heldout_access"] != "identity_hash_only":
        raise HeldoutAccessRefusal("held-out arm access must remain identity_hash_only")
    forbidden = {"heldout_results", "heldout_scores", "measured_evidence", "physical_efficacy"}
    if forbidden.intersection(manifest):
        raise HeldoutAccessRefusal("run manifest contains forbidden outcome/evidence fields")
    referenced = load_frozen_parameters()
    if manifest["frozen_parameters"] != referenced:
        raise Barrier3Error(
            "frozen_parameters differ from the referenced D2-0005 freeze-candidate values"
        )
    return manifest


def _production_profile_pin(repo_root: Path) -> dict:
    path = repo_root / PRODUCTION_PROFILE_PATH
    if not path.is_file():
        raise Barrier3Error(f"pinned production profile is missing: {PRODUCTION_PROFILE_PATH}")
    profile = json.loads(path.read_text())
    validate_profile(profile)
    verify_profile_integrity(profile)
    return {
        "profile_id": profile["profile_id"],
        "version": profile["version"],
        "path": PRODUCTION_PROFILE_PATH,
        "sha256": profile["sha256"],
        "source": profile["source"],
    }


def build_default_manifest(
    *,
    run_id: str = "BARRIER3-D20005-SYNTHETIC-001",
    root_seed: int = 20260909,
    created_utc: str = DEFAULT_CREATED_UTC,
    source_commit: str | None = None,
    repo_root: Path = _REPO_ROOT,
) -> dict:
    """Build a deterministic, synthetic-only manifest from committed inputs."""
    repo_root = Path(repo_root)
    frozen_hash = _sha256_file(repo_root / "benchmarks" / "frozen_surface_sha256.json")
    input_paths = (
        FREEZE_CANDIDATE_PATH,
        FREEZE_SEEDS_PATH,
        RUNTIME_LOCK_PATH,
        DESIGN_PROFILE_PATH,
        PRODUCTION_PROFILE_PATH,
        GENERATION_D20004_PATH,
        GENERATION_D20005_PATH,
    )
    input_hashes = {
        path: _sha256_file(repo_root / path)
        for path in input_paths
        if (repo_root / path).is_file()
    }
    if FREEZE_CANDIDATE_PATH not in input_hashes:
        raise Barrier3Error("required freeze-candidate input is missing")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "schema_id": SCHEMA_ID,
        "run_id": run_id,
        "source_commit": source_commit or _git_head(repo_root),
        "created_utc": created_utc,
        "evidence_class": EVIDENCE_CLASS,
        "rac_evidence_eligible": False,
        "physical_efficacy_claimed": False,
        "generation_ref": GENERATION_ID,
        "arm_ref": {
            "surrogate_arm": "surrogate-selection",
            "heldout_arm": "held-out-confirmation",
            "heldout_access": "identity_hash_only",
        },
        "root_seed": int(root_seed),
        "frozen_surface_manifest_sha256": frozen_hash,
        "frozen_parameters": load_frozen_parameters(repo_root),
        "stage_configs": {
            "optimization": {"pool_size": 8, "objective_id": "barrier3-synthetic-objective"},
            "eot": {"sample_count": 4, "shape": [16, 16, 3]},
            "detector_science": {
                "model_id": "barrier3-synthetic-detector",
                "model_family": "synthetic",
                "decision_threshold": 0.5,
                "mock_label": MOCK_DETECTOR_LABEL,
            },
            "pareto_style": {"family": "signal_shadow"},
            "printability": {"profile_ref": _production_profile_pin(repo_root)},
            "physical_transfer": {
                "garment_sku": "SYNTHETIC-BARRIER3",
                "fabric": "synthetic_fixture",
                "print_process": "synthetic_pipeline_validation_only",
                "camera": "synthetic-camera",
                "lighting": "synthetic-lighting",
                "pose": "synthetic-pose",
                "view": "front",
            },
        },
        "model_identity_refs": {
            "surrogate_set_id": SURROGATE_SET_ID,
            "surrogate_set_sha256": SURROGATE_SET_SHA256,
            "heldout_set_id": HELDOUT_SET_ID,
            "heldout_set_sha256": HELDOUT_SET_SHA256,
            "heldout_access": "identity_hash_only",
        },
        "input_hashes": input_hashes,
        "expected_stage_order": list(STAGES),
    }
    return validate_run_manifest(manifest)


def _verify_committed_inputs(manifest: dict, repo_root: Path) -> None:
    frozen_path = repo_root / "benchmarks" / "frozen_surface_sha256.json"
    if _sha256_file(frozen_path) != manifest["frozen_surface_manifest_sha256"]:
        raise Barrier3Error("frozen-surface manifest hash mismatch")
    for rel, expected in manifest["input_hashes"].items():
        path = repo_root / rel
        if not path.is_file():
            raise Barrier3Error(f"missing pinned input {rel}")
        actual = _sha256_file(path)
        if actual != expected:
            raise Barrier3Error(f"input hash mismatch for {rel}: expected {expected}, got {actual}")


def _optimization_stage(manifest: dict) -> tuple[dict, np.ndarray]:
    cfg = manifest["stage_configs"]["optimization"]
    frozen = manifest["frozen_parameters"]
    seed = _stage_seed(manifest["run_id"], manifest["root_seed"], "optimization", cfg)
    objective_data = {
        "schema_version": "1.0",
        "objective_id": cfg.get("objective_id", "barrier3-synthetic-objective"),
        "terms": {
            "detector_loss": {"aggregation": "CVAR", "alpha": frozen["cvar_alpha"], "log_separately": True},
            "printability_loss": {"lambda_print": 0.2, "log_separately": True},
            "style_loss": {"lambda_style": 0.1, "log_separately": True},
            "deformation_loss": {"lambda_deformation": 0.1, "log_separately": True},
            "regularization": {"lambda_reg": 0.05, "log_separately": True},
        },
        "seed": int(seed % (2**63 - 1)),
        "future_generations_only": True,
    }
    spec = ObjectiveSpec.from_dict(objective_data)
    objective = Objective(spec)
    objective.register_term("detector_loss", lambda p: (float(np.mean(np.square(p - 0.25))), {"synthetic": True}))
    objective.register_term("printability_loss", lambda p: (float(np.mean(np.abs(p - 0.5))), {"synthetic": True}))
    objective.register_term("style_loss", lambda p: (float(abs(float(np.mean(p)) - 0.4)), {"synthetic": True}))
    objective.register_term("deformation_loss", lambda p: (float(np.var(p)), {"synthetic": True}))
    objective.register_term("regularization", lambda p: (float(np.mean(np.square(p))), {"synthetic": True}))
    rng = np.random.default_rng(seed)
    pool_size = int(cfg.get("pool_size", 8))
    pool = [
        Candidate(
            candidate_id=f"barrier3-candidate-{i:03d}",
            params=np.clip(rng.normal(0.5, 0.2, size=3), 0.0, 1.0),
            metadata={"synthetic": True},
        )
        for i in range(pool_size)
    ]
    optimizer = CandidatePoolSearchOptimizer(objective, pool, maximize=False)
    result = optimizer.optimize()
    if not math.isfinite(result.best_value) or result.best_params is None:
        raise Barrier3Error("optimization returned non-finite or missing best result")
    payload = _label({
        "stage": "optimization",
        "stage_seed": seed,
        "objective_spec": objective_data,
        "best_value": result.best_value,
        "best_candidate_id": result.best_candidate_id,
        "best_params": result.best_params.tolist(),
        "n_evaluations": result.n_evaluations,
        "converged": result.converged,
        "certification": None,
    })
    return payload, np.asarray(result.best_params, dtype=float)


def _fixed_distribution_manifest() -> dict:
    fixed = lambda value: {"type": "fixed", "params": {"value": value}}
    return {
        "geometry": {
            "scale": fixed(1.0), "camera_distance": fixed(5.0), "perspective": fixed(0.0),
            "yaw": fixed(0.0), "pitch": fixed(0.0), "roll": fixed(0.0), "translation": fixed(0.0),
        },
        "imaging": {
            "blur": fixed(0.0), "resize_interpolation": fixed("bilinear"),
            "compression": fixed(100), "exposure": fixed(0.0), "contrast": fixed(1.0),
        },
        "garment": {
            "stretch": fixed(0.0), "wrinkle": fixed(0.0), "fold": fixed(0.0),
            "bend": fixed(0.0), "partial_occlusion": fixed(0.0),
        },
        "print_capture": {"gamut_mapping": fixed("identity"), "resolution_loss": fixed(0.0)},
    }


def _eot_stage(manifest: dict, best_params: np.ndarray) -> tuple[dict, np.ndarray]:
    cfg = manifest["stage_configs"]["eot"]
    seed = _stage_seed(manifest["run_id"], manifest["root_seed"], "eot", cfg)
    shape = tuple(int(v) for v in cfg.get("shape", [16, 16, 3]))
    sample_count = int(cfg.get("sample_count", 4))
    spec_data = {
        "schema_version": "1.0",
        "distribution_id": f"{manifest['run_id']}::eot",
        "parameter_manifest": _fixed_distribution_manifest(),
        "seed": int(seed % (2**63 - 1)),
        "sampling_reproducibility_note": REPRODUCIBILITY_NOTE,
        "robustness_surface": {
            "grid_axes": ["geometry.scale", "imaging.blur"],
            "response_metric": "synthetic_detector_confidence",
            "cell_value_type": "vector",
            "scalar_only_permitted": False,
        },
    }
    spec = TransformationDistributionSpec.from_dict(spec_data)
    sampler = Sampler(spec)
    arrays = [sampler.sample_array(i, shape, base=float(np.mean(best_params))) for i in range(sample_count)]
    candidate = arrays[0]
    samples = [
        {
            "sample_index": i,
            "resolved_parameters": sampler.sample(i),
            "array_sha256": _sha256_bytes(np.ascontiguousarray(arr, dtype=np.float64).tobytes()),
            "mean": float(np.mean(arr)),
        }
        for i, arr in enumerate(arrays)
    ]
    payload = _label({
        "stage": "eot",
        "stage_seed": seed,
        "distribution": spec.to_dict(),
        "distribution_manifest_sha256": spec.manifest_sha256,
        "upstream": {"optimization_best_params": [float(v) for v in best_params]},
        "samples": samples,
        "candidate_shape": list(candidate.shape),
        "candidate_pixels": candidate.tolist(),
    })
    return payload, candidate


def _detector_stage(manifest: dict, candidate: np.ndarray, eot: dict) -> dict:
    cfg = manifest["stage_configs"]["detector_science"]
    seed = _stage_seed(manifest["run_id"], manifest["root_seed"], "detector_science", cfg)
    score = float(np.clip(np.mean(candidate) + 0.1 * (_unit_interval(f"detector|{seed}") - 0.5), 0.0, 1.0))
    detection = {"boxes": [[1.0, 1.0, 10.0, 10.0]], "labels": [1], "scores": [score]}
    adapter = SyntheticDetectionAdapter()
    response = adapter.adapt(
        detection,
        model_id=cfg.get("model_id", "barrier3-synthetic-detector"),
        model_family=cfg.get("model_family", "synthetic"),
        condition_id=manifest["run_id"],
        decision_threshold=float(cfg.get("decision_threshold", 0.5)),
        target_label=1,
        raw_provenance_ref=_stage_rel_path("eot"),
    )
    validated = response.validate()
    return _label({
        "stage": "detector_science",
        "stage_seed": seed,
        "mock_detector_label": MOCK_DETECTOR_LABEL,
        "upstream": {
            "eot_artifact": _stage_rel_path("eot"),
            "eot_candidate_sha256": eot["samples"][0]["array_sha256"],
        },
        "response": validated,
    })


def _pareto_style_stage(manifest: dict, optimization: dict, detector: dict, candidate: np.ndarray) -> dict:
    cfg = manifest["stage_configs"]["pareto_style"]
    seed = _stage_seed(manifest["run_id"], manifest["root_seed"], "pareto_style", cfg)
    scorer = StyleFamilyScorer()
    family = cfg.get("family", "signal_shadow")
    base_features = {
        "motifs": [],
        "product": "tshirt",
        "scale": float(np.mean(candidate) * 100.0),
        "density": float(np.std(candidate) * 100.0),
        "distress": float(np.var(candidate) * 100.0),
    }
    style_score = scorer.score(family, base_features)
    detector_objective = float(detector["response"]["confidence"])
    records = []
    vectors = []
    for i in range(3):
        det = float(np.clip(detector_objective + (i - 1) * 0.03, 0.0, 1.0))
        style = float(np.clip(style_score + (1 - i) * 0.02, 0.0, 1.0))
        rec = StyleOptimizationRecord(
            candidate_id=f"{optimization['best_candidate_id']}-variant-{i}",
            family=family,
            initial_style_score=style_score,
            final_style_score=style,
            initial_detector_objective=detector_objective,
            final_detector_objective=det,
            initial_printability=0.0,
            final_printability=float(i) * 0.01,
            optimization_path=[{"synthetic": True, "index": i}],
        )
        records.append(rec)
        vectors.append([det, style])
    points = np.asarray(vectors, dtype=float)
    front = pareto_front(points, senses=("min", "max"))
    style_front, style_points = style_pareto_curve(records)
    return _label({
        "stage": "pareto_style",
        "stage_seed": seed,
        "family": family,
        "style_metric_scope": "art_direction_proxy_only_not_efficacy",
        "upstream": {
            "optimization_best_candidate_id": optimization["best_candidate_id"],
            "detector_confidence": detector_objective,
        },
        "pareto_front_indices": [int(v) for v in front.tolist()],
        "style_pareto_front_indices": [int(v) for v in style_front.tolist()],
        "points": style_points.tolist(),
        "records": [asdict(r) for r in records],
        "certification": None,
    })


def _load_pinned_production_profile(manifest: dict, repo_root: Path) -> dict:
    ref = manifest["stage_configs"]["printability"]["profile_ref"]
    path = repo_root / ref["path"]
    if not path.is_file():
        raise Barrier3Error(f"pinned production profile is missing: {ref['path']}")
    profile = json.loads(path.read_text())
    validate_profile(profile)
    verify_profile_integrity(profile)
    if profile["profile_id"] != ref["profile_id"] or profile["version"] != ref["version"]:
        raise Barrier3Error("production profile id/version differs from the manifest pin")
    if profile_content_sha256(profile) != ref["sha256"]:
        raise ProfileIntegrityError("production profile content differs from the manifest pin")
    return profile


def _printability_stage(manifest: dict, candidate: np.ndarray, repo_root: Path) -> dict:
    cfg = manifest["stage_configs"]["printability"]
    seed = _stage_seed(manifest["run_id"], manifest["root_seed"], "printability", cfg)
    profile = _load_pinned_production_profile(manifest, repo_root)
    loss = printability_loss(candidate, profile)
    components = {
        name: {
            "value": comp.value,
            "status": comp.status,
            "detail": comp.detail,
        }
        for name, comp in sorted(loss.components.items())
    }
    return _label({
        "stage": "printability",
        "stage_seed": seed,
        "profile_ref": dict(cfg["profile_ref"]),
        "value": loss.value,
        "partial": loss.partial,
        "available_components": loss.available_components,
        "unavailable_components": loss.unavailable_components,
        "components": components,
    })


def _physical_transfer_stage(manifest: dict, eot: dict, detector: dict) -> dict:
    cfg = manifest["stage_configs"]["physical_transfer"]
    seed = _stage_seed(manifest["run_id"], manifest["root_seed"], "physical_transfer", cfg)
    artwork = _canonical({"candidate_pixels": eot["candidate_pixels"]})
    template = _canonical({"template": "synthetic-barrier3-template", "seed": seed})
    mapping = _canonical({"mapping": "synthetic-barrier3-mapping", "run_id": manifest["run_id"]})
    captured_frame = _canonical({"eot_sample_sha256": eot["samples"][0]["array_sha256"]})
    detector_ref = _sha256_bytes(_canonical(detector["response"]))
    record = emit_transfer_record(
        artwork=artwork,
        template=template,
        mapping=mapping,
        captured_frame=captured_frame,
        garment_sku=cfg["garment_sku"],
        fabric=cfg["fabric"],
        print_process=cfg["print_process"],
        capture_id=f"{manifest['run_id']}::capture",
        camera=cfg["camera"],
        lighting=cfg["lighting"],
        pose=cfg["pose"],
        view=cfg["view"],
        detector_response_refs=[detector_ref],
        synthetic_generator=True,
        record_id=f"ptr-{_sha256_bytes((manifest['run_id'] + '|physical_transfer').encode())[:24]}",
    )
    if record["evidence_class"] != EVIDENCE_CLASS or record["physical_efficacy_claimed"] is not False:
        raise PromotionRefusedError("physical-transfer stage attempted evidence promotion")
    return _label({
        "stage": "physical_transfer",
        "stage_seed": seed,
        "upstream": {
            "eot_sample_sha256": eot["samples"][0]["array_sha256"],
            "detector_response_sha256": detector_ref,
        },
        "record": record,
    })


GENERATION_D20004_PATH = "generations/RAC-PER-D2-0004.json"
GENERATION_D20005_PATH = "generations/RAC-PER-D2-0005.json"


def _stage_rel_path(stage: str) -> str:
    return f"stages/{stage}.json"


def _load_journal(path: Path, manifest_hash: str) -> dict:
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "schema_id": "barrier3-rehearsal-journal",
            "manifest_sha256": manifest_hash,
            "stage_order": list(STAGES),
            "completed": {},
        }
    journal = json.loads(path.read_text())
    if journal.get("manifest_sha256") != manifest_hash:
        raise ResumeIntegrityError("journal belongs to a different run manifest")
    if journal.get("stage_order") != list(STAGES):
        raise ResumeIntegrityError("journal stage order differs from Barrier 3 order")
    unknown = set(journal.get("completed", {})) - set(STAGES)
    if unknown:
        raise ResumeIntegrityError(f"journal records unknown stages: {sorted(unknown)}")
    return journal


def _resume_check(output_dir: Path, journal: dict, stage: str) -> dict | None:
    entry = journal["completed"].get(stage)
    if entry is None:
        return None
    path = output_dir / entry["path"]
    if not path.is_file():
        raise ResumeIntegrityError(f"completed stage {stage} artifact is missing")
    if _sha256_file(path) != entry["sha256"]:
        raise ResumeIntegrityError(f"completed stage {stage} artifact hash mismatch")
    payload = json.loads(path.read_text())
    if payload.get("stage") != stage:
        raise ResumeIntegrityError(
            f"journaled artifact for stage {stage} carries payload stage "
            f"{payload.get('stage')!r}"
        )
    return payload


def _ensure_finite(value: Any, path: str = "payload") -> None:
    """Fail closed if a stage boundary contains NaN/Inf."""
    if isinstance(value, float) and not math.isfinite(value):
        raise Barrier3Error(f"non-finite value at {path}: {value!r}")
    if isinstance(value, dict):
        for key, child in value.items():
            _ensure_finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _ensure_finite(child, f"{path}[{index}]")


def _complete(output_dir: Path, journal_path: Path, journal: dict, stage: str, payload: dict) -> dict:
    _ensure_finite(payload, stage)
    path = output_dir / _stage_rel_path(stage)
    digest = _write_json(path, payload)
    journal["completed"][stage] = {"path": path.relative_to(output_dir).as_posix(), "sha256": digest}
    _write_json(journal_path, journal)
    return payload

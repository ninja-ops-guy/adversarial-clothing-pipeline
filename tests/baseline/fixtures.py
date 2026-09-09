"""Deterministic synthetic fixtures for the baseline preservation tests.

These fixtures characterize the CURRENT baseline selection chain —

    Product Studio candidate pool (schema 3.0 contract)
      -> surrogate scoring (ComparativeBenchmark over the transform sweep)
      -> two-stage selection: mean arm and CVaR arm
      (scripts/select_surrogate_candidate.py)

— on fully synthetic, hash-seeded inputs. No real detector weights, no
held-out models, no measured evidence are involved: surrogate "scores" are
SHA-256-derived pseudo-random numbers, and candidate artwork is a
hash-seeded synthetic texture.

Everything in this module is a pure function of ``FIXTURE_SEED`` and the
module source, so the reference manifest in
``artifacts/baseline/reference_manifest.json`` pins
``(generator code sha256, seed, output sha256s)``. To regenerate the
reference after an *intentional* baseline change, run::

    PYTHONPATH=. python tests/baseline/generate_reference.py --regenerate

Boundary: synthetic fixtures never promote to measured evidence; nothing
here touches D2-0004/D2-0005 selection rules or held-out sets.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_VERSION = "baseline-fixture-v1"
FIXTURE_SEED = 20260207

IMAGE_SIZE = 32
BASELINE_SCORE_FLOOR = 0.5  # evaluator outputs in [0.5, 1.0): baseline always qualifies
THRESHOLD = 0.75

SURROGATE_IDS = ("sur-alpha", "sur-beta", "sur-gamma")
CANDIDATE_IDS = ("cand-001", "cand-002", "cand-003", "cand-004")

# Sweeps restricted to exact, bitwise-deterministic ops (scalar brightness
# multiplies only: scale/blur/rotation identity) so the pinned hashes are
# platform-stable characterizations of the selection logic.
NOMINAL_SWEEP = {"brightness": [1.0], "scale": [1.0], "blur_sigma": [0.0], "rotation_deg": [0.0]}
FULL_SWEEP = {
    "brightness": [0.8, 1.0, 1.2],
    "scale": [1.0],
    "blur_sigma": [0.0],
    "rotation_deg": [0.0],
}

DESIGN_PROFILE = {
    "schema_version": "fixture",
    "profile_id": "baseline-preservation-fixture",
    "evidence_boundary": "synthetic fixture only; not detector or physical evidence",
    "families": {"fixture_family": {"variants": [{"name": "v1"}]}},
}


def _u01(*parts: str) -> float:
    """Deterministic uniform in [0, 1) from SHA-256 of the joined parts."""
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def candidate_array(candidate_id: str) -> np.ndarray:
    """Hash-seeded synthetic RGB texture (H, W, 3) uint8."""
    rng = np.random.default_rng(
        int.from_bytes(
            hashlib.sha256(f"{FIXTURE_VERSION}:{FIXTURE_SEED}:{candidate_id}".encode()).digest()[:8],
            "big",
        )
    )
    return rng.integers(0, 256, size=(IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)


def candidate_png_bytes(candidate_id: str) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(candidate_array(candidate_id)).save(buf, format="PNG")
    return buf.getvalue()


def design_profile_bytes() -> bytes:
    return (json.dumps(DESIGN_PROFILE, indent=2, sort_keys=True) + "\n").encode("utf-8")


def design_profile_sha256() -> str:
    return hashlib.sha256(design_profile_bytes()).hexdigest()


def build_manifest() -> dict:
    """Synthetic surrogate-only manifest (no held-out models, ever)."""
    return {
        "threshold": THRESHOLD,
        "min_baseline_score": BASELINE_SCORE_FLOOR,
        "models": [
            {
                "id": model_id,
                "role": "surrogate",
                "display_name": f"hash-seeded mock {model_id}",
                "framework": "fixture",
                "model_ref": "fixture://hash-seeded",
                "person_class": 1,
                "decision_threshold": THRESHOLD,
            }
            for model_id in SURROGATE_IDS
        ],
        "transform_sweep": FULL_SWEEP,
        "selection_sweep": FULL_SWEEP,
    }


def build_pool() -> dict:
    """Schema-3.0 candidate pool honouring the Product Studio contract."""
    candidates = []
    for candidate_id in CANDIDATE_IDS:
        candidates.append(
            {
                "candidate_id": candidate_id,
                "png": f"{candidate_id}.png",
                # deterministic synthetic proxies, hash-derived
                "printability_proxy": round(_u01(FIXTURE_VERSION, candidate_id, "print"), 6),
                "art_direction_proxy": round(_u01(FIXTURE_VERSION, candidate_id, "art"), 6),
                "reference_fidelity_score": round(_u01(FIXTURE_VERSION, candidate_id, "fidelity"), 6),
                "reference_fidelity_subscores": None,
            }
        )
    return {
        "schema_version": "3.0",
        "heldout_feedback_allowed": False,
        "selection_boundary": "SURROGATE_ONLY",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "design_profile": DESIGN_PROFILE["profile_id"],
        "design_profile_sha256": design_profile_sha256(),
        "selection_order": ["candidate_detection_rate", "candidate_mean", "reference_fidelity"],
    }


def write_pool_dir(pool_dir: Path) -> tuple[Path, Path]:
    """Write pool.json (+ PNGs + design profile bytes) and the manifest."""
    pool_dir.mkdir(parents=True, exist_ok=True)
    for candidate_id in CANDIDATE_IDS:
        (pool_dir / f"{candidate_id}.png").write_bytes(candidate_png_bytes(candidate_id))
    pool_path = pool_dir / "pool.json"
    pool_path.write_text(json.dumps(build_pool(), indent=2, sort_keys=True) + "\n")
    manifest_path = pool_dir / "model_manifest.json"
    manifest_path.write_text(json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n")
    return pool_path, manifest_path


class HashSeededEvaluator:
    """Deterministic mock surrogate: score = SHA-256(model, image bytes).

    Outputs per-image scores in [0.5, 1.0) so the synthetic baseline always
    qualifies; detection at THRESHOLD = 0.75 varies per (model, image).
    """

    def __init__(self, name: str):
        self.name = name

    def score(self, images: torch.Tensor) -> torch.Tensor:
        flat = images.detach().cpu().reshape(images.shape[0], -1)
        scores = []
        for row in flat:
            u = _u01(FIXTURE_VERSION, self.name, row.numpy().tobytes().hex())
            scores.append(BASELINE_SCORE_FLOOR + (1.0 - BASELINE_SCORE_FLOOR) * u)
        return torch.tensor(scores, dtype=torch.float32)


def make_mock_evaluators():
    return [HashSeededEvaluator(name) for name in SURROGATE_IDS]


def fake_prepare_fixture(pattern_path, manifest, runtime_dir):
    """Stand-in for run_measured_benchmark.prepare_fixture (no real imaging)."""
    array = np.asarray(Image.open(pattern_path).convert("RGB"), dtype=np.float32) / 255.0
    candidate = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
    baseline = torch.full((1, 3, IMAGE_SIZE, IMAGE_SIZE), 0.5)
    return baseline, candidate, {}


def run_selection(
    pool_dir: Path,
    output_dir: Path,
    *,
    objective: str,
    cvar_alpha: float = 0.5,
    telemetry_path: Path | None = None,
) -> dict:
    """Run the baseline two-stage selection chain with mock surrogates.

    Returns the written ``surrogate-selection.json`` report. Only
    ``build_evaluators`` / ``prepare_fixture`` are substituted (hash-seeded
    mocks); all selection, scoring, and objective logic is the pipeline's
    own code — that is exactly what is being characterized.
    """
    import scripts.select_surrogate_candidate as ssc

    orig_build, orig_prepare = ssc.build_evaluators, ssc.prepare_fixture
    ssc.build_evaluators = lambda manifest, roles=None: (make_mock_evaluators(), {}, {})
    ssc.prepare_fixture = fake_prepare_fixture

    pool_path, manifest_path = write_pool_dir(pool_dir)
    argv = [
        "select_surrogate_candidate.py",
        "--manifest",
        str(manifest_path),
        "--pool",
        str(pool_path),
        "--output-dir",
        str(output_dir),
        "--objective",
        objective,
        "--cvar-alpha",
        str(cvar_alpha),
        "--final-id",
        "FIXTURE-BASELINE-REFERENCE",
    ]
    if telemetry_path is not None:
        argv += ["--objective-telemetry", str(telemetry_path)]
    old_argv = sys.argv
    try:
        sys.argv = argv
        rc = ssc.main()
    finally:
        sys.argv = old_argv
        ssc.build_evaluators, ssc.prepare_fixture = orig_build, orig_prepare
    if rc != 0:
        raise RuntimeError(f"selection exited with {rc}")
    return json.loads((output_dir / "surrogate-selection.json").read_text())


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


VOLATILE_KEYS = {"pattern_path"}


def _strip_volatile(node):
    """Remove run-directory-dependent fields so pinned hashes are portable."""
    if isinstance(node, dict):
        return {
            key: _strip_volatile(value)
            for key, value in node.items()
            if key not in VOLATILE_KEYS
        }
    if isinstance(node, list):
        return [_strip_volatile(value) for value in node]
    return node


def report_sha256(path: Path) -> str:
    """Canonical SHA-256 of a JSON report with volatile paths stripped."""
    from ruthless_pipeline.certification.numerical_verification import canonical_sha256

    return canonical_sha256(_strip_volatile(json.loads(path.read_text())))


def generator_code_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def crafted_stage_b() -> list[dict]:
    """Fixed, analytically solvable stage-B records (mean/CVaR arms diverge)."""
    sur = tuple(f"sur-{i}" for i in range(6))
    def record(candidate_id: str, rates: dict[str, float]) -> dict:
        return {
            "candidate_id": candidate_id,
            "candidate_detection_rate": 0.5,
            "candidate_mean": 0.5,
            "reference_fidelity_score": 0.0,
            "printability_proxy": 0.0,
            "art_direction_proxy": 0.0,
            "per_surrogate_detection_rates": rates,
        }
    return [
        record("cand-a", {**{m: 0.2 for m in sur[:5]}, sur[5]: 0.9}),
        record("cand-b", {m: 0.4 for m in sur}),
    ]


def crafted_telemetry() -> dict:
    """The baseline's objective telemetry over the crafted stage-B records."""
    import scripts.select_surrogate_candidate as ssc

    return ssc.build_objective_telemetry(
        crafted_stage_b(), objective=ssc.ObjectiveSpec(name="cvar", alpha=0.5), alpha=0.5
    )


def collect_reference_payload(work_dir: Path) -> dict:
    """Run the full synthetic chain (mean + CVaR arms) and collect the
    canonical output digests that the reference manifest pins."""
    work_dir.mkdir(parents=True, exist_ok=True)
    pool_dir = work_dir / "pool"
    entries: dict[str, str] = {}

    pool_path, manifest_path = write_pool_dir(pool_dir)
    entries["pool_json_sha256"] = file_sha256(pool_path)
    entries["model_manifest_json_sha256"] = file_sha256(manifest_path)
    entries["design_profile_sha256"] = design_profile_sha256()
    for candidate_id in CANDIDATE_IDS:
        entries[f"png_sha256:{candidate_id}"] = file_sha256(pool_dir / f"{candidate_id}.png")

    mean_dir = work_dir / "run-mean"
    mean_report = run_selection(pool_dir, mean_dir, objective="mean")
    entries["mean.selection_report_sha256"] = report_sha256(mean_dir / "surrogate-selection.json")
    entries["mean.candidate_config_sha256"] = file_sha256(mean_dir / "candidate-config.json")
    entries["mean.winner_candidate_id"] = mean_report["winner"]["candidate_id"]

    cvar_dir = work_dir / "run-cvar"
    cvar_report = run_selection(
        pool_dir, cvar_dir, objective="cvar", cvar_alpha=0.5, telemetry_path=cvar_dir / "telemetry.json"
    )
    entries["cvar.selection_report_sha256"] = report_sha256(cvar_dir / "surrogate-selection.json")
    entries["cvar.candidate_config_sha256"] = file_sha256(cvar_dir / "candidate-config.json")
    entries["cvar.winner_candidate_id"] = cvar_report["winner"]["candidate_id"]
    entries["cvar.objective_telemetry_sha256"] = report_sha256(cvar_dir / "telemetry.json")

    from ruthless_pipeline.certification.numerical_verification import canonical_sha256

    entries["crafted_telemetry_sha256"] = canonical_sha256(crafted_telemetry())

    return {
        "schema_version": "1.0",
        "fixture_version": FIXTURE_VERSION,
        "seed": FIXTURE_SEED,
        "generator": {
            "path": "tests/baseline/fixtures.py",
            "sha256": generator_code_sha256(),
        },
        "chain": (
            "Product Studio candidate pool (schema 3.0) -> surrogate scoring "
            "(ComparativeBenchmark) -> two-stage selection (mean arm, CVaR_0.5 arm) "
            "via scripts/select_surrogate_candidate.py with hash-seeded mock surrogates"
        ),
        "boundary": (
            "synthetic hash-seeded fixtures only; no real detector weights, no "
            "held-out models, no measured evidence; nothing here promotes to measured"
        ),
        "entries": entries,
    }

"""Tests for scripts/ingest_closed_generation.py.

All fixtures are SYNTHETIC, built to mimic the real D2-0004 benchmark artifact
shapes (surrogate-selection.json, candidate-config.json, candidate.png,
benchmark-results.json, generation JSON) as produced by
scripts/select_surrogate_candidate.py and scripts/run_measured_benchmark.py.
No real generation file or run artifact is touched.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.experiment import (  # noqa: E402
    ExperimentArtifact,
    ExperimentRegistry,
)
from ruthless_pipeline.certification.release_format import (  # noqa: E402
    ReleaseManifest,
    compute_content_hash,
    verify_release,
)
from ruthless_pipeline.certification.telemetry_contract import (  # noqa: E402
    TelemetryRecord,
    cross_model_disagreement,
)

from scripts import ingest_closed_generation as icg  # noqa: E402

UTC = "2025-02-01T00:00:00Z"

SURROGATE_RATES = {"yolov8n": 0.25, "fasterrcnn_mobilenet_v3_320": 0.35}
HELDOUT_RATES = {"fasterrcnn_resnet50_fpn_v2": 0.10, "maskrcnn_resnet50_fpn_v2": 0.20}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _model_entry(role: str, rate: float) -> dict:
    return {
        "display_name": role,
        "framework": "torchvision",
        "model_ref": "synthetic",
        "framework_version": "0.0.0",
        "role": role,
        "decision_threshold": 0.5,
        "state_dict_sha256": "ab" * 32,
        "preregistered_hash_match": True,
        "n": 4,
        "baseline_mean_confidence": 0.9,
        "candidate_mean_confidence": 0.4,
        "baseline_detection_rate": 1.0,
        "candidate_detection_rate": rate,
        "absolute_detection_reduction": 1.0 - rate,
        "relative_detection_suppression": 1.0 - rate,
        "relative_confidence_reduction": 0.5,
    }


def _rows() -> list[dict]:
    rows = []
    for model, rate in SURROGATE_RATES.items():
        for brightness in (0.8, 1.0):
            for scale in (0.75, 1.0):
                rows.append({
                    "model": model,
                    "split": "surrogate",
                    "brightness": brightness,
                    "scale": scale,
                    "blur_sigma": 0.0,
                    "rotation_deg": 0.0,
                    "threshold": 0.5,
                    "baseline_score": 0.9,
                    "candidate_score": rate,
                    "delta": rate - 0.9,
                    "baseline_qualified": 1.0,
                    "baseline_detected": 1.0,
                    "candidate_detected": min(1.0, rate + (brightness - 1.0) + (scale - 1.0)),
                })
    for model, rate in HELDOUT_RATES.items():
        rows.append({
            "model": model,
            "split": "heldout",
            "brightness": 1.0,
            "scale": 1.0,
            "blur_sigma": 0.0,
            "rotation_deg": 0.0,
            "threshold": 0.5,
            "baseline_score": 0.95,
            "candidate_score": rate,
            "delta": rate - 0.95,
            "baseline_qualified": 1.0,
            "baseline_detected": 1.0,
            "candidate_detected": rate,
        })
    return rows


def _telemetry_block() -> dict:
    return {
        "per_surrogate_detection_rates": dict(SURROGATE_RATES),
        "transformation_sweep_variance": 0.01,
        "spectral_band_energy": {"low": 0.4, "mid": 0.5, "high": 0.1},
        "pattern_fidelity": 0.82,
        "printability": 0.91,
        "objective_trajectory": {"initial": 0.9, "final": 0.3, "best": 0.28, "evaluations": 42},
        "coverage_metrics": {"coverage_entropy": 0.74},
        "optimizer_config": {
            "optimizer_id": "two-stage-surrogate-selection",
            "seed": 1337,
            "max_evaluations": 100,
            "hyperparameters": {"top_k": 6},
        },
    }


def make_run(tmp_path: Path, *, heldout_rates=None, status: str = "measured_locked",
             strict: bool = True, baseline_rate: float = 1.0) -> dict:
    """Build a synthetic benchmark run dir + generation JSON. Returns paths."""
    run_dir = tmp_path / "runtime"
    run_dir.mkdir(parents=True, exist_ok=True)

    png_bytes = b"synthetic-candidate-png-" + str(tmp_path).encode()
    (run_dir / "candidate.png").write_bytes(png_bytes)
    candidate_sha = _sha(png_bytes)

    _write_json(run_dir / "candidate-config.json", {
        "schema_version": "3.0",
        "candidate_id": "RAC-PER-D2-9999",
        "source_candidate_id": "pool-0042",
        "source": "two-stage surrogate-only Product Studio candidate selection",
        "selection_boundary": "SURROGATE_ONLY",
        "design_profile_sha256": "cd" * 32,
        "printability_proxy": 0.91,
        "reference_fidelity_score": 0.82,
    })

    selection = {
        "schema_version": "3.0",
        "selection_boundary": "SURROGATE_ONLY",
        "surrogate_models": list(SURROGATE_RATES),
        "heldout_models_loaded": [],
        "heldout_feedback_used": False,
        "winner": {
            "candidate_id": "pool-0042",
            "pattern_sha256": candidate_sha,
            "baseline_detection_rate": baseline_rate,
            "candidate_detection_rate": 0.30,
            "candidate_mean": 0.28,
            "invalid_condition_fraction": 0.0,
            "printability_proxy": 0.91,
            "art_direction_proxy": 0.7,
            "reference_fidelity_score": 0.82,
        },
        "stage_a": [],
        "stage_b": [],
    }
    if strict:
        selection["optimization_telemetry"] = _telemetry_block()
    _write_json(run_dir / "surrogate-selection.json", selection)

    models = {m: _model_entry("surrogate", r) for m, r in SURROGATE_RATES.items()}
    models.update({m: _model_entry("heldout", r) for m, r in (heldout_rates or HELDOUT_RATES).items()})
    _write_json(tmp_path / "benchmark-results.json", {
        "schema_version": "1.0",
        "experiment_id": "RAC-PER-D2-9999:synthetic",
        "status": status,
        "certification_eligible": status == "measured_locked",
        "lock_failures": [],
        "generated_at": UTC,
        "candidate": {"config": {}, "sha256": candidate_sha, "source": "synthetic"},
        "benchmark": {"surrogate_models": list(SURROGATE_RATES),
                      "heldout_models": list(heldout_rates or HELDOUT_RATES)},
        "models": models,
        "rows": _rows(),
    })

    _write_json(tmp_path / "generation.json", {
        "schema_version": "1.0",
        "generation_id": "RAC-PER-D2-9999",
        "status": "CLOSED",
        "heldout_feedback_allowed": False,
        "lock_status": "PREREGISTERED",
        "lock_inference_performed": True,
    })
    return {
        "run_dir": run_dir,
        "measured": tmp_path / "benchmark-results.json",
        "generation": tmp_path / "generation.json",
        "candidate_sha": candidate_sha,
    }


def make_args(tmp_path: Path, fixtures: dict, *, experiment_id: str = "RAC-EXP-2025-001",
              legacy: bool = False, extra: list[str] | None = None) -> list[str]:
    argv = [
        "--run-dir", str(fixtures["run_dir"]),
        "--measured-result", str(fixtures["measured"]),
        "--generation", str(fixtures["generation"]),
        "--experiment-id", experiment_id,
        "--hypothesis-id", "HYP-SYNTH-001",
        "--run-id", "synthetic-run-0001",
        "--registry", str(tmp_path / "registry.json"),
        "--release-root", str(tmp_path / "releases"),
        "--timestamp", UTC,
        "--source-commit", "ab" * 20,
    ]
    if legacy:
        argv.append("--legacy-d20004")
    if extra:
        argv += extra
    return argv


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_happy_path_release_constructs_and_verifies(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path)
    assert icg.main(make_args(tmp_path, fixtures)) == 0

    release = tmp_path / "releases" / "RAC-EXP-2025-001"
    assert verify_release(release).ok

    artifact = ExperimentArtifact.from_dict(json.loads((release / "experiment.json").read_text()))
    assert artifact.experiment_id == "RAC-EXP-2025-001"
    assert [s.stage for s in artifact.stages] == ["candidate", "generation", "optimization_telemetry"]

    # optimization_telemetry StageRef sha256 is the telemetry frozen hash and
    # equals the file hash of the sealed canonical pre-held-out bytes.
    tele_ref = next(s for s in artifact.stages if s.stage == "optimization_telemetry")
    pre_bytes = (release / "stages" / "optimization_telemetry" / "pre-held-out.json").read_bytes()
    assert _sha(pre_bytes) == tele_ref.sha256
    record = TelemetryRecord.from_json(
        (release / "stages" / "optimization_telemetry" / "telemetry.json").read_text()
    )
    assert record.frozen_sha256() == tele_ref.sha256
    assert record.outcome is not None and record.outcome.verdict == "PASS"
    assert record.pre.cross_model_disagreement == cross_model_disagreement(
        record.pre.per_surrogate_detection_rates
    )

    # RELEASE.json content_hash recomputes over the manifest it was sealed against.
    release_meta = json.loads((release / "RELEASE.json").read_text())
    assert release_meta["release_id"] == "RAC-EXP-2025-001"
    assert len(release_meta["content_hash"]) == 64
    assert not (release / "FAILURE.json").exists()
    assert (release / "REPORT.md").read_text().startswith("# RAC-EXP-2025-001")
    log = json.loads((release / "REVISIONS.json").read_text())
    assert any(e["action"] == "freeze" for e in log["revisions"])


def test_content_hash_is_tamper_evident(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path)
    assert icg.main(make_args(tmp_path, fixtures)) == 0
    release = tmp_path / "releases" / "RAC-EXP-2025-001"
    report = release / "REPORT.md"
    report.write_text(report.read_text() + "hand edit\n")
    result = verify_release(release)
    assert not result.ok
    assert "REPORT.md" in result.tampered


# ---------------------------------------------------------------------------
# FAIL verdict -> FAILURE.json + taxonomy
# ---------------------------------------------------------------------------

def test_fail_verdict_writes_failure_json_with_taxonomy(tmp_path: Path) -> None:
    # Surrogate suppressed (0.30 vs baseline 1.0) but held-out stayed high,
    # cross-architecture -> cross_architecture_transfer_failure.
    high_heldout = {"fasterrcnn_resnet50_fpn_v2": 0.95, "maskrcnn_resnet50_fpn_v2": 0.90}
    fixtures = make_run(tmp_path, heldout_rates=high_heldout)
    assert icg.main(make_args(tmp_path, fixtures)) == 0

    release = tmp_path / "releases" / "RAC-EXP-2025-001"
    failure = json.loads((release / "FAILURE.json").read_text())
    assert failure["failure_stage"] == "generation"
    assert failure["invalidates"] == list(icg.FAIL_INVALIDATES)
    assert failure["classification"]["category"] == "cross_architecture_transfer_failure"
    assert failure["classification"]["confidence"] in {"high", "medium"}
    assert verify_release(release).ok
    record = TelemetryRecord.from_json(
        (release / "stages" / "optimization_telemetry" / "telemetry.json").read_text()
    )
    assert record.outcome.verdict == "FAIL"


def test_unlocked_measured_status_forces_fail(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path, status="measured_unlocked")
    assert icg.main(make_args(tmp_path, fixtures)) == 0
    release = tmp_path / "releases" / "RAC-EXP-2025-001"
    assert (release / "FAILURE.json").exists()


# ---------------------------------------------------------------------------
# Legacy D2-0004 mode
# ---------------------------------------------------------------------------

def test_legacy_mode_records_absent_fields_as_null(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path, strict=False)  # no optimization_telemetry block
    # Strict mode must refuse first.
    assert icg.main(make_args(tmp_path, fixtures)) == 2
    assert not (tmp_path / "releases" / "RAC-EXP-2025-001").exists()

    assert icg.main(make_args(tmp_path, fixtures, legacy=True)) == 0
    release = tmp_path / "releases" / "RAC-EXP-2025-001"
    assert verify_release(release).ok

    pre = json.loads((release / "stages" / "optimization_telemetry" / "pre-held-out.json").read_text())
    for field in icg.LEGACY_D20004_NOT_RECORDED:
        assert pre[field] is None, field
    # Reconstructed from surrogate-role measured entries, never fabricated.
    assert pre["per_surrogate_detection_rates"] == SURROGATE_RATES
    assert pre["surrogate_worst_case_detection_rate"] == max(SURROGATE_RATES.values())
    assert pre["transformation_sweep_variance"] >= 0.0
    assert pre["printability"] == 0.91
    assert pre["pattern_fidelity"] == 0.82

    experiment = json.loads((release / "experiment.json").read_text())
    flags = experiment["validity_flags"]
    assert flags["mode"] == "legacy-d20004"
    assert flags["not_recorded_fields"] == list(icg.LEGACY_D20004_NOT_RECORDED)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registry_created_and_appended(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path)
    assert icg.main(make_args(tmp_path, fixtures)) == 0
    registry = ExperimentRegistry.from_json((tmp_path / "registry.json").read_text())
    assert len(registry) == 1

    # Second, independent run appends a second experiment.
    tmp2 = tmp_path / "second"
    fixtures2 = make_run(tmp2)
    argv = make_args(tmp2, fixtures2, experiment_id="RAC-EXP-2025-002")
    argv[argv.index("--registry") + 1] = str(tmp_path / "registry.json")
    assert icg.main(argv) == 0
    registry = ExperimentRegistry.from_json((tmp_path / "registry.json").read_text())
    assert len(registry) == 2
    assert registry.get("RAC-EXP-2025-001").generation_id == "RAC-PER-D2-9999"
    found = registry.find_by_stage("optimization_telemetry", "RAC-PER-D2-9999-telemetry")
    assert {a.experiment_id for a in found} == {"RAC-EXP-2025-001", "RAC-EXP-2025-002"}


def test_registry_rejects_duplicate_experiment(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path)
    assert icg.main(make_args(tmp_path, fixtures)) == 0
    (tmp_path / "releases" / "RAC-EXP-2025-002").mkdir(parents=True)  # avoid dir-exists refusal masking
    argv = make_args(tmp_path, fixtures, experiment_id="RAC-EXP-2025-001")
    # release dir already exists -> refusal happens before registry write.
    assert icg.main(argv) == 2
    registry = ExperimentRegistry.from_json((tmp_path / "registry.json").read_text())
    assert len(registry) == 1


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------

def test_refuses_unclosed_generation(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path)
    generation = json.loads(fixtures["generation"].read_text())
    generation["lock_inference_performed"] = False
    _write_json(fixtures["generation"], generation)
    assert icg.main(make_args(tmp_path, fixtures)) == 2

    generation["lock_inference_performed"] = True
    generation["status"] = "READY_FOR_FRESH_HELDOUT_RUN"
    _write_json(fixtures["generation"], generation)
    assert icg.main(make_args(tmp_path, fixtures)) == 2
    assert not (tmp_path / "releases").exists() or not any((tmp_path / "releases").iterdir())


def test_refuses_to_overwrite_existing_release_dir(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path)
    (tmp_path / "releases" / "RAC-EXP-2025-001").mkdir(parents=True)
    assert icg.main(make_args(tmp_path, fixtures)) == 2


def test_refuses_missing_artifact(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path)
    (fixtures["run_dir"] / "surrogate-selection.json").unlink()
    assert icg.main(make_args(tmp_path, fixtures)) == 2

    fixtures = make_run(tmp_path / "fresh")
    argv = make_args(tmp_path / "fresh", fixtures)
    fixtures["measured"].unlink()
    assert icg.main(argv) == 2


def test_refuses_candidate_hash_mismatch(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path)
    (fixtures["run_dir"] / "candidate.png").write_bytes(b"tampered-candidate")
    assert icg.main(make_args(tmp_path, fixtures)) == 2


def test_failed_ingest_leaves_no_partial_release(tmp_path: Path) -> None:
    fixtures = make_run(tmp_path, strict=False)
    assert icg.main(make_args(tmp_path, fixtures)) == 2  # strict refusal
    assert not (tmp_path / "releases" / "RAC-EXP-2025-001").exists()
    assert not (tmp_path / "registry.json").exists()

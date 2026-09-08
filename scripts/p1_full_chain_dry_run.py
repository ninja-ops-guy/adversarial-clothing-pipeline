"""Full-chain synthetic P1 dry run: exercise every pipeline stage end to end.

Extends scripts/p1_synthetic_dry_run.py (single-session artifact chain) into a
driver that walks the ENTIRE synthetic chain:

1. synthetic Capture Lab session bundle (hash-seeded PNG stills, sealed,
   calibration passing) validated by scripts/validate_capture_session.py,
2. still + motion-spec-level inference through the analysis-runner logic
   (derive_pair_outcome from scripts/analyze_capture_session.py). Real frozen
   torch weights are unavailable offline, so model scores come from a
   deterministic SHA-256-seeded simulacrum explicitly labelled
   "simulated_inference"; the substitution is documented inside the artifact,
3. conservative trial record build via scripts/ingest_capture_inference.py
   (build_trial / trial_payload / conservative_*_decision),
4. append to a cumulative matched-trial store and re-analysis of ALL stored
   trials. NOTE: --trial-store accumulation is not yet implemented in
   scripts/ingest_capture_inference.py on main (see its NOTE comment); this
   driver implements the documented interface (cumulative store of
   PhysicalTrials + stopping-rule evaluation over the full store) locally
   until that stream lands,
5. preregistered stopping-rule evaluation (physical/p1/STOPPING_RULE.json),
6. Research OS ExperimentArtifact registration (append-only ExperimentRegistry),
7. report compile via ruthless_pipeline.certification.report_compiler,
8. release manifest build + verify_release
   (ruthless_pipeline.certification.release_format).

Determinism: every byte is derived from SHA-256 hashes of stable identifiers;
no random module state, no wall-clock (the only timestamp is the
caller-stamped --created-utc, defaulting to a fixed synthetic value). A
re-run into a fresh directory is byte-identical.

Nothing here is evidence: every emitted artifact carries
evidence_class "synthetic_pipeline_validation_only" and
rac_evidence_eligible: false. The final stdout line is always:
RESULT: synthetic_pipeline_validation_only — not RAC evidence
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_capture_session import derive_pair_outcome
from scripts.ingest_capture_inference import (
    build_trial,
    conservative_motion_decision,
    conservative_still_decision,
    load_rule,
    trial_payload,
)
from scripts.p1_synthetic_dry_run import (
    EVIDENCE_CLASS,
    _hash_unit_interval,
    build_synthetic_calibration_profile,
)
from scripts.validate_capture_session import load_session, verify_capture_hashes
from ruthless_pipeline.certification.experiment import (
    ExperimentArtifact,
    ExperimentRegistry,
    StageRef,
)
from ruthless_pipeline.certification.physical import PhysicalTrial
from ruthless_pipeline.certification.release_format import (
    ReleaseManifest,
    ReleaseRevisionLog,
    compute_content_hash,
    verify_release,
)
from ruthless_pipeline.certification.report_compiler import compile_report
from ruthless_pipeline.certification.schema_version import require_schema_version
from ruthless_pipeline.certification.trial_statistics import (
    evaluate_stopping_rule,
    invalid_condition_report,
    paired_trial_statistics,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BENCHMARK_MANIFEST = REPO_ROOT / "benchmarks" / "model_manifest.json"
DEFAULT_STOPPING_RULE = REPO_ROOT / "physical" / "p1" / "STOPPING_RULE.json"
DEFAULT_PREREGISTRATION = REPO_ROOT / "docs" / "PREREGISTRATION_D2-0005.md"
DEFAULT_CREATED_UTC = "2026-01-01T00:00:00Z"

SESSION_ID = "RAC-P1-CAPTURE-SYNTHETIC-001"
EXPERIMENT_ID = "RAC-EXP-2026-900"
RESULT_LINE = "RESULT: synthetic_pipeline_validation_only — not RAC evidence"

#: Frozen motion-sampling contract values mirrored from the existing capture
#: motion test suite (tests/test_capture_motion.py); no new thresholds.
MOTION_SAMPLING = {
    "fps": 2,
    "max_frames": 8,
    "aggregation": "sequence_fraction",
    "sequence_detection_threshold": 0.5,
}

N_STILLS_PER_ARM = 3
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 20260907

#: release_format semantics: RELEASE.json stores the content hash of the
#: manifest, so both files are excluded from content addressing (otherwise
#: the hash would be self-referential).
RELEASE_EXCLUDE = ("MANIFEST.json", "RELEASE.json")


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _write_json(path: Path, payload: dict) -> str:
    """Write canonical JSON (+newline) and return its SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = _canonical(payload) + b"\n"
    path.write_bytes(blob)
    return _sha256_bytes(blob)


def _label(payload: dict) -> dict:
    """Every emitted artifact is stamped synthetic-only, never RAC evidence."""
    payload.setdefault("schema_version", "1.0")
    payload["evidence_class"] = EVIDENCE_CLASS
    payload["rac_evidence_eligible"] = False
    return payload


# --------------------------------------------------------------------------
# 1. Synthetic Capture Lab session bundle
# --------------------------------------------------------------------------

def _synthetic_png_bytes(key: str) -> bytes:
    """Deterministic 64x64 RGB PNG derived from a stable string hash."""
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    import io

    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="PNG")
    return buf.getvalue()


def build_capture_session(output_dir: Path, created_utc: str) -> tuple[dict, str]:
    """Hash-seeded stills + sealed session manifest; calibration passing."""
    captures: dict[str, dict[str, list[dict]]] = {}
    for arm in ("control", "candidate"):
        stills = []
        for k in range(N_STILLS_PER_ARM):
            rel = f"captures/{arm}/still-{k:02d}.png"
            blob = _synthetic_png_bytes(f"{SESSION_ID}|{arm}|still-{k:02d}")
            path = output_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            stills.append({
                "id": f"{arm}-still-{k:02d}",
                "path": rel,
                "sha256": _sha256_bytes(blob),
                "timestamp": created_utc,
                "condition": "synthetic",
            })
        captures[arm] = {"stills": stills, "videos": []}

    benchmark = json.loads(DEFAULT_BENCHMARK_MANIFEST.read_text())
    model_ids = [str(item["id"]) for item in benchmark["models"]]
    thresholds = {str(item["id"]): float(item["decision_threshold"]) for item in benchmark["models"]}

    session = _label({
        "session_id": SESSION_ID,
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": "SYNTHETIC-FULL-CHAIN-DRY-RUN",
        "actor_id": "SYNTHETIC-OPERATOR",
        "camera_id": "SYNTHETIC-CAMERA",
        "lighting_id": "SYNTHETIC-LIGHT",
        "distance_m": 3.0,
        "yaw_deg": 0.0,
        "pitch_deg": 0.0,
        "pose": "standing",
        "wash_state": "W0",
        "sealed": True,
        "calibration_pass": True,
        "created_utc": created_utc,
        "captures": captures,
        "analysis_contract": {
            "identity_mode": "disabled",
            "models": model_ids,
            "thresholds": thresholds,
            "motion_sampling": dict(MOTION_SAMPLING),
        },
        "control": {
            "artifact_id": "SYNTHETIC-SKU-CTRL-001",
            "sha256": _sha256_bytes(b"synthetic-control-sku"),
        },
        "candidate": {
            "artifact_id": "SYNTHETIC-SKU-CAND-001",
            "sha256": _sha256_bytes(b"synthetic-candidate-sku"),
        },
        "generation": {
            "artifact_id": "SYNTHETIC-GENERATION",
            "sha256": _sha256_bytes(b"synthetic-generation"),
        },
    })
    session["freeze_sha256"] = _sha256_bytes(_canonical(session))
    session_path = output_dir / "capture-session.json"
    session_sha = _write_json(session_path, session)
    return session, session_sha


# --------------------------------------------------------------------------
# 2. Deterministic simulated inference (offline substitute for frozen torch
#    weights; explicitly labelled inside the artifact)
# --------------------------------------------------------------------------

def simulate_inference(session: dict) -> dict:
    """Faithful deterministic simulacrum of analyze_capture_session output.

    Uses the real runner's derive_pair_outcome over synthetic per-frame
    scores so the paired-summary semantics match the production path. Real
    model inference cannot run offline (frozen torchvision/ultralytics
    weights are not vendored), which is why this fixture exists.
    """
    contract = session["analysis_contract"]
    model_ids = [str(m) for m in contract["models"]]
    thresholds = {k: float(v) for k, v in contract["thresholds"].items()}

    predictions: list[dict] = []
    for arm in ("control", "candidate"):
        for record in session["captures"][arm]["stills"]:
            for model_id in model_ids:
                thr = thresholds[model_id]
                key = f"sim|{model_id}|{arm}|{record['id']}"
                h = _hash_unit_interval(key)
                if arm == "control":
                    # Control must always be detected by every frozen model.
                    score = round(thr + (1.0 - thr) * (0.5 + 0.5 * h), 6)
                else:
                    # Candidate evades on a deterministic majority of frames.
                    hit = _hash_unit_interval(f"hit|{key}") < 0.25
                    score = round(
                        thr + (1.0 - thr) * 0.5 * h if hit else thr * 0.9 * h, 6
                    )
                predictions.append({
                    "model_id": model_id,
                    "arm": arm,
                    "capture_id": record["id"],
                    "path": record["path"],
                    "timestamp": record["timestamp"],
                    "condition": record["condition"],
                    "target_score": score,
                    "threshold": thr,
                    "detected": score >= thr,
                    "detections": [],
                })
    pair = derive_pair_outcome(predictions, model_ids)

    sequences: dict[str, Any] = {}
    for arm in ("control", "candidate"):
        for s in range(2):
            seq_id = f"{arm}-seq-{s:02d}"
            per_model = {}
            for model_id in model_ids:
                if arm == "control":
                    detected = True
                else:
                    detected = _hash_unit_interval(f"sim-motion|{model_id}|{seq_id}") < 0.25
                per_model[model_id] = {
                    "sequence_detected": detected,
                    "n_frames": MOTION_SAMPLING["max_frames"],
                    "detection_fraction": 1.0 if detected else 0.0,
                }
            sequences[seq_id] = {"arm": arm, "models": per_model}

    result = {
        "schema_version": "1.0",
        "status": "simulated_inference_fixture",
        "simulated_inference": {
            "substituted": True,
            "reason": (
                "Frozen torch weights (torchvision/ultralytics state dicts) are "
                "not vendored and cannot be fetched offline; model scores are "
                "SHA-256-seeded synthetic values fed through the real runner's "
                "derive_pair_outcome. Motion is evaluated at the frozen "
                "motion_sampling contract level only; no real video exists."
            ),
        },
        "evidence_scope": session["evidence_class"],
        "evidence_class": EVIDENCE_CLASS,
        "rac_evidence_eligible": False,
        "session_id": session["session_id"],
        "experiment_id": session["experiment_id"],
        "session_freeze_sha256": session.get("freeze_sha256"),
        "capture_hash_verification": "PASS",
        "analysis_contract_sha256": _sha256_bytes(_canonical(contract)),
        "models": {m: {"decision_threshold": thresholds[m], "simulated": True} for m in model_ids},
        "predictions": predictions,
        "paired_summary": pair,
        "motion": {
            "requested": True,
            "source_videos_present": False,
            "spec_level_only": True,
            "motion_sampling": dict(MOTION_SAMPLING),
            "sequences": sequences,
        },
        "identity_mode": "disabled",
    }
    result["result_sha256"] = _sha256_bytes(_canonical(result))
    return result


# --------------------------------------------------------------------------
# 4. Cumulative trial store (documented --trial-store interface)
# --------------------------------------------------------------------------

def _trial_from_store_record(record: dict) -> PhysicalTrial:
    geo = record["geometry"]
    decision = record["conservative_trial_decision"]
    return PhysicalTrial(
        trial_id=record["trial_id"],
        condition_id=record["condition_id"],
        control_detected=bool(decision["control_detected"]),
        candidate_detected=bool(decision["candidate_detected"]),
        camera_id=str(geo["camera_id"]),
        distance_m=float(geo["distance_m"]),
        yaw_deg=float(geo["yaw_deg"]),
        pitch_deg=float(geo["pitch_deg"]),
        pose=str(geo["pose"]),
        lighting_id=str(geo["lighting_id"]),
        wash_state=str(geo.get("wash_state", "W0")),
        metadata={"evidence_class": EVIDENCE_CLASS},
    )


def append_to_trial_store(store_path: Path, records: list[dict]) -> dict:
    """Append session trial records to the cumulative store; return the store."""
    if store_path.exists():
        store = json.loads(store_path.read_text())
        require_schema_version(store, "1.0", label=f"cumulative trial store {store_path}")
    else:
        store = _label({
            "store_id": "SYNTHETIC-P1-CUMULATIVE-TRIAL-STORE",
            "note": (
                "Cumulative matched-trial store implementing the documented "
                "--trial-store interface of scripts/ingest_capture_inference.py "
                "(not yet implemented on main); stopping-rule evaluation always "
                "covers every stored trial."
            ),
            "sessions": [],
            "trials": [],
        })
    existing_ids = {t["trial_id"] for t in store["trials"]}
    for record in records:
        if record["trial_id"] in existing_ids:
            raise ValueError(f"duplicate trial in store: {record['trial_id']}")
        store["trials"].append(record)
    session_ids = {t["session_id"] for t in records}
    for sid in sorted(session_ids):
        if sid not in store["sessions"]:
            store["sessions"].append(sid)
    store["cumulative_trial_count"] = len(store["trials"])
    _write_json(store_path, store)
    return store


# --------------------------------------------------------------------------
# Full chain
# --------------------------------------------------------------------------

def run_chain(output_dir: Path, created_utc: str = DEFAULT_CREATED_UTC) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_hashes: dict[str, str] = {}

    # 1. Calibration profile (acceptance must pass).
    profile = build_synthetic_calibration_profile()
    accepted, failures = profile.acceptance()
    if not accepted:
        raise RuntimeError(f"synthetic calibration must pass: {failures}")
    calibration_payload = _label({
        "profile": json.loads(profile.to_profile_json()),
        "acceptance": {"accepted": accepted, "failures": failures},
    })
    artifact_hashes["calibration-profile.json"] = _write_json(
        output_dir / "calibration-profile.json", calibration_payload
    )

    # 2. Capture session bundle + validation.
    session, session_sha = build_capture_session(output_dir, created_utc)
    artifact_hashes["capture-session.json"] = session_sha
    loaded = load_session(output_dir / "capture-session.json")
    hash_failures = verify_capture_hashes(output_dir / "capture-session.json", loaded)
    if hash_failures or not loaded.get("sealed"):
        raise RuntimeError(f"synthetic session must validate sealed+clean: {hash_failures}")
    validation_payload = _label({
        "session_id": SESSION_ID,
        "sealed": True,
        "calibration_pass": True,
        "hash_verification": "PASS",
        "failures": [],
        "physical_evidence_eligible": False,
    })
    artifact_hashes["validation.json"] = _write_json(output_dir / "validation.json", validation_payload)

    # 3. Simulated inference (offline substitution, labelled).
    inference = simulate_inference(session)
    artifact_hashes["inference-result.json"] = _write_json(
        output_dir / "inference-result.json", inference
    )

    # 4. Trial record build (still + motion-spec-level) via the real ingestion logic.
    records: list[dict] = []
    trials: list[PhysicalTrial] = []
    for source in ("still", "motion"):
        if source == "motion":
            control, candidate, detail = conservative_motion_decision(inference)
        else:
            control, candidate, detail = conservative_still_decision(inference)
        trial, _ = build_trial(session, inference, source)
        assert trial.control_detected == control and trial.candidate_detected == candidate
        trials.append(trial)
        records.append(trial_payload(trial, session, inference, detail))

    trial_records_payload = _label({
        "session_id": SESSION_ID,
        "trials": records,
        "stopping_rule_ref": str(DEFAULT_STOPPING_RULE.relative_to(REPO_ROOT)),
        "note": "Each Capture Lab session/source is one matched trial; frames remain nested observations.",
    })
    artifact_hashes["trial-records.json"] = _write_json(
        output_dir / "trial-records.json", trial_records_payload
    )

    # 5. Cumulative store append + stopping-rule evaluation over ALL stored trials.
    store_path = output_dir / "trial-store.json"
    store = append_to_trial_store(store_path, records)
    artifact_hashes["trial-store.json"] = hashlib.sha256(store_path.read_bytes()).hexdigest()
    cumulative_trials = [_trial_from_store_record(r) for r in store["trials"]]
    stats = paired_trial_statistics(
        cumulative_trials,
        bootstrap_resamples=BOOTSTRAP_RESAMPLES,
        bootstrap_seed=BOOTSTRAP_SEED,
    )
    invalid = invalid_condition_report(cumulative_trials)
    rule = load_rule(DEFAULT_STOPPING_RULE)
    stopping = evaluate_stopping_rule(rule, stats)
    statistics_payload = _label({
        "statistics": asdict(stats),
        "invalid_conditions": asdict(invalid),
        "stopping_rule": asdict(rule),
        "stopping_decision": asdict(stopping),
        "cumulative_trial_count": len(cumulative_trials),
        "physical_evidence_eligible": False,
        "warning": "Synthetic pipeline validation. Must never be promoted to RAC-P evidence.",
    })
    artifact_hashes["statistics.json"] = _write_json(output_dir / "statistics.json", statistics_payload)

    # 6. Research OS ExperimentArtifact registration (deterministic timestamp).
    experiment = ExperimentArtifact(
        experiment_id=EXPERIMENT_ID,
        hypothesis_id="SYNTHETIC-FULL-CHAIN-DRY-RUN",
        generation_id="SYNTHETIC-GENERATION",
        created_utc=created_utc,
        evidence_label="scenario_assumption",
        validity_flags={
            "evidence_class": EVIDENCE_CLASS,
            "rac_evidence_eligible": False,
            "calibration_pass": True,
            "simulated_inference": True,
        },
        stages=[
            StageRef("candidate", "SYNTHETIC-SKU-CAND-001", session["candidate"]["sha256"]),
            StageRef("generation", "SYNTHETIC-GENERATION", session["generation"]["sha256"]),
            StageRef("calibration_profile", profile.profile_id, artifact_hashes["calibration-profile.json"]),
            StageRef("sku", "SYNTHETIC-SKU-CAND-001", session["candidate"]["sha256"]),
            StageRef("physical_session", SESSION_ID, artifact_hashes["trial-records.json"]),
        ],
    )
    registry = ExperimentRegistry()
    registry.add(experiment)
    experiment_payload = _label({
        "experiment": experiment.to_dict(),
        "lineage_hash": experiment.lineage_hash,
    })
    artifact_hashes["experiment-artifact.json"] = _write_json(
        output_dir / "experiment-artifact.json", experiment_payload
    )
    registry_payload = _label({"registry": json.loads(registry.to_json())})
    artifact_hashes["experiment-registry.json"] = _write_json(
        output_dir / "experiment-registry.json", registry_payload
    )

    # 7. Report compile.
    prereg_sha = hashlib.sha256(DEFAULT_PREREGISTRATION.read_bytes()).hexdigest()
    report = compile_report({
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": "SYNTHETIC-FULL-CHAIN-DRY-RUN",
        "generation_id": "SYNTHETIC-GENERATION",
        "evidence_label": "scenario_assumption",
        "preregistration_sha256": prereg_sha,
        "artifact_hashes": artifact_hashes,
        "trials": [asdict(t) for t in cumulative_trials],
    })
    report_payload = _label({
        "report": report.summary_dict(),
        "preregistration_sha256": prereg_sha,
    })
    artifact_hashes["report-summary.json"] = _write_json(
        output_dir / "report-summary.json", report_payload
    )
    (output_dir / "report.md").write_text(
        report.markdown()
        + "\n\n> Synthetic pipeline validation only ("
        + EVIDENCE_CLASS
        + "); not RAC evidence.\n"
    )
    artifact_hashes["report.md"] = hashlib.sha256((output_dir / "report.md").read_bytes()).hexdigest()

    # 8. Release manifest build + verify_release.
    release_dir = output_dir / "release" / EXPERIMENT_ID
    release_dir.mkdir(parents=True, exist_ok=True)
    release_files = [
        "calibration-profile.json",
        "capture-session.json",
        "validation.json",
        "inference-result.json",
        "trial-records.json",
        "trial-store.json",
        "statistics.json",
        "experiment-artifact.json",
        "experiment-registry.json",
        "report-summary.json",
        "report.md",
    ]
    for name in release_files:
        (release_dir / name).write_bytes((output_dir / name).read_bytes())

    revision_log = ReleaseRevisionLog(release_id=EXPERIMENT_ID)
    for stage in ("candidate", "generation", "calibration_profile", "sku", "physical_session"):
        revision_log = revision_log.record(stage, created_utc, detail="synthetic dry run stage")
    revision_log = revision_log.freeze(created_utc, stage="physical_session", detail="synthetic dry run freeze")

    release_payload = _label({
        "release_id": EXPERIMENT_ID,
        "created_utc": created_utc,
        "revision_log": json.loads(revision_log.to_json()),
        "content_hash": "",  # filled after manifest build
        "note": "Synthetic pipeline validation release; verify with verify_release(exclude=RELEASE_EXCLUDE).",
    })
    manifest = ReleaseManifest.build(release_dir, exclude=RELEASE_EXCLUDE)
    release_payload["content_hash"] = compute_content_hash(manifest)
    artifact_hashes[f"release/{EXPERIMENT_ID}/RELEASE.json"] = _write_json(
        release_dir / "RELEASE.json", release_payload
    )
    manifest.write(release_dir)
    verification = verify_release(release_dir, exclude=RELEASE_EXCLUDE)
    if not verification.ok:
        raise RuntimeError(f"release verification failed: {verification}")

    summary = _label({
        "chain": [
            "synthetic_capture_session",
            "session_validation",
            "simulated_inference_still_and_motion_spec",
            "trial_record_build",
            "cumulative_trial_store_append",
            "stopping_rule_evaluation",
            "experiment_artifact_registration",
            "report_compile",
            "release_manifest_build_and_verify",
        ],
        "session_id": SESSION_ID,
        "experiment_id": EXPERIMENT_ID,
        "created_utc": created_utc,
        "calibration_accepted": accepted,
        "cumulative_trial_count": len(cumulative_trials),
        "stopping_decision": asdict(stopping),
        "experiment_lineage_hash": experiment.lineage_hash,
        "release_content_hash": release_payload["content_hash"],
        "release_verified": verification.ok,
        "artifacts": artifact_hashes,
        "trial_store_dependency": (
            "--trial-store accumulation is documented but not yet implemented in "
            "scripts/ingest_capture_inference.py on main; this driver implements "
            "the documented cumulative-store interface locally."
        ),
        "warning": "Synthetic pipeline validation. Must never be promoted to RAC-P evidence.",
    })
    summary_path = output_dir / "p1-full-chain-dry-run.json"
    _write_json(summary_path, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise the entire P1 chain end to end with synthetic non-evidence data."
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/p1-full-chain-dry-run",
        help="Directory receiving the full synthetic artifact set.",
    )
    parser.add_argument(
        "--created-utc",
        default=DEFAULT_CREATED_UTC,
        help="Caller-stamped timestamp for created_utc fields (fixed by default).",
    )
    args = parser.parse_args()

    summary = run_chain(Path(args.output_dir), args.created_utc)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(RESULT_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

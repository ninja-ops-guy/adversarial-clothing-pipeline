"""Synthetic end-to-end P1 dry run: prove the artifact chain before the box arrives.

Simulates a complete P1 session with synthetic, explicitly non-evidence data
and emits every artifact a real session would emit:

1. a synthetic PrintCameraProfile passing calibration_ingest acceptance
   (mean Delta-E <= 6, scale error <= 2%, registration error <= 3 mm),
2. a session manifest (instance of physical/p1/SESSION_MANIFEST_TEMPLATE.json),
3. N synthetic matched-pair physical trials through paired_trial_statistics,
4. per-trial ingestion records (instance of
   physical/p1/PHYSICAL_TRIAL_INGESTION_TEMPLATE.json),
5. the preregistered stopping rule (physical/p1/STOPPING_RULE.json) evaluated
   via evaluate_stopping_rule,
6. a synthetic ExperimentArtifact whose physical_session stage binds the
   session manifest by SHA-256, exactly as a real session would.

Fully deterministic: every synthetic perturbation is derived from
SHA-256 hashes of stable identifiers, not from RNG state. Nothing here is
RAC-P evidence: every payload is labelled synthetic_pipeline_validation_only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from ruthless_pipeline.certification.calibration_ingest import (
    PatchMeasurement,
    PrintCameraProfile,
    RegistrationMeasurement,
    ScaleMeasurement,
)
from ruthless_pipeline.certification.experiment import ExperimentArtifact, StageRef
from ruthless_pipeline.certification.physical import PhysicalTrial
from ruthless_pipeline.certification.trial_statistics import (
    PreregisteredStoppingRule,
    evaluate_stopping_rule,
    invalid_condition_report,
    paired_trial_statistics,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STOPPING_RULE = REPO_ROOT / "physical" / "p1" / "STOPPING_RULE.json"
EVIDENCE_CLASS = "synthetic_pipeline_validation_only"

# Full P1 planned grid (must match physical/p1/SESSION_MANIFEST_TEMPLATE.json
# capture_grid and STOPPING_RULE.json max_valid_trials).
GRID_DISTANCES_M = (1.0, 3.0, 5.0)
GRID_YAW_DEG = (-45.0, 0.0, 45.0)
GRID_PITCH_DEG = (0.0,)
GRID_POSES = ("standing", "seated",)
GRID_REPETITIONS = 8
MAX_VALID_TRIALS = (
    len(GRID_DISTANCES_M)
    * len(GRID_YAW_DEG)
    * len(GRID_PITCH_DEG)
    * len(GRID_POSES)
    * GRID_REPETITIONS
)


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _write_canonical(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = _canonical(payload) + b"\n"
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


def _hash_unit_interval(key: str) -> float:
    """Deterministic pseudo-random value in [0, 1) from a stable string."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def build_synthetic_trials() -> list[PhysicalTrial]:
    """Small legacy synthetic trial set (non-evidence), kept for pipeline tests."""
    trials: list[PhysicalTrial] = []
    for i in range(36):
        trials.append(
            PhysicalTrial(
                trial_id=f"SYN-{i:03d}",
                condition_id=f"C{i % 6}",
                control_detected=(i % 17 != 0),
                candidate_detected=(i % 4 == 0),
                camera_id="SYNTHETIC-CAMERA",
                distance_m=(1.0, 3.0, 5.0)[i % 3],
                yaw_deg=(-45.0, 0.0, 45.0)[i % 3],
                pitch_deg=0.0,
                pose="synthetic_rotation",
                lighting_id=("L1", "L2")[i % 2],
                metadata={"evidence_class": "synthetic_pipeline_validation_only"},
            )
        )
    return trials


def build_synthetic_calibration_profile() -> PrintCameraProfile:
    """Synthetic profile engineered to pass calibration_ingest acceptance.

    Patch references span the Lab gamut; measurements are the reference plus
    a deterministic perturbation well inside the Delta-E <= 6 bound.
    """
    patches: list[PatchMeasurement] = []
    for i in range(24):
        L = 20.0 + 60.0 * _hash_unit_interval(f"patch-L-{i}")
        a = -60.0 + 120.0 * _hash_unit_interval(f"patch-a-{i}")
        b = -60.0 + 120.0 * _hash_unit_interval(f"patch-b-{i}")
        measured = (
            L + 0.4 * (_hash_unit_interval(f"patch-dL-{i}") - 0.5),
            a + 1.2 * (_hash_unit_interval(f"patch-da-{i}") - 0.5),
            b + 1.2 * (_hash_unit_interval(f"patch-db-{i}") - 0.5),
        )
        patches.append(
            PatchMeasurement(
                patch_id=f"SYN-PATCH-{i:02d}",
                reference_lab=(round(L, 4), round(a, 4), round(b, 4)),
                measured_lab=(round(measured[0], 4), round(measured[1], 4), round(measured[2], 4)),
            )
        )
    scales = [
        ScaleMeasurement(
            ruler_id=f"SYN-BAR-{d}",
            nominal_cm=10.0,
            measured_px=10.0 * 118.11 * (1.0 + 0.004 * (_hash_unit_interval(f"scale-{d}") - 0.5)),
            distance_m=d,
        )
        for d in (1.0, 3.0, 5.0)
    ]
    registrations = [
        RegistrationMeasurement(
            mark_id=f"FID-{corner}",
            nominal_xy_mm=(7.5, 7.5),
            measured_xy_mm=(
                7.5 + 0.8 * (_hash_unit_interval(f"fid-x-{corner}") - 0.5),
                7.5 + 0.8 * (_hash_unit_interval(f"fid-y-{corner}") - 0.5),
            ),
        )
        for corner in ("TL", "TR", "BL", "BR")
    ]
    return PrintCameraProfile(
        profile_id="RAC-PCP-SYNTHETIC-1",
        camera_id="SYNTHETIC-CAMERA",
        lighting_id="SYNTHETIC-LIGHT",
        created_utc="2026-01-01T00:00:00Z",
        patches=patches,
        scales=scales,
        registrations=registrations,
    )


def build_synthetic_session_trials() -> list[PhysicalTrial]:
    """One full-grid synthetic P1 session (MAX_VALID_TRIALS matched pairs).

    Hash-seeded outcomes: controls almost always detected (a few injected
    invalid trials), candidate detected on a deterministic minority.
    """
    trials: list[PhysicalTrial] = []
    seq = 0
    for distance in GRID_DISTANCES_M:
        for yaw in GRID_YAW_DEG:
            for pitch in GRID_PITCH_DEG:
                for pose in GRID_POSES:
                    for rep in range(1, GRID_REPETITIONS + 1):
                        seq += 1
                        condition_id = (
                            f"d{int(distance * 100):04d}_y{'m' if yaw < 0 else 'p'}"
                            f"{int(abs(yaw)):02d}_pp{int(pitch):02d}_L1_{pose}"
                        )
                        key = f"{condition_id}-r{rep:02d}"
                        control_detected = _hash_unit_interval(f"ctrl-{key}") > 0.05
                        candidate_detected = _hash_unit_interval(f"cand-{key}") < 0.15
                        trials.append(
                            PhysicalTrial(
                                trial_id=f"RAC-P1-T-S001-{seq:04d}",
                                condition_id=condition_id,
                                control_detected=control_detected,
                                candidate_detected=candidate_detected,
                                camera_id="SYNTHETIC-CAMERA",
                                distance_m=distance,
                                yaw_deg=yaw,
                                pitch_deg=pitch,
                                pose=pose,
                                lighting_id="SYNTHETIC-LIGHT",
                                metadata={"evidence_class": EVIDENCE_CLASS},
                            )
                        )
    return trials


def load_preregistered_rule(path: Path) -> PreregisteredStoppingRule:
    """Instantiate the preregistered P1 stopping rule from its frozen JSON."""
    payload = json.loads(path.read_text())
    rule = PreregisteredStoppingRule(
        rule_id=payload["rule_id"],
        min_valid_trials=int(payload["min_valid_trials"]),
        max_valid_trials=int(payload["max_valid_trials"]),
        target_interval_width=float(payload["target_interval_width"]),
        confidence_z=float(payload["confidence_z"]),
        require_interval_below_half=bool(payload["require_interval_below_half"]),
    )
    if rule.max_valid_trials != MAX_VALID_TRIALS:
        raise ValueError("stopping rule max_valid_trials does not match the planned grid")
    return rule


def _trial_record(trial: PhysicalTrial, session_id: str) -> dict:
    stem = f"P1_S001_SYNTHETIC_SKU_d{int(trial.distance_m * 100):04d}"
    return {
        "trial_id": trial.trial_id,
        "session_id": session_id,
        "condition_id": trial.condition_id,
        "garments": {
            "control_sku": "SYNTHETIC-SKU-CTRL-001",
            "candidate_sku": "SYNTHETIC-SKU-CAND-001",
        },
        "captures": {
            "control_file": f"{stem}_CTRL_{trial.condition_id}_r01.png",
            "candidate_file": f"{stem}_CAND_{trial.condition_id}_r01.png",
        },
        "geometry": {
            "camera_id": trial.camera_id,
            "distance_m": trial.distance_m,
            "yaw_deg": trial.yaw_deg,
            "pitch_deg": trial.pitch_deg,
            "pose": trial.pose,
            "lighting_id": trial.lighting_id,
            "wash_state": trial.wash_state,
        },
        "conservative_trial_decision": {
            "control_detected": trial.control_detected,
            "candidate_detected": trial.candidate_detected,
        },
        "validity": {
            "valid": trial.control_detected,
            "invalid_reason": None if trial.control_detected else "control undetected (invalid measurement condition)",
        },
    }


def run_dry_run(output_dir: Path, stopping_rule_path: Path) -> dict:
    session_id = "RAC-P1-SESSION-SYNTHETIC-001"

    # 1. Calibration profile + acceptance.
    profile = build_synthetic_calibration_profile()
    accepted, failures = profile.acceptance()
    calibration_payload = {
        "schema_version": "1.0",
        "evidence_class": EVIDENCE_CLASS,
        "profile": json.loads(profile.to_profile_json()),
        "acceptance": {"accepted": accepted, "failures": failures},
    }
    calibration_sha = _write_canonical(output_dir / "calibration-profile.json", calibration_payload)

    # 2. Session manifest.
    session_manifest = {
        "schema_version": "1.0",
        "evidence_class": EVIDENCE_CLASS,
        "session_id": session_id,
        "date_utc": "2026-01-01",
        "operator": "SYNTHETIC-OPERATOR",
        "rig": {
            "camera_id": "SYNTHETIC-CAMERA",
            "lighting_id": "SYNTHETIC-LIGHT",
            "background": "synthetic matte gray",
            "mounting": "flat-board",
        },
        "calibration": {
            "target_id": "RAC-CALT-P1-0001",
            "profile_id": profile.profile_id,
            "profile_sha256": calibration_sha,
            "acceptance_passed": accepted,
        },
        "garments": {
            "candidate_skus": ["SYNTHETIC-SKU-CAND-001"],
            "control_skus": ["SYNTHETIC-SKU-CTRL-001"],
            "reserve_skus": ["SYNTHETIC-SKU-RSV-001"],
        },
        "environment": {
            "temperature_c": 21.0,
            "relative_humidity_pct": 45.0,
            "ambient_lux_at_garment": 0.0,
        },
    }
    session_sha = _write_canonical(output_dir / "session-manifest.json", session_manifest)

    # 3. Trials through the paired statistics path.
    trials = build_synthetic_session_trials()
    stats = paired_trial_statistics(trials, bootstrap_resamples=1000, bootstrap_seed=20260907)
    invalid = invalid_condition_report(trials)

    # 4. Per-trial ingestion records.
    trial_records = {
        "schema_version": "1.0",
        "evidence_class": EVIDENCE_CLASS,
        "session_id": session_id,
        "trials": [_trial_record(t, session_id) for t in trials],
        "stopping_rule_ref": "physical/p1/STOPPING_RULE.json",
    }
    trials_sha = _write_canonical(output_dir / "trial-records.json", trial_records)

    # 5. Preregistered stopping rule evaluation.
    rule = load_preregistered_rule(stopping_rule_path)
    decision = evaluate_stopping_rule(rule, stats)

    # 6. Synthetic ExperimentArtifact binding the physical_session stage.
    dummy_hash = hashlib.sha256(b"synthetic-placeholder").hexdigest()
    artifact = ExperimentArtifact(
        experiment_id="RAC-EXP-2026-900",
        hypothesis_id="SYNTHETIC-DRY-RUN",
        generation_id="SYNTHETIC-GENERATION",
        created_utc="2026-01-01T00:00:00Z",
        evidence_label="scenario_assumption",
        validity_flags={"evidence_class": EVIDENCE_CLASS, "rac_evidence_eligible": False},
        stages=[
            StageRef(stage="candidate", artifact_id="SYNTHETIC-CANDIDATE", sha256=dummy_hash),
            StageRef(stage="generation", artifact_id="SYNTHETIC-GENERATION", sha256=dummy_hash),
            StageRef(
                stage="calibration_profile",
                artifact_id=profile.profile_id,
                sha256=calibration_sha,
            ),
            StageRef(stage="sku", artifact_id="SYNTHETIC-SKU-CAND-001", sha256=dummy_hash),
            StageRef(
                stage="physical_session",
                artifact_id=session_id,
                sha256=session_sha,
            ),
        ],
    )
    experiment_payload = {
        "schema_version": "1.0",
        "evidence_class": EVIDENCE_CLASS,
        "experiment": artifact.to_dict(),
        "lineage_hash": artifact.lineage_hash,
    }
    experiment_sha = _write_canonical(output_dir / "experiment-artifact.json", experiment_payload)

    # Summary (also printed, matching the historical single-file output).
    summary = {
        "schema_version": "1.0",
        "evidence_class": EVIDENCE_CLASS,
        "rac_evidence_eligible": False,
        "warning": "Synthetic pipeline validation. Must never be promoted to RAC-P evidence.",
        "calibration_accepted": accepted,
        "statistics": asdict(stats),
        "invalid_conditions": asdict(invalid),
        "stopping_rule": asdict(rule),
        "stopping_decision": asdict(decision),
        "artifacts": {
            "calibration-profile.json": calibration_sha,
            "session-manifest.json": session_sha,
            "trial-records.json": trials_sha,
            "experiment-artifact.json": experiment_sha,
        },
    }
    _write_canonical(output_dir / "p1-synthetic-dry-run.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise the full P1 artifact chain with synthetic non-evidence data."
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/p1-synthetic-dry-run",
        help="Directory receiving the full synthetic artifact set.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional extra path for the summary JSON (legacy single-file output).",
    )
    parser.add_argument("--stopping-rule", default=str(DEFAULT_STOPPING_RULE))
    args = parser.parse_args()

    summary = run_dry_run(Path(args.output_dir), Path(args.stopping_rule))
    if args.output:
        legacy_path = Path(args.output)
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_bytes(_canonical(summary) + b"\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

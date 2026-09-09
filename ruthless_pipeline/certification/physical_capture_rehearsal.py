"""Physical capture rehearsal: full physical chain with synthetic fixtures only.

Rehearses the complete physical pipeline end to end with synthetic,
explicitly non-measured fixtures:

1. synthetic Print Alpha package (control + candidate garment specimens),
2. receipt representation binding the specimen hashes,
3. synthetic calibration capture ingested through
   certification.calibration_ingest acceptance,
4. Capture Lab capture registration (identity uniqueness + calibration
   association enforced),
5. a hash-chained rehearsal trial store (108-row Print Alpha trial
   geometry at print-alpha/CAPTURE/trial-sheet.csv),
6. hash-seeded mock detector responses (never real models, never
   held-out data),
7. paired statistics / stopping-rule replay via certification.trial_statistics,
8. Research OS registration via certification.experiment.ExperimentRegistry,
9. report compilation via certification.report_compiler,
10. a sealed rehearsal release (certification.release_format) whose
    evidence label makes promotion to P1/physical-measured impossible.

Every artifact carries evidence_label ``synthetic_pipeline_validation_only``.
Nothing here is physical evidence: no garment was printed, no capture rig
ran, no detector executed. Fully deterministic: every synthetic value is
derived from SHA-256 of stable identifiers; no wall-clock, no RNG state.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ruthless_pipeline.certification.calibration_ingest import (
    PatchMeasurement,
    PrintCameraProfile,
    RegistrationMeasurement,
    ScaleMeasurement,
)
from ruthless_pipeline.certification.experiment import (
    ExperimentArtifact,
    ExperimentRegistry,
    StageRef,
)
from ruthless_pipeline.certification.physical import PhysicalTrial
from ruthless_pipeline.certification.release_format import (
    ReleaseManifest,
    compute_content_hash,
    hash_file,
    verify_release,
)
from ruthless_pipeline.certification.report_compiler import compile_report
from ruthless_pipeline.certification.trial_statistics import (
    PreregisteredStoppingRule,
    evaluate_stopping_rule,
    invalid_condition_report,
    paired_trial_statistics,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TRIAL_SHEET = REPO_ROOT / "print-alpha" / "CAPTURE" / "trial-sheet.csv"
DEFAULT_STOPPING_RULE = REPO_ROOT / "physical" / "p1" / "STOPPING_RULE.json"

#: Every artifact produced by this rehearsal carries exactly this label.
EVIDENCE_LABEL = "synthetic_pipeline_validation_only"
EXPERIMENT_ID = "RAC-EXP-2026-901"
HYPOTHESIS_ID = "SYNTHETIC-PHYSICAL-CAPTURE-REHEARSAL"
SESSION_ID = "RAC-REHEARSAL-SESSION-SYNTHETIC-001"
RELEASE_ID = "RAC-REHEARSAL-RELEASE-SYNTHETIC-001"
FIXED_CREATED_UTC = "2026-01-01T00:00:00Z"

#: Preregistered invalid-fraction flag threshold (report_compiler.INVALID_FRACTION_FLAG).
INVALID_FRACTION_FLAG = 0.10


class RehearsalError(ValueError):
    """Base failure for the physical capture rehearsal."""


class DuplicateCaptureError(RehearsalError):
    """A capture identity was registered twice in the Capture Lab."""


class CalibrationAssociationError(RehearsalError):
    """A capture lacks a valid association to the session calibration profile."""


class TrialStoreTamperedError(RehearsalError):
    """The rehearsal trial store hash chain does not verify."""


class PromotionRefusedError(RehearsalError):
    """Synthetic rehearsal output may never promote to physical-measured evidence."""


# ---------------------------------------------------------------------------
# deterministic helpers


def canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def _hash_unit_interval(key: str) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _write_canonical(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = canonical(payload) + b"\n"
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------------------
# 1. synthetic Print Alpha package + receipt representation


def build_synthetic_print_alpha_package() -> dict[str, Any]:
    """Synthetic garment specimens (control + candidate) as they would arrive
    from the Print Alpha package. Artwork payloads are pure SHA-256-derived
    byte strings; nothing was printed or manufactured."""
    specimens = []
    for role, sku in (
        ("control", "SYNTHETIC-SKU-CTRL-001"),
        ("candidate", "SYNTHETIC-SKU-CAND-001"),
    ):
        artwork_sha = hashlib.sha256(f"synthetic-artwork::{sku}".encode()).hexdigest()
        garment_sha = hashlib.sha256(f"synthetic-garment::{sku}".encode()).hexdigest()
        specimens.append(
            {
                "role": role,
                "sku": sku,
                "artwork_sha256": artwork_sha,
                "garment_sha256": garment_sha,
                "print_alpha_package": "RAC-PRINT-ALPHA-001",
                "physical_item_exists": False,
            }
        )
    return {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "package_id": "RAC-PRINT-ALPHA-SYNTHETIC-001",
        "specimens": specimens,
    }


def build_synthetic_receipt(package: dict[str, Any]) -> dict[str, Any]:
    """Receipt representation: binds the package specimens by hash, exactly
    the linkage a physical goods receipt would establish."""
    receipt = {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "receipt_id": "RAC-RECEIPT-SYNTHETIC-001",
        "package_id": package["package_id"],
        "received_utc": FIXED_CREATED_UTC,
        "specimen_refs": [
            {
                "sku": s["sku"],
                "role": s["role"],
                "garment_sha256": s["garment_sha256"],
            }
            for s in package["specimens"]
        ],
        "physical_receipt_occurred": False,
    }
    receipt["receipt_sha256"] = sha256_payload(receipt)
    return receipt


# ---------------------------------------------------------------------------
# 2. synthetic calibration capture


def build_synthetic_calibration_profile() -> PrintCameraProfile:
    """Synthetic PrintCameraProfile engineered to pass calibration_ingest
    acceptance (mean Delta-E <= 6, scale error <= 2%, registration <= 3 mm)."""
    patches: list[PatchMeasurement] = []
    for i in range(24):
        L = 20.0 + 60.0 * _hash_unit_interval(f"reh-patch-L-{i}")
        a = -60.0 + 120.0 * _hash_unit_interval(f"reh-patch-a-{i}")
        b = -60.0 + 120.0 * _hash_unit_interval(f"reh-patch-b-{i}")
        measured = (
            L + 0.4 * (_hash_unit_interval(f"reh-patch-dL-{i}") - 0.5),
            a + 1.2 * (_hash_unit_interval(f"reh-patch-da-{i}") - 0.5),
            b + 1.2 * (_hash_unit_interval(f"reh-patch-db-{i}") - 0.5),
        )
        patches.append(
            PatchMeasurement(
                patch_id=f"REH-PATCH-{i:02d}",
                reference_lab=(round(L, 4), round(a, 4), round(b, 4)),
                measured_lab=(round(measured[0], 4), round(measured[1], 4), round(measured[2], 4)),
            )
        )
    scales = [
        ScaleMeasurement(
            ruler_id=f"REH-BAR-{d}",
            nominal_cm=10.0,
            measured_px=10.0 * 118.11 * (1.0 + 0.004 * (_hash_unit_interval(f"reh-scale-{d}") - 0.5)),
            distance_m=d,
        )
        for d in (2.0, 5.0, 8.0)
    ]
    registrations = [
        RegistrationMeasurement(
            mark_id=f"FID-{corner}",
            nominal_xy_mm=(7.5, 7.5),
            measured_xy_mm=(
                7.5 + 0.8 * (_hash_unit_interval(f"reh-fid-x-{corner}") - 0.5),
                7.5 + 0.8 * (_hash_unit_interval(f"reh-fid-y-{corner}") - 0.5),
            ),
        )
        for corner in ("TL", "TR", "BL", "BR")
    ]
    return PrintCameraProfile(
        profile_id="RAC-PCP-SYNTHETIC-2",
        camera_id="SYNTHETIC-CAMERA",
        lighting_id="SYNTHETIC-LIGHT",
        created_utc=FIXED_CREATED_UTC,
        patches=patches,
        scales=scales,
        registrations=registrations,
    )


# ---------------------------------------------------------------------------
# 3. Capture Lab


class CaptureLab:
    """Synthetic Capture Lab: registers captures with unique identity and a
    mandatory association to the session calibration profile."""

    def __init__(self, calibration_profile_id: str, calibration_sha256: str):
        if not calibration_profile_id or len(calibration_sha256) != 64:
            raise ValueError("Capture Lab requires a bound calibration profile")
        self.calibration_profile_id = calibration_profile_id
        self.calibration_sha256 = calibration_sha256
        self._captures: dict[str, dict[str, Any]] = {}

    def register_capture(
        self,
        capture_id: str,
        garment_sku: str,
        calibration_profile_id: str | None,
    ) -> dict[str, Any]:
        if not capture_id:
            raise ValueError("capture_id is required")
        if capture_id in self._captures:
            raise DuplicateCaptureError(
                f"capture identity {capture_id!r} already registered; "
                "duplicate capture identities are rejected"
            )
        if calibration_profile_id != self.calibration_profile_id:
            raise CalibrationAssociationError(
                f"capture {capture_id!r} is not associated with session calibration "
                f"profile {self.calibration_profile_id!r} (got {calibration_profile_id!r})"
            )
        record = {
            "capture_id": capture_id,
            "garment_sku": garment_sku,
            "calibration_profile_id": calibration_profile_id,
            "calibration_sha256": self.calibration_sha256,
            "evidence_label": EVIDENCE_LABEL,
            "synthetic_frame": True,
        }
        record["capture_sha256"] = sha256_payload(record)
        self._captures[capture_id] = record
        return record

    @property
    def captures(self) -> list[dict[str, Any]]:
        return [self._captures[k] for k in sorted(self._captures)]


# ---------------------------------------------------------------------------
# 4. trial geometry + mock detector responses


def load_trial_sheet_rows(trial_sheet: Path | None = None) -> list[dict[str, Any]]:
    """Load the 108-row Print Alpha trial geometry (trial-sheet.csv)."""
    path = trial_sheet or DEFAULT_TRIAL_SHEET
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    "trial_id": raw["trial_id"],
                    "condition_id": raw["condition_id"],
                    "repeat": int(raw["repeat"]),
                    "distance_m": float(raw["distance_m"]),
                    "yaw_deg": float(raw["yaw_deg"]),
                    "pitch_deg": float(raw["pitch_deg"]),
                    "pose": raw["pose"],
                    "lighting_id": raw["lighting_id"],
                    "wash_state": raw["wash_state"],
                    "control_file": raw["control_file"],
                    "candidate_file": raw["candidate_file"],
                }
            )
    if not rows:
        raise ValueError(f"trial sheet {path} contains no rows")
    trial_ids = [r["trial_id"] for r in rows]
    if len(set(trial_ids)) != len(trial_ids):
        raise ValueError("trial sheet contains duplicate trial_id values")
    return rows


def mock_detector_response(capture_id: str, garment_sku: str, role: str) -> dict[str, Any]:
    """Hash-seeded mock detector. Never a real model, never held-out data.

    Control garments are detected unless the hash injects a synthetic invalid
    condition (~5%); candidate detection on a deterministic minority (~15%).
    """
    key = f"mock-detector::{capture_id}::{garment_sku}"
    if role == "control":
        detected = _hash_unit_interval(f"ctrl-{key}") > 0.05
    elif role == "candidate":
        detected = _hash_unit_interval(f"cand-{key}") < 0.15
    else:
        raise ValueError(f"unknown garment role {role!r}")
    confidence = round(_hash_unit_interval(f"conf-{key}"), 6)
    response = {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "model_id": "MOCK-DETECTOR-SYNTHETIC-NOT-A-MODEL",
        "mock": True,
        "capture_id": capture_id,
        "garment_sku": garment_sku,
        "detected": detected,
        "confidence": confidence,
    }
    response["response_sha256"] = sha256_payload(response)
    return response


def build_synthetic_trials(
    rows: list[dict[str, Any]],
    lab: CaptureLab,
    receipt: dict[str, Any],
    *,
    invalid_overload_condition: str | None = None,
) -> tuple[list[PhysicalTrial], list[dict[str, Any]]]:
    """Drive the trial sheet through the Capture Lab and mock detector,
    producing PhysicalTrial rows plus per-trial ingestion records.

    ``invalid_overload_condition`` forces every control in that condition to
    be undetected (failure-injection hook for the invalid-condition protocol).
    """
    sku_by_role = {s["role"]: s["sku"] for s in receipt["specimen_refs"]}
    trials: list[PhysicalTrial] = []
    records: list[dict[str, Any]] = []
    for row in rows:
        responses = {}
        for role in ("control", "candidate"):
            capture_id = f"{row['trial_id']}__{role}"
            lab.register_capture(capture_id, sku_by_role[role], lab.calibration_profile_id)
            responses[role] = mock_detector_response(capture_id, sku_by_role[role], role)
        control_detected = responses["control"]["detected"]
        candidate_detected = responses["candidate"]["detected"]
        if invalid_overload_condition and row["condition_id"] == invalid_overload_condition:
            control_detected = False
            candidate_detected = False
        trial = PhysicalTrial(
            trial_id=row["trial_id"],
            condition_id=row["condition_id"],
            control_detected=control_detected,
            candidate_detected=candidate_detected,
            camera_id="SYNTHETIC-CAMERA",
            distance_m=row["distance_m"],
            yaw_deg=row["yaw_deg"],
            pitch_deg=row["pitch_deg"],
            pose=row["pose"],
            lighting_id=row["lighting_id"],
            wash_state=row["wash_state"],
            metadata={"evidence_class": EVIDENCE_LABEL},
        )
        trials.append(trial)
        records.append(
            {
                "trial_id": trial.trial_id,
                "session_id": SESSION_ID,
                "condition_id": trial.condition_id,
                "garments": {
                    "control_sku": sku_by_role["control"],
                    "candidate_sku": sku_by_role["candidate"],
                },
                "captures": {
                    "control_capture_id": f"{row['trial_id']}__control",
                    "candidate_capture_id": f"{row['trial_id']}__candidate",
                    "control_file": row["control_file"],
                    "candidate_file": row["candidate_file"],
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
                "detector_responses": {
                    "control": responses["control"],
                    "candidate": responses["candidate"],
                },
                "conservative_trial_decision": {
                    "control_detected": control_detected,
                    "candidate_detected": candidate_detected,
                },
                "validity": {
                    "valid": control_detected,
                    "invalid_reason": (
                        None
                        if control_detected
                        else "control undetected (invalid measurement condition)"
                    ),
                },
            }
        )
    return trials, records


# ---------------------------------------------------------------------------
# 5. rehearsal trial store (hash-chained, synthetic-labelled)


def rehearsal_store_record(
    trial: PhysicalTrial,
    trial_record: dict[str, Any],
    prev_record_sha256: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "trial": asdict(trial),
        "trial_record": trial_record,
        "prev_record_sha256": prev_record_sha256,
    }


def append_rehearsal_store(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical(record).decode() + "\n")


def load_rehearsal_store(path: Path) -> list[dict[str, Any]]:
    """Load the rehearsal trial store, verifying the SHA-256 hash chain and
    trial_id uniqueness. Any tampering breaks the chain and is detected."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    prev_sha: str | None = None
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("schema_version") != "1.0":
            raise TrialStoreTamperedError(f"trial store line {line_number}: bad schema_version")
        if record.get("evidence_label") != EVIDENCE_LABEL:
            raise TrialStoreTamperedError(
                f"trial store line {line_number}: evidence_label "
                f"{record.get('evidence_label')!r} is not {EVIDENCE_LABEL!r}"
            )
        if record.get("prev_record_sha256") != prev_sha:
            raise TrialStoreTamperedError(
                f"trial store line {line_number}: hash-chain break "
                "(prev_record_sha256 does not match the previous record)"
            )
        trial = PhysicalTrial(**record["trial"])
        if any(PhysicalTrial(**r["trial"]).trial_id == trial.trial_id for r in records):
            raise TrialStoreTamperedError(
                f"trial store line {line_number}: duplicate trial_id {trial.trial_id!r}"
            )
        records.append(record)
        prev_sha = hashlib.sha256(line.encode()).hexdigest()
    return records


# ---------------------------------------------------------------------------
# 6. stopping rule + promotion gate


def load_stopping_rule(path: Path | None = None) -> PreregisteredStoppingRule:
    raw = json.loads((path or DEFAULT_STOPPING_RULE).read_text())
    return PreregisteredStoppingRule(
        rule_id=raw["rule_id"],
        min_valid_trials=int(raw["min_valid_trials"]),
        max_valid_trials=int(raw["max_valid_trials"]),
        target_interval_width=float(raw["target_interval_width"]),
        confidence_z=float(raw["confidence_z"]),
        require_interval_below_half=bool(raw["require_interval_below_half"]),
    )


def promote_rehearsal_release(release_dir: Path, target: str = "physical_garment_p1") -> None:
    """Attempt to promote a rehearsal release. ALWAYS refuses: synthetic
    pipeline validation output can never become P1/physical-measured evidence,
    regardless of caller intent or target label."""
    release_path = Path(release_dir) / "RELEASE.json"
    if not release_path.is_file():
        raise PromotionRefusedError(f"no RELEASE.json in {release_dir}; nothing promotable")
    release = json.loads(release_path.read_text())
    label = release.get("evidence_label")
    if label != EVIDENCE_LABEL:
        raise PromotionRefusedError(
            f"release evidence_label {label!r} is not a rehearsal artefact; "
            "this gate only guards rehearsal releases and still refuses promotion"
        )
    raise PromotionRefusedError(
        f"promotion to {target!r} refused: release {release.get('release_id')!r} carries "
        f"evidence_label {EVIDENCE_LABEL!r}; synthetic pipeline validation output can "
        "never promote to physical-measured evidence (physical_test_executed=false)"
    )


# ---------------------------------------------------------------------------
# 7. full rehearsal run


def run_rehearsal(
    output_dir: Path,
    *,
    trial_sheet: Path | None = None,
    stopping_rule_path: Path | None = None,
    bootstrap_resamples: int = 1000,
    invalid_overload_condition: str | None = None,
) -> dict[str, Any]:
    """Run the full synthetic physical capture rehearsal and seal a release.

    Returns the summary dict (also written to summary.json). Deterministic:
    identical inputs produce byte-identical artifacts and summary sha256.
    """
    output_dir = Path(output_dir)
    artifacts: dict[str, str] = {}

    # Stage 1: Print Alpha package + receipt representation.
    package = build_synthetic_print_alpha_package()
    artifacts["print-alpha-package.json"] = _write_canonical(output_dir / "print-alpha-package.json", package)
    receipt = build_synthetic_receipt(package)
    artifacts["receipt.json"] = _write_canonical(output_dir / "receipt.json", receipt)

    # Stage 2: synthetic calibration capture through calibration_ingest acceptance.
    profile = build_synthetic_calibration_profile()
    accepted, failures = profile.acceptance()
    if not accepted:
        raise RehearsalError(f"synthetic calibration profile failed acceptance: {failures}")
    calibration_payload = {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "profile": json.loads(profile.to_profile_json()),
        "acceptance": {"accepted": accepted, "failures": failures},
    }
    calibration_sha = _write_canonical(output_dir / "calibration-profile.json", calibration_payload)
    artifacts["calibration-profile.json"] = calibration_sha

    # Stage 3: Capture Lab + mock detector + trial rows (108-row geometry).
    lab = CaptureLab(profile.profile_id, profile.profile_sha256())
    rows = load_trial_sheet_rows(trial_sheet)
    trials, trial_records = build_synthetic_trials(
        rows, lab, receipt, invalid_overload_condition=invalid_overload_condition
    )
    captures_payload = {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "session_id": SESSION_ID,
        "captures": lab.captures,
    }
    artifacts["capture-lab.json"] = _write_canonical(output_dir / "capture-lab.json", captures_payload)

    # Stage 4: rehearsal trial store (hash-chained).
    store_path = output_dir / "trial-store.jsonl"
    if store_path.exists():
        store_path.unlink()
    prev_sha: str | None = None
    for trial, record in zip(trials, trial_records):
        store_record = rehearsal_store_record(trial, record, prev_sha)
        append_rehearsal_store(store_path, store_record)
        prev_sha = hashlib.sha256(canonical(store_record)).hexdigest()
    stored = load_rehearsal_store(store_path)
    if len(stored) != len(trials):
        raise RehearsalError("trial store round-trip lost records")
    artifacts["trial-store.jsonl"] = hash_file(store_path)

    # Stage 5: statistics + stopping-rule replay (twice; must be identical).
    stats = paired_trial_statistics(trials, bootstrap_resamples=bootstrap_resamples)
    invalid = invalid_condition_report(trials)
    rule = load_stopping_rule(stopping_rule_path)
    decision_first = evaluate_stopping_rule(rule, stats)
    decision_replay = evaluate_stopping_rule(rule, stats)
    if asdict(decision_first) != asdict(decision_replay):
        raise RehearsalError("stopping-rule replay is not deterministic")
    statistics_payload = {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "physical_evidence_eligible": False,
        "statistics": asdict(stats),
        "invalid_conditions": asdict(invalid),
        "invalid_fraction_flag_threshold": INVALID_FRACTION_FLAG,
        "stopping_rule": asdict(rule),
        "stopping_decision": asdict(decision_first),
        "stopping_rule_replay_deterministic": True,
        "trial_store_sha256": artifacts["trial-store.jsonl"],
    }
    artifacts["statistics.json"] = _write_canonical(output_dir / "statistics.json", statistics_payload)

    # Stage 6: Research OS registration (ExperimentRegistry).
    candidate_sha = hashlib.sha256(b"synthetic-candidate-artifact").hexdigest()
    generation_sha = hashlib.sha256(b"synthetic-generation-artifact").hexdigest()
    artifact = ExperimentArtifact(
        experiment_id=EXPERIMENT_ID,
        hypothesis_id=HYPOTHESIS_ID,
        generation_id="SYNTHETIC-GENERATION-REHEARSAL",
        created_utc=FIXED_CREATED_UTC,
        evidence_label="scenario_assumption",
        validity_flags={
            "evidence_class": EVIDENCE_LABEL,
            "rac_evidence_eligible": False,
            "physical_test_executed": False,
            "physical_efficacy_claimed": False,
            "calibration_pass": accepted,
        },
        stages=[
            StageRef(stage="candidate", artifact_id="SYNTHETIC-CANDIDATE-REHEARSAL", sha256=candidate_sha),
            StageRef(stage="generation", artifact_id="SYNTHETIC-GENERATION-REHEARSAL", sha256=generation_sha),
            StageRef(stage="calibration_profile", artifact_id=profile.profile_id, sha256=calibration_sha),
            StageRef(stage="sku", artifact_id="SYNTHETIC-SKU-CAND-001", sha256=candidate_sha),
            StageRef(stage="physical_session", artifact_id=SESSION_ID, sha256=artifacts["trial-store.jsonl"]),
        ],
    )
    registry = ExperimentRegistry()
    registry.add(artifact)
    registry_payload = {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "registry": json.loads(registry.to_json()),
        "lineage_hash": artifact.lineage_hash,
    }
    artifacts["research-os-registry.json"] = _write_canonical(
        output_dir / "research-os-registry.json", registry_payload
    )

    # Stage 7: report compilation.
    prereg_sha = hash_file(stopping_rule_path or DEFAULT_STOPPING_RULE)
    report = compile_report(
        {
            "experiment_id": EXPERIMENT_ID,
            "hypothesis_id": HYPOTHESIS_ID,
            "generation_id": "SYNTHETIC-GENERATION-REHEARSAL",
            "trials": [asdict(t) for t in trials],
            "conditions": {t.condition_id: {} for t in trials},
            "evidence_label": EVIDENCE_LABEL,
            "preregistration_sha256": prereg_sha,
            "artifact_hashes": {
                "trial-store.jsonl": artifacts["trial-store.jsonl"],
                "calibration-profile.json": calibration_sha,
            },
        }
    )
    (output_dir / "REPORT.md").write_text(report.markdown())
    artifacts["REPORT.md"] = hash_file(output_dir / "REPORT.md")
    artifacts["report.json"] = _write_canonical(output_dir / "report.json", report.summary_dict())

    # Stage 8: seal the rehearsal release + verify it.
    release_dir = output_dir / "release" / RELEASE_ID
    if release_dir.exists():
        raise RehearsalError(f"release directory already exists: {release_dir}")
    release_dir.mkdir(parents=True)
    release_payload = {
        "schema_version": "1.0",
        "release_id": RELEASE_ID,
        "created_utc": FIXED_CREATED_UTC,
        "evidence_label": EVIDENCE_LABEL,
        "physical_test_executed": False,
        "physical_efficacy_claimed": False,
        "promotion_eligible": False,
        "promotion_gate": f"refused: evidence_label == {EVIDENCE_LABEL}",
        "stopping_rule_id": rule.rule_id,
        "may_stop": decision_first.may_stop,
        "valid_trials": stats.valid_trials,
        "total_trials": len(trials),
        "invalid_trials": invalid.invalid_trials,
        "artifact_hashes": artifacts,
    }
    _write_canonical(release_dir / "RELEASE.json", release_payload)
    manifest = ReleaseManifest.build(release_dir)
    manifest.write(release_dir)
    verification = verify_release(release_dir)
    if not verification.ok:
        raise RehearsalError(
            "release verification failed after sealing: "
            f"tampered={verification.tampered} missing={verification.missing} extra={verification.extra}"
        )
    artifacts["release/RELEASE.json"] = hash_file(release_dir / "RELEASE.json")
    artifacts["release/MANIFEST.json"] = hash_file(release_dir / "MANIFEST.json")
    content_hash = compute_content_hash(ReleaseManifest.build(release_dir))

    flagged_conditions = [
        cid
        for cid, total in invalid.total_by_condition.items()
        if invalid.invalid_by_condition.get(cid, 0) / total > INVALID_FRACTION_FLAG
    ]
    summary = {
        "schema_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
        "rac_evidence_eligible": False,
        "physical_test_executed": False,
        "physical_efficacy_claimed": False,
        "warning": "Synthetic physical capture rehearsal. Must never be promoted to physical-measured evidence.",
        "session_id": SESSION_ID,
        "release_id": RELEASE_ID,
        "calibration_accepted": accepted,
        "total_trials": len(trials),
        "valid_trials": stats.valid_trials,
        "invalid_trials": invalid.invalid_trials,
        "flagged_invalid_conditions": sorted(flagged_conditions),
        "stopping_decision": asdict(decision_first),
        "stopping_rule_replay_deterministic": True,
        "release_verification_ok": verification.ok,
        "release_content_hash": content_hash,
        "artifacts": artifacts,
    }
    summary_sha = _write_canonical(output_dir / "summary.json", summary)
    summary["summary_sha256"] = summary_sha
    _write_canonical(output_dir / "summary.json", summary)
    return summary

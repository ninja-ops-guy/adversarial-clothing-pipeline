from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruthless_pipeline.certification.experiment import ExperimentArtifact, ExperimentRegistry, StageRef
from ruthless_pipeline.certification.p1_session_binding import validate_session_schedule_binding
from ruthless_pipeline.certification.physical import PhysicalTrial
from ruthless_pipeline.certification.schema_version import require_schema_version
from ruthless_pipeline.certification.trial_statistics import (
    PreregisteredStoppingRule,
    evaluate_stopping_rule,
    invalid_condition_report,
    paired_trial_statistics,
)


P1_EVIDENCE_CLASS = "physical_garment_p1"
FROZEN_P1_TRIAL_PREFIX = "RAC-P1-T-"


def enforce_promotion_gate(session: dict[str, Any]) -> None:
    """Require the evidence/calibration prerequisites for the cumulative P1 store.

    Schedule binding is a separate invariant and is enforced by the actual
    validation/ingestion path. Keeping this predicate narrow preserves its
    use in failure-injection and governance checks.
    """
    evidence_class = session.get("evidence_class")
    if evidence_class != P1_EVIDENCE_CLASS:
        raise ValueError(
            "trial store promotion gate: evidence_class "
            f"{evidence_class!r} may not enter the P1 trial store; "
            f"only {P1_EVIDENCE_CLASS!r} sessions are eligible"
        )
    if session.get("calibration_pass") is not True:
        raise ValueError(
            "trial store promotion gate: calibration_pass must be true for "
            "a session to enter the P1 trial store"
        )


def trial_store_record(
    trial: PhysicalTrial,
    session: dict[str, Any],
    inference: dict[str, Any],
    detail: dict[str, Any],
    prev_record_sha256: str | None,
) -> dict[str, Any]:
    record = {
        "schema_version": "1.0",
        "trial": asdict(trial),
        "trial_record": trial_payload(trial, session, inference, detail),
        "evidence_class": str(session["evidence_class"]),
        "calibration_pass": bool(session.get("calibration_pass")),
        "lineage": {
            "experiment_id": str(session["experiment_id"]),
            "hypothesis_id": str(session.get("hypothesis_id", "UNSPECIFIED")),
            "calibration_profile_id": str(session.get("calibration_profile_id", "CAPTURE-CALIBRATION")),
            "calibration_profile_sha256": session.get("calibration_profile_sha256"),
            "candidate": session.get("candidate", {}),
            "generation": session.get("generation", {}),
            "p1_schedule": session.get("p1_schedule"),
        },
        "prev_record_sha256": prev_record_sha256,
    }
    return record


def trial_from_store_record(record: dict[str, Any]) -> PhysicalTrial:
    raw = record.get("trial")
    if not isinstance(raw, dict):
        raise ValueError("trial store record is missing the 'trial' payload")
    return PhysicalTrial(**raw)


def _validate_stored_schedule(record: dict[str, Any]) -> None:
    """Validate schedule lineage for platform-era frozen P1 trial IDs.

    Pre-platform stores used session-derived trial IDs and did not carry the
    frozen schedule object. Those records remain readable for historical
    compatibility, but every RAC-P1-T-* record is fail-closed unless its
    frozen schedule lineage is present and exact.
    """
    trial = record.get("trial") or {}
    lineage = record.get("lineage") or {}
    trial_id = str(trial.get("trial_id") or "")
    binding = lineage.get("p1_schedule")
    if not isinstance(binding, dict):
        if trial_id.startswith(FROZEN_P1_TRIAL_PREFIX):
            raise ValueError("trial store record is missing frozen p1_schedule lineage")
        return
    validate_session_schedule_binding(
        {
            "evidence_class": P1_EVIDENCE_CLASS,
            "trial_id": trial_id,
            "distance_m": trial.get("distance_m"),
            "yaw_deg": trial.get("yaw_deg"),
            "pitch_deg": trial.get("pitch_deg"),
            "pose": trial.get("pose"),
            "lighting_variant": binding.get("lighting_variant"),
            "p1_schedule": binding,
        },
        verify_capture_order=False,
    )


def load_trial_store(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    # Pass 1 verifies framing/schema/hash-chain integrity across the whole
    # append-only file before semantic validation. This ensures corruption of
    # a prior line is reported as a hash-chain break rather than as a
    # downstream schedule/content error in the tampered payload.
    parsed: list[tuple[int, dict[str, Any]]] = []
    prev_sha: str | None = None
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        require_schema_version(record, "1.0", label=f"trial store line {line_number}")
        if record.get("prev_record_sha256") != prev_sha:
            raise ValueError(
                f"trial store line {line_number}: hash-chain break "
                "(prev_record_sha256 does not match the previous record)"
            )
        parsed.append((line_number, record))
        prev_sha = hashlib.sha256(line.encode()).hexdigest()

    # Pass 2 applies scientific semantics after the append-only structure is
    # known intact.
    records: list[dict[str, Any]] = []
    trial_ids: set[str] = set()
    for line_number, record in parsed:
        enforce_promotion_gate(
            {"evidence_class": record.get("evidence_class"), "calibration_pass": record.get("calibration_pass")}
        )
        _validate_stored_schedule(record)
        trial = trial_from_store_record(record)
        if trial.trial_id in trial_ids:
            raise ValueError(f"trial store line {line_number}: duplicate trial_id {trial.trial_id!r}")
        trial_ids.add(trial.trial_id)
        records.append(record)
    return records


def append_trial_store(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical(record).decode() + "\n")


def canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rule(path: Path) -> PreregisteredStoppingRule:
    raw = json.loads(path.read_text())
    return PreregisteredStoppingRule(
        rule_id=raw["rule_id"],
        min_valid_trials=int(raw["min_valid_trials"]),
        max_valid_trials=int(raw["max_valid_trials"]),
        target_interval_width=float(raw["target_interval_width"]),
        confidence_z=float(raw["confidence_z"]),
        require_interval_below_half=bool(raw["require_interval_below_half"]),
    )


def conservative_still_decision(inference: dict[str, Any]) -> tuple[bool, bool, dict[str, Any]]:
    outcomes = inference["paired_summary"]["model_outcomes"]
    control = bool(outcomes) and all(bool(v["control_detected"]) for v in outcomes.values())
    candidate = any(bool(v["candidate_detected"]) for v in outcomes.values()) if control else False
    return control, candidate, outcomes


def conservative_motion_decision(inference: dict[str, Any]) -> tuple[bool, bool, dict[str, Any]]:
    sequences = inference.get("motion", {}).get("sequences", {})
    control_sequences = [v for v in sequences.values() if v["arm"] == "control"]
    candidate_sequences = [v for v in sequences.values() if v["arm"] == "candidate"]
    if not control_sequences or not candidate_sequences:
        raise ValueError("motion P1 ingestion requires both control and candidate sequences")

    model_ids = list(inference["models"])
    detail: dict[str, Any] = {}
    for model_id in model_ids:
        control_detected = all(bool(seq["models"][model_id]["sequence_detected"]) for seq in control_sequences)
        candidate_detected = any(bool(seq["models"][model_id]["sequence_detected"]) for seq in candidate_sequences)
        detail[model_id] = {
            "control_detected": control_detected,
            "candidate_detected": candidate_detected,
            "valid": control_detected,
            "invalid_reason": None if control_detected else "control_not_detected",
        }
    control = bool(detail) and all(v["control_detected"] for v in detail.values())
    candidate = any(v["candidate_detected"] for v in detail.values()) if control else False
    return control, candidate, detail


def build_trial(session: dict[str, Any], inference: dict[str, Any], source: str) -> tuple[PhysicalTrial, dict[str, Any]]:
    if source == "motion":
        control, candidate, detail = conservative_motion_decision(inference)
    else:
        control, candidate, detail = conservative_still_decision(inference)
    condition = "|".join([
        f"d={session.get('distance_m', 0)}m",
        f"yaw={session.get('yaw_deg', 0)}",
        f"pitch={session.get('pitch_deg', 0)}",
        f"pose={session.get('pose', 'unspecified')}",
        f"light={session.get('lighting_id', 'unspecified')}",
        f"source={source}",
    ])
    trial = PhysicalTrial(
        trial_id=str(session.get("trial_id") or f"{session['session_id']}:{source}"),
        condition_id=condition,
        control_detected=control,
        candidate_detected=candidate,
        camera_id=str(session["camera_id"]),
        distance_m=float(session.get("distance_m", 0)),
        yaw_deg=float(session.get("yaw_deg", 0)),
        pitch_deg=float(session.get("pitch_deg", 0)),
        pose=str(session.get("pose", "unspecified")),
        lighting_id=str(session.get("lighting_id", "unspecified")),
        wash_state=str(session.get("wash_state", "W0")),
        metadata={
            "experiment_id": str(session["experiment_id"]),
            "session_id": str(session["session_id"]),
            "inference_sha256": str(inference["result_sha256"]),
            "observation_source": source,
            "evidence_class": str(session["evidence_class"]),
            "p1_schedule_sha256": str((session.get("p1_schedule") or {}).get("schedule_sha256", "")),
        },
    )
    return trial, detail


def trial_payload(trial: PhysicalTrial, session: dict[str, Any], inference: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "trial_id": trial.trial_id,
        "session_id": session["session_id"],
        "condition_id": trial.condition_id,
        "p1_schedule": session.get("p1_schedule"),
        "garments": {
            "control_sku": session["control"]["artifact_id"],
            "candidate_sku": session["candidate"]["artifact_id"],
        },
        "captures": session["captures"],
        "geometry": {
            "camera_id": trial.camera_id,
            "distance_m": trial.distance_m,
            "yaw_deg": trial.yaw_deg,
            "pitch_deg": trial.pitch_deg,
            "pose": trial.pose,
            "lighting_id": trial.lighting_id,
            "wash_state": trial.wash_state,
        },
        "detector_outputs": detail,
        "conservative_trial_decision": {
            "rule": "control_detected = ALL frozen models detect control; candidate_detected = ANY frozen model detects candidate, only when control qualifies",
            "control_detected": trial.control_detected,
            "candidate_detected": trial.candidate_detected,
        },
        "validity": {
            "valid": trial.control_detected,
            "invalid_reason": None if trial.control_detected else "control undetected (invalid measurement condition)",
        },
        "inference_result_sha256": inference["result_sha256"],
    }


def register_experiment(
    session: dict[str, Any],
    physical_artifact_path: Path,
    registry_path: Path,
    calibration_sha256: str | None,
) -> ExperimentArtifact:
    candidate = session.get("candidate", {})
    generation = session.get("generation", {})
    for label, payload in (("candidate", candidate), ("generation", generation)):
        if not payload.get("artifact_id") or len(str(payload.get("sha256", ""))) != 64:
            raise ValueError(f"{label} artifact id and frozen SHA-256 are required for Research OS registration")

    stages = [
        StageRef("candidate", str(candidate["artifact_id"]), str(candidate["sha256"])),
        StageRef("generation", str(generation["artifact_id"]), str(generation["sha256"])),
    ]
    if calibration_sha256:
        stages.append(
            StageRef(
                "calibration_profile",
                str(session.get("calibration_profile_id", "CAPTURE-CALIBRATION")),
                calibration_sha256,
            )
        )
    stages.append(StageRef("physical_session", str(session["session_id"]), sha256_file(physical_artifact_path)))

    artifact = ExperimentArtifact(
        experiment_id=str(session["experiment_id"]),
        hypothesis_id=str(session.get("hypothesis_id", "UNSPECIFIED")),
        generation_id=str(generation["artifact_id"]),
        created_utc=datetime.now(timezone.utc).isoformat(),
        stages=stages,
        evidence_label="internally_measured"
        if session["evidence_class"] == P1_EVIDENCE_CLASS
        else "scenario_assumption",
        validity_flags={
            "capture_evidence_class": session["evidence_class"],
            "physical_evidence_eligible": session["evidence_class"] == P1_EVIDENCE_CLASS,
            "calibration_pass": bool(session.get("calibration_pass")),
            "p1_schedule_bound": session.get("evidence_class") != P1_EVIDENCE_CLASS
            or isinstance(session.get("p1_schedule"), dict),
        },
    )
    registry = ExperimentRegistry.from_json(registry_path.read_text()) if registry_path.exists() else ExperimentRegistry()
    registry.add(artifact)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(registry.to_json() + "\n")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert sealed Capture Lab inference into P1 statistics and Research OS lineage.")
    parser.add_argument("session_json")
    parser.add_argument("inference_json")
    parser.add_argument("--source", choices=("still", "motion"), default="still")
    parser.add_argument("--stopping-rule", default="physical/p1/STOPPING_RULE.json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--registry", default=None)
    parser.add_argument("--calibration-profile", default=None)
    parser.add_argument(
        "--trial-store",
        default=None,
        help="Append this session to a cumulative matched-trial store and analyze all stored trials.",
    )
    args = parser.parse_args()

    session_path = Path(args.session_json)
    inference_path = Path(args.inference_json)
    session = json.loads(session_path.read_text())
    inference = json.loads(inference_path.read_text())
    if not session.get("sealed"):
        raise SystemExit("ingestion blocked: session is not sealed")
    if inference.get("session_id") != session.get("session_id") or inference.get("experiment_id") != session.get("experiment_id"):
        raise SystemExit("ingestion blocked: session/inference lineage mismatch")
    if inference.get("capture_hash_verification") != "PASS":
        raise SystemExit("ingestion blocked: capture integrity did not pass")
    if session["evidence_class"] == P1_EVIDENCE_CLASS:
        if not session.get("calibration_pass"):
            raise SystemExit("ingestion blocked: P1 calibration gate did not pass")
        try:
            validate_session_schedule_binding(session, verify_capture_order=True)
        except ValueError as exc:
            raise SystemExit(f"ingestion blocked: {exc}")

    trial, detail = build_trial(session, inference, args.source)
    store_records: list[dict[str, Any]] | None = None
    if args.trial_store:
        try:
            enforce_promotion_gate(session)
        except ValueError as exc:
            raise SystemExit(f"ingestion blocked: {exc}")
        store_path = Path(args.trial_store)
        try:
            store_records = load_trial_store(store_path)
        except ValueError as exc:
            raise SystemExit(f"ingestion blocked: {exc}")
        if any(trial_from_store_record(r).trial_id == trial.trial_id for r in store_records):
            raise SystemExit(f"ingestion blocked: duplicate trial_id {trial.trial_id!r} already in trial store")
        prev_sha = hashlib.sha256(canonical(store_records[-1])).hexdigest() if store_records else None
        record = trial_store_record(trial, session, inference, detail, prev_sha)
        append_trial_store(store_path, record)
        store_records.append(record)
        analysis_trials = [trial_from_store_record(r) for r in store_records]
    else:
        analysis_trials = [trial]
    stats = (
        paired_trial_statistics(analysis_trials, bootstrap_resamples=1000)
        if any(t.control_detected for t in analysis_trials)
        else None
    )
    invalid = invalid_condition_report(analysis_trials)
    rule = load_rule(Path(args.stopping_rule))
    stopping = evaluate_stopping_rule(rule, stats) if stats else None

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    trial_record = {
        "schema_version": "1.0",
        "evidence_label": "internally_measured"
        if session["evidence_class"] == P1_EVIDENCE_CLASS
        else "scenario_assumption",
        "trials": [trial_payload(trial, session, inference, detail)],
        "stopping_rule_ref": args.stopping_rule,
    }
    trial_path = out / "trial-records.json"
    trial_path.write_text(json.dumps(trial_record, indent=2, sort_keys=True) + "\n")
    statistics_payload = {
        "schema_version": "1.0",
        "evidence_class": session["evidence_class"],
        "physical_evidence_eligible": session["evidence_class"] == P1_EVIDENCE_CLASS,
        "statistics": asdict(stats) if stats else None,
        "invalid_conditions": asdict(invalid),
        "stopping_rule": asdict(rule),
        "stopping_decision": asdict(stopping) if stopping else None,
        "warning": "Each Capture Lab session/source is one matched trial; frames remain nested. Continue collection until the preregistered stopping rule is satisfied.",
        "cumulative_trial_count": len(analysis_trials),
    }
    if args.trial_store:
        statistics_payload["trial_store"] = str(args.trial_store)
        statistics_payload["stored_trial_count"] = len(analysis_trials)
        statistics_payload["valid_trial_count"] = sum(1 for t in analysis_trials if t.control_detected)
    stats_path = out / "statistics.json"
    stats_path.write_text(json.dumps(statistics_payload, indent=2, sort_keys=True) + "\n")

    experiment = None
    if args.registry:
        calibration_hash = sha256_file(Path(args.calibration_profile)) if args.calibration_profile else None
        experiment = register_experiment(session, trial_path, Path(args.registry), calibration_hash)
        (out / "experiment-artifact.json").write_bytes(experiment.canonical_json() + b"\n")

    summary = {
        "trial_id": trial.trial_id,
        "trial_records": str(trial_path),
        "statistics": str(stats_path),
        "trial_valid": trial.control_detected,
        "candidate_detected": trial.candidate_detected if trial.control_detected else None,
        "may_stop": stopping.may_stop if stopping else False,
        "cumulative_trial_count": len(analysis_trials),
        "experiment_registered": experiment.experiment_id if experiment else None,
    }
    if args.trial_store:
        summary["trial_store"] = str(args.trial_store)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

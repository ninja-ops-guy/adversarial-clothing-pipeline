"""Export a sealed physical RAC-EXP-* release from the cumulative P1 trial store.

Fail-closed pipeline: the preregistered stopping rule
(physical/p1/STOPPING_RULE.json) must evaluate to may_stop=True over ALL
stored valid trials before anything is written. Only sessions that passed the
promotion gate (evidence_class == "physical_garment_p1" AND
calibration_pass == true) exist in the store; the gate is re-verified on
load (see scripts.ingest_capture_inference.load_trial_store).

Release contents (all SHA-256 addressed in MANIFEST.json):
- trial-records.json / statistics.json / invalid-conditions.json
- calibration.json (calibration profile ref, sha256)
- inference-refs.json (sha256 list of all frozen inference results)
- experiment.json (canonical ExperimentArtifact lineage contract)
- REPORT.md + report.json (compiled via certification.report_compiler)
- RELEASE.json (release id, content hash, caller-stamped created_utc)
- MANIFEST.json (ReleaseManifest; verified with verify_release)

Determinism: canonical JSON everywhere; the only wall-clock value is the
caller-supplied --created-utc stamp. Stdlib + repo modules only.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.experiment import ExperimentArtifact, StageRef
from ruthless_pipeline.certification.release_format import (
    ReleaseManifest,
    compute_content_hash,
    hash_file,
    verify_release,
)
from ruthless_pipeline.certification.report_compiler import compile_report
from ruthless_pipeline.certification.trial_statistics import (
    evaluate_stopping_rule,
    invalid_condition_report,
    paired_trial_statistics,
)

from scripts.ingest_capture_inference import (
    canonical,
    load_rule,
    load_trial_store,
    sha256_payload,
    trial_from_store_record,
)


def _require_consistent(records: list[dict[str, Any]], key: str) -> Any:
    values = {canonical(record["lineage"].get(key)) for record in records}
    if len(values) != 1:
        raise ValueError(f"trial store lineage is inconsistent for {key!r}")
    return records[0]["lineage"].get(key)


def build_release(
    trial_store: Path,
    calibration_profile: Path,
    release_id: str,
    output_parent: Path,
    created_utc: str,
    stopping_rule_path: Path,
    *,
    bootstrap_resamples: int = 1000,
    preregistration: Path | None = None,
) -> tuple[Path, ReleaseManifest]:
    """Build and seal the release directory. Raises ValueError (fail closed)
    when the stopping rule is not satisfied or the store is inconsistent."""
    if not created_utc:
        raise ValueError("created_utc is required (explicit caller stamp; no wall-clock reads)")
    records = load_trial_store(trial_store)
    if not records:
        raise ValueError("trial store is empty; no physical P1 trials to release")
    experiment_id = str(_require_consistent(records, "experiment_id"))
    if experiment_id != release_id:
        raise ValueError(
            f"release id {release_id!r} does not match trial store experiment_id {experiment_id!r}"
        )
    trials = [trial_from_store_record(r) for r in records]
    stats = paired_trial_statistics(trials, bootstrap_resamples=bootstrap_resamples)
    rule = load_rule(stopping_rule_path)
    decision = evaluate_stopping_rule(rule, stats)
    if not decision.may_stop:
        raise ValueError(
            f"release blocked: preregistered stopping rule {rule.rule_id} is not "
            f"satisfied ({decision.reason}); continue capture before exporting"
        )

    hypothesis_id = str(_require_consistent(records, "hypothesis_id"))
    candidate = _require_consistent(records, "candidate")
    generation = _require_consistent(records, "generation")
    for label, payload in (("candidate", candidate), ("generation", generation)):
        if not payload.get("artifact_id") or len(str(payload.get("sha256", ""))) != 64:
            raise ValueError(f"{label} artifact id and frozen SHA-256 are required in trial store lineage")

    calibration_sha256 = hash_file(calibration_profile)
    calibration_profile_id = str(records[0]["lineage"].get("calibration_profile_id", "CAPTURE-CALIBRATION"))
    inference_sha256 = sorted({str(r["trial_record"]["inference_result_sha256"]) for r in records})
    trial_store_sha256 = hash_file(trial_store)
    prereg_sha256 = hash_file(preregistration) if preregistration else hash_file(stopping_rule_path)

    release_dir = output_parent / release_id
    if release_dir.exists():
        raise ValueError(f"release directory already exists: {release_dir}")
    release_dir.mkdir(parents=True)

    trial_records_payload = {
        "schema_version": "1.0",
        "evidence_label": "internally_measured",
        "trials": [r["trial_record"] for r in records],
        "stopping_rule_ref": str(stopping_rule_path),
        "trial_store_sha256": trial_store_sha256,
    }
    (release_dir / "trial-records.json").write_text(
        json.dumps(trial_records_payload, indent=2, sort_keys=True) + "\n"
    )

    invalid = invalid_condition_report(trials)
    statistics_payload = {
        "schema_version": "1.0",
        "evidence_class": "physical_garment_p1",
        "physical_evidence_eligible": True,
        "statistics": asdict(stats),
        "invalid_conditions": asdict(invalid),
        "stopping_rule": asdict(rule),
        "stopping_decision": asdict(decision),
        "cumulative_trial_count": len(trials),
        "valid_trial_count": stats.valid_trials,
        "trial_store_sha256": trial_store_sha256,
    }
    (release_dir / "statistics.json").write_text(
        json.dumps(statistics_payload, indent=2, sort_keys=True) + "\n"
    )
    (release_dir / "invalid-conditions.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "rule": "control-undetected trials are invalid measurement conditions, never candidate successes",
                **asdict(invalid),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (release_dir / "calibration.json").write_text(
        json.dumps(
            {
                "calibration_profile_id": calibration_profile_id,
                "sha256": calibration_sha256,
                "source_path": str(calibration_profile),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (release_dir / "inference-refs.json").write_text(
        json.dumps(
            {"schema_version": "1.0", "inference_sha256": inference_sha256},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    experiment = ExperimentArtifact(
        experiment_id=experiment_id,
        hypothesis_id=hypothesis_id,
        generation_id=str(generation["artifact_id"]),
        created_utc=created_utc,
        stages=[
            StageRef("candidate", str(candidate["artifact_id"]), str(candidate["sha256"])),
            StageRef("generation", str(generation["artifact_id"]), str(generation["sha256"])),
            StageRef("calibration_profile", calibration_profile_id, calibration_sha256),
            StageRef("physical_session", f"{release_id}-trial-store", trial_store_sha256),
        ],
        evidence_label="internally_measured",
        validity_flags={
            "capture_evidence_class": "physical_garment_p1",
            "physical_evidence_eligible": True,
            "calibration_pass": True,
            "promotion_gate": "evidence_class == physical_garment_p1 AND calibration_pass == true",
            "stopping_rule_id": rule.rule_id,
            "may_stop": True,
        },
    )
    experiment.validate()
    (release_dir / "experiment.json").write_bytes(experiment.canonical_json() + b"\n")

    bundle = {
        "experiment_id": experiment_id,
        "hypothesis_id": hypothesis_id,
        "generation_id": str(generation["artifact_id"]),
        "trials": [r["trial"] for r in records],
        "conditions": {t.condition_id: {} for t in trials},
        "evidence_label": "internally_measured",
        "preregistration_sha256": prereg_sha256,
        "artifact_hashes": {
            "trial-records.json": sha256_payload(trial_records_payload),
            "calibration_profile": calibration_sha256,
        },
    }
    report = compile_report(bundle)
    (release_dir / "REPORT.md").write_text(report.markdown())
    (release_dir / "report.json").write_text(json.dumps(report.summary_dict(), indent=2, sort_keys=True) + "\n")

    # Content hash covers every payload file sealed so far; RELEASE.json and
    # MANIFEST.json are then added and the directory is verified end to end.
    content_hash = compute_content_hash(ReleaseManifest.build(release_dir))
    (release_dir / "RELEASE.json").write_text(
        json.dumps(
            {
                "release_id": release_id,
                "created_utc": created_utc,
                "content_hash": content_hash,
                "stopping_rule_id": rule.rule_id,
                "valid_trials": stats.valid_trials,
                "cumulative_trial_count": len(trials),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    manifest = ReleaseManifest.build(release_dir)
    manifest.write(release_dir)
    result = verify_release(release_dir)
    if not result.ok:
        raise ValueError(
            "release verification failed after sealing: "
            f"tampered={result.tampered} missing={result.missing} extra={result.extra}"
        )
    return release_dir, manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seal a physical RAC-EXP-* release from the cumulative P1 trial store (fail closed on the stopping rule)."
    )
    parser.add_argument("--trial-store", required=True)
    parser.add_argument("--calibration-profile", required=True)
    parser.add_argument("--release-id", required=True, help="RAC-EXP-YYYY-NNN; must match the store experiment_id")
    parser.add_argument("--output-parent", required=True, help="Parent directory; the release dir is created inside")
    parser.add_argument("--created-utc", required=True, help="Explicit ISO-8601 UTC stamp (no wall-clock reads)")
    parser.add_argument("--stopping-rule", default="physical/p1/STOPPING_RULE.json")
    parser.add_argument("--preregistration", default=None, help="Optional preregistration doc to hash (defaults to the stopping rule)")
    args = parser.parse_args()

    try:
        release_dir, manifest = build_release(
            trial_store=Path(args.trial_store),
            calibration_profile=Path(args.calibration_profile),
            release_id=args.release_id,
            output_parent=Path(args.output_parent),
            created_utc=args.created_utc,
            stopping_rule_path=Path(args.stopping_rule),
            preregistration=Path(args.preregistration) if args.preregistration else None,
        )
    except ValueError as exc:
        print(f"export blocked: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "release_dir": str(release_dir),
                "release_id": args.release_id,
                "files": len(manifest.entries),
                "content_hash": compute_content_hash(manifest),
                "verified": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

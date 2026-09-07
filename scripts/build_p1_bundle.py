from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from ruthless_pipeline.certification import (
    ArtifactBundle,
    ArtifactRef,
    EvidenceState,
    PatternManifest,
    issue_certificate,
    load_protocol,
    verify_certificate_bundle,
)


def load_pattern_manifest(path: Path) -> PatternManifest:
    payload = json.loads(path.read_text())
    master = payload["master"]
    return PatternManifest(
        pattern_id=payload["pattern_id"],
        version=payload["version"],
        task=payload["task"],
        source_commit=payload["source_commit"],
        optimizer=payload["optimizer"],
        optimizer_version=payload["optimizer_version"],
        seed=int(payload["seed"]),
        master=ArtifactRef(
            path=master["path"],
            sha256=master["sha256"],
            media_type=master.get("media_type", "application/octet-stream"),
        ),
        protocol_id=payload["protocol_id"],
        surrogate_model_set=payload["surrogate_model_set"],
        heldout_model_set=payload["heldout_model_set"],
        textile_profile=payload.get("textile_profile"),
        print_profile=payload.get("print_profile"),
        evidence_state=EvidenceState(payload.get("evidence_state", "RAC-D0")),
        metadata=payload.get("metadata", {}),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RAC-P1 evidence from a sealed D2 bundle and measured physical results.")
    parser.add_argument("--d2-bundle", default="certification_artifacts/latest-d2")
    parser.add_argument("--physical-results", default="physical-results.json")
    parser.add_argument("--protocol", default="protocols/RAC-PERSON-DETECT-1.1.json")
    parser.add_argument("--output", default="certification_artifacts/latest-p1")
    args = parser.parse_args()

    d2_root = Path(args.d2_bundle)
    physical_results_path = Path(args.physical_results)
    output = Path(args.output)
    if not d2_root.is_dir():
        raise SystemExit(f"missing D2 bundle: {d2_root}")
    if not physical_results_path.is_file():
        raise SystemExit(f"missing physical results: {physical_results_path}")

    physical_results = json.loads(physical_results_path.read_text())
    if physical_results.get("status") != "measured_physical":
        raise SystemExit("physical result status must be measured_physical")

    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(d2_root, output)
    for stale in (output / "certificate.json", output / "hashes.sha256"):
        if stale.exists():
            stale.unlink()

    bundle = ArtifactBundle.create(output)
    manifest = load_pattern_manifest(output / "manifests" / "pattern.json")
    if physical_results.get("candidate_id") != manifest.pattern_id:
        raise SystemExit("physical candidate_id does not match D2 pattern manifest")

    physical_summary = physical_results["physical_summary"]
    bundle.write_json(
        "physical/summary.json",
        {
            "total_trials": int(physical_summary["total_trials"]),
            "valid_trials": int(physical_summary["valid_trials"]),
            "invalid_trials": int(physical_summary["invalid_trials"]),
            "control_detection_rate": float(physical_summary["control_detection_rate"]),
            "candidate_detection_rate": float(physical_summary["candidate_detection_rate"]),
            "invalid_condition_fraction": float(physical_summary["invalid_condition_fraction"]),
            "relative_detection_reduction": float(physical_summary["relative_detection_reduction"]),
            "criteria_pass": bool(physical_summary["criteria_pass"]),
            "decision_basis": physical_summary.get("decision_basis", "physical matched capture"),
        },
    )
    bundle.write_json("physical/results.json", physical_results)

    rows = list(physical_results.get("rows", []))
    if not rows:
        raise SystemExit("physical results contain no measured rows")
    trials_csv = output / "physical" / "trials.csv"
    trials_csv.parent.mkdir(parents=True, exist_ok=True)
    with trials_csv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    captures: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (str(row["trial_id"]), str(row["condition_id"]))
        if key not in captures:
            captures[key] = {
                "trial_id": row["trial_id"],
                "condition_id": row["condition_id"],
                "camera_id": row["camera_id"],
                "distance_m": row["distance_m"],
                "yaw_deg": row["yaw_deg"],
                "pitch_deg": row["pitch_deg"],
                "pose": row["pose"],
                "lighting_id": row["lighting_id"],
                "wash_state": row["wash_state"],
                "control_sha256": row["control_sha256"],
                "candidate_sha256": row["candidate_sha256"],
            }
    bundle.write_json(
        "physical/capture-manifest.json",
        {
            "schema_version": "1.0",
            "candidate_id": manifest.pattern_id,
            "captures": list(captures.values()),
        },
    )

    protocol = load_protocol(args.protocol)
    digital_summary = json.loads((output / "digital" / "summary.json").read_text())
    cert = issue_certificate(
        bundle=bundle,
        manifest=manifest,
        protocol=protocol,
        digital_summary=digital_summary,
        requested_state=EvidenceState.PHYSICAL,
        physical_evidence_present=True,
    )
    verified, failures = verify_certificate_bundle(bundle.root)
    status = {
        "candidate_id": manifest.pattern_id,
        "protocol_id": protocol.protocol_id,
        "protocol_version": protocol.version,
        "decision": cert.decision.value,
        "evidence_state": cert.evidence_state.value,
        "certificate_id": cert.certificate_id,
        "bundle_verified": verified,
        "verification_failures": failures,
        "physical_summary": physical_summary,
    }
    Path("p1-latest-status.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if verified else 3


if __name__ == "__main__":
    raise SystemExit(main())

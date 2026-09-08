from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ruthless_pipeline.certification.physical import PhysicalTrial
from ruthless_pipeline.certification.schema_version import require_schema_version


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_session(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    require_schema_version(payload, "1.0", label=f"capture session {path}")
    required = {"session_id", "experiment_id", "evidence_class", "actor_id", "camera_id", "captures"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"session missing required fields: {missing}")
    if payload.get("evidence_class") == "synthetic_pipeline_validation_only":
        payload["physical_evidence_eligible"] = False
    return payload


def verify_capture_hashes(session_path: Path, payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    root = session_path.parent
    for arm in ("control", "candidate"):
        arm_payload = payload.get("captures", {}).get(arm, {})
        for kind in ("stills", "videos"):
            for record in arm_payload.get(kind, []):
                rel = record.get("path")
                expected = record.get("sha256")
                if not rel or not expected:
                    failures.append(f"{arm}/{kind}: missing path or sha256")
                    continue
                path = root / rel
                if not path.is_file():
                    failures.append(f"missing capture: {rel}")
                    continue
                if sha256_file(path) != expected:
                    failures.append(f"hash mismatch: {rel}")
    return failures


def build_trial(
    payload: dict[str, Any],
    *,
    condition_id: str,
    control_detected: bool,
    candidate_detected: bool,
    trial_id: str,
) -> PhysicalTrial:
    return PhysicalTrial(
        trial_id=trial_id,
        condition_id=condition_id,
        control_detected=control_detected,
        candidate_detected=candidate_detected,
        camera_id=str(payload["camera_id"]),
        distance_m=float(payload.get("distance_m", 0.0)),
        yaw_deg=float(payload.get("yaw_deg", 0.0)),
        pitch_deg=float(payload.get("pitch_deg", 0.0)),
        pose=str(payload.get("pose", "unspecified")),
        lighting_id=str(payload.get("lighting_id", "unspecified")),
        wash_state=str(payload.get("wash_state", "W0")),
        metadata={
            "session_id": str(payload["session_id"]),
            "actor_id": str(payload["actor_id"]),
            "experiment_id": str(payload["experiment_id"]),
            "evidence_class": str(payload["evidence_class"]),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a RAC Capture Lab session before local inference/ingestion.")
    parser.add_argument("session_json")
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()

    path = Path(args.session_json)
    payload = load_session(path)
    failures = verify_capture_hashes(path, payload) if args.verify_files else []
    result = {
        "session_id": payload["session_id"],
        "experiment_id": payload["experiment_id"],
        "evidence_class": payload["evidence_class"],
        "physical_evidence_eligible": payload.get("evidence_class") == "physical_garment_p1",
        "hash_verification": "PASS" if not failures else "FAIL",
        "failures": failures,
        "analysis_contract": payload.get("analysis_contract"),
        "next_step": "run authorized frozen ensemble locally" if not failures else "repair capture bundle before inference",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_with_hash(src: Path, dst: Path) -> dict:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {"path": dst.as_posix(), "sha256": sha256(dst), "bytes": dst.stat().st_size}


def capture_rows() -> list[dict]:
    rows: list[dict] = []
    for distance in (2, 5, 8):
        for yaw in (0, 30, -30):
            for pose in ("standing", "walking"):
                for lighting in ("indoor-even", "daylight-even"):
                    condition = f"D{distance:02d}_Y{yaw:+03d}_P0_{pose.upper()}_{lighting.upper().replace('-', '_')}"
                    for repeat in (1, 2, 3):
                        trial_id = f"{condition}__R{repeat}"
                        rows.append(
                            {
                                "trial_id": trial_id,
                                "condition_id": condition,
                                "repeat": repeat,
                                "distance_m": float(distance),
                                "yaw_deg": float(yaw),
                                "pitch_deg": 0.0,
                                "pose": pose,
                                "lighting_id": lighting,
                                "wash_state": "W0",
                                "control_file": f"captures/{trial_id}__control.jpg",
                                "candidate_file": f"captures/{trial_id}__candidate.jpg",
                            }
                        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Seal a selected digital candidate into a print-and-test kit.")
    parser.add_argument("--kit-dir", default="print-test-kit")
    parser.add_argument("--benchmark", default="benchmark-results.json")
    parser.add_argument("--d2-status", default="d2-latest-status.json")
    parser.add_argument("--selection", default="benchmarks/runtime/surrogate-selection.json")
    parser.add_argument("--model-manifest", default="benchmarks/model_manifest.json")
    parser.add_argument("--protocol", default="protocols/RAC-PHYSICAL-PRINT-TEST-1.0.md")
    parser.add_argument("--zip", default="print-test-kit.zip")
    args = parser.parse_args()

    root = Path(args.kit_dir)
    verification_path = root / "export-verification.json"
    candidate_config_path = root / "design" / "candidate-config.json"
    if not verification_path.exists() or not candidate_config_path.exists():
        raise SystemExit("build_print_test_kit.js must run before packaging")

    verification = json.loads(verification_path.read_text())
    candidate = json.loads(candidate_config_path.read_text())
    if verification.get("status") != "digital_print_assets_verified":
        raise SystemExit("print assets are not verified")

    evidence_dir = root / "evidence"
    protocol_dir = root / "protocol"
    evidence_sources = {
        "benchmark-results.json": Path(args.benchmark),
        "d2-latest-status.json": Path(args.d2_status),
        "surrogate-selection.json": Path(args.selection),
        "model_manifest.json": Path(args.model_manifest),
    }
    evidence_records: dict[str, dict] = {}
    for name, src in evidence_sources.items():
        if not src.exists():
            raise SystemExit(f"missing evidence source: {src}")
        dst = evidence_dir / name
        copy_with_hash(src, dst)
        evidence_records[name] = {"path": f"evidence/{name}", "sha256": sha256(dst)}

    protocol_path = Path(args.protocol)
    if not protocol_path.exists():
        raise SystemExit(f"missing physical protocol: {protocol_path}")
    copy_with_hash(protocol_path, protocol_dir / protocol_path.name)

    rows = capture_rows()
    physical_dir = root / "physical_trial"
    captures_dir = physical_dir / "captures"
    captures_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0",
        "protocol_id": "RAC-PHYSICAL-PRINT-TEST",
        "protocol_version": "1.0",
        "candidate_id": candidate["candidate_id"],
        "candidate_artifact_sha256": verification["pattern_tile"]["sha256"],
        "camera_id": "SET_BEFORE_EVALUATION",
        "capture_processing": "Record device/app processing and keep it fixed across matched pairs.",
        "matched_control_required": True,
        "expected_pair_count": len(rows),
        "trials": rows,
    }
    (physical_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with (physical_dir / "capture_sheet.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    benchmark = json.loads(Path(args.benchmark).read_text())
    d2 = json.loads(Path(args.d2_status).read_text())
    kit_manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_id": candidate["candidate_id"],
        "source_candidate_id": candidate.get("source_candidate_id"),
        "family": candidate.get("family") or candidate.get("patternType"),
        "primary_product": verification["primary_product"],
        "digital_status": benchmark.get("status"),
        "d2_decision": d2.get("decision"),
        "d2_evidence_state": d2.get("evidence_state"),
        "ready_for_print_and_physical_test": True,
        "physical_validation_performed": False,
        "pattern_tile": verification["pattern_tile"],
        "reference_boards": verification["mockups"],
        "evidence": evidence_records,
        "physical_trial_pair_count": len(rows),
        "claim_boundary": "Digital print candidate only. Physical efficacy is unknown until the included protocol is executed.",
    }
    (root / "print-test-manifest.json").write_text(json.dumps(kit_manifest, indent=2, sort_keys=True) + "\n")

    readme = f"""# PRINT TEST KIT — {candidate['candidate_id']}

This directory is sealed digital preparation for a physical garment trial.

1. Print `design/pattern_tile_4096.png` without editing the artwork.
2. Use the primary product `{verification['primary_product']}` for the first matched test when practical.
3. Print/order a matched control garment using the same product, size, fabric and process without the candidate artwork.
4. Record the real camera identifier in `physical_trial/manifest.json`.
5. Capture every matched pair listed in `physical_trial/capture_sheet.csv` using the specified filenames.
6. Run `python scripts/evaluate_physical_trial.py --trial-manifest physical_trial/manifest.json --captures physical_trial/captures --model-manifest evidence/model_manifest.json --output physical-results.json` from the repository environment.

Current digital D2 decision: **{d2.get('decision', 'UNKNOWN')}**. This does not determine the physical result.
"""
    (root / "README_PRINT_TEST.md").write_text(readme)

    zip_path = Path(args.zip)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file in sorted(root.rglob("*")):
            if file.is_file():
                zf.write(file, file.relative_to(root.parent))

    status = {
        "candidate_id": candidate["candidate_id"],
        "family": kit_manifest["family"],
        "primary_product": kit_manifest["primary_product"],
        "ready_for_print_and_physical_test": True,
        "physical_validation_performed": False,
        "kit_zip": zip_path.name,
        "kit_zip_sha256": sha256(zip_path),
        "pattern_sha256": verification["pattern_tile"]["sha256"],
        "d2_decision": d2.get("decision"),
        "d2_evidence_state": d2.get("evidence_state"),
    }
    Path("print-test-kit-status.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

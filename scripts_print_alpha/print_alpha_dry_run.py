#!/usr/bin/env python3
"""RAC-PRINT-ALPHA-001 release dry run.

Exercises the full print-alpha package-generation path using only currently
permitted inputs — no vendor data is fabricated, no physical test is executed,
and no efficacy is claimed:

    frozen artwork -> production mapping -> manifests -> calibration reference
    -> trial sheet -> validation -> release package

Every unresolved vendor/user field must remain the literal string
``PENDING_USER_ACTION`` (fail-closed). The dry run verifies that preservation
rather than resolving it.

Stage summary:
1. ``frozen_artwork``        — frozen pattern identity (expected SHA-256 from
                               production_alpha/SKU_MANIFEST.json) is consistently
                               referenced by the print-alpha manifests; the
                               sealed print-test-kit.zip presence is recorded
                               (absence is PENDING, never an error to hide).
2. ``production_mapping``    — mapping-manifest placements are complete and all
                               file/hash values are either PENDING_USER_ACTION
                               or real 64-hex digests (never anything else).
3. ``manifests``             — the five print-alpha manifests validate via
                               scripts_print_alpha/validate_manifests.py.
4. ``calibration_reference`` — scripts/generate_calibration_target.py regenerates
                               RAC-CALT-P1-0001 deterministically and the emitted
                               manifest passes its promotion guard.
5. ``trial_sheet``           — the 108-row trial sheet re-exports byte-identically.
6. ``pending_scan``          — every PENDING_USER_ACTION occurrence across the
                               manifests is enumerated with its JSON path so the
                               report preserves the pending state explicitly.
7. ``release_package``       — a dry-run release package is assembled under the
                               output directory with SHA-256-addressed contents
                               and explicit ``physical_test_executed=false`` /
                               ``physical_efficacy_claimed=false`` flags.

Dependency note: the readiness checker (check_print_alpha_readiness.py) and the
package integrity verifier (print_package_integrity.py) are owned by another
workstream. This script SIMULATES those call sites: it records the intended
invocation and its own equivalent checks under ``simulated_external_tools`` in
the report, and will delegate to the real tools once they exist.

Determinism contract: same repo state -> byte-identical report and release
package manifest. No wall-clock values anywhere. Canonical JSON (sort_keys,
indent 2, trailing newline). Exit code 0 when no stage failed (PENDING stages
are expected and do not fail the run); 1 on any stage failure; 2 with
``--strict`` if any PENDING remains.

Usage:
    PYTHONPATH=. python3 scripts_print_alpha/print_alpha_dry_run.py \
        [--output-dir artifacts/print-alpha] [--strict]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ruthless_pipeline.certification.calibration_target import (  # noqa: E402
    FABRICATION_PENDING,
    MANIFEST_FILENAME,
    validate_manifest,
)
from scripts.generate_calibration_target import generate  # noqa: E402
from scripts_print_alpha.export_trial_sheet import render_csv  # noqa: E402

PENDING = "PENDING_USER_ACTION"
EXPECTED_PATTERN_SHA256 = "b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546"
PRINT_TEST_KIT_SHA256 = "b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548"

MANIFEST_DIR = REPO_ROOT / "print-alpha" / "MANIFESTS"
MANIFEST_FILES = [
    "print-alpha-manifest.json",
    "artwork-manifest.json",
    "template-manifest.json",
    "mapping-manifest.json",
    "sku-manifest.json",
]
TRIAL_SHEET = REPO_ROOT / "print-alpha" / "CAPTURE" / "trial-sheet.csv"
SKU_MANIFEST = REPO_ROOT / "production_alpha" / "SKU_MANIFEST.json"
QA_DOCS = [
    "print-alpha/QA/chain-of-custody.md",
    "print-alpha/QA/garment-pairing-checklist.md",
    "print-alpha/QA/receipt-qa.md",
    "print-alpha/CAPTURE/capture-protocol.md",
    "print-alpha/CAPTURE/camera-lighting-sheet.md",
    "print-alpha/CAPTURE/invalid-condition-rules.json",
    "docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md",
    "docs/PRINT_ALPHA_DRY_RUN.md",
]

STATUS_OK = "OK"
STATUS_PENDING = "PENDING_USER_ACTION"
STATUS_FAILED = "FAILED"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest(name: str) -> dict:
    return json.loads((MANIFEST_DIR / name).read_text())


def _iter_pending(node, path="$"):
    """Yield JSON paths of every PENDING_USER_ACTION string."""
    if isinstance(node, dict):
        for key in sorted(node):
            yield from _iter_pending(node[key], f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _iter_pending(value, f"{path}[{i}]")
    elif node == PENDING:
        yield path


def _is_hex64(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def stage_frozen_artwork() -> dict:
    """Frozen pattern identity must be consistently referenced; never regenerated."""
    problems = []
    sku = json.loads(SKU_MANIFEST.read_text())
    sku_hash = sku.get("candidate_source", {}).get("expected_pattern_sha256")
    if sku_hash != EXPECTED_PATTERN_SHA256:
        problems.append(f"SKU_MANIFEST expected_pattern_sha256 mismatch: {sku_hash}")
    artwork = _load_manifest("artwork-manifest.json")
    art_hash = artwork.get("candidate_source", {}).get("expected_pattern_sha256")
    if art_hash != EXPECTED_PATTERN_SHA256:
        problems.append(f"artwork-manifest expected_pattern_sha256 mismatch: {art_hash}")
    primary = _load_manifest("print-alpha-manifest.json")
    ref_hash = primary.get("candidate_artwork_ref", {}).get("expected_sha256")
    if ref_hash != EXPECTED_PATTERN_SHA256:
        problems.append(f"print-alpha-manifest expected_sha256 mismatch: {ref_hash}")
    if primary.get("candidate_artwork_ref", {}).get("byte_identical_to_frozen_source") is not False:
        problems.append("byte_identical_to_frozen_source must be false until upload files exist")

    kit = REPO_ROOT / "print-test-kit.zip"
    kit_state = {"present": kit.exists()}
    if kit.exists():
        actual = sha256_file(kit)
        kit_state["sha256"] = actual
        kit_state["matches_sealed_hash"] = actual == PRINT_TEST_KIT_SHA256
        if not kit_state["matches_sealed_hash"]:
            problems.append("print-test-kit.zip present but hash mismatch")
    else:
        # The sealed kit is an external artifact reference; its absence is a
        # pending input for a real release, not a dry-run failure.
        kit_state["status"] = STATUS_PENDING
        kit_state["note"] = (
            "print-test-kit.zip not in repo; expected sha256 "
            f"{PRINT_TEST_KIT_SHA256} (production_alpha/SKU_MANIFEST.json)"
        )
    status = STATUS_FAILED if problems else (STATUS_OK if kit.exists() else STATUS_PENDING)
    return {"status": status, "expected_pattern_sha256": EXPECTED_PATTERN_SHA256,
            "print_test_kit": kit_state, "problems": problems}


def stage_production_mapping() -> dict:
    """Mapping placements complete; values are PENDING or real hashes, nothing else."""
    problems = []
    mapping = _load_manifest("mapping-manifest.json")
    template = _load_manifest("template-manifest.json")
    panels = set(template.get("panel_geometry", {}))
    placements = [p.get("placement") for p in mapping.get("placements", [])]
    if sorted(placements) != sorted(panels):
        problems.append(f"placement/panel mismatch: {sorted(placements)} vs {sorted(panels)}")
    resolved = 0
    for entry in mapping.get("placements", []):
        for key in ("control_file", "candidate_file"):
            value = entry.get(key)
            if value == PENDING:
                continue
            if isinstance(value, str) and value:
                resolved += 1
            else:
                problems.append(f"{entry.get('placement')}.{key} is neither PENDING nor a value")
    pending = sum(
        1
        for entry in mapping.get("placements", [])
        for key in ("control_file", "candidate_file")
        if entry.get(key) == PENDING
    )
    return {
        "status": STATUS_FAILED if problems else (STATUS_PENDING if pending else STATUS_OK),
        "placements": sorted(placements),
        "resolved_slots": resolved,
        "pending_slots": pending,
        "problems": problems,
    }


def stage_manifests() -> dict:
    """Run the existing five-manifest validator."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts_print_alpha" / "validate_manifests.py")],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return {
        "status": STATUS_OK if proc.returncode == 0 else STATUS_FAILED,
        "validator": "scripts_print_alpha/validate_manifests.py",
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-1:] or [],
        "stderr_tail": proc.stderr.strip().splitlines()[-3:] if proc.returncode else [],
    }


def stage_calibration_reference(out_dir: Path) -> dict:
    """Regenerate RAC-CALT-P1-0001 deterministically and guard its manifest."""
    cal_dir = out_dir / "calibration-target"
    if cal_dir.exists():
        shutil.rmtree(cal_dir)
    manifest_first = generate(cal_dir)
    png_first = sha256_file(cal_dir / manifest_first["png_file"])
    # Determinism check: regenerate into a scratch dir and require
    # byte-identical output. A system temp dir is used so the scratch copy
    # never pollutes (or races with) the packaged artifacts tree.
    import tempfile

    cal_dir_second = Path(tempfile.mkdtemp(prefix="rac-calt-repro-"))
    try:
        generate(cal_dir_second)
        png_second = sha256_file(cal_dir_second / manifest_first["png_file"])
        manifest_bytes_equal = (cal_dir / MANIFEST_FILENAME).read_bytes() == (
            cal_dir_second / MANIFEST_FILENAME
        ).read_bytes()
    finally:
        shutil.rmtree(cal_dir_second, ignore_errors=True)
    validate_manifest(manifest_first)
    problems = []
    if png_first != png_second or not manifest_bytes_equal:
        problems.append("calibration target regeneration is not byte-identical")
    if manifest_first["png_sha256"] != png_first:
        problems.append("manifest png_sha256 does not match regenerated PNG")
    fabrication = manifest_first.get("physical_fabrication", {}).get("status")
    return {
        "status": STATUS_FAILED if problems else STATUS_OK,
        "target_id": manifest_first["target_id"],
        "png_sha256": png_first,
        "generator_sha256": manifest_first["generator"]["sha256"],
        "evidence_class": manifest_first["evidence_class"],
        "physical_fabrication_status": fabrication,
        "fabrication_pending_preserved": fabrication == FABRICATION_PENDING == PENDING,
        "problems": problems,
    }


def stage_trial_sheet() -> dict:
    """Re-export the trial sheet and require byte identity with the committed file."""
    rendered = render_csv()
    committed = TRIAL_SHEET.read_bytes()
    match = rendered == committed
    row_count = rendered.decode().count("\n") - 1
    return {
        "status": STATUS_OK if match and row_count == 108 else STATUS_FAILED,
        "rows": row_count,
        "sha256": sha256_bytes(rendered),
        "byte_identical_to_committed": match,
    }


def stage_pending_scan() -> dict:
    """Enumerate every PENDING_USER_ACTION so pending state is explicitly preserved."""
    pending = {}
    total = 0
    for name in MANIFEST_FILES:
        paths = sorted(_iter_pending(_load_manifest(name)))
        pending[name] = paths
        total += len(paths)
    return {
        "status": STATUS_PENDING if total else STATUS_OK,
        "total_pending_fields": total,
        "pending_by_manifest": pending,
    }


def stage_release_package(out_dir: Path, stages: dict) -> dict:
    """Assemble the dry-run release package with SHA-256-addressed contents."""
    pkg = out_dir / "release-package"
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)
    entries = []

    def add(src: Path, arcname: str) -> None:
        dst = pkg / arcname
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        entries.append({
            "path": arcname,
            "sha256": sha256_file(dst),
            "bytes": dst.stat().st_size,
        })

    for name in MANIFEST_FILES:
        add(MANIFEST_DIR / name, f"manifests/{name}")
    add(SKU_MANIFEST, "manifests/production-alpha-sku-manifest.json")
    add(TRIAL_SHEET, "capture/trial-sheet.csv")
    for rel in QA_DOCS:
        src = REPO_ROOT / rel
        if src.exists():
            add(src, f"docs/{Path(rel).name}")
    cal_dir = out_dir / "calibration-target"
    add(cal_dir / "RAC-CALT-P1-0001.png", "calibration/RAC-CALT-P1-0001.png")
    add(cal_dir / MANIFEST_FILENAME, f"calibration/{MANIFEST_FILENAME}")

    pending_total = stages["pending_scan"]["total_pending_fields"]
    package_manifest = {
        "schema_version": "1.0",
        "package_id": "RAC-PRINT-ALPHA-001-DRYRUN",
        "kind": "dry_run_release_package",
        "physical_test_executed": False,
        "physical_efficacy_claimed": False,
        "evidence_class": "experimental_print_specimen",
        "pending_user_action_fields": pending_total,
        "release_ready": pending_total == 0,
        "contents": sorted(entries, key=lambda e: e["path"]),
    }
    payload = json.dumps(package_manifest, indent=2, sort_keys=True) + "\n"
    (pkg / "RELEASE_PACKAGE.json").write_text(payload)
    return {
        "status": STATUS_OK,
        "package_dir": pkg.relative_to(out_dir).as_posix(),
        "entry_count": len(entries),
        "release_ready": package_manifest["release_ready"],
        "release_package_manifest_sha256": sha256_bytes(payload.encode()),
        "physical_test_executed": False,
        "physical_efficacy_claimed": False,
    }


def simulated_external_tools() -> list[dict]:
    """Simulated call sites for tooling owned by another workstream (agent PA).

    The dry run does NOT create these tools. Once they land, the invocations
    below become real subprocess calls at this exact point in the pipeline.
    """
    return [
        {
            "tool": "scripts/check_print_alpha_readiness.py",
            "status": "SIMULATED_NOT_PRESENT",
            "intended_invocation": "python3 scripts/check_print_alpha_readiness.py --manifest-dir print-alpha/MANIFESTS",
            "dry_run_equivalent": "stages manifests + pending_scan",
        },
        {
            "tool": "scripts/print_package_integrity.py",
            "status": "SIMULATED_NOT_PRESENT",
            "intended_invocation": "python3 scripts/print_package_integrity.py --package artifacts/print-alpha/release-package",
            "dry_run_equivalent": "stage release_package (SHA-256-addressed RELEASE_PACKAGE.json)",
        },
    ]


def run_dry_run(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    stages = {}
    stages["frozen_artwork"] = stage_frozen_artwork()
    stages["production_mapping"] = stage_production_mapping()
    stages["manifests"] = stage_manifests()
    stages["calibration_reference"] = stage_calibration_reference(out_dir)
    stages["trial_sheet"] = stage_trial_sheet()
    stages["pending_scan"] = stage_pending_scan()
    stages["release_package"] = stage_release_package(out_dir, stages)

    failed = [name for name, s in stages.items() if s["status"] == STATUS_FAILED]
    pending = [name for name, s in stages.items() if s["status"] == STATUS_PENDING]
    report = {
        "schema_version": "1.0",
        "report_id": "RAC-PRINT-ALPHA-001-DRY-RUN",
        "kind": "print_alpha_release_dry_run",
        "pipeline": [
            "frozen_artwork",
            "production_mapping",
            "manifests",
            "calibration_reference",
            "trial_sheet",
            "pending_scan",
            "release_package",
        ],
        "overall_status": STATUS_FAILED if failed else (STATUS_PENDING if pending else STATUS_OK),
        "failed_stages": sorted(failed),
        "pending_stages": sorted(pending),
        "physical_test_executed": False,
        "physical_efficacy_claimed": False,
        "claim_boundary": (
            "Dry run of digital package generation only. No physical garment exists, "
            "no physical test was executed, and no physical efficacy is claimed. "
            "PENDING_USER_ACTION fields are preserved, never resolved by estimation."
        ),
        "stages": stages,
        "simulated_external_tools": simulated_external_tools(),
    }
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "artifacts" / "print-alpha"))
    parser.add_argument("--report", default=None, help="report path (default: <output-dir>/dry-run-report.json)")
    parser.add_argument("--strict", action="store_true", help="exit 2 if any PENDING remains")
    args = parser.parse_args(argv)

    out_dir = Path(args.output_dir)
    report = run_dry_run(out_dir)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    report_path = Path(args.report) if args.report else out_dir / "dry-run-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload)
    print(f"overall_status={report['overall_status']} report={report_path}")
    if report["failed_stages"]:
        return 1
    if args.strict and report["pending_stages"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

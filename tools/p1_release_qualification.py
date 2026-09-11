#!/usr/bin/env python3
"""Fail-closed qualification gate for the exact P1 research-production revision.

This gate does not authorize spend and does not claim physical efficacy. It
binds a qualification receipt to one Git commit and verifies the invariants
that must remain true before that revision is used for P1 execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PASS = "PASS"
FAIL = "FAIL"
GATE_ID = "RAC-P1-RELEASE-QUALIFICATION-001"
FROZEN_SURFACE = "benchmarks/frozen_surface_sha256.json"
ALPHA_RECOVERY = "evidence/p1/alpha001-source-recovery.json"
D2005 = "generations/RAC-PER-D2-0005.json"
D2007 = "evidence/d2-0007/stage1-screening-closure.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def frozen_surface_check(root: Path) -> dict:
    pins = json.loads((root / FROZEN_SURFACE).read_text())
    mismatches = []
    for rel, expected in sorted(pins.items()):
        path = root / rel
        actual = sha256_file(path) if path.is_file() else "MISSING"
        if actual != expected:
            mismatches.append({"path": rel, "expected": expected, "actual": actual})
    return {"status": PASS if not mismatches else FAIL, "files_checked": len(pins), "mismatches": mismatches}


def lineage_check(root: Path) -> dict:
    problems: list[str] = []

    d5 = json.loads((root / D2005).read_text())
    if d5.get("status") != "PREREGISTERED" or d5.get("lock_status") != "PREREGISTERED":
        problems.append("D2-0005 is not PREREGISTERED")
    if d5.get("lock_inference_performed") is not False:
        problems.append("D2-0005 lock inference was performed")
    if d5.get("heldout_feedback_allowed") is not False:
        problems.append("D2-0005 held-out feedback is enabled")

    d7 = json.loads((root / D2007).read_text())
    sci = d7.get("scientific_result", {})
    boundary = d7.get("boundary_verification", {})
    closure = d7.get("closure_consequence", {})
    if d7.get("generation_status") != "CLOSED_SCREENED_OUT_H0":
        problems.append("D2-0007 is not closed SCREENED_OUT_H0")
    if sci.get("survivor_count") != 0 or sci.get("admitted_count") != 0:
        problems.append("D2-0007 unexpectedly has admitted survivors")
    for key in ("heldout_access", "body_garment_anchor_support_built", "optimization_opened", "candidate_freeze_created", "alpha_002_promoted", "d2_0005_touched", "alpha_001_rebound"):
        if boundary.get(key) is not False:
            problems.append(f"D2-0007 boundary regression: {key}={boundary.get(key)!r}")
    for key in ("stage2_anchor_engineering_authorized", "stage3_optimization_authorized", "stage5_candidate_freeze_authorized", "stage6_heldout_evaluation_authorized", "alpha_002_promotion_authorized"):
        if closure.get(key) is not False:
            problems.append(f"D2-0007 closure regression: {key}={closure.get(key)!r}")

    return {"status": PASS if not problems else FAIL, "problems": problems}


def alpha_source_check(root: Path) -> dict:
    payload = json.loads((root / ALPHA_RECOVERY).read_text())
    text = json.dumps(payload, sort_keys=True)
    expected_kit = "b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548"
    expected_pattern = "b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546"
    problems = []
    if expected_kit not in text:
        problems.append("Alpha-001 sealed kit hash is not bound to the recovery receipt")
    if expected_pattern not in text:
        problems.append("Alpha-001 pattern hash is not bound to the recovery receipt")
    if '"source_regenerated": false' not in text and payload.get("source_regenerated") is not False:
        problems.append("Alpha-001 source_regenerated is not false")
    if '"source_retuned": false' not in text and payload.get("source_retuned") is not False:
        problems.append("Alpha-001 source_retuned is not false")
    return {"status": PASS if not problems else FAIL, "problems": problems, "kit_sha256": expected_kit, "pattern_sha256": expected_pattern}


def command_check(root: Path, name: str, command: list[str]) -> dict:
    proc = subprocess.run(command, cwd=root, text=True, capture_output=True)
    tail = (proc.stdout + "\n" + proc.stderr).strip()[-4000:]
    return {"status": PASS if proc.returncode == 0 else FAIL, "name": name, "command": command, "returncode": proc.returncode, "output_tail": tail}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--json-out", default="artifacts/p1-release-qualification/qualification-receipt.json")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--skip-full-pytest", action="store_true", help="Developer-only shortcut; receipt is marked non-release if used.")
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    commit = git(root, "rev-parse", "HEAD")
    dirty = git(root, "status", "--porcelain")

    checks: dict[str, dict] = {}
    checks["working_tree_clean"] = {
        "status": PASS if (not dirty or args.allow_dirty) else FAIL,
        "dirty": bool(dirty),
        "allow_dirty": args.allow_dirty,
    }
    checks["frozen_surface"] = frozen_surface_check(root)
    checks["scientific_lineage"] = lineage_check(root)
    checks["alpha001_source"] = alpha_source_check(root)
    checks["json_integrity"] = command_check(root, "json_integrity", [sys.executable, "scripts/check_json_integrity.py"])
    checks["provenance"] = command_check(root, "provenance", [sys.executable, "scripts/build_provenance_graph.py", "--verify"])
    checks["p1_no_spend"] = command_check(root, "p1_no_spend", [sys.executable, "tools/p1_no_spend_readiness_gate.py"])
    checks["p1_schedule_binding_tests"] = command_check(root, "p1_schedule_binding_tests", [sys.executable, "-m", "pytest", "-q", "tests/test_p1_session_binding.py"])
    if args.skip_full_pytest:
        checks["full_pytest"] = {"status": FAIL, "reason": "full pytest skipped; not release-qualified"}
    else:
        checks["full_pytest"] = command_check(root, "full_pytest", [sys.executable, "-m", "pytest", "-q"])

    qualified = all(item.get("status") == PASS for item in checks.values())
    receipt = {
        "schema_version": "1.0",
        "gate_id": GATE_ID,
        "qualified_commit": commit,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "release_qualified": qualified,
        "spend_authorized": False,
        "physical_efficacy_claimed": False,
        "checks": checks,
    }
    out = root / args.json_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(f"P1_RELEASE_QUALIFICATION={'PASS' if qualified else 'FAIL'}")
    print(f"QUALIFIED_COMMIT={commit}")
    print(f"RECEIPT={out.relative_to(root)}")
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())

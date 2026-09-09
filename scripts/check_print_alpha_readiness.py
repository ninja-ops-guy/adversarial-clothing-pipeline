#!/usr/bin/env python3
"""RAC-PRINT-ALPHA-001 Friday readiness checker.

Deterministically answers: "can RAC-PRINT-ALPHA-001 go to manufacturing now?"
and writes the schema-versioned verdict to
``artifacts/print-alpha/readiness.json``.

Verdicts
--------
READY_TO_ORDER
    Every software check passes AND every vendor/physical field is resolved
    AND every per-placement artwork hash is present and verified against
    bytes on disk.
USER_ACTION_REQUIRED
    Every software check passes but one or more vendor/physical fields are
    still the literal ``PENDING_USER_ACTION`` (or artwork is not yet on
    disk). Missing physical/vendor inputs are NEVER silently treated as
    pass.
NOT_READY
    At least one software/integrity check failed (schema violation,
    non-canonical pending literal, non-deterministic trial sheet, wrong
    trial geometry, evidence-boundary breach, or a resolved hash that does
    not match the bytes on disk).

Fail-closed invariants (regression-tested):
- ``PENDING_USER_ACTION`` can never become PASS; it routes to
  ``USER_ACTION_REQUIRED`` at best.
- ``physical_efficacy_claimed`` must be false in every manifest; any other
  value is NOT_READY (evidence-boundary breach).
- Output contains no timestamps or absolute paths: same repo state ->
  byte-identical ``readiness.json``.

Exit codes: 0 = READY_TO_ORDER, 1 = NOT_READY, 2 = USER_ACTION_REQUIRED.

Usage:
    PYTHONPATH=. python3 scripts/check_print_alpha_readiness.py \
        [--repo-root PATH] [--output PATH] [--check-only]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

PENDING = "PENDING_USER_ACTION"
RELEASE_ID = "RAC-PRINT-ALPHA-001"
SCHEMA_VERSION = "1.0"

MANIFEST_NAMES = [
    "print-alpha-manifest.json",
    "artwork-manifest.json",
    "template-manifest.json",
    "mapping-manifest.json",
    "sku-manifest.json",
]

TRIAL_SHEET = Path("print-alpha/CAPTURE/trial-sheet.csv")

READY = "READY_TO_ORDER"
NOT_READY = "NOT_READY"
USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED"

PASS = "PASS"
FAIL = "FAIL"

_HEX64 = set("0123456789abcdef")


def _is_sha256(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in _HEX64 for c in value)
    )


def _iter_strings(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _iter_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _iter_strings(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _render_trial_sheet(repo_root: Path) -> bytes:
    """Re-render the trial sheet in memory via the frozen exporter logic."""
    sys.path.insert(0, str(repo_root))
    try:
        from scripts_print_alpha.export_trial_sheet import render_csv
    finally:
        try:
            sys.path.remove(str(repo_root))
        except ValueError:
            pass
    return render_csv()


def assess_readiness(repo_root: Path) -> dict:
    """Assess RAC-PRINT-ALPHA-001 readiness. Pure function of repo state."""
    repo_root = Path(repo_root)
    manifest_dir = repo_root / "print-alpha" / "MANIFESTS"

    checks: dict[str, dict] = {}
    pending_fields: list[str] = []
    user_action_refs: set[str] = set()

    def record(name: str, category: str, ok: bool, detail: str) -> None:
        checks[name] = {
            "status": PASS if ok else FAIL,
            "category": category,
            "detail": detail,
        }

    # --- software check 1: all five manifests exist -----------------------
    missing = [n for n in MANIFEST_NAMES if not (manifest_dir / n).is_file()]
    record(
        "manifests_present",
        "software",
        not missing,
        "all 5 manifests present" if not missing else f"missing: {missing}",
    )
    manifests = {}
    for name in MANIFEST_NAMES:
        path = manifest_dir / name
        if path.is_file():
            try:
                manifests[name] = json.loads(path.read_text())
            except json.JSONDecodeError as exc:
                record("manifests_parse", "software", False, f"{name}: {exc}")
                manifests[name] = None
    if "manifests_parse" not in checks and not missing:
        record("manifests_parse", "software", True, "all manifests parse as JSON")

    # --- software check 2: frozen schema + evidence boundary --------------
    frozen_schema_path = repo_root / "schemas" / "print_alpha_manifest.schema.json"
    boundary_ok = True
    boundary_detail = "physical_efficacy_claimed=false and evidence_class ok in all manifests"
    for name, data in manifests.items():
        if not isinstance(data, dict):
            boundary_ok = False
            continue
        if data.get("physical_efficacy_claimed") is not False:
            boundary_ok = False
            boundary_detail = f"{name}: physical_efficacy_claimed is not false"
        if data.get("evidence_class") != "experimental_print_specimen":
            boundary_ok = False
            boundary_detail = f"{name}: evidence_class is not experimental_print_specimen"
        for ref in data.get("user_action_refs", []):
            user_action_refs.add(ref)
    record("evidence_boundary", "software", boundary_ok, boundary_detail)

    schema_ok = True
    schema_detail = "primary manifest validates against frozen schema"
    try:
        import jsonschema

        frozen = json.loads(frozen_schema_path.read_text())
        primary = manifests.get("print-alpha-manifest.json")
        if isinstance(primary, dict):
            jsonschema.validate(primary, frozen)
        elif primary is not None:
            raise ValueError("primary manifest missing")
    except Exception as exc:  # noqa: BLE001 - any schema failure is NOT_READY
        schema_ok = False
        schema_detail = f"frozen-schema validation failed: {exc}"
    record("frozen_schema_conformity", "software", schema_ok, schema_detail)

    # --- software check 3: pending literals canonical ----------------------
    canonical_ok = True
    canonical_detail = "all pending fields are literal PENDING_USER_ACTION"
    for name, data in manifests.items():
        if not isinstance(data, dict):
            continue
        for path, value in _iter_strings(data):
            if value.upper().startswith("PENDING") and value != PENDING:
                canonical_ok = False
                canonical_detail = f"{name}:{path} non-canonical pending literal {value!r}"
            if value == PENDING:
                pending_fields.append(f"{name}:{path}")
    record("pending_literals_canonical", "software", canonical_ok, canonical_detail)

    # --- software check 4: trial sheet exists, 108 rows, deterministic -----
    trial_path = repo_root / TRIAL_SHEET
    trial_ok = trial_path.is_file()
    trial_detail = "trial sheet present"
    if trial_ok:
        with trial_path.open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        trial_ok = len(rows) == 108
        trial_detail = f"{len(rows)} data rows (expected 108)"
    record("trial_geometry_108", "software", trial_ok, trial_detail)

    det_ok = True
    det_detail = "re-export byte-identical"
    try:
        rendered = _render_trial_sheet(repo_root)
        if not trial_path.is_file() or trial_path.read_bytes() != rendered:
            det_ok = False
            det_detail = "committed trial sheet differs from deterministic re-export"
    except Exception as exc:  # noqa: BLE001
        det_ok = False
        det_detail = f"trial sheet re-export failed: {exc}"
    record("trial_sheet_deterministic", "software", det_ok, det_detail)

    # --- vendor/physical inputs (never promoted from PENDING to PASS) ------
    template = manifests.get("template-manifest.json") or {}
    template_sha = template.get("template_archive_sha256")
    vendor_template_bound = _is_sha256(template_sha)
    checks["vendor_template_bound"] = {
        "status": PASS if vendor_template_bound else PENDING,
        "category": "vendor",
        "detail": (
            "template archive hash bound"
            if vendor_template_bound
            else "template_archive_sha256 unresolved (UA-1)"
        ),
    }

    sku = manifests.get("sku-manifest.json") or {}
    garments = sku.get("garments", []) if isinstance(sku, dict) else []
    sku_bound = bool(garments) and all(
        isinstance(g, dict)
        and g.get("variant_id") not in (None, "", PENDING)
        and g.get("size") not in (None, "", PENDING)
        for g in garments
    )
    checks["sku_bound"] = {
        "status": PASS if sku_bound else PENDING,
        "category": "vendor",
        "detail": (
            "variant_id and size resolved for both garments"
            if sku_bound
            else "variant_id/size unresolved (user size selection, UA-1/UA-2)"
        ),
    }

    garment = (manifests.get("print-alpha-manifest.json") or {}).get("garment", {})
    vendor_fields_bound = bool(garment) and all(
        garment.get(k) not in (None, PENDING)
        for k in ("size", "print_technology", "printer_vendor")
    )
    checks["garment_vendor_fields_bound"] = {
        "status": PASS if vendor_fields_bound else PENDING,
        "category": "vendor",
        "detail": (
            "size/print_technology/printer_vendor resolved"
            if vendor_fields_bound
            else "garment vendor fields unresolved (UA-1..UA-4)"
        ),
    }

    artwork = manifests.get("artwork-manifest.json") or {}
    entries = artwork.get("artworks", []) if isinstance(artwork, dict) else []
    artwork_ok = bool(entries)
    artwork_detail = "all per-placement artwork hashes verified against bytes on disk"
    pending_art = 0
    for entry in entries:
        if not isinstance(entry, dict):
            artwork_ok = False
            artwork_detail = "malformed artwork entry"
            continue
        digest = entry.get("artwork_sha256")
        if digest == PENDING:
            pending_art += 1
            continue
        if not _is_sha256(digest):
            artwork_ok = False
            artwork_detail = f"{entry.get('file')}: malformed artwork_sha256"
            continue
        fpath = repo_root / str(entry.get("file", ""))
        if not fpath.is_file():
            artwork_ok = False
            artwork_detail = f"{entry.get('file')}: resolved hash but file missing"
            continue
        if _sha256_file(fpath) != digest:
            artwork_ok = False
            artwork_detail = f"{entry.get('file')}: sha256 mismatch"
    if not artwork_ok:
        # A resolved-but-wrong hash or missing file is a hard failure and
        # dominates any still-pending sibling entries.
        checks["artwork_hash_verified"] = {
            "status": FAIL,
            "category": "physical",
            "detail": artwork_detail,
        }
    elif pending_art:
        checks["artwork_hash_verified"] = {
            "status": PENDING,
            "category": "physical",
            "detail": f"{pending_art} per-placement artworks unresolved (UA-1)",
        }
    else:
        checks["artwork_hash_verified"] = {
            "status": PASS,
            "category": "physical",
            "detail": artwork_detail,
        }

    # --- verdict ------------------------------------------------------------
    software_ready = all(
        c["status"] == PASS for c in checks.values() if c["category"] == "software"
    )
    non_software_fail = any(
        c["status"] == FAIL for c in checks.values() if c["category"] != "software"
    )
    any_pending = any(c["status"] == PENDING for c in checks.values())

    if not software_ready or non_software_fail:
        verdict = NOT_READY
    elif any_pending:
        verdict = USER_ACTION_REQUIRED
    else:
        verdict = READY

    return {
        "schema_version": SCHEMA_VERSION,
        "release_id": RELEASE_ID,
        "verdict": verdict,
        "software_ready": software_ready,
        "vendor_template_bound": checks["vendor_template_bound"]["status"] == PASS,
        "sku_bound": checks["sku_bound"]["status"] == PASS,
        "artwork_hash_verified": checks["artwork_hash_verified"]["status"] == PASS,
        "physical_efficacy_claimed": False,
        "evidence_class": "experimental_print_specimen",
        "checks": checks,
        "pending_user_action_fields": sorted(pending_fields),
        "user_action_refs": sorted(user_action_refs),
    }


def render_report(report: dict) -> bytes:
    """Canonical deterministic bytes for the readiness report."""
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    return payload.encode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parent.parent)
    parser.add_argument(
        "--output",
        default=None,
        help="default: <repo-root>/artifacts/print-alpha/readiness.json",
    )
    parser.add_argument("--check-only", action="store_true", help="do not write output")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    output = (
        Path(args.output)
        if args.output
        else repo_root / "artifacts" / "print-alpha" / "readiness.json"
    )

    report = assess_readiness(repo_root)
    if not args.check_only:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(render_report(report))

    print(f"verdict: {report['verdict']}")
    for name, check in sorted(report["checks"].items()):
        print(f"  {check['status']:>20}  {name} ({check['category']}): {check['detail']}")
    if report["verdict"] == USER_ACTION_REQUIRED:
        print(f"  outstanding user actions: {', '.join(report['user_action_refs'])}")
    if not args.check_only:
        print(f"wrote {output}")

    return {READY: 0, NOT_READY: 1, USER_ACTION_REQUIRED: 2}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())

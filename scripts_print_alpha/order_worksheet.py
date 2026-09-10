#!/usr/bin/env python3
"""Generate the Print Alpha order worksheet (Lane D).

Consolidates the five RAC-PRINT-ALPHA-001 manifests into a single
deterministic order worksheet for the vendor action (UA-4/UA-5). Every
unresolved vendor field is carried through as the literal
PENDING_USER_ACTION — never fabricated. The worksheet binds:

- artwork manifest (control/candidate per placement),
- template manifest (panel geometry, template archive hash pin),
- mapping manifest (placement -> files + source_manifest_sha256 pin),
- sku manifest (garment SKUs),
- the readiness verdict.

Output: artifacts/print-alpha/order-worksheet.json plus a human-readable
docs rendering is intentionally NOT produced here (docs stay manual).

Exit nonzero if manifests are invalid or if any guard fails.

Usage:
    python3 scripts_print_alpha/order_worksheet.py [--output artifacts/print-alpha/order-worksheet.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import-safe CLI entrypoint

from scripts_print_alpha.validate_manifests import (
    MANIFEST_DIR,
    PENDING,
    validate_mapping_pairing,
    validate_mapping_source_pin,
)

WORKSHEET_SCHEMA_VERSION = "1.0"


def _load(name: str) -> dict:
    return json.loads((MANIFEST_DIR / name).read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_worksheet(readiness_path: Path | None = None) -> dict:
    artwork = _load("artwork-manifest.json")
    template = _load("template-manifest.json")
    mapping = _load("mapping-manifest.json")
    sku = _load("sku-manifest.json")
    primary = _load("print-alpha-manifest.json")

    # Fail-closed guards (matrix items 13/14) run before any worksheet exists.
    validate_mapping_pairing(mapping)
    validate_mapping_source_pin(mapping, MANIFEST_DIR / mapping["source_manifest_ref"])

    readiness = None
    if readiness_path is not None and readiness_path.exists():
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))

    def pending_count(node) -> int:
        if isinstance(node, dict):
            return sum(pending_count(v) for v in node.values())
        if isinstance(node, list):
            return sum(pending_count(v) for v in node)
        return 1 if node == PENDING else 0

    worksheet = {
        "schema_version": WORKSHEET_SCHEMA_VERSION,
        "worksheet_id": "RAC-PRINT-ALPHA-001-ORDER-WORKSHEET",
        "evidence_class": "experimental_print_specimen",
        "physical_efficacy_claimed": False,
        "source_manifests": {
            name: _sha256_file(MANIFEST_DIR / name)
            for name in (
                "print-alpha-manifest.json",
                "artwork-manifest.json",
                "template-manifest.json",
                "mapping-manifest.json",
                "sku-manifest.json",
            )
        },
        "order": {
            "garments": sku["garments"],
            "placements": mapping["placements"],
            "template_archive_sha256": template["template_archive_sha256"],
            "artworks": artwork["artworks"],
            "primary_manifest_id": primary["manifest_id"],
        },
        "user_action_refs": sorted(
            set(artwork.get("user_action_refs", []))
            | set(template.get("user_action_refs", []))
            | set(mapping.get("user_action_refs", []))
            | set(sku.get("user_action_refs", []))
            | set(primary.get("user_action_refs", []))
        ),
        "pending_user_action_fields": pending_count(
            {
                "artwork": artwork,
                "template": template,
                "mapping": mapping,
                "sku": sku,
                "primary": primary,
            }
        ),
        "readiness_verdict": (readiness or {}).get("verdict", "NOT_EVALUATED"),
        "status": "USER_ACTION_REQUIRED",
    }
    return worksheet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="artifacts/print-alpha/order-worksheet.json")
    parser.add_argument("--readiness", default="artifacts/print-alpha/readiness.json")
    args = parser.parse_args()

    worksheet = build_worksheet(Path(args.readiness))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(worksheet, indent=2, sort_keys=True) + "\n"
    out.write_text(text, encoding="utf-8")
    print(f"worksheet written: {out}")
    print(f"pending USER_ACTION fields: {worksheet['pending_user_action_fields']}")
    print(f"status: {worksheet['status']} (verdict: {worksheet['readiness_verdict']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

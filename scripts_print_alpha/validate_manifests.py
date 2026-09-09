#!/usr/bin/env python3
"""Validate the five RAC-PRINT-ALPHA-001 manifests.

- print-alpha/MANIFESTS/print-alpha-manifest.json is validated against the
  FROZEN contract schemas/print_alpha_manifest.schema.json (never modified).
- The four supporting manifests (artwork, template, mapping, sku) have no
  frozen repo schema; they are validated against the minimal structural
  schemas embedded below, which enforce the fail-closed rule that every
  unresolved vendor field is the literal string "PENDING_USER_ACTION".

Exit code is nonzero on any validation failure.

Usage:
    PYTHONPATH=. python3 scripts_print_alpha/validate_manifests.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "print-alpha" / "MANIFESTS"
FROZEN_SCHEMA = REPO_ROOT / "schemas" / "print_alpha_manifest.schema.json"

PENDING = "PENDING_USER_ACTION"

_PENDING_OR_VALUE = {
    "anyOf": [
        {"type": "string", "const": PENDING},
        {"type": "string", "minLength": 1},
    ]
}

_ARTWORK_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "manifest_id", "artworks", "evidence_class", "physical_efficacy_claimed"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "manifest_id": {"type": "string", "minLength": 1},
        "physical_efficacy_claimed": {"const": False},
        "evidence_class": {"const": "experimental_print_specimen"},
        "artworks": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "required": ["role", "placement", "file", "artwork_sha256"],
                "properties": {
                    "role": {"enum": ["control", "candidate"]},
                    "placement": {"type": "string", "minLength": 1},
                    "file": {"type": "string", "minLength": 1},
                    "artwork_sha256": {
                        "anyOf": [
                            {"type": "string", "const": PENDING},
                            {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                        ]
                    },
                },
            },
        },
    },
}

_TEMPLATE_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "manifest_id", "template_archive_sha256", "panel_geometry", "evidence_class", "physical_efficacy_claimed"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "manifest_id": {"type": "string", "minLength": 1},
        "physical_efficacy_claimed": {"const": False},
        "evidence_class": {"const": "experimental_print_specimen"},
        "template_archive_sha256": {
            "anyOf": [
                {"type": "string", "const": PENDING},
                {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            ]
        },
        "panel_geometry": {"type": "object", "minProperties": 1},
    },
}

_MAPPING_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "manifest_id", "placements", "evidence_class", "physical_efficacy_claimed"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "manifest_id": {"type": "string", "minLength": 1},
        "physical_efficacy_claimed": {"const": False},
        "evidence_class": {"const": "experimental_print_specimen"},
        "placements": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["placement", "control_file", "candidate_file", "panel_geometry_ref"],
                "properties": {
                    "placement": {"type": "string", "minLength": 1},
                    "control_file": _PENDING_OR_VALUE,
                    "candidate_file": _PENDING_OR_VALUE,
                    "panel_geometry_ref": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}

_SKU_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "manifest_id", "source_manifest_ref", "garments", "evidence_class", "physical_efficacy_claimed"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "manifest_id": {"type": "string", "minLength": 1},
        "physical_efficacy_claimed": {"const": False},
        "evidence_class": {"const": "experimental_print_specimen"},
        "source_manifest_ref": {"type": "string", "minLength": 1},
        "garments": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "required": ["sku_id", "role", "product_id", "variant_id", "size", "color"],
                "properties": {
                    "sku_id": {"type": "string", "minLength": 1},
                    "role": {"enum": ["control", "candidate"]},
                    "product_id": {"type": "integer"},
                    "variant_id": _PENDING_OR_VALUE,
                    "size": _PENDING_OR_VALUE,
                    "color": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}

SUPPORTING_SCHEMAS = {
    "artwork-manifest.json": _ARTWORK_SCHEMA,
    "template-manifest.json": _TEMPLATE_SCHEMA,
    "mapping-manifest.json": _MAPPING_SCHEMA,
    "sku-manifest.json": _SKU_SCHEMA,
}


def _check_pending_literals(path: str, node) -> list[str]:
    """Recursively forbid near-miss pending placeholders (fail-closed)."""
    failures = []
    if isinstance(node, dict):
        for key, value in node.items():
            failures += _check_pending_literals(f"{path}.{key}", value)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            failures += _check_pending_literals(f"{path}[{i}]", value)
    elif isinstance(node, str) and node.upper().startswith("PENDING") and node != PENDING:
        failures.append(f"{path}: non-canonical pending placeholder {node!r}; must be literal {PENDING!r}")
    return failures


def main() -> int:
    failures: list[str] = []

    frozen = json.loads(FROZEN_SCHEMA.read_text())
    primary_path = MANIFEST_DIR / "print-alpha-manifest.json"
    primary = json.loads(primary_path.read_text())
    try:
        jsonschema.validate(primary, frozen)
        print(f"OK  {primary_path.name} validates against {FROZEN_SCHEMA.relative_to(REPO_ROOT)}")
    except jsonschema.ValidationError as exc:
        failures.append(f"{primary_path.name}: {exc.message}")

    for name, schema in SUPPORTING_SCHEMAS.items():
        path = MANIFEST_DIR / name
        data = json.loads(path.read_text())
        try:
            jsonschema.validate(data, schema)
            print(f"OK  {name} validates against embedded structural schema")
        except jsonschema.ValidationError as exc:
            failures.append(f"{name}: {exc.message}")

    for name in ["print-alpha-manifest.json", *SUPPORTING_SCHEMAS]:
        path = MANIFEST_DIR / name
        failures += _check_pending_literals(name, json.loads(path.read_text()))

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    print("all 5 manifests valid; all pending fields are literal PENDING_USER_ACTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

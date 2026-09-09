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

import hashlib
import json
import re
import sys
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator, validators
from jsonschema.validators import validates

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "print-alpha" / "MANIFESTS"
FROZEN_SCHEMA = REPO_ROOT / "schemas" / "print_alpha_manifest.schema.json"

PENDING = "PENDING_USER_ACTION"

# A matched trial/condition pair is named "<trial_id>__control.*" /
# "<trial_id>__candidate.*" (see print-alpha/CAPTURE/capture-protocol.md).
_TRIAL_PAIR_RE = re.compile(r"^(?P<trial>.+)__(?P<role>control|candidate)(?:\.|$)")

# Canonical sources a production mapping manifest may be generated from.
# The mapping's ``source_manifest_sha256`` pin must match one of these (or
# the file named by an explicit ``source_manifest_ref``).
MAPPING_SOURCE_CANDIDATES = (
    "print-alpha/MANIFESTS/sku-manifest.json",
    "print-alpha/CAPTURE/trial-sheet.csv",
    "production_alpha/SKU_MANIFEST.json",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _distinct_file_pair(validator, _value, instance, _schema):
    """placement-level guard: a garment must never be compared to itself.

    Fail-closed rules (only fully unresolved PENDING pairs are exempt,
    because no comparison can happen until both files exist):
    - control_file == candidate_file is refused once resolved;
    - when both filenames embed the "<trial>__control|__candidate" pairing
      convention, their trial ids must match (same matched trial/condition);
    - exactly one filename following the pairing convention is refused.
    """
    if not isinstance(instance, dict):
        return
    control = instance.get("control_file")
    candidate = instance.get("candidate_file")
    if not (isinstance(control, str) and isinstance(candidate, str)):
        return
    if control == candidate and control != PENDING:
        yield jsonschema.ValidationError(
            f"control_file and candidate_file must differ once resolved; "
            f"got {control!r} for both (a specimen would be compared "
            f"against itself)"
        )
        return
    cm = _TRIAL_PAIR_RE.match(Path(control).name)
    pm = _TRIAL_PAIR_RE.match(Path(candidate).name)
    if cm and pm and cm.group("trial") != pm.group("trial"):
        yield jsonschema.ValidationError(
            f"control_file {control!r} and candidate_file {candidate!r} "
            f"belong to different trials ({cm.group('trial')!r} vs "
            f"{pm.group('trial')!r}); matched-pair violation"
        )
    elif bool(cm) != bool(pm):
        yield jsonschema.ValidationError(
            f"only one of control_file {control!r} / candidate_file "
            f"{candidate!r} follows the '<trial>__control|__candidate' "
            f"pairing convention; matched-pair violation"
        )


def _source_pin_guard(validator, _value, instance, _schema):
    """mapping-level guard: source_manifest_sha256 must pin a live source.

    Recomputes the SHA-256 of the expected source (SKU manifest / trial
    sheet) and refuses a pin that does not match, a pin naming a source
    file that does not exist, and an explicit source_manifest_ref whose
    file is missing. Missing pins are refused by the schema's ``required``.
    """
    if not isinstance(instance, dict):
        return
    pin = instance.get("source_manifest_sha256")
    if not (isinstance(pin, str) and re.fullmatch(r"[0-9a-f]{64}", pin)):
        # Malformed pins are refused by the schema pattern; nothing further
        # to recompute here.
        return
    ref = instance.get("source_manifest_ref")
    if ref is not None:
        if not isinstance(ref, str) or ref.startswith("/") or ".." in Path(ref).parts:
            yield jsonschema.ValidationError(
                f"source_manifest_ref {ref!r} must be a repo-relative path"
            )
            return
        path = REPO_ROOT / ref
        if not path.is_file():
            yield jsonschema.ValidationError(
                f"source_manifest_ref {ref!r} does not exist; fail closed"
            )
            return
        if _sha256_file(path) != pin:
            yield jsonschema.ValidationError(
                f"source_manifest_sha256 does not match {ref!r}; "
                f"stale production mapping refused"
            )
        return
    candidates = [REPO_ROOT / rel for rel in MAPPING_SOURCE_CANDIDATES]
    existing = [p for p in candidates if p.is_file()]
    if not existing:
        yield jsonschema.ValidationError(
            "no mapping source file exists (expected one of "
            f"{list(MAPPING_SOURCE_CANDIDATES)}); fail closed"
        )
        return
    if not any(_sha256_file(p) == pin for p in existing):
        yield jsonschema.ValidationError(
            "source_manifest_sha256 does not match any live mapping source "
            f"({[str(p.relative_to(REPO_ROOT)) for p in existing]}); "
            f"stale production mapping refused"
        )


_PrintAlphaValidator = validates("print_alpha_mapping")(
    validators.extend(
        Draft202012Validator,
        {
            "distinctFilePair": _distinct_file_pair,
            "sourcePin": _source_pin_guard,
        },
    )
)
_MAPPING_META_SCHEMA_ID = _PrintAlphaValidator.META_SCHEMA["$id"]

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
    "$schema": _MAPPING_META_SCHEMA_ID,
    "type": "object",
    "sourcePin": True,
    "required": ["schema_version", "manifest_id", "placements", "evidence_class", "physical_efficacy_claimed", "source_manifest_sha256"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "manifest_id": {"type": "string", "minLength": 1},
        "physical_efficacy_claimed": {"const": False},
        "evidence_class": {"const": "experimental_print_specimen"},
        "source_manifest_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "source_manifest_ref": {"type": "string", "minLength": 1},
        "placements": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "distinctFilePair": True,
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

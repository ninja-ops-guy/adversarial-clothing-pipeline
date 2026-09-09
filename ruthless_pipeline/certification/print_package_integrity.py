"""RAC-PRINT-ALPHA-001 package integrity: root-manifest binding.

A Print Alpha release package binds every release-relevant artifact —
candidate artwork, control artwork, calibration target, provider template,
SKU manifests, production mapping, capture protocol, trial sheet, and QA
forms — into a single deterministic root manifest. Verifying the package
recomputes each bound artifact's SHA-256; modifying (or deleting) any bound
artifact invalidates the package.

Fail-closed rules
-----------------
- Fields/artifacts that are not yet resolved are recorded with the literal
  ``PENDING_USER_ACTION`` instead of a hash. They are NEVER bound as final
  and NEVER fabricated; verification reports them as ``PENDING_USER_ACTION``
  and the package status is at best ``INCOMPLETE_PENDING_USER_ACTION``.
- ``physical_efficacy_claimed`` is always False and ``evidence_class`` is
  always ``experimental_print_specimen`` in emitted manifests.
- Serialization is canonical (sorted keys, fixed separators, trailing
  newline): same inputs -> byte-identical manifest and identical
  ``package_root_sha256``.

Statuses: ``INTACT`` (all bound artifacts match), ``TAMPERED`` (any bound
artifact hash mismatch or missing file), ``INCOMPLETE_PENDING_USER_ACTION``
(no tampering, but unresolved pending entries remain).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PENDING = "PENDING_USER_ACTION"
SCHEMA_VERSION = "1.0"
RELEASE_ID = "RAC-PRINT-ALPHA-001"

INTACT = "INTACT"
TAMPERED = "TAMPERED"
INCOMPLETE = "INCOMPLETE_PENDING_USER_ACTION"

_HEX64 = set("0123456789abcdef")


def _is_sha256(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in _HEX64 for c in value)
    )


def hash_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_bytes(payload: dict) -> bytes:
    """Canonical deterministic serialization (sorted keys, trailing \n)."""
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def bind_artifact(root: str | Path, rel_path: str, role: str) -> dict:
    """Create one binding entry. Never fabricates a hash for missing files."""
    root = Path(root)
    path = root / rel_path
    if path.is_file():
        return {
            "path": rel_path,
            "role": role,
            "sha256": hash_file(path),
            "status": "bound",
        }
    return {"path": rel_path, "role": role, "sha256": PENDING, "status": PENDING}


def bind_pending(rel_path: str, role: str) -> dict:
    """Explicitly record an unresolved artifact as PENDING_USER_ACTION."""
    return {"path": rel_path, "role": role, "sha256": PENDING, "status": PENDING}


def build_package_manifest(root: str | Path, entries: list[dict]) -> dict:
    """Build the deterministic root manifest from binding entries.

    ``entries`` come from :func:`bind_artifact` / :func:`bind_pending`.
    The ``package_root_sha256`` commits to the sorted entry list, so changing
    any path, role, status, or hash changes the root hash.
    """
    sorted_entries = sorted(entries, key=lambda e: (e["path"], e["role"]))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "release_id": RELEASE_ID,
        "physical_efficacy_claimed": False,
        "evidence_class": "experimental_print_specimen",
        "artifacts": sorted_entries,
    }
    root_hash = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
    manifest["package_root_sha256"] = root_hash
    return manifest


def verify_package(manifest: dict, root: str | Path) -> dict:
    """Verify a package root manifest against bytes on disk.

    Deterministic pure function of (manifest, filesystem). Returns a report
    dict with ``status`` in {INTACT, TAMPERED, INCOMPLETE_PENDING_USER_ACTION}.
    """
    root = Path(root)
    mismatches: list[dict] = []
    pending: list[str] = []
    verified: list[str] = []

    entries = manifest.get("artifacts", [])
    for entry in entries:
        rel = entry.get("path")
        expected = entry.get("sha256")
        status = entry.get("status")
        if expected == PENDING or status == PENDING:
            pending.append(rel)
            continue
        path = root / rel
        if not path.is_file():
            mismatches.append({"path": rel, "reason": "missing_file"})
            continue
        if not _is_sha256(expected):
            # Non-canonical, non-pending placeholder: fail closed.
            mismatches.append({"path": rel, "reason": "non_canonical_hash_field"})
            continue
        actual = hash_file(path)
        if actual != expected:
            mismatches.append(
                {"path": rel, "reason": "sha256_mismatch", "expected": expected, "actual": actual}
            )
        else:
            verified.append(rel)

    # Root-hash self-consistency: recompute over the manifest without the hash.
    root_ok = True
    if "package_root_sha256" in manifest:
        stripped = {k: v for k, v in manifest.items() if k != "package_root_sha256"}
        root_ok = (
            hashlib.sha256(canonical_bytes(stripped)).hexdigest()
            == manifest["package_root_sha256"]
        )
    else:
        root_ok = False
    if not root_ok:
        mismatches.append({"path": "<manifest>", "reason": "package_root_sha256_mismatch"})

    boundary_ok = (
        manifest.get("physical_efficacy_claimed") is False
        and manifest.get("evidence_class") == "experimental_print_specimen"
    )
    if not boundary_ok:
        mismatches.append({"path": "<manifest>", "reason": "evidence_boundary_violation"})

    if mismatches:
        status = TAMPERED
    elif pending:
        status = INCOMPLETE
    else:
        status = INTACT

    return {
        "schema_version": SCHEMA_VERSION,
        "release_id": manifest.get("release_id"),
        "status": status,
        "package_root_sha256_valid": root_ok,
        "verified_count": len(verified),
        "verified": sorted(verified),
        "pending_user_action": sorted(pending),
        "mismatches": mismatches,
        "physical_efficacy_claimed": False,
        "evidence_class": "experimental_print_specimen",
    }


# --- canonical Print Alpha binding set -------------------------------------
# Roles per release binding: candidate artwork, control artwork, calibration
# target, provider template, SKU, production mapping, capture protocol,
# trial sheet, QA forms. Anything unresolved stays PENDING_USER_ACTION.

PLACEMENTS = [
    "front",
    "back",
    "sleeve_left",
    "sleeve_right",
    "pocket",
    "hood",
    "label_panel",
    "label_inside",
]

PRINT_ALPHA_ROLES: list[tuple[str, str]] = (
    [("print-alpha/CANDIDATE/{p}.png".format(p=p), "candidate_artwork") for p in PLACEMENTS]
    + [("print-alpha/CONTROL/{p}.png".format(p=p), "control_artwork") for p in PLACEMENTS]
    + [
        ("print-alpha/CALIBRATION/calibration-target.png", "calibration_target"),
        ("print-alpha/CALIBRATION/README.md", "calibration_reference"),
        ("print-alpha/MANIFESTS/template-manifest.json", "provider_template"),
        ("print-alpha/MANIFESTS/sku-manifest.json", "sku"),
        ("print-alpha/MANIFESTS/print-alpha-manifest.json", "sku"),
        ("production_alpha/SKU_MANIFEST.json", "sku"),
        ("print-alpha/MANIFESTS/mapping-manifest.json", "production_mapping"),
        ("print-alpha/MANIFESTS/artwork-manifest.json", "production_mapping"),
        ("print-alpha/CAPTURE/capture-protocol.md", "capture_protocol"),
        ("print-alpha/CAPTURE/camera-lighting-sheet.md", "capture_protocol"),
        ("print-alpha/CAPTURE/invalid-condition-rules.json", "capture_protocol"),
        ("print-alpha/CAPTURE/trial-sheet.csv", "trial_sheet"),
        ("print-alpha/QA/chain-of-custody.md", "qa_form"),
        ("print-alpha/QA/garment-pairing-checklist.md", "qa_form"),
        ("print-alpha/QA/receipt-qa.md", "qa_form"),
        ("production_alpha/RECEIPT_QA_FORM.md", "qa_form"),
    ]
)


def build_print_alpha_manifest(root: str | Path) -> dict:
    """Bind the canonical RAC-PRINT-ALPHA-001 artifact set.

    Artwork files that do not exist yet (pre-UA-1) are recorded as
    PENDING_USER_ACTION, never bound with fabricated hashes.
    """
    entries = [bind_artifact(root, rel, role) for rel, role in PRINT_ALPHA_ROLES]
    return build_package_manifest(root, entries)

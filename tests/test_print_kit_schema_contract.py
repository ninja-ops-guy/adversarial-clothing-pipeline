"""Contract tests for the Product Studio manifest schema_version registry.

synthetic_pipeline_validation_only: every manifest exercised here is
synthetic; no real generation, capture, or held-out artifact is touched.

These tests eliminate the D2-0004 drift incident class: the print-test-kit
consumer (scripts/build_print_test_kit.js) previously hardcoded the accepted
schema_version as a JS literal, invisible to Python-side schema governance.
The accepted version now lives in a single machine-readable registry
(schemas/product_studio_manifest.contract.json) read by both sides.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "scripts" / "build_print_test_kit.js"
CONTRACT_PATH = ROOT / "schemas" / "product_studio_manifest.contract.json"
PRODUCER_PATH = ROOT / "product-studio.js"

EVIDENCE_SCOPE = "synthetic_pipeline_validation_only"


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text())


def _synthetic_manifest(schema_version: str) -> dict:
    return {
        "schema_version": schema_version,
        "evidence_scope": EVIDENCE_SCOPE,
        "product": "hoodie",
        "production_status": "digital_design_ready",
        "design": {
            "family": "machine_static",
            "seed": 7,
            "master_export_px": 4096,
        },
        "outputs": {
            "reference_board_px": [4096, 5119],
            "production_tile_px": [4096, 4096],
        },
    }


def test_contract_registry_is_well_formed():
    contract = _load_contract()
    assert contract["contract_id"] == "product_studio_manifest"
    assert isinstance(contract["accepted_schema_version"], str)
    assert contract["accepted_schema_version"]
    assert contract["compatibility_rule"] == "exact_match"
    assert contract["evidence_scope"] == EVIDENCE_SCOPE
    assert "scripts/build_print_test_kit.js" in contract["consumers"]


def test_js_consumer_has_no_hardcoded_manifest_schema_literal():
    """The manifest guard must not pin a version literal in JS source."""
    src = JS_PATH.read_text()
    guard = src[src.index("function validateStudioManifest"):]
    guard = guard[: guard.index("\nasync function")]
    assert "ACCEPTED_MANIFEST_SCHEMA_VERSION" in guard
    # No quoted semver literal may survive inside the manifest guard.
    assert not re.search(r"""['"]\d+\.\d+['"]""", guard), (
        "hardcoded schema_version literal found in validateStudioManifest"
    )
    # The version must come from the shared registry, not a local constant.
    assert "product_studio_manifest.contract.json" in src
    assert "loadAcceptedManifestSchemaVersion" in src


def test_registry_matches_python_schema_governance_and_producer():
    """Cross-language drift guard: registry == producer's emitted version."""
    accepted = _load_contract()["accepted_schema_version"]

    # Python-side schema governance must treat the registry value as a
    # fail-closed exact-match contract (schema_version.py semantics).
    from ruthless_pipeline.certification.schema_version import (
        SchemaVersionError,
        require_schema_version,
    )

    payload = {"schema_version": accepted}
    assert require_schema_version(payload, accepted, label="synthetic") is payload
    with pytest.raises(SchemaVersionError):
        require_schema_version({"schema_version": "1.3"}, accepted, label="synthetic")

    # The producer (product-studio.js) must emit exactly the registry version.
    producer_src = PRODUCER_PATH.read_text()
    emitted = re.findall(r"schema_version\s*:\s*'(\d+\.\d+)'", producer_src)
    assert emitted, "producer emits no schema_version literal"
    assert set(emitted) == {accepted}, (
        f"producer emits {set(emitted)} but registry accepts {accepted!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node runtime unavailable")
def test_js_validator_accepts_and_rejects_per_registry(tmp_path: Path):
    """Run the real JS guard: registry version accepted, 1.3 fails closed."""
    accepted = _load_contract()["accepted_schema_version"]
    accept_manifest = tmp_path / "manifest_accept.json"
    reject_manifest = tmp_path / "manifest_reject.json"
    accept_manifest.write_text(json.dumps(_synthetic_manifest(accepted)))
    legacy_version = "1.3" if accepted != "1.3" else "1.2"
    reject_manifest.write_text(json.dumps(_synthetic_manifest(legacy_version)))

    driver = """
const path = require('path');
const kit = require(process.argv[1]);
const [acceptFile, rejectFile, accepted] = process.argv.slice(2);
const cfg = { seed: 7 };
kit.validateStudioManifest(acceptFile, cfg, 'hoodie', 'machine_static');
let rejected = false;
try {
  kit.validateStudioManifest(rejectFile, cfg, 'hoodie', 'machine_static');
} catch (err) {
  rejected = true;
  if (!String(err.message).includes('schema_version')) {
    console.error('unexpected error message: ' + err.message);
    process.exit(2);
  }
}
if (!rejected) { console.error('legacy schema was not rejected'); process.exit(3); }
if (kit.ACCEPTED_MANIFEST_SCHEMA_VERSION !== accepted) {
  console.error('JS accepted version diverged from registry'); process.exit(4);
}
console.log('ok');
"""
    proc = subprocess.run(
        [
            "node",
            "-e",
            driver,
            str(JS_PATH),
            str(accept_manifest),
            str(reject_manifest),
            accepted,
        ],
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ok" in proc.stdout

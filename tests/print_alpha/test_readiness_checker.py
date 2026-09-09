"""Tests for scripts/check_print_alpha_readiness.py (RAC-PRINT-ALPHA-001).

Hard contract under test: PENDING_USER_ACTION can never become PASS/READY.
Missing physical/vendor inputs yield USER_ACTION_REQUIRED; software or
integrity failures yield NOT_READY; only a fully bound, hash-verified
package with all software checks passing yields READY_TO_ORDER.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_print_alpha_readiness.py"
sys.path.insert(0, str(REPO_ROOT))

from scripts.check_print_alpha_readiness import (  # noqa: E402
    FAIL,
    NOT_READY,
    PASS,
    PENDING,
    READY,
    USER_ACTION_REQUIRED,
    assess_readiness,
    render_report,
)

PENDING_FILES = [
    "print-alpha/MANIFESTS/print-alpha-manifest.json",
    "print-alpha/MANIFESTS/artwork-manifest.json",
    "print-alpha/MANIFESTS/template-manifest.json",
    "print-alpha/MANIFESTS/mapping-manifest.json",
    "print-alpha/MANIFESTS/sku-manifest.json",
    "print-alpha/CAPTURE/trial-sheet.csv",
    "schemas/print_alpha_manifest.schema.json",
    "scripts_print_alpha/export_trial_sheet.py",
    "ruthless_pipeline/physical_protocol.py",
]


def _make_fixture(tmp_path: Path) -> Path:
    """Minimal repo copy sufficient for assess_readiness()."""
    root = tmp_path / "repo"
    for rel in PENDING_FILES:
        src = REPO_ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return root


def _load_manifest(root: Path, name: str) -> dict:
    return json.loads((root / "print-alpha" / "MANIFESTS" / name).read_text())


def _write_manifest(root: Path, name: str, data: dict) -> None:
    (root / "print-alpha" / "MANIFESTS" / name).write_text(
        json.dumps(data, indent=2)
    )


class TestLiveRepo:
    def test_verdict_is_user_action_required(self):
        report = assess_readiness(REPO_ROOT)
        assert report["verdict"] == USER_ACTION_REQUIRED

    def test_software_ready_true(self):
        report = assess_readiness(REPO_ROOT)
        assert report["software_ready"] is True
        for name, check in report["checks"].items():
            if check["category"] == "software":
                assert check["status"] == PASS, name

    def test_vendor_inputs_pending_not_pass(self):
        report = assess_readiness(REPO_ROOT)
        assert report["vendor_template_bound"] is False
        assert report["sku_bound"] is False
        assert report["artwork_hash_verified"] is False
        for key in ("vendor_template_bound", "sku_bound", "artwork_hash_verified"):
            assert report["checks"][key]["status"] == PENDING

    def test_pending_never_promoted_to_ready(self):
        report = assess_readiness(REPO_ROOT)
        assert report["pending_user_action_fields"], "expected pending fields"
        assert report["verdict"] != READY

    def test_boundary_fields(self):
        report = assess_readiness(REPO_ROOT)
        assert report["physical_efficacy_claimed"] is False
        assert report["evidence_class"] == "experimental_print_specimen"
        assert report["schema_version"] == "1.0"
        assert report["release_id"] == "RAC-PRINT-ALPHA-001"

    def test_committed_readiness_json_matches_regeneration(self):
        committed = (
            REPO_ROOT / "artifacts" / "print-alpha" / "readiness.json"
        ).read_bytes()
        assert committed == render_report(assess_readiness(REPO_ROOT))

    def test_report_is_deterministic(self):
        assert render_report(assess_readiness(REPO_ROOT)) == render_report(
            assess_readiness(REPO_ROOT)
        )

    def test_cli_exit_code_2_and_writes_output(self, tmp_path):
        out = tmp_path / "readiness.json"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--output", str(out)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2, result.stderr
        assert json.loads(out.read_text())["verdict"] == USER_ACTION_REQUIRED


class TestFailClosed:
    def test_pending_never_becomes_pass(self, tmp_path):
        root = _make_fixture(tmp_path)
        report = assess_readiness(root)
        assert report["verdict"] == USER_ACTION_REQUIRED
        assert report["verdict"] != READY
        assert all(
            c["status"] != PASS
            for c in report["checks"].values()
            if c["category"] in ("vendor", "physical")
        )

    def test_efficacy_claim_true_is_not_ready(self, tmp_path):
        root = _make_fixture(tmp_path)
        data = _load_manifest(root, "artwork-manifest.json")
        data["physical_efficacy_claimed"] = True
        _write_manifest(root, "artwork-manifest.json", data)
        report = assess_readiness(root)
        assert report["verdict"] == NOT_READY
        assert report["checks"]["evidence_boundary"]["status"] == FAIL

    def test_noncanonical_pending_literal_is_not_ready(self, tmp_path):
        root = _make_fixture(tmp_path)
        data = _load_manifest(root, "sku-manifest.json")
        data["garments"][0]["variant_id"] = "pending_user_action"
        _write_manifest(root, "sku-manifest.json", data)
        report = assess_readiness(root)
        assert report["verdict"] == NOT_READY
        assert report["checks"]["pending_literals_canonical"]["status"] == FAIL

    def test_fabricated_hash_without_file_is_not_ready(self, tmp_path):
        root = _make_fixture(tmp_path)
        data = _load_manifest(root, "artwork-manifest.json")
        data["artworks"][0]["artwork_sha256"] = "a" * 64  # fabricated
        _write_manifest(root, "artwork-manifest.json", data)
        report = assess_readiness(root)
        assert report["verdict"] == NOT_READY
        assert report["checks"]["artwork_hash_verified"]["status"] == FAIL

    def test_missing_manifest_is_not_ready(self, tmp_path):
        root = _make_fixture(tmp_path)
        (root / "print-alpha" / "MANIFESTS" / "sku-manifest.json").unlink()
        report = assess_readiness(root)
        assert report["verdict"] == NOT_READY
        assert report["software_ready"] is False

    def test_trial_sheet_tamper_is_not_ready(self, tmp_path):
        root = _make_fixture(tmp_path)
        csv_path = root / "print-alpha" / "CAPTURE" / "trial-sheet.csv"
        rows = csv_path.read_text().splitlines(keepends=True)
        csv_path.write_text("".join(rows[:-1]))  # drop a row -> 107 + drift
        report = assess_readiness(root)
        assert report["verdict"] == NOT_READY
        assert report["checks"]["trial_geometry_108"]["status"] == FAIL
        assert report["checks"]["trial_sheet_deterministic"]["status"] == FAIL

    def test_frozen_schema_violation_is_not_ready(self, tmp_path):
        root = _make_fixture(tmp_path)
        data = _load_manifest(root, "print-alpha-manifest.json")
        data["evidence_class"] = "internally_measured"  # forbidden promotion
        _write_manifest(root, "print-alpha-manifest.json", data)
        report = assess_readiness(root)
        assert report["verdict"] == NOT_READY
        assert report["checks"]["frozen_schema_conformity"]["status"] == FAIL


class TestFullyBoundPackage:
    """A fully resolved, hash-true fixture must reach READY_TO_ORDER."""

    def test_ready_to_order(self, tmp_path):
        import hashlib

        root = _make_fixture(tmp_path)

        template = _load_manifest(root, "template-manifest.json")
        template["template_archive_sha256"] = hashlib.sha256(b"tpl").hexdigest()
        for panel in template["panel_geometry"].values():
            panel["width_mm"] = 500.0
            panel["height_mm"] = 600.0
            panel["dpi"] = 150
        _write_manifest(root, "template-manifest.json", template)

        sku = _load_manifest(root, "sku-manifest.json")
        for garment in sku["garments"]:
            garment["variant_id"] = 12345
            garment["size"] = "L"
        _write_manifest(root, "sku-manifest.json", sku)

        primary = _load_manifest(root, "print-alpha-manifest.json")
        primary["garment"]["size"] = "L"
        primary["garment"]["print_technology"] = "sublimation"
        primary["garment"]["printer_vendor"] = "Printful"
        _write_manifest(root, "print-alpha-manifest.json", primary)

        artwork = _load_manifest(root, "artwork-manifest.json")
        for entry in artwork["artworks"]:
            payload = f"art:{entry['role']}:{entry['placement']}".encode()
            dest = root / entry["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
            entry["artwork_sha256"] = hashlib.sha256(payload).hexdigest()
        _write_manifest(root, "artwork-manifest.json", artwork)

        mapping = _load_manifest(root, "mapping-manifest.json")
        for placement in mapping["placements"]:
            placement["control_file"] = (
                f"print-alpha/CONTROL/{placement['placement']}.png"
            )
            placement["candidate_file"] = (
                f"print-alpha/CANDIDATE/{placement['placement']}.png"
            )
        _write_manifest(root, "mapping-manifest.json", mapping)

        report = assess_readiness(root)
        assert report["verdict"] == READY
        assert report["software_ready"] is True
        assert report["vendor_template_bound"] is True
        assert report["sku_bound"] is True
        assert report["artwork_hash_verified"] is True
        assert report["physical_efficacy_claimed"] is False

    def test_ready_package_tampered_artwork_drops_to_not_ready(self, tmp_path):
        import hashlib

        root = _make_fixture(tmp_path)
        template = _load_manifest(root, "template-manifest.json")
        template["template_archive_sha256"] = hashlib.sha256(b"tpl").hexdigest()
        _write_manifest(root, "template-manifest.json", template)
        sku = _load_manifest(root, "sku-manifest.json")
        for garment in sku["garments"]:
            garment["variant_id"] = 1
            garment["size"] = "M"
        _write_manifest(root, "sku-manifest.json", sku)
        primary = _load_manifest(root, "print-alpha-manifest.json")
        primary["garment"]["size"] = "M"
        primary["garment"]["print_technology"] = "sublimation"
        primary["garment"]["printer_vendor"] = "Printful"
        _write_manifest(root, "print-alpha-manifest.json", primary)
        artwork = _load_manifest(root, "artwork-manifest.json")
        for entry in artwork["artworks"]:
            payload = entry["file"].encode()
            dest = root / entry["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
            entry["artwork_sha256"] = hashlib.sha256(payload).hexdigest()
        _write_manifest(root, "artwork-manifest.json", artwork)

        assert assess_readiness(root)["verdict"] == READY
        # Tamper with one bound artwork byte.
        target = root / artwork["artworks"][0]["file"]
        target.write_bytes(target.read_bytes() + b"x")
        report = assess_readiness(root)
        assert report["verdict"] == NOT_READY
        assert report["checks"]["artwork_hash_verified"]["status"] == FAIL


@pytest.mark.parametrize("name", ["readiness.json"])
def test_readiness_json_is_valid_schema_versioned(name):
    data = json.loads(
        (REPO_ROOT / "artifacts" / "print-alpha" / name).read_text()
    )
    assert data["schema_version"] == "1.0"
    assert data["verdict"] in (READY, NOT_READY, USER_ACTION_REQUIRED)

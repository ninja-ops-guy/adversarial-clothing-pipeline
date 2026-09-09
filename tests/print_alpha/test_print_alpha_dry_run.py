"""Contract tests for the RAC-PRINT-ALPHA-001 release dry run.

Covers:
- the dry run completes with no FAILED stages (PENDING stages are expected
  pre-order and must NOT fail the run);
- the report is byte-deterministic across runs;
- physical_test_executed and physical_efficacy_claimed are false everywhere;
- every unresolved manifest field remains the literal PENDING_USER_ACTION
  (fail-closed preservation — never fabricated, never silently resolved);
- the release package is SHA-256-addressed and matches the on-disk manifests;
- the trial sheet stage verifies byte identity with the committed CSV.

Runs the dry run into a pytest tmp_path so the repo tree is untouched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts_print_alpha" / "print_alpha_dry_run.py"
MANIFEST_DIR = REPO_ROOT / "print-alpha" / "MANIFESTS"
PENDING = "PENDING_USER_ACTION"

MANIFEST_FILES = [
    "print-alpha-manifest.json",
    "artwork-manifest.json",
    "template-manifest.json",
    "mapping-manifest.json",
    "sku-manifest.json",
]


def _run(out_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(out_dir), *extra],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


@pytest.fixture(scope="module")
def dry_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("dry-run")
    proc = _run(out)
    assert proc.returncode == 0, proc.stderr
    report = json.loads((out / "dry-run-report.json").read_text())
    return out, report


class TestDryRunContract:
    def test_no_failed_stages(self, dry_run):
        _, report = dry_run
        assert report["failed_stages"] == []
        assert report["overall_status"] in {"OK", PENDING}

    def test_pending_stages_preserved_not_failed(self, dry_run):
        _, report = dry_run
        # Vendor-gated stages must surface as PENDING, never as pass or fail.
        assert "pending_scan" in report["pending_stages"]
        assert report["stages"]["pending_scan"]["total_pending_fields"] > 0
        assert report["stages"]["release_package"]["release_ready"] is False

    def test_evidence_boundary_flags(self, dry_run):
        _, report = dry_run
        assert report["physical_test_executed"] is False
        assert report["physical_efficacy_claimed"] is False
        pkg = report["stages"]["release_package"]
        assert pkg["physical_test_executed"] is False
        assert pkg["physical_efficacy_claimed"] is False

    def test_determinism(self, dry_run, tmp_path):
        out1, report1 = dry_run
        out2 = tmp_path / "second"
        proc = _run(out2)
        assert proc.returncode == 0, proc.stderr
        assert (out1 / "dry-run-report.json").read_bytes() == (
            out2 / "dry-run-report.json"
        ).read_bytes()
        assert (out1 / "release-package" / "RELEASE_PACKAGE.json").read_bytes() == (
            out2 / "release-package" / "RELEASE_PACKAGE.json"
        ).read_bytes()

    def test_strict_mode_exits_2_on_pending(self, tmp_path):
        proc = _run(tmp_path / "strict", "--strict")
        assert proc.returncode == 2

    def test_trial_sheet_byte_identity(self, dry_run):
        _, report = dry_run
        stage = report["stages"]["trial_sheet"]
        assert stage["status"] == "OK"
        assert stage["rows"] == 108
        assert stage["byte_identical_to_committed"] is True

    def test_calibration_fabrication_stays_pending(self, dry_run):
        out, report = dry_run
        stage = report["stages"]["calibration_reference"]
        assert stage["status"] == "OK"
        assert stage["physical_fabrication_status"] == PENDING
        assert stage["fabrication_pending_preserved"] is True
        manifest = json.loads(
            (out / "calibration-target" / "calibration-target-manifest.json").read_text()
        )
        assert manifest["evidence_class"] == "generated_digital_reference"
        assert manifest["physical_fabrication"]["status"] == PENDING

    def test_release_package_hashes_match_files(self, dry_run):
        out, _ = dry_run
        pkg_dir = out / "release-package"
        pkg = json.loads((pkg_dir / "RELEASE_PACKAGE.json").read_text())
        assert pkg["physical_test_executed"] is False
        assert pkg["physical_efficacy_claimed"] is False
        import hashlib

        for entry in pkg["contents"]:
            data = (pkg_dir / entry["path"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == entry["sha256"]
            assert len(data) == entry["bytes"]

    def test_packaged_manifests_byte_identical_to_repo(self, dry_run):
        out, _ = dry_run
        for name in MANIFEST_FILES:
            assert (out / "release-package" / "manifests" / name).read_bytes() == (
                MANIFEST_DIR / name
            ).read_bytes()

    def test_pending_scan_covers_repo_manifests(self, dry_run):
        """Every PENDING string in the repo manifests appears in the scan."""

        def _paths(node, path="$"):
            if isinstance(node, dict):
                for key in sorted(node):
                    yield from _paths(node[key], f"{path}.{key}")
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    yield from _paths(value, f"{path}[{i}]")
            elif node == PENDING:
                yield path

        _, report = dry_run
        scan = report["stages"]["pending_scan"]["pending_by_manifest"]
        for name in MANIFEST_FILES:
            repo_pending = sorted(_paths(json.loads((MANIFEST_DIR / name).read_text())))
            assert scan[name] == repo_pending

    def test_simulated_external_tools_recorded(self, dry_run):
        _, report = dry_run
        tools = {t["tool"]: t for t in report["simulated_external_tools"]}
        assert tools["scripts/check_print_alpha_readiness.py"]["status"] == "SIMULATED_NOT_PRESENT"
        assert tools["scripts/print_package_integrity.py"]["status"] == "SIMULATED_NOT_PRESENT"

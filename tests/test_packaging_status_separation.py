"""Tests for prospective packaging-status separation (status format 1.0).

synthetic_pipeline_validation_only: all status payloads exercised here are
synthetic. The sealed D2-0004 record (root d2-latest-status.json) is
immutable; it is only read for a byte-identical regression/integrity check.

Incident class prevented: a downstream print-test-kit (packaging) failure
making a sealed, closed scientific experiment look unresolved because the
status artifact had no machine-readable packaging channel.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
D2_STATUS_PATH = ROOT / "d2-latest-status.json"

from ruthless_pipeline.certification.experiment_status import (
    D2_STATUS_SCHEMA_VERSION,
    PACKAGING_COMPLETE,
    PACKAGING_FAILED,
    PACKAGING_NOT_ATTEMPTED,
    PACKAGING_PENDING,
    SCIENTIFIC_FIELDS,
    is_legacy_status,
    make_packaging_block,
    read_d2_status,
    with_packaging,
    write_d2_status,
)
from ruthless_pipeline.certification.schema_version import SchemaVersionError

EVIDENCE_SCOPE = "synthetic_pipeline_validation_only"

# Byte-identical integrity pin for the sealed D2-0004 record (legacy format).
D2_0004_STATUS_SHA256 = "d761fd947342cca722e6820e9beed0f78b925638e02389c4487e4061f59db4b9"


def _sealed_scientific_status() -> dict:
    """Synthetic sealed scientific record (legacy shape, pre-packaging)."""
    return {
        "bundle_verified": True,
        "candidate_id": "RAC-PER-SYNTH-0000",
        "certificate_id": "RAC-PER-SYNTH-0000-1.0.0-1.0",
        "decision": "FAIL",
        "evidence_state": "RAC-D0",
        "heldout": {"n": 36, "valid_n": 36, "mean_delta": -0.1},
        "heldout_model_set": "SYNTH-HO",
        "invalid_condition_fraction": 0.0,
        "protocol_id": "RAC-SYNTH",
        "protocol_version": "1.0",
        "source_commit": "0" * 40,
        "surrogate_model_set": "SYNTH-SUR",
        "verification_failures": [],
        "evidence_scope": EVIDENCE_SCOPE,
    }


def _snapshot_scientific(status: dict) -> dict:
    return {k: status[k] for k in SCIENTIFIC_FIELDS if k in status}


def test_d2_0004_status_file_is_byte_identical_legacy_and_readable():
    """Regression: the sealed D2-0004 record is untouched and still parses."""
    raw = D2_STATUS_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == D2_0004_STATUS_SHA256, (
        "sealed D2-0004 status record changed; it is immutable by design"
    )
    status = read_d2_status(D2_STATUS_PATH)
    assert is_legacy_status(status)
    assert status["candidate_id"] == "RAC-PER-D2-0004"
    assert status["decision"] == "FAIL"
    assert status["evidence_state"] == "RAC-D0"
    assert "packaging" not in status


def test_packaging_crash_leaves_scientific_record_intact(tmp_path: Path):
    """Sealed science + packaging crash -> FAILED block, science unchanged."""
    sealed = _sealed_scientific_status()
    before = _snapshot_scientific(sealed)

    updated = with_packaging(sealed, PACKAGING_FAILED, "simulated print-kit crash")
    assert updated["schema_version"] == D2_STATUS_SCHEMA_VERSION
    assert updated["packaging"] == {
        "production_packaging_status": PACKAGING_FAILED,
        "packaging_failure_detail": "simulated print-kit crash",
        "scientific_result_independent_of_packaging": True,
    }
    assert _snapshot_scientific(updated) == before
    # The original sealed payload object is not mutated in place.
    assert "packaging" not in sealed

    path = tmp_path / "status.json"
    write_d2_status(path, updated)
    reread = read_d2_status(path)
    assert _snapshot_scientific(reread) == before
    assert reread["packaging"]["production_packaging_status"] == PACKAGING_FAILED


def test_packaging_success_marks_complete(tmp_path: Path):
    sealed = _sealed_scientific_status()
    updated = with_packaging(sealed, PACKAGING_COMPLETE)
    assert updated["packaging"]["production_packaging_status"] == PACKAGING_COMPLETE
    assert updated["packaging"]["packaging_failure_detail"] is None
    assert _snapshot_scientific(updated) == _snapshot_scientific(sealed)


def test_packaging_block_validation():
    assert make_packaging_block()["production_packaging_status"] == PACKAGING_NOT_ATTEMPTED
    assert make_packaging_block(PACKAGING_PENDING)["packaging_failure_detail"] is None
    with pytest.raises(ValueError):
        make_packaging_block("BOGUS")
    with pytest.raises(ValueError):
        make_packaging_block(PACKAGING_FAILED)  # detail required
    with pytest.raises(ValueError):
        make_packaging_block(PACKAGING_COMPLETE, "detail without failure")


def test_reader_rejects_unknown_future_versions(tmp_path: Path):
    payload = _sealed_scientific_status()
    payload["schema_version"] = "9.9"
    path = tmp_path / "status.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(SchemaVersionError):
        read_d2_status(path)


def test_packaging_writer_script_records_failed_and_complete(tmp_path: Path):
    """End-to-end through the packaging CLI on synthetic inputs."""
    status_path = tmp_path / "d2-latest-status.json"
    write_d2_status(status_path, with_packaging(_sealed_scientific_status(), PACKAGING_NOT_ATTEMPTED))
    before = _snapshot_scientific(read_d2_status(status_path))

    script = ROOT / "scripts" / "package_print_test_kit.py"

    def invoke(extra: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(script),
                "--kit-dir",
                str(tmp_path / "kit"),
                "--d2-status",
                str(status_path),
                "--zip",
                str(tmp_path / "kit.zip"),
                *extra,
            ],
            text=True,
            capture_output=True,
            cwd=tmp_path,
        )

    # Crash path: the print-kit build never ran, so packaging aborts.
    proc = invoke([])
    assert proc.returncode != 0
    status = read_d2_status(status_path)
    assert status["packaging"]["production_packaging_status"] == PACKAGING_FAILED
    assert status["packaging"]["packaging_failure_detail"]
    assert _snapshot_scientific(status) == before

    # Success path: synthesize a minimal verified kit and evidence sources.
    kit = tmp_path / "kit"
    (kit / "design").mkdir(parents=True)
    (kit / "design" / "candidate-config.json").write_text(
        json.dumps({"candidate_id": "RAC-PER-SYNTH-0000", "family": "machine_static"})
    )
    (kit / "export-verification.json").write_text(
        json.dumps(
            {
                "status": "digital_print_assets_verified",
                "primary_product": "hoodie",
                "pattern_tile": {"sha256": "a" * 64},
                "mockups": {},
            }
        )
    )
    (tmp_path / "benchmark-results.json").write_text(json.dumps({"status": "measured_locked"}))
    (tmp_path / "surrogate-selection.json").write_text(json.dumps({"selected": "synthetic"}))
    (tmp_path / "model_manifest.json").write_text(json.dumps({"models": []}))
    (tmp_path / "protocol.md").write_text("synthetic protocol\n")
    proc = invoke(
        [
            "--benchmark", str(tmp_path / "benchmark-results.json"),
            "--selection", str(tmp_path / "surrogate-selection.json"),
            "--model-manifest", str(tmp_path / "model_manifest.json"),
            "--protocol", str(tmp_path / "protocol.md"),
        ]
    )
    assert proc.returncode == 0, proc.stderr
    status = read_d2_status(status_path)
    assert status["packaging"]["production_packaging_status"] == PACKAGING_COMPLETE
    assert status["packaging"]["packaging_failure_detail"] is None
    assert _snapshot_scientific(status) == before

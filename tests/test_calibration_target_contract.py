"""Wave I item 10 tests: digital calibration-target contract.

Covers the requirements the Wave F generator did not yet bind:
- determinism: two runs produce byte-identical PNG output (same sha256);
- manifest hash verification: generator-code sha256 and PNG sha256
  recompute exactly (and tampering is detected);
- promotion guard: the manifest can never carry a measured evidence class
  until a future measured-ingestion step exists;
- physical fabrication remains PENDING_USER_ACTION (an open USER ACTION).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.generate_calibration_target import TARGET_ID, generate

from ruthless_pipeline.certification.calibration_target import (
    EVIDENCE_CLASS_GENERATED,
    FABRICATION_PENDING,
    GENERATOR_PATH,
    MANIFEST_FILENAME,
    MANIFEST_SCHEMA_VERSION,
    MEASURED_EVIDENCE_CLASSES,
    CalibrationTargetManifestError,
    generator_code_sha256,
    validate_manifest,
    verify_manifest,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_generation_is_deterministic_identical_png_sha256(tmp_path: Path) -> None:
    a = generate(tmp_path / "run_a")
    b = generate(tmp_path / "run_b")
    assert a["png_sha256"] == b["png_sha256"]
    assert (tmp_path / "run_a" / a["png_file"]).read_bytes() == (
        tmp_path / "run_b" / b["png_file"]
    ).read_bytes()
    # Manifests are identical too (canonical JSON, no timestamps).
    assert a == b


def test_manifest_hash_verification_roundtrip(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    verified = verify_manifest(tmp_path / MANIFEST_FILENAME, REPO_ROOT)
    assert verified == manifest
    # Generator binding recomputes against the committed script.
    assert manifest["generator"]["path"] == GENERATOR_PATH
    assert manifest["generator"]["sha256"] == generator_code_sha256(REPO_ROOT)
    assert manifest["generator"]["sha256"] == hashlib.sha256(
        (REPO_ROOT / GENERATOR_PATH).read_bytes()
    ).hexdigest()
    # Output image binding recomputes.
    png = tmp_path / manifest["png_file"]
    assert hashlib.sha256(png.read_bytes()).hexdigest() == manifest["png_sha256"]


def test_manifest_verification_detects_png_tampering(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    png = tmp_path / manifest["png_file"]
    png.write_bytes(png.read_bytes() + b"tampered")
    with pytest.raises(CalibrationTargetManifestError, match="png_sha256 mismatch"):
        verify_manifest(tmp_path / MANIFEST_FILENAME, REPO_ROOT)


def test_manifest_verification_detects_generator_mismatch(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    manifest["generator"]["sha256"] = "0" * 64
    (tmp_path / MANIFEST_FILENAME).write_text(json.dumps(manifest))
    with pytest.raises(CalibrationTargetManifestError, match="generator.sha256 mismatch"):
        verify_manifest(tmp_path / MANIFEST_FILENAME, REPO_ROOT)


@pytest.mark.parametrize("measured_class", MEASURED_EVIDENCE_CLASSES)
def test_promotion_guard_rejects_measured_evidence_class(
    tmp_path: Path, measured_class: str
) -> None:
    manifest = generate(tmp_path)
    manifest["evidence_class"] = measured_class
    with pytest.raises(CalibrationTargetManifestError, match="measured"):
        validate_manifest(manifest)


def test_promotion_guard_rejects_unknown_evidence_class(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    manifest["evidence_class"] = "published_observation"
    with pytest.raises(CalibrationTargetManifestError, match="evidence_class"):
        validate_manifest(manifest)


def test_manifest_is_generated_only_and_fabrication_pending(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["target_id"] == TARGET_ID
    assert manifest["evidence_class"] == EVIDENCE_CLASS_GENERATED
    # No legacy measured label may survive on the manifest.
    assert "evidence_label" not in manifest
    assert manifest["physical_fabrication"]["status"] == FABRICATION_PENDING


def test_fabrication_status_cannot_be_marked_complete(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    for forbidden in ("FABRICATED", "COMPLETE", "DONE", "measured"):
        manifest["physical_fabrication"]["status"] = forbidden
        with pytest.raises(CalibrationTargetManifestError, match="USER ACTION"):
            validate_manifest(manifest)


def test_parameters_block_binds_grid_geometry(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    params = manifest["parameters"]
    assert params["grid_rows"] * params["grid_cols"] == len(manifest["patches"])
    assert params["dpi"] == manifest["dpi"] == 300

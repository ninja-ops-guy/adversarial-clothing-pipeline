"""Digital calibration-target contract for RAC-CALT-P1-0001 (Wave I, item 10).

Production Alpha tracks the calibration target RAC-CALT-P1-0001 as an open
USER ACTION (physical fabrication). This module is the digital side of that
tracking: it defines the schema-versioned manifest contract that binds the
*exact digital source* of the printed target so the physical print can later
be measured against it, and it guards the evidence boundary:

- The target is a **generated digital reference**. Its manifest carries
  ``evidence_class: "generated_digital_reference"`` — never a measured
  class. Nothing here measures anything; no print, photograph, or Delta-E
  reading exists until the physical P1 session runs.
- ``physical_fabrication.status`` is ``PENDING_USER_ACTION``. The physical
  step (print at 100 % scale, photograph under the locked P1 rig) stays a
  USER ACTION; this module must not print, fabricate, or simulate capture.
- Promotion guard: a manifest whose ``evidence_class`` is a measured class
  (``measured`` / ``internally_measured``) is rejected. A measured class can
  only appear once a future measured-ingestion step exists (the P1 session
  calibration-capture path in
  ``ruthless_pipeline.certification.calibration_ingest``), and that step
  will mint a *new* artifact rather than mutating this one.

The generator itself lives in ``scripts/generate_calibration_target.py``
(Wave F); it renders the deterministic PNG and emits the manifest validated
here. Stdlib-only. Canonical JSON conventions (sort_keys, compact
separators, trailing newline).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "ALLOWED_EVIDENCE_CLASSES",
    "ALLOWED_FABRICATION_STATUSES",
    "EVIDENCE_CLASS_GENERATED",
    "FABRICATION_PENDING",
    "GENERATOR_PATH",
    "MANIFEST_FILENAME",
    "MANIFEST_SCHEMA_VERSION",
    "MEASURED_EVIDENCE_CLASSES",
    "TARGET_ID",
    "CalibrationTargetManifestError",
    "generator_code_sha256",
    "validate_manifest",
    "verify_manifest",
]

#: The single calibration target tracked by Production Alpha.
TARGET_ID = "RAC-CALT-P1-0001"

#: Schema version of the calibration-target manifest (1.1 added the
#: generator-binding, parameters, evidence_class and physical_fabrication
#: blocks on top of the Wave F 1.0 geometry manifest).
MANIFEST_SCHEMA_VERSION = "1.1"

#: Manifest filename written next to the PNG by the generator.
MANIFEST_FILENAME = "calibration-target-manifest.json"

#: Repo-relative path of the generator script the manifest binds by sha256.
GENERATOR_PATH = "scripts/generate_calibration_target.py"

#: The only evidence class a digital-source manifest may carry: the target
#: is generated, not measured.
EVIDENCE_CLASS_GENERATED = "generated_digital_reference"
ALLOWED_EVIDENCE_CLASSES: tuple[str, ...] = (EVIDENCE_CLASS_GENERATED,)

#: Measured evidence classes. A calibration-target manifest may NEVER carry
#: one of these: there is no measured-ingestion step for the target yet
#: (the future P1 calibration capture will be ingested via
#: calibration_ingest.PrintCameraProfile, a separate artifact).
MEASURED_EVIDENCE_CLASSES: tuple[str, ...] = ("measured", "internally_measured")

#: Physical fabrication of the printed target is an open USER ACTION.
FABRICATION_PENDING = "PENDING_USER_ACTION"
ALLOWED_FABRICATION_STATUSES: tuple[str, ...] = (FABRICATION_PENDING,)

#: Parameter keys the manifest must bind (mirrors the generator constants).
REQUIRED_PARAMETER_KEYS: tuple[str, ...] = (
    "dpi",
    "grid_rows",
    "grid_cols",
    "patch_mm",
    "patch_gap_mm",
    "margin_mm",
    "scale_bar_mm",
    "scale_bar_height_mm",
    "fiducial_radius_mm",
)


class CalibrationTargetManifestError(ValueError):
    """Raised when a calibration-target manifest violates the contract."""


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def generator_code_sha256(repo_root: str | Path) -> str:
    """SHA-256 of the generator script source at ``GENERATOR_PATH``."""
    path = Path(repo_root) / GENERATOR_PATH
    if not path.is_file():
        raise CalibrationTargetManifestError(f"generator script missing: {GENERATOR_PATH}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    """Fail-closed validation of one calibration-target manifest mapping.

    Checks the schema version, target id, generator binding shape, parameter
    binding, PNG hash shape, the physical-fabrication USER-ACTION status,
    and — critically — that the evidence class is generated-only. Any
    measured evidence class is rejected: promotion to measured requires a
    future measured-ingestion step that does not exist yet.
    """
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise CalibrationTargetManifestError(
            f"schema_version must be {MANIFEST_SCHEMA_VERSION!r}: "
            f"{manifest.get('schema_version')!r}"
        )
    if manifest.get("target_id") != TARGET_ID:
        raise CalibrationTargetManifestError(
            f"target_id must be {TARGET_ID!r}: {manifest.get('target_id')!r}"
        )

    # Promotion guard: generated-only evidence class.
    evidence_class = manifest.get("evidence_class")
    if evidence_class in MEASURED_EVIDENCE_CLASSES:
        raise CalibrationTargetManifestError(
            f"evidence_class {evidence_class!r} is a measured class: the "
            "digital calibration target can never carry measured evidence "
            "until a measured-ingestion step exists (future P1 calibration "
            "capture via calibration_ingest); this manifest is the generated "
            "digital source only"
        )
    if evidence_class not in ALLOWED_EVIDENCE_CLASSES:
        raise CalibrationTargetManifestError(
            f"evidence_class must be one of {ALLOWED_EVIDENCE_CLASSES}: "
            f"{evidence_class!r}"
        )

    # Physical fabrication stays an open USER ACTION.
    fabrication = manifest.get("physical_fabrication")
    if not isinstance(fabrication, Mapping):
        raise CalibrationTargetManifestError("physical_fabrication block is required")
    status = fabrication.get("status")
    if status not in ALLOWED_FABRICATION_STATUSES:
        raise CalibrationTargetManifestError(
            f"physical_fabrication.status must be one of "
            f"{ALLOWED_FABRICATION_STATUSES}: {status!r} — fabrication is an "
            "open USER ACTION and cannot be marked complete by the digital side"
        )

    # Generator code binding.
    generator = manifest.get("generator")
    if not isinstance(generator, Mapping):
        raise CalibrationTargetManifestError("generator block is required")
    if generator.get("path") != GENERATOR_PATH:
        raise CalibrationTargetManifestError(
            f"generator.path must be {GENERATOR_PATH!r}: {generator.get('path')!r}"
        )
    if not _is_sha256(generator.get("sha256")):
        raise CalibrationTargetManifestError(
            "generator.sha256 must be a 64-hex SHA-256 of the generator source"
        )

    # Parameter binding.
    parameters = manifest.get("parameters")
    if not isinstance(parameters, Mapping):
        raise CalibrationTargetManifestError("parameters block is required")
    missing = [key for key in REQUIRED_PARAMETER_KEYS if key not in parameters]
    if missing:
        raise CalibrationTargetManifestError(
            f"parameters missing required keys: {missing}"
        )

    # Output image binding.
    if not isinstance(manifest.get("png_file"), str) or not manifest["png_file"]:
        raise CalibrationTargetManifestError("png_file is required")
    if not _is_sha256(manifest.get("png_sha256")):
        raise CalibrationTargetManifestError(
            "png_sha256 must be a 64-hex SHA-256 of the rendered PNG"
        )

    # Geometry payload sanity (the digital source the print is measured against).
    patches = manifest.get("patches")
    grid = manifest.get("grid")
    if not isinstance(grid, Mapping) or not isinstance(patches, list):
        raise CalibrationTargetManifestError("grid and patches blocks are required")
    expected = int(grid["rows"]) * int(grid["cols"])
    if len(patches) != expected:
        raise CalibrationTargetManifestError(
            f"patch count {len(patches)} does not match grid {expected}"
        )
    if not isinstance(manifest.get("fiducials"), list) or len(manifest["fiducials"]) != 4:
        raise CalibrationTargetManifestError("exactly four fiducials are required")


def verify_manifest(manifest_path: str | Path, repo_root: str | Path) -> dict:
    """Load, validate, and recompute every hash binding in a manifest.

    Recomputes (1) the PNG sha256 against the image next to the manifest and
    (2) the generator-code sha256 against ``repo_root / GENERATOR_PATH``.
    Returns the validated manifest. Any mismatch raises
    :class:`CalibrationTargetManifestError`.
    """
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    validate_manifest(manifest)

    png_path = manifest_path.parent / manifest["png_file"]
    if not png_path.is_file():
        raise CalibrationTargetManifestError(f"PNG missing: {png_path}")
    actual_png = hashlib.sha256(png_path.read_bytes()).hexdigest()
    if actual_png != manifest["png_sha256"]:
        raise CalibrationTargetManifestError(
            f"png_sha256 mismatch: manifest {manifest['png_sha256']} != recomputed {actual_png}"
        )

    actual_generator = generator_code_sha256(repo_root)
    if actual_generator != manifest["generator"]["sha256"]:
        raise CalibrationTargetManifestError(
            "generator.sha256 mismatch: the manifest was not produced by the "
            f"committed generator {GENERATOR_PATH} "
            f"(manifest {manifest['generator']['sha256']} != recomputed {actual_generator})"
        )
    return manifest

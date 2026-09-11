"""Hash-bound artifact manifests for governed pattern candidate exports.

The core generator candidate record hashes the in-memory RGB array. Product
surfaces, however, consume an encoded image artifact. This module binds those
two layers without changing the scientific meaning of either hash:

* ``pattern_sha256`` remains the raw generated-array hash from ``to_candidate``.
* ``artifact_sha256`` is the exact encoded artifact byte hash consumed by Studio.

The manifest is deliberately fail-closed and does not claim physical efficacy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ruthless_pipeline.pattern_genome.canonical import sha256_bytes

from .base import GeneratedPattern

SCHEMA_VERSION = "rac_pattern_candidate_artifact/v1"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class PatternArtifactManifestError(ValueError):
    """Artifact manifest is incomplete, inconsistent, or tampered with."""


def _require_hex64(value: Any, field: str) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise PatternArtifactManifestError(f"{field} must be a 64-character lowercase hex SHA-256")
    return text


def build_candidate_artifact_manifest(
    pattern: GeneratedPattern,
    *,
    research_family: str,
    artifact_bytes: bytes,
    artifact_filename: str,
    artifact_media_type: str = "image/png",
) -> dict[str, Any]:
    """Bind a generated candidate record to the exact encoded artifact bytes.

    ``research_family`` must match the generator's registered name. The current
    Product Studio contract accepts PNG artifacts only so browser decoding and
    byte-hash verification are deterministic and unambiguous.
    """
    family = str(research_family or "").strip()
    if not family:
        raise PatternArtifactManifestError("research_family is required")
    if family != pattern.generator_name:
        raise PatternArtifactManifestError(
            f"research_family {family!r} does not match generator {pattern.generator_name!r}"
        )

    filename = str(artifact_filename or "").strip()
    if not filename or Path(filename).name != filename:
        raise PatternArtifactManifestError("artifact_filename must be a non-empty basename")

    raw = bytes(artifact_bytes)
    if artifact_media_type != "image/png":
        raise PatternArtifactManifestError("artifact_media_type must be image/png")
    if not raw.startswith(PNG_SIGNATURE):
        raise PatternArtifactManifestError("artifact bytes do not have a PNG signature")

    candidate = pattern.to_candidate()
    return {
        "schema_version": SCHEMA_VERSION,
        "research_family": family,
        **candidate,
        "artifact_filename": filename,
        "artifact_media_type": artifact_media_type,
        "artifact_sha256": sha256_bytes(raw),
    }


def verify_candidate_artifact_manifest(
    manifest: Mapping[str, Any],
    artifact_bytes: bytes,
    *,
    expected_family: str | None = None,
) -> bool:
    """Fail closed unless a candidate manifest binds to these exact bytes."""
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise PatternArtifactManifestError("unsupported artifact manifest schema_version")

    family = str(manifest.get("research_family") or "")
    generator = str(manifest.get("generator") or "")
    if not family or generator != family:
        raise PatternArtifactManifestError("generator must equal research_family")
    if expected_family is not None and family != expected_family:
        raise PatternArtifactManifestError("manifest research_family does not match expected family")

    if manifest.get("artifact_media_type") != "image/png":
        raise PatternArtifactManifestError("artifact_media_type must be image/png")
    raw = bytes(artifact_bytes)
    if not raw.startswith(PNG_SIGNATURE):
        raise PatternArtifactManifestError("artifact bytes do not have a PNG signature")
    if _require_hex64(manifest.get("artifact_sha256"), "artifact_sha256") != sha256_bytes(raw):
        raise PatternArtifactManifestError("artifact_sha256 does not match artifact bytes")

    _require_hex64(manifest.get("pattern_sha256"), "pattern_sha256")
    _require_hex64(manifest.get("provenance_hash"), "provenance_hash")
    if not str(manifest.get("candidate_id") or "").startswith("RAC-PAT-CAND-"):
        raise PatternArtifactManifestError("candidate_id is missing or invalid")
    if not str(manifest.get("generator_version") or "").strip():
        raise PatternArtifactManifestError("generator_version is required")
    if manifest.get("evidence_class") != "digital_candidate":
        raise PatternArtifactManifestError("evidence_class must be digital_candidate")
    if manifest.get("physical_efficacy_claimed") is not False:
        raise PatternArtifactManifestError("physical_efficacy_claimed must be false")
    if manifest.get("claim_state") != "EXPLORATORY":
        raise PatternArtifactManifestError("claim_state must be EXPLORATORY")
    if not isinstance(manifest.get("params"), Mapping):
        raise PatternArtifactManifestError("params must be present")

    filename = str(manifest.get("artifact_filename") or "")
    if not filename or Path(filename).name != filename:
        raise PatternArtifactManifestError("artifact_filename must be a non-empty basename")
    return True

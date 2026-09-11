from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.patterns.artifact_manifest import (
    PatternArtifactManifestError,
    build_candidate_artifact_manifest,
    verify_candidate_artifact_manifest,
)
from ruthless_pipeline.patterns.base import GeneratedPattern, GeneratorParams


TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000f5d49a73"
    "0000001649444154789c63145070606060606260606060600000053a00745ed4a1"
    "d10000000049454e44ae426082"
)


def _pattern() -> GeneratedPattern:
    params = GeneratorParams(
        seed=7,
        mask_geometry={"landmarks": {"left_eye": {"position": [1, 1]}}},
        output_size=(2, 2),
    )
    return GeneratedPattern(
        image=np.zeros((2, 2, 3), dtype=np.uint8),
        params=params,
        generator_version="1.0.0",
        provenance_hash="a" * 64,
        generator_name="hyperface_like",
    )


def test_artifact_manifest_binds_encoded_png_without_claiming_physical_efficacy() -> None:
    manifest = build_candidate_artifact_manifest(
        _pattern(),
        research_family="hyperface_like",
        artifact_bytes=TINY_PNG,
        artifact_filename="hyperface-like.png",
    )

    assert manifest["schema_version"] == "rac_pattern_candidate_artifact/v1"
    assert manifest["research_family"] == "hyperface_like"
    assert manifest["generator"] == "hyperface_like"
    assert manifest["artifact_filename"] == "hyperface-like.png"
    assert manifest["artifact_media_type"] == "image/png"
    assert len(manifest["artifact_sha256"]) == 64
    assert len(manifest["pattern_sha256"]) == 64
    assert manifest["evidence_class"] == "digital_candidate"
    assert manifest["physical_efficacy_claimed"] is False
    assert manifest["claim_state"] == "EXPLORATORY"
    assert verify_candidate_artifact_manifest(
        manifest, TINY_PNG, expected_family="hyperface_like"
    )


def test_artifact_manifest_rejects_family_mismatch() -> None:
    with pytest.raises(PatternArtifactManifestError, match="does not match generator"):
        build_candidate_artifact_manifest(
            _pattern(),
            research_family="feature_collage",
            artifact_bytes=TINY_PNG,
            artifact_filename="candidate.png",
        )


def test_artifact_manifest_rejects_tampered_artifact_bytes() -> None:
    manifest = build_candidate_artifact_manifest(
        _pattern(),
        research_family="hyperface_like",
        artifact_bytes=TINY_PNG,
        artifact_filename="candidate.png",
    )
    tampered = TINY_PNG[:-1] + bytes([TINY_PNG[-1] ^ 1])
    with pytest.raises(PatternArtifactManifestError, match="artifact_sha256 does not match"):
        verify_candidate_artifact_manifest(manifest, tampered)


def test_artifact_manifest_rejects_non_png_bytes() -> None:
    with pytest.raises(PatternArtifactManifestError, match="PNG signature"):
        build_candidate_artifact_manifest(
            _pattern(),
            research_family="hyperface_like",
            artifact_bytes=b"not-a-png",
            artifact_filename="candidate.png",
        )

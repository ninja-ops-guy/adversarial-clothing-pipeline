"""Fail-closed tests: invalid input, SHA mismatch, missing provenance, NaN."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
import pytest
from ruthless_pipeline.pattern_genome import PatternGenomeInputError, PatternGenomeProvenanceError, extract_genome, load_config

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "pattern_genome_v1.json"

def _rgb(seed=42, size=64):
    rng = np.random.RandomState(seed)
    return (rng.rand(size, size, 3) * 255).astype(np.uint8)

def _sha(b): return hashlib.sha256(b).hexdigest()

def _extract(rgb, **overrides):
    config = load_config(CONFIG_PATH)
    kwargs = dict(candidate_sha256=_sha(rgb.tobytes()), source_artifact_ref="test://failclosed",
                  source_commit="test", runtime_lock_sha256="0" * 64, config=config)
    kwargs.update(overrides)
    return extract_genome(rgb, **kwargs)

def test_sha_mismatch_refused():
    with pytest.raises(PatternGenomeInputError, match="candidate_sha256 mismatch"):
        _extract(_rgb(), candidate_sha256="f" * 64)

def test_corrupt_bytes_refused():
    data=b"not an image at all"
    with pytest.raises(PatternGenomeInputError, match="cannot decode"):
        extract_genome(data, candidate_sha256=_sha(data), source_artifact_ref="test://corrupt",
                       source_commit="test", runtime_lock_sha256="0"*64, config=load_config(CONFIG_PATH))

def test_wrong_shape_refused():
    bad=np.zeros((64,64),dtype=np.uint8)
    with pytest.raises(PatternGenomeInputError, match=r"expected \(H,W,3\)"): _extract(bad)

def test_zero_size_refused():
    with pytest.raises(PatternGenomeInputError):
        extract_genome(b"", candidate_sha256=_sha(b""), source_artifact_ref="test://empty",
                       source_commit="test", runtime_lock_sha256="0"*64, config=load_config(CONFIG_PATH))

def test_missing_provenance_field_refused():
    from ruthless_pipeline.pattern_genome.provenance import build_provenance
    with pytest.raises(PatternGenomeProvenanceError, match="required"):
        build_provenance(candidate_sha256="a"*64, source_artifact_ref="", source_commit="test",
                         runtime_lock_sha256="0"*64, extractor_config_sha256="1"*64,
                         extracted_utc="2026-01-01T00:00:00Z")

def test_empty_provenance_field_refused():
    from ruthless_pipeline.pattern_genome.provenance import build_provenance
    with pytest.raises(PatternGenomeProvenanceError, match="required"):
        build_provenance(candidate_sha256="a"*64, source_artifact_ref="test://x", source_commit="  ",
                         runtime_lock_sha256="0"*64, extractor_config_sha256="1"*64,
                         extracted_utc="2026-01-01T00:00:00Z")

def test_unknown_evidence_class_refused():
    from ruthless_pipeline.pattern_genome.provenance import validate_provenance
    from ruthless_pipeline.pattern_genome.schema import GenomeProvenance
    bad=GenomeProvenance(candidate_sha256="a"*64, source_artifact_ref="test://x",
        extractor_version="1.0.0", genome_schema="rac-pattern-genome/1.0", source_commit="test",
        runtime_lock_sha256="0"*64, extractor_config_sha256="1"*64,
        extracted_utc="2026-01-01T00:00:00Z", evidence_class="measured")
    with pytest.raises(PatternGenomeProvenanceError, match="unknown evidence_class"): validate_provenance(bad)

def test_nan_in_image_refused():
    rgb=_rgb().astype(np.float64); rgb[0,0,0]=np.nan
    with pytest.raises(PatternGenomeInputError, match="uint8"): _extract(rgb)

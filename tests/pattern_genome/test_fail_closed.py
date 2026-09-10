import pytest
from ruthless_pipeline.pattern_genome import extract_genome, PatternGenomeInputError, PatternGenomeProvenanceError

def test_corrupt_rejected(cfg):
    import hashlib
    data=b"not-an-image"
    with pytest.raises(PatternGenomeInputError): extract_genome(data,candidate_sha256=hashlib.sha256(data).hexdigest(),source_artifact_ref="x",source_commit="c",runtime_lock_sha256="0"*64,config=cfg,extracted_utc="2026-09-09T22:00:00Z")

def test_sha_mismatch(checker_bytes,kwargs):
    bad=dict(kwargs); bad["candidate_sha256"]="f"*64
    with pytest.raises(PatternGenomeInputError): extract_genome(checker_bytes,**bad)

def test_missing_provenance(checker_bytes,kwargs):
    bad=dict(kwargs); bad["source_commit"]=""
    with pytest.raises(PatternGenomeProvenanceError): extract_genome(checker_bytes,**bad)

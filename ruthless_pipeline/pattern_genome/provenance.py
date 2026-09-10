from __future__ import annotations
import re
from datetime import datetime, timezone
from .errors import PatternGenomeProvenanceError
from .schema import EVIDENCE_CLASS, GenomeProvenance, SCHEMA_VERSION

_HEX64=re.compile(r"^[0-9a-f]{64}$")

def build_provenance(*, candidate_sha256:str, source_artifact_ref:str, source_commit:str, runtime_lock_sha256:str, extractor_config_sha256:str, extracted_utc:str|None=None) -> GenomeProvenance:
    if extracted_utc is None:
        extracted_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    p=GenomeProvenance(candidate_sha256=candidate_sha256, source_artifact_ref=source_artifact_ref, extractor_version="1.0.0", genome_schema=SCHEMA_VERSION, source_commit=source_commit, runtime_lock_sha256=runtime_lock_sha256, extractor_config_sha256=extractor_config_sha256, extracted_utc=extracted_utc, evidence_class=EVIDENCE_CLASS)
    validate_provenance(p); return p

def validate_provenance(p: GenomeProvenance) -> None:
    if not _HEX64.match(p.candidate_sha256 or ""): raise PatternGenomeProvenanceError("candidate_sha256 must be lowercase 64-hex")
    if not _HEX64.match(p.runtime_lock_sha256 or ""): raise PatternGenomeProvenanceError("runtime_lock_sha256 must be lowercase 64-hex")
    if not _HEX64.match(p.extractor_config_sha256 or ""): raise PatternGenomeProvenanceError("extractor_config_sha256 must be lowercase 64-hex")
    if not p.source_artifact_ref: raise PatternGenomeProvenanceError("source_artifact_ref required")
    if not p.source_commit: raise PatternGenomeProvenanceError("source_commit required")
    if p.genome_schema != SCHEMA_VERSION: raise PatternGenomeProvenanceError("genome schema mismatch")
    if p.evidence_class != EVIDENCE_CLASS: raise PatternGenomeProvenanceError("invalid evidence class")
    if not p.extracted_utc.endswith("Z"): raise PatternGenomeProvenanceError("extracted_utc must be UTC Z")

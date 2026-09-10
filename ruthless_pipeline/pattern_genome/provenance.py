"""Provenance construction and validation for Pattern Genome."""
from __future__ import annotations
from .errors import PatternGenomeProvenanceError
from .schema import SCHEMA_VERSION, EXTRACTOR_VERSION, GenomeProvenance

REQUIRED_PROVENANCE_FIELDS = (
    "candidate_sha256", "source_artifact_ref", "extractor_version",
    "genome_schema", "source_commit", "runtime_lock_sha256",
    "extractor_config_sha256", "extracted_utc", "evidence_class",
)
VALID_EVIDENCE_CLASSES = frozenset({"derived_digital_measurement"})

def build_provenance(*, candidate_sha256, source_artifact_ref, source_commit,
                     runtime_lock_sha256, extractor_config_sha256, extracted_utc):
    for name, value in (
        ("candidate_sha256", candidate_sha256),
        ("source_artifact_ref", source_artifact_ref),
        ("source_commit", source_commit),
        ("runtime_lock_sha256", runtime_lock_sha256),
        ("extractor_config_sha256", extractor_config_sha256),
        ("extracted_utc", extracted_utc),
    ):
        if not value or not str(value).strip():
            raise PatternGenomeProvenanceError(f"provenance field '{name}' is required")
    return GenomeProvenance(
        candidate_sha256=candidate_sha256,
        source_artifact_ref=source_artifact_ref,
        extractor_version=EXTRACTOR_VERSION,
        genome_schema=SCHEMA_VERSION,
        source_commit=source_commit,
        runtime_lock_sha256=runtime_lock_sha256,
        extractor_config_sha256=extractor_config_sha256,
        extracted_utc=extracted_utc,
        evidence_class="derived_digital_measurement",
    )

def validate_provenance(prov: GenomeProvenance) -> None:
    for f in REQUIRED_PROVENANCE_FIELDS:
        if not getattr(prov, f, None):
            raise PatternGenomeProvenanceError(f"provenance field '{f}' is missing")
    if prov.evidence_class not in VALID_EVIDENCE_CLASSES:
        raise PatternGenomeProvenanceError(f"unknown evidence_class value: {prov.evidence_class!r}")

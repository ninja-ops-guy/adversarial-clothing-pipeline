"""Certification and provenance primitives for RAC evidence-backed patterns."""

from .manifest import ArtifactRef, EvidenceState, PatternManifest, hash_file, sha256_bytes
from .protocol import CertificationProtocol, PassCriteria, load_protocol
from .registry import ModelManifest, ModelRegistry
from .statistics import MetricSummary, summarize_values, wilson_interval
from .artifact_bundle import ArtifactBundle
from .certificate import Certificate, CertificateDecision, issue_certificate
from .verification import verify_certificate_bundle

__all__ = [
    "ArtifactRef", "EvidenceState", "PatternManifest", "hash_file", "sha256_bytes",
    "CertificationProtocol", "PassCriteria", "load_protocol",
    "ModelManifest", "ModelRegistry", "MetricSummary", "summarize_values", "wilson_interval",
    "ArtifactBundle", "Certificate", "CertificateDecision", "issue_certificate",
    "verify_certificate_bundle",
]

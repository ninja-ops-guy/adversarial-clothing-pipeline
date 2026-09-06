"""Certification and provenance primitives for RAC evidence-backed patterns."""

from .artifact_bundle import ArtifactBundle
from .calibration import PrintCalibration, TextileProfile
from .certificate import Certificate, CertificateDecision, issue_certificate
from .evidence import (
    BenchmarkObservation,
    EvidenceRecord,
    EvidenceType,
    ObservationStatus,
    eligible_values,
    require_evidence_for_state,
    validate_transition,
)
from .manifest import ArtifactRef, EvidenceState, PatternManifest, hash_file, sha256_bytes
from .manufacturing import (
    ConformityLimits,
    ConformityMeasurement,
    evaluate_lot_conformity,
)
from .physical import PhysicalSummary, PhysicalTrial, summarize_physical_trials
from .protocol import CertificationProtocol, PassCriteria, load_protocol
from .registry import ModelManifest, ModelRegistry
from .statistics import MetricSummary, summarize_values, wilson_interval
from .verification import verify_certificate_bundle

__all__ = [
    "ArtifactBundle",
    "ArtifactRef",
    "BenchmarkObservation",
    "Certificate",
    "CertificateDecision",
    "CertificationProtocol",
    "ConformityLimits",
    "ConformityMeasurement",
    "EvidenceRecord",
    "EvidenceState",
    "EvidenceType",
    "MetricSummary",
    "ModelManifest",
    "ModelRegistry",
    "ObservationStatus",
    "PassCriteria",
    "PatternManifest",
    "PhysicalSummary",
    "PhysicalTrial",
    "PrintCalibration",
    "TextileProfile",
    "eligible_values",
    "evaluate_lot_conformity",
    "hash_file",
    "issue_certificate",
    "load_protocol",
    "require_evidence_for_state",
    "sha256_bytes",
    "summarize_physical_trials",
    "summarize_values",
    "validate_transition",
    "verify_certificate_bundle",
    "wilson_interval",
]

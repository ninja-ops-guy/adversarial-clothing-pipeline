from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from .artifact_bundle import ArtifactBundle
from .manifest import EvidenceState, PatternManifest
from .protocol import CertificationProtocol


class CertificateDecision(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class Certificate:
    certificate_id: str
    pattern_id: str
    pattern_version: str
    evidence_state: EvidenceState
    protocol_id: str
    decision: CertificateDecision
    manifest_sha256: str
    bundle_sha256: str
    software_commit: str
    scope: str
    limitations: tuple[str, ...]


def issue_certificate(
    *,
    bundle: ArtifactBundle,
    manifest: PatternManifest,
    protocol: CertificationProtocol,
    digital_summary: dict,
    requested_state: EvidenceState,
    physical_evidence_present: bool = False,
) -> Certificate:
    manifest.validate()
    protocol.validate()
    if manifest.protocol_id != protocol.protocol_id:
        raise ValueError("manifest protocol does not match certification protocol")
    if manifest.heldout_model_set != protocol.heldout_model_set:
        raise ValueError("held-out model set mismatch")

    heldout = digital_summary.get("heldout", {})
    invalid_fraction = float(digital_summary.get("invalid_condition_fraction", 1.0))
    baseline_rate = float(heldout.get("baseline_detection_rate", 0.0))
    candidate_rate = float(heldout.get("candidate_detection_rate", 1.0))
    relative_reduction = 0.0 if baseline_rate <= 0 else (baseline_rate - candidate_rate) / baseline_rate

    criteria = protocol.criteria
    digital_pass = (
        baseline_rate >= criteria.min_baseline_detection_rate
        and candidate_rate <= criteria.max_candidate_detection_rate
        and relative_reduction >= criteria.min_relative_reduction
        and invalid_fraction <= criteria.max_invalid_condition_fraction
    )
    physical_needed = requested_state.value in protocol.physical_required_for
    if physical_needed and not physical_evidence_present:
        raise ValueError(f"{requested_state.value} requires physical evidence")

    _, bundle_hash = bundle.seal()
    decision = CertificateDecision.PASS if digital_pass else CertificateDecision.FAIL
    cert = Certificate(
        certificate_id=f"{manifest.pattern_id}-{manifest.version}-{protocol.version}",
        pattern_id=manifest.pattern_id,
        pattern_version=manifest.version,
        evidence_state=requested_state if decision == CertificateDecision.PASS else EvidenceState.DESIGN,
        protocol_id=protocol.protocol_id,
        decision=decision,
        manifest_sha256=manifest.manifest_sha256,
        bundle_sha256=bundle_hash,
        software_commit=manifest.source_commit,
        scope=protocol.task,
        limitations=(
            "Valid only for the frozen protocol/model manifests and tested conditions.",
            "Does not imply performance against untested or arbitrary surveillance systems.",
        ),
    )
    bundle.write_json("certificate.json", {
        **asdict(cert),
        "evidence_state": cert.evidence_state.value,
        "decision": cert.decision.value,
    })
    return cert

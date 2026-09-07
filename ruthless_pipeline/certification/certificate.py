from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from enum import Enum

from .artifact_bundle import ArtifactBundle
from .manifest import EvidenceState, PatternManifest, hash_file
from .protocol import CertificationProtocol


class CertificateDecision(str, Enum):
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


def _validate_rates(baseline_rate: float, candidate_rate: float, invalid_fraction: float) -> tuple[float, float, float]:
    rates = {
        "baseline_detection_rate": baseline_rate,
        "candidate_detection_rate": candidate_rate,
        "invalid_condition_fraction": invalid_fraction,
    }
    for name, value in rates.items():
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be a finite value within [0,1]")
    return baseline_rate, candidate_rate, invalid_fraction


def _digital_rates(digital_summary: dict) -> tuple[float, float, float]:
    heldout = digital_summary.get("heldout", {})
    return _validate_rates(
        float(heldout.get("baseline_detection_rate", 0.0)),
        float(heldout.get("candidate_detection_rate", 1.0)),
        float(digital_summary.get("invalid_condition_fraction", 1.0)),
    )


def _physical_rates(bundle: ArtifactBundle) -> tuple[float, float, float]:
    summary_path = bundle.root / "physical" / "summary.json"
    if not summary_path.is_file():
        raise ValueError("physical certification requires bundled physical/summary.json")
    payload = json.loads(summary_path.read_text())
    total = int(payload.get("total_trials", 0))
    invalid = int(payload.get("invalid_trials", total))
    if total <= 0 or invalid < 0 or invalid > total:
        raise ValueError("physical summary trial counts are invalid")
    return _validate_rates(
        float(payload.get("control_detection_rate", 0.0)),
        float(payload.get("candidate_detection_rate", 1.0)),
        invalid / total,
    )


def issue_certificate(
    *,
    bundle: ArtifactBundle,
    manifest: PatternManifest,
    protocol: CertificationProtocol,
    digital_summary: dict,
    requested_state: EvidenceState,
    physical_evidence_present: bool = False,
    manufacturing_evidence_present: bool = False,
) -> Certificate:
    manifest.validate()
    protocol.validate()
    if manifest.protocol_id != protocol.protocol_id:
        raise ValueError("manifest protocol does not match certification protocol")
    if manifest.heldout_model_set != protocol.heldout_model_set:
        raise ValueError("held-out model set mismatch")

    master_path = bundle.resolve_path(manifest.master.path)
    if not master_path.exists() or not master_path.is_file():
        raise ValueError(f"missing master artifact: {manifest.master.path}")
    if hash_file(master_path) != manifest.master.sha256:
        raise ValueError("master artifact hash mismatch")

    manufacturing_states = {
        EvidenceState.GOLDEN_SAMPLE,
        EvidenceState.LOT_CONFORMITY,
    }
    physical_states = {
        EvidenceState.PHYSICAL,
        EvidenceState.DURABILITY,
        *manufacturing_states,
    }

    if requested_state in manufacturing_states and not manufacturing_evidence_present:
        raise ValueError(f"{requested_state.value} requires manufacturing evidence")

    physical_needed = requested_state.value in protocol.physical_required_for
    if physical_needed:
        if not physical_evidence_present:
            raise ValueError(f"{requested_state.value} requires physical evidence")
        required_physical = [
            bundle.root / "physical" / "summary.json",
            bundle.root / "physical" / "trials.csv",
        ]
        missing = [str(path.relative_to(bundle.root)) for path in required_physical if not path.is_file()]
        if missing:
            raise ValueError(
                f"{requested_state.value} requires bundled physical evidence artifacts: {', '.join(missing)}"
            )

    if requested_state == EvidenceState.DURABILITY:
        durability_path = bundle.root / "physical" / "durability.json"
        if not durability_path.is_file():
            raise ValueError("RAC-P2 requires bundled durability evidence: physical/durability.json")

    if requested_state in manufacturing_states:
        required_name = "golden_sample.json" if requested_state == EvidenceState.GOLDEN_SAMPLE else "lot_conformity.json"
        required_path = bundle.root / "manufacturing" / required_name
        if not required_path.is_file():
            raise ValueError(
                f"{requested_state.value} requires bundled manufacturing evidence: manufacturing/{required_name}"
            )

    # Digital states are decided from held-out digital evidence. Physical and
    # manufacturing states are decided from the measured physical summary so a
    # strong digital benchmark can never substitute for a failed garment test.
    if requested_state in physical_states:
        baseline_rate, candidate_rate, invalid_fraction = _physical_rates(bundle)
        decision_basis = "physical"
    else:
        baseline_rate, candidate_rate, invalid_fraction = _digital_rates(digital_summary)
        decision_basis = "digital_heldout"

    relative_reduction = 0.0 if baseline_rate <= 0 else (baseline_rate - candidate_rate) / baseline_rate
    criteria = protocol.criteria
    evidence_pass = (
        baseline_rate >= criteria.min_baseline_detection_rate
        and candidate_rate <= criteria.max_candidate_detection_rate
        and relative_reduction >= criteria.min_relative_reduction
        and invalid_fraction <= criteria.max_invalid_condition_fraction
    )

    _, bundle_hash = bundle.seal()
    decision = CertificateDecision.PASS if evidence_pass else CertificateDecision.FAIL
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
            f"Decision basis: {decision_basis} evidence under the frozen protocol.",
            "Valid only for the frozen protocol/model manifests and tested conditions.",
            "Does not imply performance against untested or arbitrary surveillance systems.",
        ),
    )
    bundle.write_json(
        "certificate.json",
        {
            **asdict(cert),
            "evidence_state": cert.evidence_state.value,
            "decision": cert.decision.value,
        },
    )
    bundle.seal(exclude=("hashes.sha256",))
    return cert

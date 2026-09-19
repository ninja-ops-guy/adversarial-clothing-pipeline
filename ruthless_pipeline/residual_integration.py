"""RAC <-> RESIDUAL improvement-loop contracts.

This module is orchestration-only. It does not generate patterns, run held-out
evaluation, arm physical experiments, or promote scientific claims. It provides
immutable, hash-addressed contracts that RESIDUAL can orchestrate without
becoming part of RAC's measurement implementation.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "rac-residual-improvement/1.0"
EVIDENCE_SCHEMA_VERSION = "rac-residual-evidence/1.0"
DECISION_SCHEMA_VERSION = "rac-residual-decision/1.0"

_SPEC_ID_RE = re.compile(r"^RAC-I-[0-9]{6}$")
_HYPOTHESIS_ID_RE = re.compile(r"^RAC-H-[0-9]{6}$")
_EVIDENCE_ID_RE = re.compile(r"^RAC-EV-[0-9]{6}$")
_DECISION_ID_RE = re.compile(r"^RAC-D-[0-9]{6}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")

OUTCOMES = frozenset({"PASS", "FAIL", "INCONCLUSIVE"})
DECISIONS = frozenset({"PROMOTABLE", "REJECTED", "INCONCLUSIVE"})
DEFAULT_FORBIDDEN_CAPABILITIES = (
    "held_out_candidate_selection",
    "physical_experiment_execution",
    "automatic_scientific_promotion",
)


class RACResidualContractError(ValueError):
    """Raised when an improvement-loop artifact violates a frozen contract."""


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw_json(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(v) for v in value]
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _thaw_json(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _freeze_json(value: Any) -> Any:
    """Recursively freeze finite JSON-compatible data."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise RACResidualContractError("non-finite floats are forbidden")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(k, str) for k in value):
            raise RACResidualContractError("mapping keys must be strings")
        return MappingProxyType({k: _freeze_json(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(v) for v in value)
    raise RACResidualContractError(
        f"value of type {type(value).__name__} is not finite JSON data"
    )


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RACResidualContractError(f"{field_name} must be non-empty text")
    return value


def _require_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise RACResidualContractError(f"{field_name} must be lowercase sha256")
    return value


def _require_revision(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _REVISION_RE.fullmatch(value):
        raise RACResidualContractError(
            f"{field_name} must be a lowercase 40-64 hex source revision"
        )
    return value


@dataclass(frozen=True)
class RACImprovementSpec:
    """Frozen hypothesis-to-experiment contract proposed to RESIDUAL."""

    spec_id: str
    hypothesis_id: str
    baseline_revision: str
    target_component: str
    proposed_change: str
    evaluation_version: str
    acceptance: Mapping[str, Any]
    falsification: Mapping[str, Any]
    created_utc: str
    forbidden_capabilities: tuple[str, ...] = DEFAULT_FORBIDDEN_CAPABILITIES
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise RACResidualContractError("unsupported improvement schema_version")
        if not _SPEC_ID_RE.fullmatch(self.spec_id):
            raise RACResidualContractError("spec_id must match RAC-I-######")
        if not _HYPOTHESIS_ID_RE.fullmatch(self.hypothesis_id):
            raise RACResidualContractError("hypothesis_id must match RAC-H-######")
        _require_revision(self.baseline_revision, "baseline_revision")
        _require_text(self.target_component, "target_component")
        _require_text(self.proposed_change, "proposed_change")
        _require_text(self.evaluation_version, "evaluation_version")
        _require_text(self.created_utc, "created_utc")
        if not isinstance(self.acceptance, Mapping) or not self.acceptance:
            raise RACResidualContractError("acceptance must be a non-empty mapping")
        if not isinstance(self.falsification, Mapping) or not self.falsification:
            raise RACResidualContractError("falsification must be a non-empty mapping")
        object.__setattr__(self, "acceptance", _freeze_json(self.acceptance))
        object.__setattr__(self, "falsification", _freeze_json(self.falsification))
        forbidden = tuple(self.forbidden_capabilities)
        if not forbidden or any(not isinstance(v, str) or not v for v in forbidden):
            raise RACResidualContractError(
                "forbidden_capabilities must be non-empty strings"
            )
        missing = set(DEFAULT_FORBIDDEN_CAPABILITIES) - set(forbidden)
        if missing:
            raise RACResidualContractError(
                f"mandatory forbidden capabilities cannot be removed: {sorted(missing)}"
            )
        object.__setattr__(self, "forbidden_capabilities", forbidden)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "spec_id": self.spec_id,
            "hypothesis_id": self.hypothesis_id,
            "baseline_revision": self.baseline_revision,
            "target_component": self.target_component,
            "proposed_change": self.proposed_change,
            "evaluation_version": self.evaluation_version,
            "acceptance": _thaw_json(self.acceptance),
            "falsification": _thaw_json(self.falsification),
            "created_utc": self.created_utc,
            "forbidden_capabilities": list(self.forbidden_capabilities),
        }

    @property
    def content_sha256(self) -> str:
        return _sha256(self.to_dict())


@dataclass(frozen=True)
class RACEvidenceBundle:
    """One immutable execution/verification result for an ImprovementSpec."""

    evidence_id: str
    spec_sha256: str
    source_revision: str
    evaluation_version: str
    experiment_manifest_sha256: str
    firewall_attestation_sha256: str
    artifact_sha256s: tuple[str, ...]
    outcome: str
    producer_id: str
    producer_identity_sha256: str
    independent_verifier_id: str
    independent_verifier_identity_sha256: str
    independent_verifier_receipt_sha256: str
    replication_id: str
    replication_receipt_sha256: str
    notes: str = ""
    schema_version: str = EVIDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_SCHEMA_VERSION:
            raise RACResidualContractError("unsupported evidence schema_version")
        if not _EVIDENCE_ID_RE.fullmatch(self.evidence_id):
            raise RACResidualContractError("evidence_id must match RAC-EV-######")
        _require_sha256(self.spec_sha256, "spec_sha256")
        _require_revision(self.source_revision, "source_revision")
        _require_text(self.evaluation_version, "evaluation_version")
        _require_sha256(
            self.experiment_manifest_sha256, "experiment_manifest_sha256"
        )
        _require_sha256(
            self.firewall_attestation_sha256, "firewall_attestation_sha256"
        )
        artifacts = tuple(self.artifact_sha256s)
        if not artifacts:
            raise RACResidualContractError("artifact_sha256s cannot be empty")
        for index, value in enumerate(artifacts):
            _require_sha256(value, f"artifact_sha256s[{index}]")
        object.__setattr__(self, "artifact_sha256s", artifacts)
        if self.outcome not in OUTCOMES:
            raise RACResidualContractError(
                f"outcome must be one of {sorted(OUTCOMES)}"
            )
        _require_text(self.producer_id, "producer_id")
        _require_sha256(self.producer_identity_sha256, "producer_identity_sha256")
        _require_text(self.independent_verifier_id, "independent_verifier_id")
        _require_sha256(
            self.independent_verifier_identity_sha256,
            "independent_verifier_identity_sha256",
        )
        _require_sha256(
            self.independent_verifier_receipt_sha256,
            "independent_verifier_receipt_sha256",
        )
        if (
            self.independent_verifier_id == self.producer_id
            or self.independent_verifier_identity_sha256
            == self.producer_identity_sha256
        ):
            raise RACResidualContractError(
                "independent verifier must differ from the producer by id and identity"
            )
        _require_text(self.replication_id, "replication_id")
        _require_sha256(
            self.replication_receipt_sha256, "replication_receipt_sha256"
        )
        if not isinstance(self.notes, str):
            raise RACResidualContractError("notes must be text")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "spec_sha256": self.spec_sha256,
            "source_revision": self.source_revision,
            "evaluation_version": self.evaluation_version,
            "experiment_manifest_sha256": self.experiment_manifest_sha256,
            "firewall_attestation_sha256": self.firewall_attestation_sha256,
            "artifact_sha256s": list(self.artifact_sha256s),
            "outcome": self.outcome,
            "producer_id": self.producer_id,
            "producer_identity_sha256": self.producer_identity_sha256,
            "independent_verifier_id": self.independent_verifier_id,
            "independent_verifier_identity_sha256": self.independent_verifier_identity_sha256,
            "independent_verifier_receipt_sha256": self.independent_verifier_receipt_sha256,
            "replication_id": self.replication_id,
            "replication_receipt_sha256": self.replication_receipt_sha256,
            "notes": self.notes,
        }

    @property
    def content_sha256(self) -> str:
        return _sha256(self.to_dict())


@dataclass(frozen=True)
class RACImprovementDecision:
    """Deterministic advisory decision. It is never a promotion receipt."""

    decision_id: str
    spec_sha256: str
    evidence_sha256s: tuple[str, ...]
    status: str
    reason: str
    human_gate_required: bool = True
    automation_may_promote: bool = False
    schema_version: str = DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DECISION_SCHEMA_VERSION:
            raise RACResidualContractError("unsupported decision schema_version")
        if not _DECISION_ID_RE.fullmatch(self.decision_id):
            raise RACResidualContractError("decision_id must match RAC-D-######")
        _require_sha256(self.spec_sha256, "spec_sha256")
        refs = tuple(self.evidence_sha256s)
        for index, value in enumerate(refs):
            _require_sha256(value, f"evidence_sha256s[{index}]")
        object.__setattr__(self, "evidence_sha256s", refs)
        if self.status not in DECISIONS:
            raise RACResidualContractError(
                f"status must be one of {sorted(DECISIONS)}"
            )
        _require_text(self.reason, "reason")
        if self.human_gate_required is not True:
            raise RACResidualContractError(
                "human_gate_required is invariantly true"
            )
        if self.automation_may_promote is not False:
            raise RACResidualContractError(
                "automation_may_promote is invariantly false"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "spec_sha256": self.spec_sha256,
            "evidence_sha256s": list(self.evidence_sha256s),
            "status": self.status,
            "reason": self.reason,
            "human_gate_required": self.human_gate_required,
            "automation_may_promote": self.automation_may_promote,
        }

    @property
    def content_sha256(self) -> str:
        return _sha256(self.to_dict())


def evaluate_improvement(
    spec: RACImprovementSpec,
    evidence: Iterable[RACEvidenceBundle],
    *,
    decision_id: str,
) -> RACImprovementDecision:
    """Evaluate retained evidence without granting authority to promote."""
    bundles = tuple(evidence)
    for bundle in bundles:
        if bundle.spec_sha256 != spec.content_sha256:
            raise RACResidualContractError(
                "evidence references a different ImprovementSpec"
            )
        if bundle.evaluation_version != spec.evaluation_version:
            raise RACResidualContractError(
                "evidence evaluation_version drifted from the spec"
            )

    refs = tuple(bundle.content_sha256 for bundle in bundles)
    if any(bundle.outcome == "FAIL" for bundle in bundles):
        status = "REJECTED"
        reason = "at least one retained evidence bundle falsified the improvement"
    elif any(bundle.outcome == "INCONCLUSIVE" for bundle in bundles):
        status = "INCONCLUSIVE"
        reason = "at least one retained evidence bundle is inconclusive"
    elif (
        len({b.replication_id for b in bundles}) < 2
        or len({b.replication_receipt_sha256 for b in bundles}) < 2
    ):
        status = "INCONCLUSIVE"
        reason = "promotion requires two independently receipted replications"
    elif (
        len({b.independent_verifier_id for b in bundles}) < 2
        or len({b.independent_verifier_identity_sha256 for b in bundles}) < 2
        or len({b.independent_verifier_receipt_sha256 for b in bundles}) < 2
    ):
        status = "INCONCLUSIVE"
        reason = "promotion requires two hash-distinct independent verifier identities and receipts"
    elif bundles and all(bundle.outcome == "PASS" for bundle in bundles):
        status = "PROMOTABLE"
        reason = (
            "replicated evidence passed the frozen acceptance contract; "
            "human promotion remains required"
        )
    else:
        status = "INCONCLUSIVE"
        reason = "insufficient evidence"

    return RACImprovementDecision(
        decision_id=decision_id,
        spec_sha256=spec.content_sha256,
        evidence_sha256s=refs,
        status=status,
        reason=reason,
    )


def build_residual_candidate(
    spec: RACImprovementSpec,
    evidence: Iterable[RACEvidenceBundle],
    decision: RACImprovementDecision,
) -> dict[str, Any]:
    """Build the JSON candidate RESIDUAL should hash and verify."""
    bundles = tuple(evidence)
    if decision.spec_sha256 != spec.content_sha256:
        raise RACResidualContractError(
            "decision references a different ImprovementSpec"
        )
    expected_refs = tuple(bundle.content_sha256 for bundle in bundles)
    if decision.evidence_sha256s != expected_refs:
        raise RACResidualContractError(
            "decision evidence references do not match supplied evidence"
        )
    return {
        "contract": "rac-residual-candidate/1.0",
        "improvement_spec": spec.to_dict(),
        "evidence": [bundle.to_dict() for bundle in bundles],
        "decision": decision.to_dict(),
        "authority": {
            "advisory_only": True,
            "human_gate_required": True,
            "automatic_promotion_forbidden": True,
        },
    }

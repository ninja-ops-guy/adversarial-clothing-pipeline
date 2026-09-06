from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Iterable
import math

from .manifest import EvidenceState


class EvidenceType(str, Enum):
    DIGITAL = "digital"
    PHYSICAL = "physical"
    MANUFACTURING = "manufacturing"


class ObservationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    EXCLUDED = "excluded"


_STATE_ORDER = (
    EvidenceState.DESIGN,
    EvidenceState.SURROGATE,
    EvidenceState.DIGITAL_HELDOUT,
    EvidenceState.PHYSICAL,
    EvidenceState.DURABILITY,
    EvidenceState.GOLDEN_SAMPLE,
    EvidenceState.LOT_CONFORMITY,
)

_STATE_TYPE = {
    EvidenceState.DESIGN: EvidenceType.DIGITAL,
    EvidenceState.SURROGATE: EvidenceType.DIGITAL,
    EvidenceState.DIGITAL_HELDOUT: EvidenceType.DIGITAL,
    EvidenceState.PHYSICAL: EvidenceType.PHYSICAL,
    EvidenceState.DURABILITY: EvidenceType.PHYSICAL,
    EvidenceState.GOLDEN_SAMPLE: EvidenceType.MANUFACTURING,
    EvidenceState.LOT_CONFORMITY: EvidenceType.MANUFACTURING,
}


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def validate_transition(current: EvidenceState, target: EvidenceState) -> None:
    """Reject skipped, reversed, or duplicate RAC state transitions."""
    current_index = _STATE_ORDER.index(current)
    target_index = _STATE_ORDER.index(target)
    if target_index != current_index + 1:
        raise ValueError(
            f"illegal RAC transition: {current.value} -> {target.value}; "
            "transitions must be adjacent and forward"
        )


@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable provenance record for one RAC evidence artifact set."""

    rac_state: EvidenceState
    evidence_type: EvidenceType
    source: str
    fixture_type: str
    created_at: str
    code_commit: str
    configuration: dict[str, Any]
    artifact_hashes: dict[str, str]
    model_metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate provenance completeness and state/evidence boundaries."""
        expected = _STATE_TYPE[self.rac_state]
        if self.evidence_type != expected:
            raise ValueError(
                f"{self.rac_state.value} requires evidence_type={expected.value}"
            )
        if not self.source or not self.fixture_type or not self.code_commit:
            raise ValueError("source, fixture_type, and code_commit are required")
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("created_at must be ISO-8601") from exc
        if not self.artifact_hashes:
            raise ValueError("at least one artifact SHA-256 is required")
        for name, digest in self.artifact_hashes.items():
            if not name or not _is_sha256(digest):
                raise ValueError(f"invalid SHA-256 for artifact {name!r}")
        if self.evidence_type == EvidenceType.DIGITAL and self.model_metadata:
            required = {"models", "preprocessing", "thresholds"}
            missing = required - set(self.model_metadata)
            if missing:
                raise ValueError(
                    "digital model evidence missing metadata: "
                    + ", ".join(sorted(missing))
                )


@dataclass(frozen=True)
class BenchmarkObservation:
    """One preregistered benchmark observation with explicit validity."""

    value: float
    status: ObservationStatus
    invalid_reason: str | None = None

    def validate(self) -> None:
        if not math.isfinite(float(self.value)):
            raise ValueError("benchmark observation value must be finite")
        if self.status == ObservationStatus.INVALID and not self.invalid_reason:
            raise ValueError("invalid observations require invalid_reason")
        if self.status == ObservationStatus.VALID and self.invalid_reason:
            raise ValueError("valid observations cannot have invalid_reason")


def eligible_values(observations: Iterable[BenchmarkObservation]) -> list[float]:
    """Return only valid observations after validating every record."""
    values: list[float] = []
    for observation in observations:
        observation.validate()
        if observation.status == ObservationStatus.VALID:
            values.append(float(observation.value))
    return values


def require_evidence_for_state(
    target: EvidenceState,
    evidence: Iterable[EvidenceRecord],
) -> None:
    """Fail closed unless evidence of the target class exists and validates."""
    records = list(evidence)
    for record in records:
        record.validate()

    required_type = _STATE_TYPE[target]
    if not any(record.evidence_type == required_type for record in records):
        raise ValueError(
            f"{target.value} requires {required_type.value} evidence"
        )

    if required_type == EvidenceType.MANUFACTURING:
        if not any(
            record.evidence_type == EvidenceType.PHYSICAL for record in records
        ):
            raise ValueError(
                f"{target.value} requires prior physical evidence"
            )

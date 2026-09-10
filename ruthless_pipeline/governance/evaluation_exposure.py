"""Evaluation-exposure ledger and independent-confirmation gating (NR-01).

Basis: the Generic Holdout requirement (Nakkiran & Blasiok) plus the RAC
sealing/sentinel boundaries.  Seals (``seal.py``) freeze what a cohort *is*;
the sentinel protocol (``sentinel.py``) freezes *how* a blind evaluation is
run.  Neither records *which cohort outputs were already visible when a
selection decision was made*.  This module closes that gap additively:

* :class:`ExposureEvent` / :class:`EvaluationExposureLedger` — an append-only,
  hash-pinned record that a specific cohort output class (surrogate
  evaluation, dashboard feedback, outcome-derived covariate, held-out
  evaluation) was available to, and consumed by, a named selection decision.
* :func:`issue_independent_confirmation_label` — fail-closed gate: a cohort
  whose evaluation output influenced any selection decision can never receive
  an ``INDEPENDENT_CONFIRMATION`` label for that same cohort, no matter how
  clean the final evaluation pipeline is.
* :class:`FeatureProvenance` / :func:`review_feature_provenance` — provenance
  review for features/covariates: every declared source artifact is hash-pinned
  and role-classified; any source that consumed experimental outcome labels
  (or any undeclared/unknown source role) fails review.

The module is additive: it changes no frozen schema, no seal byte, and no
existing validator.  All new artifacts carry explicit ``schema_version``
fields and sha256 pins.  Fail-closed throughout: unknown roles, unknown
label names, and unlisted cohorts raise :class:`EvaluationExposureError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

from .ids import GovernanceId, IdKind


_HEX = frozenset("0123456789abcdef")


class EvaluationExposureError(RuntimeError):
    pass


def _kind(raw: str, kind: IdKind, field: str) -> None:
    parsed = GovernanceId.parse(raw)
    if parsed.kind is not kind:
        raise EvaluationExposureError(f"{field} must be RAC-{kind.value}-...")


def _hash(value: str, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in _HEX for c in value):
        raise EvaluationExposureError(f"{field} must be a lowercase sha256")


def _canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Evaluation-exposure ledger (audit question b: what was visible, when)
# ---------------------------------------------------------------------------

class CohortOutputClass(str, Enum):
    """Classes of cohort outputs that can be exposed before a selection decision."""

    SURROGATE_EVALUATION = "surrogate_evaluation"
    DASHBOARD_FEEDBACK = "dashboard_feedback"
    OUTCOME_DERIVED_COVARIATE = "outcome_derived_covariate"
    HELDOUT_EVALUATION = "heldout_evaluation"


#: Output classes whose pre-decision availability is legitimate for a
#: discovery/selection role.  HELDOUT_EVALUATION is never permitted before a
#: selection decision on the same cohort.
SELECTION_PERMITTED_OUTPUTS = frozenset({
    CohortOutputClass.SURROGATE_EVALUATION,
    CohortOutputClass.DASHBOARD_FEEDBACK,
})

EXPOSURE_SCHEMA_VERSION = "rac-evaluation-exposure/1.0"


@dataclass(frozen=True)
class ExposureEvent:
    """One recorded fact: ``output_hash`` of ``cohort_id`` (class
    ``output_class``) was available to and consumed by ``decision_id``."""

    event_id: str
    cohort_id: str
    output_class: CohortOutputClass
    output_hash: str
    decision_id: str
    decision_influenced: bool
    schema_version: str = EXPOSURE_SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != EXPOSURE_SCHEMA_VERSION:
            raise EvaluationExposureError(
                f"unsupported exposure schema_version: {self.schema_version!r}"
            )
        _kind(self.event_id, IdKind.EVENT, "event_id")
        _kind(self.cohort_id, IdKind.COHORT, "cohort_id")
        if not isinstance(self.output_class, CohortOutputClass):
            raise EvaluationExposureError("output_class must be a CohortOutputClass")
        _hash(self.output_hash, "output_hash")
        if not isinstance(self.decision_id, str) or not self.decision_id.strip():
            raise EvaluationExposureError("decision_id is required")
        if not isinstance(self.decision_influenced, bool):
            raise EvaluationExposureError("decision_influenced must be a bool")
        if (
            self.output_class is CohortOutputClass.HELDOUT_EVALUATION
            and self.decision_influenced
        ):
            raise EvaluationExposureError(
                "held-out evaluation may never influence a selection decision "
                "on the same cohort"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "cohort_id": self.cohort_id,
            "output_class": self.output_class.value,
            "output_hash": self.output_hash,
            "decision_id": self.decision_id,
            "decision_influenced": self.decision_influenced,
        }


class EvaluationExposureLedger:
    """Append-only ledger of exposure events; one immutable record per event id."""

    def __init__(self) -> None:
        self._events: dict[str, ExposureEvent] = {}

    def register(self, event: ExposureEvent) -> None:
        event.validate()
        if event.event_id in self._events:
            raise EvaluationExposureError(f"duplicate exposure event: {event.event_id}")
        self._events[event.event_id] = event

    def events_for(self, cohort_id: str) -> tuple[ExposureEvent, ...]:
        _kind(cohort_id, IdKind.COHORT, "cohort_id")
        return tuple(e for e in self._events.values() if e.cohort_id == cohort_id)

    def ledger_hash(self) -> str:
        """Deterministic hash over the complete ledger (sorted event ids)."""
        payload = [self._events[k].to_dict() for k in sorted(self._events)]
        return sha256(_canonical(payload)).hexdigest()

    def cohort_influenced_selection(self, cohort_id: str) -> bool:
        """True iff any recorded cohort output influenced a selection decision."""
        return any(e.decision_influenced for e in self.events_for(cohort_id))


# ---------------------------------------------------------------------------
# Independent-confirmation gating (acceptance fixture i)
# ---------------------------------------------------------------------------

CONFIRMATION_LABEL_SCHEMA_VERSION = "rac-confirmation-label/1.0"
LABEL_INDEPENDENT_CONFIRMATION = "INDEPENDENT_CONFIRMATION"


@dataclass(frozen=True)
class ConfirmationLabel:
    """A granted confirmation label, bound to the ledger hash at grant time."""

    cohort_id: str
    label: str
    basis_evidence_hash: str
    ledger_hash: str
    schema_version: str = CONFIRMATION_LABEL_SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != CONFIRMATION_LABEL_SCHEMA_VERSION:
            raise EvaluationExposureError(
                f"unsupported confirmation-label schema_version: {self.schema_version!r}"
            )
        _kind(self.cohort_id, IdKind.COHORT, "cohort_id")
        if self.label != LABEL_INDEPENDENT_CONFIRMATION:
            raise EvaluationExposureError(f"unknown confirmation label: {self.label!r}")
        _hash(self.basis_evidence_hash, "basis_evidence_hash")
        _hash(self.ledger_hash, "ledger_hash")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "cohort_id": self.cohort_id,
            "label": self.label,
            "basis_evidence_hash": self.basis_evidence_hash,
            "ledger_hash": self.ledger_hash,
        }


def issue_independent_confirmation_label(
    *,
    cohort_id: str,
    basis_evidence_hash: str,
    ledger: EvaluationExposureLedger,
) -> ConfirmationLabel:
    """Grant an INDEPENDENT_CONFIRMATION label only when the cohort's outputs
    never influenced any selection decision.

    Fail-closed: the Generic Holdout property is enforced against the ledger,
    not against caller intent.  If any recorded exposure event marks a cohort
    output as decision-influencing (surrogate evaluation, dashboard feedback,
    or an outcome-derived covariate), the same cohort cannot later be
    re-labeled as an independent confirmation set.
    """
    _kind(cohort_id, IdKind.COHORT, "cohort_id")
    _hash(basis_evidence_hash, "basis_evidence_hash")
    if not isinstance(ledger, EvaluationExposureLedger):
        raise EvaluationExposureError("ledger must be an EvaluationExposureLedger")
    influencing = [e for e in ledger.events_for(cohort_id) if e.decision_influenced]
    if influencing:
        classes = sorted({e.output_class.value for e in influencing})
        raise EvaluationExposureError(
            f"cohort {cohort_id} outputs influenced selection decisions "
            f"({', '.join(classes)}); INDEPENDENT_CONFIRMATION is unreachable "
            "for this cohort"
        )
    label = ConfirmationLabel(
        cohort_id=cohort_id,
        label=LABEL_INDEPENDENT_CONFIRMATION,
        basis_evidence_hash=basis_evidence_hash,
        ledger_hash=ledger.ledger_hash(),
    )
    label.validate()
    return label


# ---------------------------------------------------------------------------
# Feature provenance review (acceptance fixture ii)
# ---------------------------------------------------------------------------

FEATURE_PROVENANCE_SCHEMA_VERSION = "rac-feature-provenance/1.0"


class FeatureSourceRole(str, Enum):
    """Roles a source artifact can play in feature computation."""

    RAW_MEASUREMENT = "raw_measurement"
    CALIBRATION_STATE = "calibration_state"
    DESIGN_METADATA = "design_metadata"
    OUTCOME_LABEL = "outcome_label"
    DERIVED_FEATURE = "derived_feature"


#: Source roles permitted for features that feed pre-outcome analysis.
#: OUTCOME_LABEL and DERIVED_FEATURE require explicit downstream review and
#: are never permitted here; DERIVED_FEATURE is transitively unverifiable in
#: v1 and therefore fails closed.
PERMITTED_FEATURE_SOURCES = frozenset({
    FeatureSourceRole.RAW_MEASUREMENT,
    FeatureSourceRole.CALIBRATION_STATE,
    FeatureSourceRole.DESIGN_METADATA,
})


@dataclass(frozen=True)
class FeatureSource:
    """One hash-pinned input to a feature computation."""

    artifact_id: str
    sha256: str
    role: FeatureSourceRole
    consumed_outcome_labels: bool = False

    def validate(self) -> None:
        if not isinstance(self.artifact_id, str) or not self.artifact_id.strip():
            raise EvaluationExposureError("feature source artifact_id is required")
        _hash(self.sha256, "feature source sha256")
        if not isinstance(self.role, FeatureSourceRole):
            raise EvaluationExposureError("feature source role must be a FeatureSourceRole")
        if not isinstance(self.consumed_outcome_labels, bool):
            raise EvaluationExposureError("consumed_outcome_labels must be a bool")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
            "role": self.role.value,
            "consumed_outcome_labels": self.consumed_outcome_labels,
        }


@dataclass(frozen=True)
class FeatureProvenance:
    """Schema-versioned, hash-pinned provenance record for one feature/covariate."""

    feature_id: str
    feature_hash: str
    sources: tuple[FeatureSource, ...]
    synthetic: bool = False
    schema_version: str = FEATURE_PROVENANCE_SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != FEATURE_PROVENANCE_SCHEMA_VERSION:
            raise EvaluationExposureError(
                f"unsupported feature-provenance schema_version: {self.schema_version!r}"
            )
        if not isinstance(self.feature_id, str) or not self.feature_id.strip():
            raise EvaluationExposureError("feature_id is required")
        _hash(self.feature_hash, "feature_hash")
        if not self.sources:
            raise EvaluationExposureError("feature provenance requires >=1 source")
        if not isinstance(self.synthetic, bool):
            raise EvaluationExposureError("synthetic must be a bool")
        for source in self.sources:
            source.validate()

    def provenance_hash(self) -> str:
        self.validate()
        return sha256(_canonical(self.to_dict())).hexdigest()

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "feature_id": self.feature_id,
            "feature_hash": self.feature_hash,
            "synthetic": self.synthetic,
            "sources": [s.to_dict() for s in self.sources],
        }


def review_feature_provenance(feature: FeatureProvenance) -> None:
    """Fail-closed provenance review for a feature used in pre-outcome analysis.

    A feature fails review if ANY source consumed experimental outcome labels,
    has a prohibited/derived role, or is otherwise undeclared.  Synthetic
    features are reviewable but remain labeled ``synthetic`` and can never be
    promoted to measured evidence by this review.
    """
    if not isinstance(feature, FeatureProvenance):
        raise EvaluationExposureError("feature must be a FeatureProvenance")
    feature.validate()
    violations: list[str] = []
    for source in feature.sources:
        if source.consumed_outcome_labels:
            violations.append(
                f"{source.artifact_id}: source consumed experimental outcome labels"
            )
        if source.role not in PERMITTED_FEATURE_SOURCES:
            violations.append(
                f"{source.artifact_id}: source role {source.role.value!r} is not "
                "permitted for pre-outcome features"
            )
    if violations:
        raise EvaluationExposureError(
            "feature provenance review failed: " + "; ".join(violations)
        )

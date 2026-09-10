"""Constraint lineage and scientific-impact classification (Governance Pass 2).

The original prototype exposed ``ConstraintSet`` plus a compact
``classify_migration`` helper.  Governance v1 requires a stronger prospective
path: immutable registration, explicit population/cohort/estimand impact,
preregistered tolerance policy, and an auditable migration decision.  The
prototype helper remains as a compatibility wrapper for existing callers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Mapping

from .ids import GovernanceId, IdKind


class ConstraintImpact(str, Enum):
    NONE = "NONE"
    SEMANTIC_CORRECTION = "SEMANTIC_CORRECTION"
    POPULATION_CHANGE = "POPULATION_CHANGE"
    DEFINITION_CHANGE = "DEFINITION_CHANGE"


class MigrationOutcome(str, Enum):
    NO_IMPACT = "NO_IMPACT"
    MINOR_CORRECTION = "MINOR_CORRECTION"
    BRIDGE_REQUIRED = "BRIDGE_REQUIRED"
    COHORT_INVALIDATION = "COHORT_INVALIDATION"
    NEW_REGIME = "NEW_REGIME"


class EstimandImpact(str, Enum):
    UNCHANGED = "UNCHANGED"
    CHANGED = "CHANGED"


class ConstraintRegistryError(RuntimeError):
    """Raised when immutable constraint lineage cannot be registered safely."""


class FrozenArtifactMutationError(RuntimeError):
    """Raised when a migration attempts to alter a protected frozen D2 input."""


def _require_sha256(value: str, field: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{field} must be a lowercase sha256")


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _canonical_constraint_id(value: str) -> str:
    parsed = GovernanceId.parse(value)
    if parsed.kind is not IdKind.CONSTRAINT:
        raise ValueError("constraint identifier must be RAC-CS-*")
    return parsed.canonical


def _require_utc(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field} must be UTC")


@dataclass(frozen=True)
class ConstraintSet:
    """Immutable scientific constraint-set artifact.

    The first eight fields preserve the pre-adoption positional API.
    ``encoder_version`` was added by the adopted contract and defaults only for
    read compatibility with prototype fixtures.  Prospective registry writes
    require it explicitly via ``validate(adopted=True)``.
    """

    constraint_id: str
    parent_id: str | None
    semantic_hash: str
    rules_hash: str
    encoder_hash: str
    projection_version: str
    software_version: str
    impact: ConstraintImpact
    encoder_version: str = "legacy-unspecified"

    @property
    def constraint_set_id(self) -> str:
        return _canonical_constraint_id(self.constraint_id)

    @property
    def parent_constraint_set_id(self) -> str | None:
        return (
            _canonical_constraint_id(self.parent_id)
            if self.parent_id is not None
            else None
        )

    @property
    def scientific_projection_version(self) -> str:
        return self.projection_version

    @property
    def scientific_impact(self) -> ConstraintImpact:
        return self.impact

    def validate(self, *, adopted: bool = False) -> None:
        _canonical_constraint_id(self.constraint_id)
        if self.parent_id is not None:
            _canonical_constraint_id(self.parent_id)
        for name in ("semantic_hash", "rules_hash", "encoder_hash"):
            _require_sha256(getattr(self, name), name)
        if not self.projection_version or not self.software_version:
            raise ValueError("projection_version and software_version are required")
        if not isinstance(self.impact, ConstraintImpact):
            raise ValueError("impact must be a ConstraintImpact")
        if not isinstance(self.encoder_version, str) or not self.encoder_version:
            raise ValueError("encoder_version is required")
        if adopted and self.encoder_version == "legacy-unspecified":
            raise ValueError(
                "prospective Governance v1 constraint sets require encoder_version"
            )

    def to_dict(self) -> dict[str, str | None]:
        """Serialize with the canonical field names from Governance v1 §6."""
        self.validate(adopted=True)
        return {
            "constraint_set_id": self.constraint_set_id,
            "software_version": self.software_version,
            "parent_constraint_set_id": self.parent_constraint_set_id,
            "semantic_hash": self.semantic_hash,
            "rules_hash": self.rules_hash,
            "encoder_version": self.encoder_version,
            "encoder_hash": self.encoder_hash,
            "scientific_projection_version": self.projection_version,
            "scientific_impact": self.impact.value,
        }


class ConstraintSetRegistry:
    """Append-only in-memory registry keyed by canonical constraint identity."""

    def __init__(self) -> None:
        self._records: dict[str, ConstraintSet] = {}

    @property
    def records(self) -> tuple[ConstraintSet, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def add(self, constraint_set: ConstraintSet) -> ConstraintSet:
        constraint_set.validate(adopted=True)
        canonical_id = constraint_set.constraint_set_id
        if canonical_id in self._records:
            raise ConstraintRegistryError(
                f"constraint set already registered: {canonical_id}"
            )
        parent_id = constraint_set.parent_constraint_set_id
        if parent_id is not None and parent_id not in self._records:
            raise ConstraintRegistryError(
                f"parent constraint set must already be registered: {parent_id}"
            )
        self._records[canonical_id] = constraint_set
        return constraint_set

    def get(self, constraint_id: str) -> ConstraintSet:
        canonical_id = _canonical_constraint_id(constraint_id)
        try:
            return self._records[canonical_id]
        except KeyError as exc:
            raise ConstraintRegistryError(
                f"unknown constraint set: {canonical_id}"
            ) from exc

    def children(self, constraint_id: str) -> tuple[ConstraintSet, ...]:
        canonical_id = _canonical_constraint_id(constraint_id)
        return tuple(
            record
            for record in self.records
            if record.parent_constraint_set_id == canonical_id
        )

    def to_json(self) -> str:
        return _canonical_json(
            {"schema_version": "1.0", "constraint_sets": [r.to_dict() for r in self.records]}
        ) + "\n"


@dataclass(frozen=True)
class TolerancePolicy:
    """Preregistered numerical materiality policy for one constraint family."""

    constraint_family: str
    created_at: str
    max_population_displacement: float
    max_cohort_change_fraction: float
    registered_before_outcomes: bool
    version: str = "1.0"

    def validate(self) -> None:
        if not isinstance(self.constraint_family, str) or not self.constraint_family.strip():
            raise ValueError("constraint_family is required")
        _require_utc(self.created_at, "created_at")
        for field in (
            "max_population_displacement",
            "max_cohort_change_fraction",
        ):
            value = getattr(self, field)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{field} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{field} must be in [0, 1]")
        if self.registered_before_outcomes is not True:
            raise ValueError(
                "tolerance policy must be preregistered before outcome inspection"
            )
        if not self.version:
            raise ValueError("version is required")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return asdict(self)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical_json(self.to_dict()).encode()).hexdigest()


@dataclass(frozen=True)
class MigrationImpactAnalysis:
    """Three-axis historical-impact analysis required before evidence reuse."""

    constraint_family: str
    population_displacement: float
    cohort_changed_count: int
    cohort_total_count: int
    estimand_impact: EstimandImpact

    def validate(self) -> None:
        if not isinstance(self.constraint_family, str) or not self.constraint_family.strip():
            raise ValueError("constraint_family is required")
        if (
            not isinstance(self.population_displacement, (int, float))
            or isinstance(self.population_displacement, bool)
            or not 0.0 <= float(self.population_displacement) <= 1.0
        ):
            raise ValueError("population_displacement must be in [0, 1]")
        for name in ("cohort_changed_count", "cohort_total_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.cohort_changed_count > self.cohort_total_count:
            raise ValueError("cohort_changed_count cannot exceed cohort_total_count")
        if not isinstance(self.estimand_impact, EstimandImpact):
            raise ValueError("estimand_impact must be an EstimandImpact")

    @property
    def cohort_change_fraction(self) -> float:
        if self.cohort_total_count == 0:
            return 0.0
        return self.cohort_changed_count / self.cohort_total_count


@dataclass(frozen=True)
class MigrationDecisionRecord:
    old_constraint_set_id: str
    new_constraint_set_id: str
    scientific_impact: ConstraintImpact
    population_displacement: float
    cohort_changed_count: int
    cohort_total_count: int
    cohort_change_fraction: float
    estimand_impact: EstimandImpact
    tolerance_policy_sha256: str
    outcome: MigrationOutcome

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["scientific_impact"] = self.scientific_impact.value
        payload["estimand_impact"] = self.estimand_impact.value
        payload["outcome"] = self.outcome.value
        return payload


def _require_parent_link(old: ConstraintSet, new: ConstraintSet) -> None:
    old.validate()
    new.validate()
    if new.parent_constraint_set_id != old.constraint_set_id:
        raise ValueError(
            "new constraint set must reference old constraint_set_id as parent"
        )


def assess_migration(
    old: ConstraintSet,
    new: ConstraintSet,
    *,
    analysis: MigrationImpactAnalysis,
    tolerance_policy: TolerancePolicy,
) -> MigrationDecisionRecord:
    """Classify a migration from explicit, preregistered three-axis evidence.

    Semantic redefinition or estimand change always creates a new regime;
    numerical tolerances can never override that decision.
    """
    _require_parent_link(old, new)
    old.validate(adopted=True)
    new.validate(adopted=True)
    analysis.validate()
    tolerance_policy.validate()
    if analysis.constraint_family != tolerance_policy.constraint_family:
        raise ValueError(
            "impact analysis and tolerance policy must name the same constraint family"
        )

    population = float(analysis.population_displacement)
    cohort_fraction = analysis.cohort_change_fraction

    if (
        new.impact is ConstraintImpact.DEFINITION_CHANGE
        or analysis.estimand_impact is EstimandImpact.CHANGED
    ):
        outcome = MigrationOutcome.NEW_REGIME
    elif new.impact is ConstraintImpact.NONE:
        if (old.semantic_hash, old.rules_hash, old.projection_version) != (
            new.semantic_hash,
            new.rules_hash,
            new.projection_version,
        ):
            raise ValueError(
                "impact NONE is incompatible with scientific-semantic changes"
            )
        if population != 0.0 or analysis.cohort_changed_count != 0:
            raise ValueError(
                "impact NONE is incompatible with measured population/cohort impact"
            )
        outcome = MigrationOutcome.NO_IMPACT
    elif new.impact is ConstraintImpact.POPULATION_CHANGE:
        if cohort_fraction > tolerance_policy.max_cohort_change_fraction:
            outcome = MigrationOutcome.COHORT_INVALIDATION
        else:
            outcome = MigrationOutcome.BRIDGE_REQUIRED
    elif new.impact is ConstraintImpact.SEMANTIC_CORRECTION:
        if cohort_fraction > tolerance_policy.max_cohort_change_fraction:
            outcome = MigrationOutcome.COHORT_INVALIDATION
        elif (
            population > tolerance_policy.max_population_displacement
            or analysis.cohort_changed_count > 0
        ):
            outcome = MigrationOutcome.BRIDGE_REQUIRED
        else:
            outcome = MigrationOutcome.MINOR_CORRECTION
    else:  # pragma: no cover - enum exhaustiveness guard
        raise ValueError(f"unsupported scientific impact: {new.impact!r}")

    return MigrationDecisionRecord(
        old_constraint_set_id=old.constraint_set_id,
        new_constraint_set_id=new.constraint_set_id,
        scientific_impact=new.impact,
        population_displacement=population,
        cohort_changed_count=analysis.cohort_changed_count,
        cohort_total_count=analysis.cohort_total_count,
        cohort_change_fraction=cohort_fraction,
        estimand_impact=analysis.estimand_impact,
        tolerance_policy_sha256=tolerance_policy.sha256,
        outcome=outcome,
    )


def classify_migration(
    old: ConstraintSet,
    new: ConstraintSet,
    *,
    historical_population_changed: bool = False,
) -> MigrationOutcome:
    """Backward-compatible prototype classifier.

    New prospective governance code should use :func:`assess_migration`, which
    requires the full three-axis analysis and a preregistered tolerance policy.
    """
    _require_parent_link(old, new)
    if new.impact is ConstraintImpact.DEFINITION_CHANGE:
        return MigrationOutcome.NEW_REGIME
    if new.impact is ConstraintImpact.POPULATION_CHANGE:
        return (
            MigrationOutcome.COHORT_INVALIDATION
            if historical_population_changed
            else MigrationOutcome.BRIDGE_REQUIRED
        )
    if new.impact is ConstraintImpact.SEMANTIC_CORRECTION:
        return (
            MigrationOutcome.BRIDGE_REQUIRED
            if historical_population_changed
            else MigrationOutcome.MINOR_CORRECTION
        )
    if (old.semantic_hash, old.rules_hash, old.projection_version) != (
        new.semantic_hash,
        new.rules_hash,
        new.projection_version,
    ):
        raise ValueError("impact NONE is incompatible with scientific-semantic changes")
    return MigrationOutcome.NO_IMPACT


FROZEN_D2_ARTIFACT_IDS = frozenset(
    {
        "RAC-PER-D2-0003",
        "RAC-PER-D2-0004",
        "RAC-PER-D2-0005-PREREGISTRATION",
    }
)


def assert_frozen_d2_artifacts_unchanged(
    before_hashes: Mapping[str, str],
    after_hashes: Mapping[str, str],
) -> None:
    """Fail closed if any protected pre-Governance D2 input was rewritten.

    Callers supply content hashes taken before and after a migration operation.
    All protected artifacts must be present in both snapshots and byte-identical.
    """
    for artifact_id in sorted(FROZEN_D2_ARTIFACT_IDS):
        if artifact_id not in before_hashes or artifact_id not in after_hashes:
            raise FrozenArtifactMutationError(
                f"missing protected frozen artifact snapshot: {artifact_id}"
            )
        before = before_hashes[artifact_id]
        after = after_hashes[artifact_id]
        try:
            _require_sha256(before, f"before_hashes[{artifact_id!r}]")
            _require_sha256(after, f"after_hashes[{artifact_id!r}]")
        except ValueError as exc:
            raise FrozenArtifactMutationError(str(exc)) from exc
        if before != after:
            raise FrozenArtifactMutationError(
                f"frozen D2 artifact changed during migration: {artifact_id}"
            )

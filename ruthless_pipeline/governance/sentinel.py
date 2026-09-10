"""Sentinel, calibration-isolation, and pipeline-bridge primitives (Governance Pass 4).

These types govern *how* already-selected specimens are re-evaluated. They do
not contain outcome values and deliberately cannot consume prior-wave labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable, Mapping

from .ids import GovernanceId, IdKind
from .seal import CohortSeal


_SHA256_HEX = frozenset("0123456789abcdef")


class SentinelGovernanceError(RuntimeError):
    pass


def _require_kind(raw: str, kind: IdKind, field: str) -> None:
    parsed = GovernanceId.parse(raw)
    if parsed.kind is not kind:
        raise SentinelGovernanceError(f"{field} must be RAC-{kind.value}-...")


def _sha256(value: str, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in _SHA256_HEX for c in value):
        raise SentinelGovernanceError(f"{field} must be a lowercase sha256")


def _seed(value: int, field: str = "seed") -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value < 2**32):
        raise SentinelGovernanceError(f"{field} must be an integer in [0, 2^32)")


@dataclass(frozen=True)
class SentinelCohort:
    """Immutable anchor selected from one sealed source cohort at Wave N."""

    sentinel_id: str
    source_wave_id: str
    source_cohort_id: str
    experiment_id: str
    constraint_id: str
    specimen_ids: tuple[str, ...]
    selection_seed: int
    selection_policy_hash: str
    source_manifest_hash: str

    def validate(self) -> None:
        _require_kind(self.sentinel_id, IdKind.SENTINEL, "sentinel_id")
        _require_kind(self.source_cohort_id, IdKind.COHORT, "source_cohort_id")
        _require_kind(self.experiment_id, IdKind.EXPERIMENT, "experiment_id")
        _require_kind(self.constraint_id, IdKind.CONSTRAINT, "constraint_id")
        if not self.source_wave_id:
            raise SentinelGovernanceError("source_wave_id is required")
        if not self.specimen_ids or len(self.specimen_ids) != len(set(self.specimen_ids)):
            raise SentinelGovernanceError("sentinel specimen_ids must be non-empty and unique")
        _seed(self.selection_seed, "selection_seed")
        _sha256(self.selection_policy_hash, "selection_policy_hash")
        _sha256(self.source_manifest_hash, "source_manifest_hash")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": "1.0",
            "sentinel_id": self.sentinel_id,
            "source_wave_id": self.source_wave_id,
            "source_cohort_id": self.source_cohort_id,
            "experiment_id": self.experiment_id,
            "constraint_id": self.constraint_id,
            "specimen_ids": list(self.specimen_ids),
            "selection_seed": self.selection_seed,
            "selection_policy_hash": self.selection_policy_hash,
            "source_manifest_hash": self.source_manifest_hash,
        }


class SentinelRegistry:
    """Append-only sentinel registry: a source wave can be anchored exactly once."""

    def __init__(self) -> None:
        self._by_id: dict[str, SentinelCohort] = {}
        self._by_wave: dict[str, str] = {}

    def register(self, sentinel: SentinelCohort) -> None:
        sentinel.validate()
        if sentinel.sentinel_id in self._by_id:
            raise SentinelGovernanceError(f"duplicate sentinel_id: {sentinel.sentinel_id}")
        if sentinel.source_wave_id in self._by_wave:
            existing = self._by_wave[sentinel.source_wave_id]
            raise SentinelGovernanceError(
                f"source wave {sentinel.source_wave_id!r} already anchored by {existing}; "
                "sentinel resampling is forbidden"
            )
        self._by_id[sentinel.sentinel_id] = sentinel
        self._by_wave[sentinel.source_wave_id] = sentinel.sentinel_id

    def get(self, sentinel_id: str) -> SentinelCohort:
        try:
            return self._by_id[sentinel_id]
        except KeyError as exc:
            raise KeyError(f"unknown sentinel_id: {sentinel_id}") from exc


def create_sentinel(
    *,
    sentinel_id: str,
    source_wave_id: str,
    source_seal: CohortSeal,
    cohort_manifest: Mapping[str, object],
    specimen_ids: Iterable[str],
    selection_seed: int,
    selection_policy_hash: str,
) -> SentinelCohort:
    """Create a sentinel from a sealed cohort without re-sampling it later."""

    if source_seal.state != "SEALED":
        raise SentinelGovernanceError("sentinel source cohort must be SEALED")
    manifest_hash = sha256(
        json.dumps(dict(cohort_manifest), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if manifest_hash != source_seal.manifest_hash:
        raise SentinelGovernanceError("cohort manifest hash does not match source seal")
    if cohort_manifest.get("cohort_id") != source_seal.cohort_id:
        raise SentinelGovernanceError("cohort manifest does not match source seal")
    if cohort_manifest.get("constraint_id") != source_seal.constraint_id:
        raise SentinelGovernanceError("constraint_id does not match source seal")
    available = cohort_manifest.get("specimen_ids")
    if not isinstance(available, list):
        raise SentinelGovernanceError("cohort manifest specimen_ids must be a list")
    selected = tuple(specimen_ids)
    if not selected or not set(selected).issubset(set(available)):
        raise SentinelGovernanceError("sentinel specimens must be a non-empty subset of the sealed cohort")
    sentinel = SentinelCohort(
        sentinel_id=sentinel_id,
        source_wave_id=source_wave_id,
        source_cohort_id=source_seal.cohort_id,
        experiment_id=source_seal.experiment_id,
        constraint_id=source_seal.constraint_id,
        specimen_ids=selected,
        selection_seed=selection_seed,
        selection_policy_hash=selection_policy_hash,
        source_manifest_hash=source_seal.manifest_hash,
    )
    sentinel.validate()
    return sentinel


class PreprocessingMode(str, Enum):
    STATELESS = "STATELESS"
    CALIBRATED = "CALIBRATED"


@dataclass(frozen=True)
class CalibrationState:
    """Frozen preprocessing/calibration state fitted without sentinel outcomes."""

    calibration_id: str
    member_ids: tuple[str, ...]
    state_hash: str
    source_manifest_hash: str
    random_seed: int
    outcome_labels_consumed: bool = False

    def validate(self) -> None:
        _require_kind(self.calibration_id, IdKind.CALIBRATION, "calibration_id")
        if not self.member_ids or len(self.member_ids) != len(set(self.member_ids)):
            raise SentinelGovernanceError("calibration member_ids must be non-empty and unique")
        _sha256(self.state_hash, "state_hash")
        _sha256(self.source_manifest_hash, "source_manifest_hash")
        _seed(self.random_seed, "calibration random_seed")
        if self.outcome_labels_consumed:
            raise SentinelGovernanceError("calibration state may not consume experimental outcome labels")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": "1.0",
            "calibration_id": self.calibration_id,
            "member_ids": list(self.member_ids),
            "state_hash": self.state_hash,
            "source_manifest_hash": self.source_manifest_hash,
            "random_seed": self.random_seed,
            "outcome_labels_consumed": self.outcome_labels_consumed,
        }


@dataclass(frozen=True)
class EvaluationPipeline:
    """Frozen evaluation initialization contract for sentinel remeasurement."""

    pipeline_id: str
    software_version: str
    code_hash: str
    detector_hash: str
    preprocessing_hash: str
    random_seed: int
    preprocessing_mode: PreprocessingMode
    calibration_id: str | None = None
    calibration_state_hash: str | None = None
    prior_outcome_access: bool = False

    def validate(self) -> None:
        _require_kind(self.pipeline_id, IdKind.PIPELINE, "pipeline_id")
        if not self.software_version:
            raise SentinelGovernanceError("software_version is required")
        for field in ("code_hash", "detector_hash", "preprocessing_hash"):
            _sha256(getattr(self, field), field)
        _seed(self.random_seed, "pipeline random_seed")
        if self.prior_outcome_access:
            raise SentinelGovernanceError("sentinel pipeline may not access prior-wave outcomes")
        if self.preprocessing_mode is PreprocessingMode.STATELESS:
            if self.calibration_id is not None or self.calibration_state_hash is not None:
                raise SentinelGovernanceError("stateless preprocessing cannot bind calibration state")
        elif self.preprocessing_mode is PreprocessingMode.CALIBRATED:
            if self.calibration_id is None or self.calibration_state_hash is None:
                raise SentinelGovernanceError("calibrated preprocessing requires calibration_id and state hash")
            _require_kind(self.calibration_id, IdKind.CALIBRATION, "calibration_id")
            _sha256(self.calibration_state_hash, "calibration_state_hash")
        else:
            raise SentinelGovernanceError("unknown preprocessing_mode")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": "1.0",
            "pipeline_id": self.pipeline_id,
            "software_version": self.software_version,
            "code_hash": self.code_hash,
            "detector_hash": self.detector_hash,
            "preprocessing_hash": self.preprocessing_hash,
            "random_seed": self.random_seed,
            "preprocessing_mode": self.preprocessing_mode.value,
            "calibration_id": self.calibration_id,
            "calibration_state_hash": self.calibration_state_hash,
            "prior_outcome_access": self.prior_outcome_access,
        }

    @property
    def fingerprint(self) -> tuple[object, ...]:
        self.validate()
        return (
            self.software_version,
            self.code_hash,
            self.detector_hash,
            self.preprocessing_hash,
            self.random_seed,
            self.preprocessing_mode.value,
            self.calibration_id,
            self.calibration_state_hash,
        )


def validate_blind_sentinel_evaluation(
    sentinel: SentinelCohort,
    pipeline: EvaluationPipeline,
    *,
    calibration: CalibrationState | None = None,
    bridge_ids: Iterable[str] = (),
    treatment_ids: Iterable[str] = (),
    heldout_ids: Iterable[str] = (),
) -> None:
    """Fail closed on blind-but-biased sentinel initialization."""

    sentinel.validate()
    pipeline.validate()
    if pipeline.preprocessing_mode is PreprocessingMode.CALIBRATED:
        if calibration is None:
            raise SentinelGovernanceError("calibrated sentinel evaluation requires frozen calibration state")
        calibration.validate()
        if calibration.calibration_id != pipeline.calibration_id:
            raise SentinelGovernanceError("pipeline calibration_id does not match calibration state")
        if calibration.state_hash != pipeline.calibration_state_hash:
            raise SentinelGovernanceError("pipeline calibration state hash mismatch")
        forbidden = set(sentinel.specimen_ids) | set(bridge_ids) | set(treatment_ids) | set(heldout_ids)
        overlap = set(calibration.member_ids) & forbidden
        if overlap:
            raise SentinelGovernanceError(
                "calibration set overlaps sentinel/bridge/treatment/held-out membership: "
                + ", ".join(sorted(overlap))
            )
    elif calibration is not None:
        raise SentinelGovernanceError("stateless sentinel pipeline must not receive calibration state")


@dataclass(frozen=True)
class PipelineBridgePlan:
    bridge_id: str
    sentinel_id: str
    old_pipeline_id: str
    new_pipeline_id: str
    paired_evaluation_required: bool = True

    def validate(self) -> None:
        _require_kind(self.bridge_id, IdKind.BRIDGE, "bridge_id")
        _require_kind(self.sentinel_id, IdKind.SENTINEL, "sentinel_id")
        _require_kind(self.old_pipeline_id, IdKind.PIPELINE, "old_pipeline_id")
        _require_kind(self.new_pipeline_id, IdKind.PIPELINE, "new_pipeline_id")
        if self.old_pipeline_id == self.new_pipeline_id:
            raise SentinelGovernanceError("pipeline bridge requires distinct old/new pipeline ids")
        if not self.paired_evaluation_required:
            raise SentinelGovernanceError("pipeline bridge must require paired sentinel evaluation")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": "1.0",
            "bridge_id": self.bridge_id,
            "sentinel_id": self.sentinel_id,
            "old_pipeline_id": self.old_pipeline_id,
            "new_pipeline_id": self.new_pipeline_id,
            "paired_evaluation_required": self.paired_evaluation_required,
        }


def pipeline_change_requires_bridge(old: EvaluationPipeline, new: EvaluationPipeline) -> bool:
    old.validate()
    new.validate()
    return old.fingerprint != new.fingerprint


def validate_pipeline_transition(
    old: EvaluationPipeline,
    new: EvaluationPipeline,
    *,
    sentinel: SentinelCohort,
    bridge: PipelineBridgePlan | None,
) -> None:
    """Require an explicit paired bridge whenever evaluation initialization changes."""

    changed = pipeline_change_requires_bridge(old, new)
    if not changed:
        if bridge is not None:
            raise SentinelGovernanceError("pipeline bridge supplied even though pipeline fingerprint is unchanged")
        return
    if bridge is None:
        raise SentinelGovernanceError("pipeline change requires an explicit pipeline bridge")
    bridge.validate()
    if bridge.sentinel_id != sentinel.sentinel_id:
        raise SentinelGovernanceError("pipeline bridge must evaluate the frozen sentinel")
    if bridge.old_pipeline_id != old.pipeline_id or bridge.new_pipeline_id != new.pipeline_id:
        raise SentinelGovernanceError("pipeline bridge does not bind the supplied old/new pipelines")

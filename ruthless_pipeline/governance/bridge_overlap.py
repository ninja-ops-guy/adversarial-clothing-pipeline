"""Pass 4 sentinel, bridge, calibration-isolation, and overlap decision engine.

Prospective/additive only. This module never reads held-out outcomes and never
mutates frozen experiment artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable


class RegimeDecision(str, Enum):
    COMPARABLE = "COMPARABLE"
    BRIDGE_REQUIRED = "BRIDGE_REQUIRED"
    REGIME_RESET = "REGIME_RESET"


class BridgeGovernanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class SentinelRecord:
    wave_id: str
    specimen_ids: tuple[str, ...]
    frozen_seed: int
    pipeline_hash: str
    calibration_set_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.wave_id or not self.specimen_ids:
            raise BridgeGovernanceError("wave_id and non-empty sentinel specimen_ids required")
        if len(set(self.specimen_ids)) != len(self.specimen_ids):
            raise BridgeGovernanceError("duplicate sentinel specimen id")
        overlap = set(self.specimen_ids) & set(self.calibration_set_ids)
        if overlap:
            raise BridgeGovernanceError(f"calibration set overlaps sentinel: {sorted(overlap)}")
        if len(self.pipeline_hash) != 64:
            raise BridgeGovernanceError("pipeline_hash must be sha256 hex")

    @property
    def sentinel_hash(self) -> str:
        self.validate()
        payload = {
            "wave_id": self.wave_id,
            "specimen_ids": list(self.specimen_ids),
            "frozen_seed": self.frozen_seed,
            "pipeline_hash": self.pipeline_hash,
            "calibration_set_ids": list(self.calibration_set_ids),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class OverlapEstimate:
    old_support_fraction: float
    new_support_fraction: float
    policy_overlap: float
    ci_low: float
    ci_high: float
    material_strata_covered: bool
    estimator: str

    def validate(self) -> None:
        for name, value in (
            ("old_support_fraction", self.old_support_fraction),
            ("new_support_fraction", self.new_support_fraction),
            ("policy_overlap", self.policy_overlap),
            ("ci_low", self.ci_low),
            ("ci_high", self.ci_high),
        ):
            if not 0.0 <= value <= 1.0:
                raise BridgeGovernanceError(f"{name} must be in [0,1]")
        if self.ci_low > self.ci_high:
            raise BridgeGovernanceError("invalid confidence interval")
        if not self.estimator:
            raise BridgeGovernanceError("estimator identity required")


def assert_calibration_isolation(*, calibration_ids: Iterable[str], sentinel_ids: Iterable[str], bridge_ids: Iterable[str], treatment_ids: Iterable[str], held_out_ids: Iterable[str]) -> None:
    """Fail closed if calibration intersects any scientific evaluation surface."""
    calibration = set(calibration_ids)
    forbidden = set(sentinel_ids) | set(bridge_ids) | set(treatment_ids) | set(held_out_ids)
    overlap = sorted(calibration & forbidden)
    if overlap:
        raise BridgeGovernanceError(f"calibration leakage into governed cohort: {overlap}")


def require_blind_re_evaluation(*, prior_outcome_ids: Iterable[str], initialization_input_ids: Iterable[str]) -> None:
    """Reject Wave N+1 initialization that consumes Wave N outcome artifacts."""
    leaked = sorted(set(prior_outcome_ids) & set(initialization_input_ids))
    if leaked:
        raise BridgeGovernanceError(f"prior-wave outcome leakage: {leaked}")


def classify_regime(estimate: OverlapEstimate, *, min_support: float = 0.70, min_policy_overlap: float = 0.60) -> RegimeDecision:
    """Classify comparability using preregistered-style thresholds.

    Thresholds are caller-supplied policy values, not scientific constants.
    Uncertainty is treated conservatively by using the lower CI bound.
    """
    estimate.validate()
    if not estimate.material_strata_covered:
        return RegimeDecision.REGIME_RESET
    if min(estimate.old_support_fraction, estimate.new_support_fraction, estimate.ci_low) < min_support:
        return RegimeDecision.REGIME_RESET
    if estimate.policy_overlap < min_policy_overlap:
        return RegimeDecision.BRIDGE_REQUIRED
    return RegimeDecision.COMPARABLE


def require_pooling_legal(decision: RegimeDecision) -> None:
    if decision is RegimeDecision.REGIME_RESET:
        raise BridgeGovernanceError("naive pooling forbidden after regime reset")

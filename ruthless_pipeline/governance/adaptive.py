"""Adaptive CTM governance using only sealed prior-wave evidence.

Pass 7 keeps the temporal firewall mechanical: a policy for Wave N+1 may be
informed only by a sealed Wave N evidence artifact, and the complete policy
(including constrained/chaos allocation) is frozen before Wave N+1 sampling.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Any, Mapping


class AdaptiveGovernanceError(RuntimeError):
    pass


class PolicyState(str, Enum):
    PROPOSED = "PROPOSED"
    FROZEN = "FROZEN"


@dataclass(frozen=True)
class EvidenceSeal:
    wave_id: str
    seal_id: str
    evidence_hash: str
    state: str = "SEALED"

    def validate(self) -> None:
        if not self.wave_id or not self.seal_id:
            raise AdaptiveGovernanceError("evidence wave_id and seal_id are required")
        if self.state != "SEALED":
            raise AdaptiveGovernanceError("unsealed prior wave cannot drive adaptation")
        if (
            not isinstance(self.evidence_hash, str)
            or len(self.evidence_hash) != 64
            or any(ch not in "0123456789abcdefABCDEF" for ch in self.evidence_hash)
        ):
            raise AdaptiveGovernanceError("evidence_hash must be sha256 hex")


@dataclass(frozen=True)
class AllocationPolicy:
    """Frozen next-wave allocation between governed and chaos exploration lanes."""

    constrained_fraction: float
    chaos_fraction: float
    version: str
    stopping_rule: str
    reallocation_rule: str

    def validate(self) -> None:
        for name, value in (
            ("constrained_fraction", self.constrained_fraction),
            ("chaos_fraction", self.chaos_fraction),
        ):
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise AdaptiveGovernanceError(f"{name} must be finite")
            if not 0.0 <= float(value) <= 1.0:
                raise AdaptiveGovernanceError(f"{name} must be in [0,1]")
        if not math.isclose(
            float(self.constrained_fraction) + float(self.chaos_fraction),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise AdaptiveGovernanceError(
                "constrained_fraction + chaos_fraction must equal 1"
            )
        if not self.version.strip():
            raise AdaptiveGovernanceError("allocation policy version is required")
        if not self.stopping_rule.strip() or not self.reallocation_rule.strip():
            raise AdaptiveGovernanceError(
                "allocation stopping and reallocation rules must be preregistered"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "constrained_fraction": float(self.constrained_fraction),
            "chaos_fraction": float(self.chaos_fraction),
            "version": self.version,
            "stopping_rule": self.stopping_rule,
            "reallocation_rule": self.reallocation_rule,
        }


@dataclass(frozen=True)
class FrozenPolicy:
    source_wave_id: str
    target_wave_id: str
    source_seal_id: str
    policy_hash: str
    policy: Mapping[str, Any]
    source_evidence_hash: str = ""
    allocation: AllocationPolicy | None = None
    state: PolicyState = PolicyState.FROZEN


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def propose_next_wave_policy(
    *,
    prior: EvidenceSeal,
    target_wave_id: str,
    policy: Mapping[str, Any],
    current_wave_outcomes: Mapping[str, Any] | None = None,
    allocation: AllocationPolicy | None = None,
) -> FrozenPolicy:
    """Freeze a Wave N+1 policy from a sealed Wave N evidence artifact.

    ``current_wave_outcomes`` is a tripwire, not an optional source.  Supplying
    it at all (including an empty mapping) is rejected so a caller cannot blur
    the temporal boundary by passing a current-wave outcome container that just
    happens to be empty at freeze time.
    """
    prior.validate()
    if current_wave_outcomes is not None:
        raise AdaptiveGovernanceError(
            "current-wave outcomes cannot tune current-wave policy"
        )
    if not isinstance(target_wave_id, str) or not target_wave_id.strip():
        raise AdaptiveGovernanceError("target_wave_id is required")
    if target_wave_id == prior.wave_id:
        raise AdaptiveGovernanceError("adaptive policy must target a later wave")
    if not isinstance(policy, Mapping):
        raise AdaptiveGovernanceError("policy must be a mapping")
    if allocation is not None:
        allocation.validate()

    frozen_policy = dict(policy)
    allocation_payload = allocation.to_dict() if allocation is not None else None
    material = {
        "source_wave_id": prior.wave_id,
        "target_wave_id": target_wave_id,
        "source_seal_id": prior.seal_id,
        "evidence_hash": prior.evidence_hash,
        "policy": frozen_policy,
        "allocation": allocation_payload,
    }
    return FrozenPolicy(
        source_wave_id=prior.wave_id,
        target_wave_id=target_wave_id,
        source_seal_id=prior.seal_id,
        policy_hash=_digest(material),
        policy=frozen_policy,
        source_evidence_hash=prior.evidence_hash,
        allocation=allocation,
    )


def freeze_allocation_policy(
    *,
    prior: EvidenceSeal,
    target_wave_id: str,
    constrained_fraction: float,
    chaos_fraction: float,
    version: str,
    stopping_rule: str,
    reallocation_rule: str,
    policy: Mapping[str, Any] | None = None,
    current_wave_outcomes: Mapping[str, Any] | None = None,
) -> FrozenPolicy:
    """Freeze an adaptive allocation without a fixed universal 70/20/10 split."""
    allocation = AllocationPolicy(
        constrained_fraction=constrained_fraction,
        chaos_fraction=chaos_fraction,
        version=version,
        stopping_rule=stopping_rule,
        reallocation_rule=reallocation_rule,
    )
    return propose_next_wave_policy(
        prior=prior,
        target_wave_id=target_wave_id,
        policy=policy or {},
        current_wave_outcomes=current_wave_outcomes,
        allocation=allocation,
    )


def require_policy_frozen_before_sampling(
    policy: FrozenPolicy,
    target_wave_id: str,
) -> None:
    if policy.state is not PolicyState.FROZEN or policy.target_wave_id != target_wave_id:
        raise AdaptiveGovernanceError(
            "sampling requires a frozen policy for this wave"
        )
    if not policy.source_evidence_hash:
        raise AdaptiveGovernanceError(
            "sampling requires policy provenance to a sealed evidence hash"
        )
    if policy.allocation is not None:
        policy.allocation.validate()

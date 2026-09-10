"""Adaptive CTM governance using only sealed prior-wave evidence."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Any
import hashlib, json

class AdaptiveGovernanceError(RuntimeError): pass
class PolicyState(str, Enum):
    PROPOSED="PROPOSED"; FROZEN="FROZEN"

@dataclass(frozen=True)
class EvidenceSeal:
    wave_id: str
    seal_id: str
    evidence_hash: str
    state: str = "SEALED"

@dataclass(frozen=True)
class FrozenPolicy:
    source_wave_id: str
    target_wave_id: str
    source_seal_id: str
    policy_hash: str
    policy: Mapping[str, Any]
    state: PolicyState = PolicyState.FROZEN

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def propose_next_wave_policy(*, prior: EvidenceSeal, target_wave_id: str, policy: Mapping[str, Any], current_wave_outcomes: Mapping[str, Any] | None = None) -> FrozenPolicy:
    if prior.state != "SEALED":
        raise AdaptiveGovernanceError("unsealed prior wave cannot drive adaptation")
    if current_wave_outcomes:
        raise AdaptiveGovernanceError("current-wave outcomes cannot tune current-wave policy")
    if target_wave_id == prior.wave_id:
        raise AdaptiveGovernanceError("adaptive policy must target a later wave")
    material={"source_wave_id":prior.wave_id,"target_wave_id":target_wave_id,"source_seal_id":prior.seal_id,"evidence_hash":prior.evidence_hash,"policy":policy}
    return FrozenPolicy(prior.wave_id,target_wave_id,prior.seal_id,_digest(material),dict(policy))

def require_policy_frozen_before_sampling(policy: FrozenPolicy, target_wave_id: str) -> None:
    if policy.state is not PolicyState.FROZEN or policy.target_wave_id != target_wave_id:
        raise AdaptiveGovernanceError("sampling requires a frozen policy for this wave")

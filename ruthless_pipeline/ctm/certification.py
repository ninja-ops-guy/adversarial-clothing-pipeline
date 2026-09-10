"""CTM-A claim certification gate."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import CTMClaim, CTMClaimState, validate_anti_optimization_invariant
from .firewall import FirewallResult, require_provenance_firewall
from .nulls import MatchedNullDesign


@dataclass(frozen=True)
class CTMCertificationResult:
    claim_id: str
    claim_state: CTMClaimState
    certified: bool
    firewall: FirewallResult
    matched_nulls_verified: tuple[str, ...]


def certify_ctm_claim(
    claim: CTMClaim,
    *,
    provenance_graph: dict,
    matched_nulls: tuple[MatchedNullDesign, ...] = (),
) -> CTMCertificationResult:
    """Fail closed unless all CTM-A invariants are mechanically satisfied."""
    claim.validate()
    validate_anti_optimization_invariant(claim)
    firewall = require_provenance_firewall(claim, provenance_graph)

    null_by_id = {}
    for design in matched_nulls:
        design.validate()
        if design.null_id in null_by_id:
            raise ValueError(f"duplicate matched-null id: {design.null_id}")
        null_by_id[design.null_id] = design

    required_ids = set(claim.matched_null_design_ids)
    missing = sorted(required_ids - set(null_by_id))
    if missing:
        raise ValueError(f"claim references missing matched-null designs: {missing}")

    if claim.state == CTMClaimState.CONTROLLED_EFFECT and not required_ids:
        # Duplicates claim.validate intentionally: certification gate must remain
        # fail-closed even if callers bypass or later refactor model validation.
        raise ValueError("controlled_effect certification requires matched-property nulls")

    return CTMCertificationResult(
        claim_id=claim.claim_id,
        claim_state=claim.state,
        certified=True,
        firewall=firewall,
        matched_nulls_verified=tuple(sorted(required_ids)),
    )

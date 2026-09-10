"""Cumulative Transfer Map contracts and certification guards."""
from .certification import CTMCertificationResult, certify_ctm_claim
from .contracts import (
    CTMArtifactRole,
    CTMArtifactUse,
    CTMClaim,
    CTMClaimState,
    CTM_SCHEMA_VERSION,
    validate_anti_optimization_invariant,
)
from .firewall import FirewallResult, check_provenance_firewall, require_provenance_firewall
from .nulls import MatchedNullDesign, MatchedNullType
from .optimizer_constraints import (
    OPTIMIZER_CONSTRAINTS_SCHEMA_VERSION,
    OptimizerConstraints,
    experimental_unit_id,
    same_experimental_unit,
)
from .scalar_types import SCALAR_CLASSES, ANALYSIS_ROLES, TypedScalar
from .swap_validity import (
    FACTOR_RELATIONSHIPS,
    SWAP_VALIDITY_SCHEMA_VERSION,
    SwapValidity,
    check_pooling,
    require_controlled_effect_eligible,
)

__all__ = [
    "CTM_SCHEMA_VERSION", "CTMClaimState", "CTMArtifactRole", "CTMArtifactUse",
    "CTMClaim", "MatchedNullType", "MatchedNullDesign", "FirewallResult",
    "CTMCertificationResult", "validate_anti_optimization_invariant",
    "check_provenance_firewall", "require_provenance_firewall", "certify_ctm_claim",
    "SwapValidity", "SWAP_VALIDITY_SCHEMA_VERSION", "FACTOR_RELATIONSHIPS",
    "check_pooling", "require_controlled_effect_eligible",
    "TypedScalar", "SCALAR_CLASSES", "ANALYSIS_ROLES",
    "OptimizerConstraints", "OPTIMIZER_CONSTRAINTS_SCHEMA_VERSION",
    "experimental_unit_id", "same_experimental_unit",
]

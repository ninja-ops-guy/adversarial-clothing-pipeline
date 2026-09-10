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
from .channel import (
    CHANNEL_SCHEMA_VERSION,
    ChannelRecord,
    ChannelSemanticsError,
    claim_ceiling,
    require_digital_claim_eligible,
    require_physical_replicated_eligible,
    require_strong_physical_eligible,
)
from .citations import (
    CITATION_SCHEMA_VERSION,
    Citation,
    CitationVerificationError,
    check_claim_export,
    export_claim_artifact,
)
from .claim_lint import (
    CLAIM_LINT_RULESET_VERSION,
    ClaimLintResult,
    ClaimLintViolation,
    lint_text,
    require_bounded,
)
from .corpus import (
    CORPUS_SNAPSHOT_SCHEMA_VERSION,
    CorpusSnapshot,
    LiteratureEntry,
    SnapshotVerificationError,
    build_snapshot,
    verify_snapshot,
)
from .evaluation_surface import (
    GOODHART_EXPOSURE_SCHEMA_VERSION,
    EvaluationSurface,
    derive_evaluation_surface,
    derive_manifest_evaluation_surface,
)
from .external_cohort import (
    EXTERNAL_OBSERVATION_SCHEMA_VERSION,
    EVIDENCE_CLASS as EXTERNAL_EVIDENCE_CLASS,
    ExternalCohortError,
    ExternalObservation,
    build_analysis_pool,
    claim_ceiling as external_claim_ceiling,
    fabrication_delta,
    promote_to_controlled_efficacy,
)
from .firewall import FirewallResult, check_provenance_firewall, require_provenance_firewall
from .nulls import MatchedNullDesign, MatchedNullType
from .retro_mining import (
    DECISION_STATES,
    RETRO_DECISION_SCHEMA_VERSION,
    FamilyResult,
    RetroMiningError,
    RetroPreregistration,
    require_reject_legal,
    seal_decision,
    verify_decision,
)
from .pipeline_stage import (
    CLAIM_SCOPE_SCHEMA_VERSION,
    PIPELINE_STAGES,
    ClaimScope,
    ScopeConformanceError,
    require_prose_conformant,
)
from .positioning import (
    POSITIONING_SCHEMA_VERSION,
    Positioning,
    PositioningError,
    require_narrative_conformant,
    serialize_positioning,
)
from .target_semantics import (
    HEAD_CLASSES,
    MECHANISM_CLASSES,
    TARGET_SEMANTICS_SCHEMA_VERSION,
    MechanismTag,
    TargetSemantics,
    TargetSemanticsError,
    require_not_identity_collapse,
)
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
    "EvaluationSurface", "GOODHART_EXPOSURE_SCHEMA_VERSION",
    "derive_evaluation_surface", "derive_manifest_evaluation_surface",
    "ChannelRecord", "CHANNEL_SCHEMA_VERSION", "ChannelSemanticsError",
    "claim_ceiling", "require_digital_claim_eligible",
    "require_strong_physical_eligible", "require_physical_replicated_eligible",
    "TargetSemantics", "MechanismTag", "TARGET_SEMANTICS_SCHEMA_VERSION",
    "HEAD_CLASSES", "MECHANISM_CLASSES", "TargetSemanticsError",
    "require_not_identity_collapse",
    "LiteratureEntry", "CorpusSnapshot", "CORPUS_SNAPSHOT_SCHEMA_VERSION",
    "build_snapshot", "verify_snapshot", "SnapshotVerificationError",
    "Citation", "CITATION_SCHEMA_VERSION", "CitationVerificationError",
    "check_claim_export", "export_claim_artifact",
    "ClaimScope", "CLAIM_SCOPE_SCHEMA_VERSION", "PIPELINE_STAGES",
    "ScopeConformanceError", "require_prose_conformant",
    "ClaimLintResult", "ClaimLintViolation", "CLAIM_LINT_RULESET_VERSION",
    "lint_text", "require_bounded",
    "Positioning", "POSITIONING_SCHEMA_VERSION", "PositioningError",
    "serialize_positioning", "require_narrative_conformant",
    "ExternalObservation", "EXTERNAL_OBSERVATION_SCHEMA_VERSION",
    "EXTERNAL_EVIDENCE_CLASS", "ExternalCohortError", "build_analysis_pool",
    "external_claim_ceiling", "fabrication_delta", "promote_to_controlled_efficacy",
    "RetroPreregistration", "FamilyResult", "DECISION_STATES",
    "RETRO_DECISION_SCHEMA_VERSION", "RetroMiningError",
    "require_reject_legal", "seal_decision", "verify_decision",
]

"""Prospective RAC experimental-governance primitives.

This namespace is additive and must not mutate frozen historical experiment
artifacts. See docs/experimental_governance/IMPLEMENTATION_PASSES.md.
"""

from .ids import GovernanceId, IdKind
from .ledger import GovernanceEvent, GovernanceLedger, LedgerIntegrityError
from .state import ExperimentState, GovernanceStateMachine, StateTransitionError
from .validators import GovernanceValidationError, validate_manifest
from .constraints import ConstraintImpact, ConstraintSet, MigrationOutcome, classify_migration
from .seal import CohortSeal, SealError, seal_cohort, verify_seal
from .bridge_overlap import (
    BridgeGovernanceError,
    OverlapEstimate,
    RegimeDecision,
    SentinelRecord,
    assert_calibration_isolation,
    classify_regime,
    require_blind_re_evaluation,
    require_pooling_legal,
)
from .cic_adapter import (
    CICError,
    CICResult,
    ConstraintRepresentation,
    SolveStatus,
    SolverReply,
    StructuralMetrics,
    check as cic_check,
    require_cross_encoding_agreement,
)
from .sampling import (
    BackendSelection,
    BackendTelemetry,
    DiagnosticBundle,
    DiagnosticPolicy,
    RepresentativenessState,
    SamplerLane,
    SamplingGovernanceError,
    SamplingRequest,
    SamplingResult,
    diagnose,
    require_confirmatory_eligible,
    select_backend,
)

__all__ = [
    "BackendSelection", "BackendTelemetry", "BridgeGovernanceError", "CICError",
    "CICResult", "CohortSeal", "ConstraintImpact", "ConstraintRepresentation",
    "ConstraintSet", "DiagnosticBundle", "DiagnosticPolicy", "ExperimentState",
    "GovernanceEvent", "GovernanceId", "GovernanceLedger", "GovernanceStateMachine",
    "GovernanceValidationError", "IdKind", "LedgerIntegrityError", "MigrationOutcome",
    "OverlapEstimate", "RegimeDecision", "RepresentativenessState", "SamplerLane",
    "SamplingGovernanceError", "SamplingRequest", "SamplingResult", "SealError",
    "SentinelRecord", "SolveStatus", "SolverReply", "StateTransitionError",
    "StructuralMetrics", "assert_calibration_isolation", "cic_check",
    "classify_migration", "classify_regime", "diagnose", "require_blind_re_evaluation",
    "require_confirmatory_eligible", "require_cross_encoding_agreement",
    "require_pooling_legal", "seal_cohort", "select_backend", "validate_manifest",
    "verify_seal",
]

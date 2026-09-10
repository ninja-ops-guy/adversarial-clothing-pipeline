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
from .bridge import ConstraintBridgeCohort, ConstraintBridgeError, validate_common_support
from .sentinel import (
    CalibrationState,
    EvaluationPipeline,
    PipelineBridgePlan,
    PreprocessingMode,
    SentinelCohort,
    SentinelGovernanceError,
    SentinelRegistry,
    create_sentinel,
    pipeline_change_requires_bridge,
    validate_blind_sentinel_evaluation,
    validate_pipeline_transition,
)
from .overlap import (
    BidirectionalOverlapEstimate,
    CountEstimate,
    DetailedRegimeDecision,
    IntervalEstimate,
    MaterialityPolicy,
    OverlapAnalysis,
    OverlapGovernanceError,
    RegimeDecisionPolicy,
    StratumOverlap,
    binomial_wilson,
    decide_regime,
    estimate_bidirectional_overlap,
    estimate_policy_overlap,
    estimate_stratified_support,
    require_overlap_analysis_for_migration,
    support_overlap_from_counts,
)

__all__ = [
    "BidirectionalOverlapEstimate",
    "BridgeGovernanceError",
    "CalibrationState",
    "CohortSeal",
    "ConstraintBridgeCohort",
    "ConstraintBridgeError",
    "ConstraintImpact",
    "ConstraintSet",
    "CountEstimate",
    "DetailedRegimeDecision",
    "EvaluationPipeline",
    "ExperimentState",
    "GovernanceEvent",
    "GovernanceId",
    "GovernanceLedger",
    "GovernanceStateMachine",
    "GovernanceValidationError",
    "IdKind",
    "IntervalEstimate",
    "LedgerIntegrityError",
    "MaterialityPolicy",
    "MigrationOutcome",
    "OverlapAnalysis",
    "OverlapEstimate",
    "OverlapGovernanceError",
    "PipelineBridgePlan",
    "PreprocessingMode",
    "RegimeDecision",
    "RegimeDecisionPolicy",
    "SealError",
    "SentinelCohort",
    "SentinelGovernanceError",
    "SentinelRecord",
    "SentinelRegistry",
    "StateTransitionError",
    "StratumOverlap",
    "assert_calibration_isolation",
    "binomial_wilson",
    "classify_migration",
    "classify_regime",
    "create_sentinel",
    "decide_regime",
    "estimate_bidirectional_overlap",
    "estimate_policy_overlap",
    "estimate_stratified_support",
    "pipeline_change_requires_bridge",
    "require_blind_re_evaluation",
    "require_overlap_analysis_for_migration",
    "require_pooling_legal",
    "seal_cohort",
    "support_overlap_from_counts",
    "validate_blind_sentinel_evaluation",
    "validate_common_support",
    "validate_manifest",
    "validate_pipeline_transition",
    "verify_seal",
]

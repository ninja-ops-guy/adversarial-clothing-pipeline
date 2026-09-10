"""Prospective RAC experimental-governance primitives.

This namespace is additive and must not mutate frozen historical experiment
artifacts. See docs/experimental_governance/IMPLEMENTATION_PASSES.md.
"""

from .ids import GovernanceId, IdKind
from .ledger import GovernanceEvent, GovernanceEventType, GovernanceLedger, LedgerIntegrityError, payload_sha256
from .state import ExperimentState, GovernanceStateMachine, InvariantConflict, StateTransitionError
from .validators import GovernanceValidationError, validate_manifest
from .constraints import (FROZEN_D2_ARTIFACT_IDS, ConstraintImpact, ConstraintRegistryError, ConstraintSet, ConstraintSetRegistry, EstimandImpact, FrozenArtifactMutationError, MigrationDecisionRecord, MigrationImpactAnalysis, MigrationOutcome, TolerancePolicy, assess_migration, assert_frozen_d2_artifacts_unchanged, classify_migration)
from .migration import record_migration_decision
from .seal import CohortSeal, GovernanceCohortSeal, SealError, TimestampAdapter, seal_cohort, seal_governed_cohort, verify_governed_seal, verify_seal
from .bridge_overlap import BridgeGovernanceError, OverlapEstimate, RegimeDecision, SentinelRecord, assert_calibration_isolation, classify_regime, require_blind_re_evaluation, require_pooling_legal
from .cic_adapter import CICError, CICResult, ConstraintRepresentation, SolveStatus, SolverReply, StructuralMetrics, check as cic_check, require_cross_encoding_agreement
from .sampling import (BackendSelection, BackendTelemetry, CalibrationMetrics, DiagnosticBundle, DiagnosticPolicy, ExactProjectedPopulationBackend, ExternalSamplerReply, PopulationIdentity, ProjectedSamplerAdapter, RepresentativenessState, SamplerLane, SamplingGovernanceError, SamplingRequest, SamplingResult, build_sampling_manifest, diagnose, require_confirmatory_eligible, select_backend)
from .sampling_diagnostics import exact_distribution_diagnostics, repeated_seed_instability
from .sampling_routing import EmpiricalLaneModel, select_backend_empirical
from .adaptive import AdaptiveGovernanceError, EvidenceSeal, FrozenPolicy, PolicyState, propose_next_wave_policy, require_policy_frozen_before_sampling
from .chaos import ChaosArchive, ChaosCandidate, ChaosEvent, ChaosGovernanceError, ChaosStatus

__all__ = [name for name in globals() if not name.startswith("_")]

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

__all__ = [
    "CohortSeal",
    "ConstraintImpact",
    "ConstraintSet",
    "ExperimentState",
    "GovernanceEvent",
    "GovernanceId",
    "GovernanceLedger",
    "GovernanceStateMachine",
    "GovernanceValidationError",
    "IdKind",
    "LedgerIntegrityError",
    "MigrationOutcome",
    "SealError",
    "StateTransitionError",
    "classify_migration",
    "seal_cohort",
    "validate_manifest",
    "verify_seal",
]

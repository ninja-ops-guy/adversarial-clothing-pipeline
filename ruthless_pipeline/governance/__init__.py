"""Prospective RAC experimental-governance primitives.

This namespace is additive and must not mutate frozen historical experiment
artifacts. See docs/experimental_governance/IMPLEMENTATION_PASSES.md.
"""

from .ids import GovernanceId, IdKind
from .ledger import GovernanceEvent, GovernanceLedger, LedgerIntegrityError
from .state import ExperimentState, GovernanceStateMachine, StateTransitionError
from .validators import GovernanceValidationError, validate_manifest

__all__ = [
    "ExperimentState",
    "GovernanceEvent",
    "GovernanceId",
    "GovernanceLedger",
    "GovernanceStateMachine",
    "GovernanceValidationError",
    "IdKind",
    "LedgerIntegrityError",
    "StateTransitionError",
    "validate_manifest",
]

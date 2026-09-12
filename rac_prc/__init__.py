"""RAC Prospective Robustness Characterization (PRC).

Additive, read-only validation infrastructure for prospectively comparing frozen
digital robustness predictions with later P1 physical observations. PRC never
mutates P1 authority, Pattern Genome v1, or candidate lineages.
"""

from .analysis import characterize
from .authority import AuthorityError, AuthoritySnapshot, validate_repository_authority
from .p1_adapter import PRCP1Adapter
from .prediction_freeze import freeze_receipt, validate_prediction_freeze

__all__ = [
    "AuthorityError",
    "AuthoritySnapshot",
    "PRCP1Adapter",
    "characterize",
    "freeze_receipt",
    "validate_prediction_freeze",
    "validate_repository_authority",
]

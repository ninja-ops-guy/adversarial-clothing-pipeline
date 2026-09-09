"""Detector science tooling (RAC-D, Wave 3 item 3).

Additive namespace for detector-response records, evaluator adapters,
model-family registry, and cross-family transfer analysis. No certification
is produced from this infrastructure.
"""

from .response import (
    AdapterCapabilities,
    DetectorResponse,
    FabricationGuardError,
    validate,
)
from .family_registry import (
    UnknownFamilyError,
    concentration_report,
    family_for_model,
    load_registry,
)
from .transfer_matrix import (
    InsufficientDataError,
    build_transfer_matrix,
    leave_one_family_out,
    surrogate_diversity_report,
)

__all__ = [
    "AdapterCapabilities",
    "DetectorResponse",
    "FabricationGuardError",
    "validate",
    "UnknownFamilyError",
    "concentration_report",
    "family_for_model",
    "load_registry",
    "InsufficientDataError",
    "build_transfer_matrix",
    "leave_one_family_out",
    "surrogate_diversity_report",
]

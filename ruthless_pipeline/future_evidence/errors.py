"""Fail-closed typed errors for the future-evidence infrastructure lane.

Every guard in this package raises one of these subclasses; nothing is
silently coerced, defaulted, or skipped. All inherit from ValueError so
call sites that catch ValueError keep working unchanged.
"""
from __future__ import annotations


class FutureEvidenceError(ValueError):
    """Base failure for future-evidence contracts."""


class MeasuredFlagAbsentError(FutureEvidenceError):
    """The measured flag was absent; it can never be inferred or defaulted."""


class DuplicateTrialIdError(FutureEvidenceError):
    """A trial/observation identity was registered twice."""


class UnboundProvenanceError(FutureEvidenceError):
    """A record lacks a bound provenance reference (hash or content id)."""


class PairingError(FutureEvidenceError):
    """Candidate/control linkage is missing, dangling, or inconsistent."""


class MissingMetadataError(FutureEvidenceError):
    """Required metadata (camera, environment, specimen, calibration) absent."""


class LeakageError(FutureEvidenceError):
    """Calibration/evaluation (or candidate/control) set leakage detected."""


class InconsistentIdentityError(FutureEvidenceError):
    """The same logical identity carries conflicting metadata."""


class SchemaFrozenError(FutureEvidenceError):
    """A released/frozen schema version or sealed registry entry was mutated."""


class PromotionImpossibleError(FutureEvidenceError):
    """Synthetic evidence may never be promoted to measured physical evidence."""


class TemporalOrderError(FutureEvidenceError):
    """Frames are unordered, duplicated, or non-temporal input posed as a sequence."""


class ReservedFieldError(FutureEvidenceError):
    """A reserved future field was populated before its evidence channel exists."""

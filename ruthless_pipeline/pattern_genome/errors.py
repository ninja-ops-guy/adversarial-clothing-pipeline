"""Pattern Genome error hierarchy. Every failure mode is a typed refusal."""
from __future__ import annotations

class PatternGenomeError(Exception):
    """Base class for all Pattern Genome failures."""

class PatternGenomeInputError(PatternGenomeError):
    """Input image is invalid, corrupt, or unsupported."""

class PatternGenomeValidationError(PatternGenomeError):
    """Genome record failed schema or invariant validation."""

class PatternGenomeProvenanceError(PatternGenomeError):
    """Required provenance field is absent or inconsistent."""

class PatternGenomeNonFiniteError(PatternGenomeError):
    """NaN, Infinity, or out-of-range value detected."""

class PatternGenomeDeterminismError(PatternGenomeError):
    """Golden-vector or cross-process determinism check failed."""

class PatternGenomeSchemaError(PatternGenomeError):
    """Unknown or incompatible schema version."""

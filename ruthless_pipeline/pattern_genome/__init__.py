"""Pattern Genome v1 — deterministic structural descriptor for adversarial textile candidates.

Measurement only. No prediction. No held-out access. Evidence class: derived_digital_measurement.
"""
from .canonical import canonical_json, genome_sha256, sha256_bytes
from .config import PatternGenomeConfig, load_config
from .errors import (
    PatternGenomeDeterminismError, PatternGenomeError, PatternGenomeInputError,
    PatternGenomeNonFiniteError, PatternGenomeProvenanceError,
    PatternGenomeSchemaError, PatternGenomeValidationError,
)
from .extractor import extract_genome
from .schema import (
    SCHEMA_VERSION, EXTRACTOR_VERSION, ColorGenome, GenomeProvenance,
    GenomeQuality, GenomeSource, GeometryGenome, PatternGenome,
    SpectralGenome, TopologyGenome,
)
from .validation import validate_genome

__all__ = [
    "SCHEMA_VERSION", "EXTRACTOR_VERSION",
    "extract_genome", "validate_genome", "canonical_json", "genome_sha256", "sha256_bytes",
    "load_config", "PatternGenomeConfig", "PatternGenome", "GenomeSource",
    "SpectralGenome", "TopologyGenome", "ColorGenome", "GeometryGenome",
    "GenomeQuality", "GenomeProvenance", "PatternGenomeError",
    "PatternGenomeInputError", "PatternGenomeValidationError",
    "PatternGenomeProvenanceError", "PatternGenomeNonFiniteError",
    "PatternGenomeDeterminismError", "PatternGenomeSchemaError",
]

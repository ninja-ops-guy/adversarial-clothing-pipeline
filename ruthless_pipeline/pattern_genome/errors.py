class PatternGenomeError(Exception):
    """Base error for Pattern Genome v1."""

class PatternGenomeInputError(PatternGenomeError): pass
class PatternGenomeValidationError(PatternGenomeError): pass
class PatternGenomeProvenanceError(PatternGenomeError): pass
class PatternGenomeNonFiniteError(PatternGenomeValidationError): pass
class PatternGenomeDeterminismError(PatternGenomeError): pass
class PatternGenomeSchemaError(PatternGenomeValidationError): pass

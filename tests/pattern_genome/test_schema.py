from dataclasses import replace
import pytest
from ruthless_pipeline.pattern_genome import extract_genome, validate_genome, PatternGenomeValidationError

def test_valid(checker_bytes,kwargs): validate_genome(extract_genome(checker_bytes,**kwargs))
def test_bad_radial_sum(checker_bytes,kwargs):
    g=extract_genome(checker_bytes,**kwargs); s=replace(g.spectral,radial_energy=(1.0,)*8); g=replace(g,spectral=s)
    with pytest.raises(PatternGenomeValidationError): validate_genome(g)

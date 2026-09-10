from ruthless_pipeline.pattern_genome import extract_genome, canonical_json

def test_same_input_byte_identical(checker_bytes,kwargs):
    a=extract_genome(checker_bytes,**kwargs); b=extract_genome(checker_bytes,**kwargs)
    assert canonical_json(a)==canonical_json(b)
    assert a.genome_id==b.genome_id

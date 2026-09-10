import json
from ruthless_pipeline.pattern_genome import extract_genome, canonical_json

def test_json_roundtrip(checker_bytes,kwargs):
    g=extract_genome(checker_bytes,**kwargs); parsed=json.loads(canonical_json(g)); assert parsed["genome_id"]==g.genome_id; assert parsed["provenance"]["evidence_class"]=="derived_digital_measurement"

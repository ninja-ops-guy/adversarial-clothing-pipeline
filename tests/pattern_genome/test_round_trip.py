"""Round-trip tests: genome -> canonical JSON -> parse -> validate."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
from ruthless_pipeline.pattern_genome import canonical_json, extract_genome, genome_sha256, load_config

REPO_ROOT=Path(__file__).resolve().parents[2]
CONFIG_PATH=REPO_ROOT/"configs"/"pattern_genome_v1.json"

def _extract(seed=42):
    rng=np.random.RandomState(seed); rgb=(rng.rand(64,64,3)*255).astype(np.uint8)
    sha=hashlib.sha256(rgb.tobytes()).hexdigest(); config=load_config(CONFIG_PATH)
    return extract_genome(rgb,candidate_sha256=sha,source_artifact_ref="test://roundtrip",
                          source_commit="test",runtime_lock_sha256="0"*64,config=config)

def test_canonical_json_is_valid_json():
    g=_extract(); data=json.loads(canonical_json(g))
    assert data["schema_version"]=="rac-pattern-genome/1.0"
    assert data["genome_id"]==g.genome_id
    assert len(data["spectral"]["radial_energy"])==8
    assert data["provenance"]["evidence_class"]=="derived_digital_measurement"

def test_canonical_json_deterministic():
    g=_extract(); assert canonical_json(g)==canonical_json(g)

def test_genome_sha256_stable():
    g=_extract(); h1=genome_sha256(g); h2=genome_sha256(g)
    assert h1==h2 and len(h1)==64
    assert g.genome_id==f"RAC-GENOME-{h1[:16]}"

def test_round_trip_preserves_all_fields():
    data=json.loads(canonical_json(_extract()))
    for field in ("schema_version","genome_id","candidate_sha256","source","spectral","topology","color","geometry","quality","provenance"):
        assert field in data

def test_no_nan_in_canonical_json():
    raw=canonical_json(_extract()); assert b"NaN" not in raw and b"Infinity" not in raw

import io, hashlib
import numpy as np
from PIL import Image
from ruthless_pipeline.pattern_genome import extract_genome

def pb(a):
    b=io.BytesIO(); Image.fromarray(a.astype(np.uint8),"RGB").save(b,format="PNG"); return b.getvalue()
def ex(a,cfg,name):
    d=pb(a); return extract_genome(d,candidate_sha256=hashlib.sha256(d).hexdigest(),source_artifact_ref=name,source_commit="c",runtime_lock_sha256="0"*64,config=cfg,extracted_utc="2026-09-09T22:00:00Z")
def test_noise_has_more_high_frequency_than_gradient(cfg):
    rng=np.random.default_rng(1); n=rng.integers(0,256,(64,64,3),dtype=np.uint8)
    g=np.tile(np.linspace(0,255,64,dtype=np.uint8),(64,1)); g=np.stack([g,g,g],axis=-1)
    assert ex(n,cfg,"noise").spectral.high_frequency_ratio > ex(g,cfg,"gradient").spectral.high_frequency_ratio
def test_checker_more_symmetric_than_asymmetric(cfg):
    y,x=np.indices((64,64)); c=((x//8+y//8)%2)*255; c=np.stack([c,c,c],axis=-1).astype(np.uint8)
    a=np.zeros((64,64,3),dtype=np.uint8); a[3:21,7:17]=255; a[40:61,45:63]=128
    cg=ex(c,cfg,"checker"); ag=ex(a,cfg,"asym")
    assert cg.topology.rotational_symmetry_180 > ag.topology.rotational_symmetry_180

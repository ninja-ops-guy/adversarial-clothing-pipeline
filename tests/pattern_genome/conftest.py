import io, hashlib
import numpy as np
import pytest
from PIL import Image
from ruthless_pipeline.pattern_genome import PatternGenomeConfig

def png_bytes(arr):
    b=io.BytesIO(); Image.fromarray(arr.astype(np.uint8),"RGB").save(b,format="PNG"); return b.getvalue()

@pytest.fixture
def cfg(): return PatternGenomeConfig()

@pytest.fixture
def checker_bytes():
    y,x=np.indices((64,64)); c=((x//8+y//8)%2)*255; arr=np.stack([c,c,c],axis=-1).astype(np.uint8); return png_bytes(arr)

@pytest.fixture
def kwargs(checker_bytes,cfg):
    return dict(candidate_sha256=hashlib.sha256(checker_bytes).hexdigest(),source_artifact_ref="fixture://checker.png",source_commit="deadbeef",runtime_lock_sha256="0"*64,config=cfg,extracted_utc="2026-09-09T22:00:00Z")

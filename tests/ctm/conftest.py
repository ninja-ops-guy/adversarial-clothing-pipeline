"""Shared CTM bridge fixtures (owned by lane B1). Deterministic, in-memory."""
import hashlib
import io

import numpy as np
import pytest
from PIL import Image

from ruthless_pipeline.pattern_genome import load_config

FIXED_EXTRACTED_UTC = "2026-01-01T00:00:00Z"
FIXED_SOURCE_COMMIT = "0" * 40
FIXED_RUNTIME_LOCK_SHA256 = "0" * 64
CONFIG_PATH = "configs/pattern_genome_v1.json"


def png_bytes(arr):
    b = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8), "RGB").save(b, format="PNG")
    return b.getvalue()


@pytest.fixture
def cfg():
    return load_config(CONFIG_PATH)


@pytest.fixture
def checker_bytes():
    y, x = np.indices((64, 64))
    c = ((x // 8 + y // 8) % 2) * 255
    arr = np.stack([c, c, c], axis=-1).astype(np.uint8)
    return png_bytes(arr)


@pytest.fixture
def stripes_bytes():
    y, x = np.indices((64, 64))
    r = ((x // 4) % 2) * 255
    g = ((y // 4) % 2) * 255
    arr = np.stack([r, g, np.zeros_like(r)], axis=-1).astype(np.uint8)
    return png_bytes(arr)


@pytest.fixture
def extract_kwargs(cfg):
    return dict(
        source_commit=FIXED_SOURCE_COMMIT,
        runtime_lock_sha256=FIXED_RUNTIME_LOCK_SHA256,
        config=cfg,
        extracted_utc=FIXED_EXTRACTED_UTC,
    )


@pytest.fixture
def registry_root(tmp_path):
    return str(tmp_path / "ctm_registry")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

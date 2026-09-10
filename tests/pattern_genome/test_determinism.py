"""Determinism tests: same bytes -> same genome, across process restarts."""
from __future__ import annotations
import hashlib
import subprocess
import sys
from pathlib import Path
import numpy as np
from ruthless_pipeline.pattern_genome import canonical_json, extract_genome, genome_sha256, load_config

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "pattern_genome_v1.json"

def _make_pattern(seed: int, size: int = 64) -> np.ndarray:
    rng = np.random.RandomState(seed)
    return (rng.rand(size, size, 3) * 255).astype(np.uint8)

def _extract(rgb: np.ndarray):
    config = load_config(CONFIG_PATH)
    sha = hashlib.sha256(rgb.tobytes()).hexdigest()
    return extract_genome(rgb, candidate_sha256=sha, source_artifact_ref="test://determinism",
                          source_commit="test", runtime_lock_sha256="0" * 64, config=config)

def test_same_bytes_same_genome():
    rgb = _make_pattern(42)
    g1 = _extract(rgb); g2 = _extract(rgb)
    assert g1.genome_id == g2.genome_id
    assert g1.genome_id == f"RAC-GENOME-{genome_sha256(g1)[:16]}"
    assert genome_sha256(g1) == genome_sha256(g2)
    assert canonical_json(g1) == canonical_json(g2)

def test_different_bytes_different_genome():
    assert _extract(_make_pattern(42)).genome_id != _extract(_make_pattern(43)).genome_id

def test_cross_process_determinism():
    rgb = _make_pattern(42)
    sha = hashlib.sha256(rgb.tobytes()).hexdigest()
    rgb_hex = rgb.tobytes().hex()
    script = f'''
import sys
sys.path.insert(0, "{REPO_ROOT}")
import numpy as np
from ruthless_pipeline.pattern_genome import extract_genome, load_config, genome_sha256
rgb = np.frombuffer(bytes.fromhex("{rgb_hex}"), dtype=np.uint8).reshape(64, 64, 3)
config = load_config("{CONFIG_PATH}")
g = extract_genome(rgb, candidate_sha256="{sha}", source_artifact_ref="test://determinism",
    source_commit="test", runtime_lock_sha256="{"0"*64}", config=config)
print(genome_sha256(g))
'''
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert result.returncode == 0, f"subprocess failed: {result.stderr}"
    assert genome_sha256(_extract(rgb)) == result.stdout.strip()

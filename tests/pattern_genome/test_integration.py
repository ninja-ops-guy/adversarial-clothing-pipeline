from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ruthless_pipeline.pattern_genome import freeze_pool_genomes
from ruthless_pipeline.pattern_genome.errors import PatternGenomeProvenanceError

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "pattern_genome_v1.json"
RUNTIME_LOCK = ROOT / "benchmarks" / "runtime_lock.json"


def _write_png(path: Path, value: int) -> str:
    arr = np.full((32, 32, 3), value, dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_pool_genomes_writes_sidecars_and_index(tmp_path):
    pool = tmp_path / "pool"
    out = tmp_path / "out"
    pool.mkdir()
    sha_a = _write_png(pool / "a.png", 32)
    sha_b = _write_png(pool / "b.png", 224)
    candidates = [
        {"candidate_id": "a", "png": "a.png", "png_sha256": sha_a},
        {"candidate_id": "b", "png": "b.png", "png_sha256": sha_b},
    ]
    index = freeze_pool_genomes(
        candidates,
        pool_dir=pool,
        output_dir=out,
        config_path=CONFIG,
        runtime_lock_path=RUNTIME_LOCK,
        source_commit="deadbeef",
        repo_root=ROOT,
    )
    assert index["candidate_count"] == 2
    assert index["selection_influence"] == "NONE_MEASUREMENT_ONLY"
    assert index["heldout_access"] is False
    assert (out / "a.json").is_file()
    assert (out / "b.json").is_file()
    persisted = json.loads((out / "index.json").read_text())
    assert persisted["candidate_count"] == 2
    assert persisted["candidates"]["a"]["evidence_class"] == "derived_digital_measurement"


def test_declared_candidate_sha_mismatch_refuses(tmp_path):
    pool = tmp_path / "pool"
    pool.mkdir()
    _write_png(pool / "a.png", 64)
    with pytest.raises(PatternGenomeProvenanceError, match="png_sha256"):
        freeze_pool_genomes(
            [{"candidate_id": "a", "png": "a.png", "png_sha256": "f" * 64}],
            pool_dir=pool,
            output_dir=tmp_path / "out",
            config_path=CONFIG,
            runtime_lock_path=RUNTIME_LOCK,
            source_commit="deadbeef",
            repo_root=ROOT,
        )


def test_uniform_candidate_is_valid(tmp_path):
    pool = tmp_path / "pool"
    pool.mkdir()
    sha = _write_png(pool / "solid.png", 128)
    index = freeze_pool_genomes(
        [{"candidate_id": "solid", "png": "solid.png", "png_sha256": sha}],
        pool_dir=pool,
        output_dir=tmp_path / "out",
        config_path=CONFIG,
        runtime_lock_path=RUNTIME_LOCK,
        source_commit="deadbeef",
        repo_root=ROOT,
    )
    genome = json.loads((tmp_path / "out" / "solid.json").read_text())
    assert genome["spectral"]["high_frequency_ratio"] == 0.0
    assert genome["spectral"]["low_frequency_ratio"] == 1.0
    assert index["candidates"]["solid"]["candidate_sha256"] == sha


def test_surrogate_selector_freezes_all_genomes_without_using_them_for_ranking(tmp_path):
    from tests.baseline.fixtures import CANDIDATE_IDS, run_selection

    pool_dir = tmp_path / "pool"
    output_dir = tmp_path / "run"
    report = run_selection(pool_dir, output_dir, objective="mean")

    genome_dir = output_dir / "pattern-genomes"
    assert (genome_dir / "index.json").is_file()
    for candidate_id in CANDIDATE_IDS:
        assert (genome_dir / f"{candidate_id}.json").is_file()

    selected_ref = json.loads((output_dir / "candidate-genome-ref.json").read_text())
    assert selected_ref["selection_influence"] == "NONE_MEASUREMENT_ONLY"
    assert selected_ref["heldout_access"] is False
    assert selected_ref["candidate_id"] == report["winner"]["candidate_id"]
    assert selected_ref["genome_ref"]["candidate_sha256"] == report["winner"]["pattern_sha256"]

    # V1 instrumentation is sidecar-only: the scientific selection report has
    # no genome feature fields and therefore cannot rank on them.
    assert "pattern_genome" not in report
    assert "genome_ref" not in report["winner"]

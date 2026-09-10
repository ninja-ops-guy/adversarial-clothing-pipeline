"""Schema validation tests: validate_genome accepts valid, rejects violations."""
from __future__ import annotations
import hashlib
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from ruthless_pipeline.pattern_genome import PatternGenomeValidationError, extract_genome, load_config, validate_genome

REPO_ROOT=Path(__file__).resolve().parents[2]
CONFIG_PATH=REPO_ROOT/"configs"/"pattern_genome_v1.json"

def _valid_genome():
    rng=np.random.RandomState(42); rgb=(rng.rand(64,64,3)*255).astype(np.uint8)
    sha=hashlib.sha256(rgb.tobytes()).hexdigest(); config=load_config(CONFIG_PATH)
    return extract_genome(rgb,candidate_sha256=sha,source_artifact_ref="test://schema",
                          source_commit="test",runtime_lock_sha256="0"*64,config=config)

def test_valid_genome_passes(): validate_genome(_valid_genome())

def test_wrong_schema_version_refused():
    g=replace(_valid_genome(),schema_version="rac-pattern-genome/2.0")
    with pytest.raises(PatternGenomeValidationError,match="schema_version"): validate_genome(g)

def test_empty_genome_id_refused():
    g=replace(_valid_genome(),genome_id="")
    with pytest.raises(PatternGenomeValidationError,match="genome_id"): validate_genome(g)

def test_short_candidate_sha_refused():
    g=replace(_valid_genome(),candidate_sha256="abc123")
    with pytest.raises(PatternGenomeValidationError,match="64 hex"): validate_genome(g)

def test_radial_energy_wrong_length_refused():
    g=_valid_genome(); g=replace(g,spectral=replace(g.spectral,radial_energy=(0.5,0.5)))
    with pytest.raises(PatternGenomeValidationError,match="8 bins"): validate_genome(g)

def test_radial_energy_not_sum_to_one_refused():
    g=_valid_genome(); g=replace(g,spectral=replace(g.spectral,radial_energy=(0.1,)*8))
    with pytest.raises(PatternGenomeValidationError,match="sum to 1.0"): validate_genome(g)

def test_symmetry_out_of_range_refused():
    g=_valid_genome(); g=replace(g,topology=replace(g.topology,horizontal_symmetry=1.5))
    with pytest.raises(PatternGenomeValidationError,match="horizontal_symmetry"): validate_genome(g)

def test_negative_component_count_refused():
    g=_valid_genome(); g=replace(g,topology=replace(g.topology,connected_component_count=-1))
    with pytest.raises(PatternGenomeValidationError,match="connected_component_count"): validate_genome(g)

def test_quality_not_finite_refused():
    from ruthless_pipeline.pattern_genome.schema import GenomeQuality
    g=replace(_valid_genome(),quality=GenomeQuality(all_finite=False,warnings=("nan detected",)))
    with pytest.raises(PatternGenomeValidationError,match="all_finite"): validate_genome(g)

def test_zero_width_refused():
    g=_valid_genome(); g=replace(g,source=replace(g.source,width_px=0))
    with pytest.raises(PatternGenomeValidationError,match="width_px"): validate_genome(g)

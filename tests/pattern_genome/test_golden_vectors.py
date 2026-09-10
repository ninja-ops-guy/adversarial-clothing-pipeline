"""Golden-vector tests: synthetic patterns with known qualitative properties."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
from ruthless_pipeline.pattern_genome import extract_genome, load_config, validate_genome

REPO_ROOT=Path(__file__).resolve().parents[2]
CONFIG_PATH=REPO_ROOT/"configs"/"pattern_genome_v1.json"

def _extract(rgb):
    config=load_config(CONFIG_PATH); sha=hashlib.sha256(rgb.tobytes()).hexdigest()
    g=extract_genome(rgb,candidate_sha256=sha,source_artifact_ref="test://golden",
                     source_commit="test",runtime_lock_sha256="0"*64,config=config)
    validate_genome(g); return g

def _checkerboard(size=72,sq=8):
    yy,xx=np.indices((size,size)); cells=((yy//sq)+(xx//sq))%2
    rgb=np.empty((size,size,3),dtype=np.uint8); rgb[cells==0]=[200,50,50]; rgb[cells==1]=[50,50,200]
    return rgb

def _gradient(size=64):
    rgb=np.zeros((size,size,3),dtype=np.uint8)
    for x in range(size):
        v=int(255*x/(size-1)); rgb[:,x]=[v,v,255-v]
    return rgb

def _noise(size=64,seed=42):
    rng=np.random.RandomState(seed); return (rng.rand(size,size,3)*255).astype(np.uint8)

def _solid(size=64):
    rgb=np.zeros((size,size,3),dtype=np.uint8); rgb[:]=[128,64,192]; return rgb

class TestCheckerboard:
    def setup_method(self): self.g=_extract(_checkerboard())
    def test_high_symmetry(self):
        assert self.g.topology.horizontal_symmetry>0.9
        assert self.g.topology.vertical_symmetry>0.9
    def test_low_color_entropy(self): assert self.g.color.color_entropy<1.1
    def test_palette_size_two(self): assert self.g.color.palette_size==2
    def test_structured_components(self): assert self.g.topology.connected_component_count==2
    def test_nonzero_feature_width(self): assert self.g.geometry.min_feature_width_px>0

class TestGradient:
    def setup_method(self): self.g=_extract(_gradient())
    def test_low_high_frequency(self): assert self.g.spectral.high_frequency_ratio<0.3
    def test_low_color_entropy(self): assert self.g.color.color_entropy>0.5

class TestNoise:
    def setup_method(self): self.g=_extract(_noise())
    def test_high_high_frequency(self): assert self.g.spectral.high_frequency_ratio>0.3
    def test_low_symmetry(self):
        assert self.g.topology.horizontal_symmetry<0.5
        assert self.g.topology.vertical_symmetry<0.5
    def test_high_color_entropy(self): assert self.g.color.color_entropy>2.0
    def test_many_components(self): assert self.g.topology.connected_component_count>50

class TestSolid:
    def setup_method(self): self.g=_extract(_solid())
    def test_zero_high_frequency(self): assert self.g.spectral.high_frequency_ratio<0.01
    def test_perfect_symmetry(self):
        assert self.g.topology.horizontal_symmetry>0.99
        assert self.g.topology.vertical_symmetry>0.99
        assert self.g.topology.rotational_symmetry_180>0.99
    def test_palette_size_one(self): assert self.g.color.palette_size==1
    def test_zero_edge_density(self): assert self.g.topology.edge_density<0.01

class TestCrossPatternOrdering:
    def test_noise_more_components_than_solid(self):
        assert _extract(_noise()).topology.connected_component_count>_extract(_solid()).topology.connected_component_count
    def test_checkerboard_more_symmetric_than_noise(self):
        assert _extract(_checkerboard()).topology.horizontal_symmetry>_extract(_noise()).topology.horizontal_symmetry
    def test_noise_higher_freq_than_gradient(self):
        assert _extract(_noise()).spectral.high_frequency_ratio>_extract(_gradient()).spectral.high_frequency_ratio
    def test_solid_lowest_entropy(self):
        assert _extract(_solid()).color.color_entropy<_extract(_noise()).color.color_entropy

"""P0 generator evidence-integrity tests: determinism, provenance, fail-closed."""
import copy

import pytest

from ruthless_pipeline.patterns import (
    AdversarialPatchGenerator,
    DazzleSurgicalLinesGenerator,
    FeatureCollageGenerator,
    GeneratorParams,
    HyperfaceLikeGenerator,
    KeyFeatureBlackoutGenerator,
    LandmarkNoiseGenerator,
    MissingLandmarksError,
    PatternNondeterminismError,
    PatternGenerator,
    ProvenanceMismatchError,
    PatternParamError,
    SaliencyEyeAttackGenerator,
    SwappedLandmarksGenerator,
)
from ruthless_pipeline.patterns.base import base_param_schema

from .conftest import make_mask

ALL_P0 = [
    HyperfaceLikeGenerator,
    DazzleSurgicalLinesGenerator,
    KeyFeatureBlackoutGenerator,
    SaliencyEyeAttackGenerator,
    AdversarialPatchGenerator,
    SwappedLandmarksGenerator,
    LandmarkNoiseGenerator,
    FeatureCollageGenerator,
]

# Generators that must fail closed when landmarks/bboxes are absent.
LANDMARK_REQUIRED = [
    HyperfaceLikeGenerator,
    DazzleSurgicalLinesGenerator,
    KeyFeatureBlackoutGenerator,
    AdversarialPatchGenerator,
    SwappedLandmarksGenerator,
    LandmarkNoiseGenerator,
]


@pytest.mark.parametrize("cls", ALL_P0, ids=[c.name for c in ALL_P0])
def test_determinism_same_seed(cls, params):
    gen = cls()
    a = gen.generate(params)
    b = gen.generate(params)
    assert a.image.tobytes() == b.image.tobytes()
    assert a.provenance_hash == b.provenance_hash
    gen.assert_deterministic(params)  # must not raise


@pytest.mark.parametrize("cls", ALL_P0, ids=[c.name for c in ALL_P0])
def test_different_seed_differs(cls, params):
    gen = cls()
    other = GeneratorParams(seed=params.seed + 1,
                            mask_geometry=params.mask_geometry,
                            output_size=params.output_size)
    a = gen.generate(params)
    b = gen.generate(other)
    assert a.image.tobytes() != b.image.tobytes()
    assert a.provenance_hash != b.provenance_hash


@pytest.mark.parametrize("cls", ALL_P0, ids=[c.name for c in ALL_P0])
def test_provenance_roundtrip_and_tamper_trap(cls, params):
    gen = cls()
    pattern = gen.generate(params)
    assert gen.verify_provenance(pattern) is True
    gen.verify_provenance_strict(pattern)

    tampered = copy.deepcopy(pattern)
    tampered.params.seed += 1  # tamper with recorded params
    assert gen.verify_provenance(tampered) is False
    with pytest.raises(ProvenanceMismatchError):
        gen.verify_provenance_strict(tampered)


@pytest.mark.parametrize("cls", ALL_P0, ids=[c.name for c in ALL_P0])
def test_param_schema_violation_raises(cls, params):
    gen = cls()
    bad = GeneratorParams(seed="not-an-int", mask_geometry=params.mask_geometry,
                          output_size=params.output_size)
    with pytest.raises(PatternParamError):
        gen.generate(bad)
    bad2 = GeneratorParams(seed=1, mask_geometry=params.mask_geometry,
                           output_size=(128, 128), color_space="HSV")
    with pytest.raises(PatternParamError):
        gen.generate(bad2)


@pytest.mark.parametrize("cls", LANDMARK_REQUIRED,
                         ids=[c.name for c in LANDMARK_REQUIRED])
def test_missing_landmarks_fail_closed(cls):
    gen = cls()
    empty = GeneratorParams(seed=7, mask_geometry={}, output_size=(128, 128))
    with pytest.raises(MissingLandmarksError):
        gen.generate(empty)


def test_adversarial_patch_multi_mode(params):
    gen = AdversarialPatchGenerator(mode="multi")
    a = gen.generate(params)
    b = gen.generate(params)
    assert a.image.tobytes() == b.image.tobytes()
    assert gen.verify_provenance(a)


def test_hyperface_color_scheme_param(mask_geometry):
    gen = HyperfaceLikeGenerator()
    p = GeneratorParams(seed=3, mask_geometry=mask_geometry, output_size=(96, 96),
                        params={"color_scheme": "bw", "shape_count": 8,
                                "concentric_count": 4})
    pat = gen.generate(p)
    assert gen.verify_provenance(pat)
    bad = GeneratorParams(seed=3, mask_geometry=mask_geometry, output_size=(96, 96),
                          params={"color_scheme": "neon"})
    with pytest.raises(PatternParamError):
        gen.generate(bad)


class _NondeterministicGenerator(PatternGenerator):
    """Intentionally broken generator: uses unseeded randomness."""
    name = "nondeterministic_fake"
    version = "1.0.0"
    category = "test"
    priority = "P0"

    def generate(self, params):
        import os
        import numpy as np
        img = np.frombuffer(os.urandom(16 * 16 * 3), dtype=np.uint8).reshape(16, 16, 3)
        return self._finalize(params, img)

    def get_param_schema(self):
        return base_param_schema()


def test_nondeterminism_detected():
    gen = _NondeterministicGenerator()
    p = GeneratorParams(seed=1, mask_geometry={}, output_size=(16, 16))
    with pytest.raises(PatternNondeterminismError):
        gen.assert_deterministic(p)

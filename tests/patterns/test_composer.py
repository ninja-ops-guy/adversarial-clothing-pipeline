"""Composer tests: blend math, composition_hash determinism/tamper, fail-closed."""
import copy

import numpy as np
import pytest

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from ruthless_pipeline.patterns import (
    GeneratorParams,
    HyperfaceLikeGenerator,
    LandmarkNoiseGenerator,
    PatternCompositionError,
    PatternComposer,
)

from .conftest import make_mask


def _layers():
    mask = make_mask()
    return [
        (HyperfaceLikeGenerator(),
         GeneratorParams(seed=11, mask_geometry=mask, output_size=(128, 128))),
        (LandmarkNoiseGenerator(),
         GeneratorParams(seed=22, mask_geometry=mask, output_size=(128, 128))),
    ]


def test_blend_math_sanity():
    blend = PatternComposer._blend
    black = np.zeros((2, 2, 3))
    white = np.ones((2, 2, 3))
    # multiply: black wins; screen: white wins; weight mixes.
    assert np.allclose(blend(black, white, "multiply", 1.0), 0.0)
    assert np.allclose(blend(black, white, "screen", 1.0), 1.0)
    assert np.allclose(blend(black, white, "multiply", 0.5), 0.0)  # base black
    mid = np.full((2, 2, 3), 0.25)
    # overlay with base<0.5: 2*b*l; weight 1.0
    assert np.allclose(blend(mid, white, "overlay", 1.0), 0.5)
    # weight 0 returns base
    assert np.allclose(blend(mid, white, "screen", 0.0), mid)
    with pytest.raises(PatternCompositionError):
        blend(mid, white, "dodge", 0.5)


def test_compose_determinism_and_log():
    composer = PatternComposer()
    out = composer.compose(_layers(), ["overlay", "multiply"], [1.0, 0.5])
    assert out.image.shape == (128, 128, 3)
    assert len(out.composition_log) == 2
    for entry in out.composition_log:
        assert set(entry) == {"generator", "version", "blend_mode", "weight",
                              "provenance_hash"}
        assert len(entry["provenance_hash"]) == 64

    composer2 = PatternComposer()
    out2 = composer2.compose(_layers(), ["overlay", "multiply"], [1.0, 0.5])
    assert out.image.tobytes() == out2.image.tobytes()
    assert out.composition_hash == out2.composition_hash
    assert out.composition_hash == sha256_bytes(canonical_json(out.composition_log))


def test_composition_hash_tamper_evident():
    out = PatternComposer().compose(_layers(), ["overlay", "screen"], [1.0, 0.7])
    tampered_log = copy.deepcopy(out.composition_log)
    tampered_log[0]["weight"] = 0.12345
    assert sha256_bytes(canonical_json(tampered_log)) != out.composition_hash


def test_unknown_blend_mode_refused():
    with pytest.raises(PatternCompositionError):
        PatternComposer().compose(_layers(), ["overlay", "dodge"], [1.0, 0.5])


def test_composed_candidate_marks_exploratory():
    out = PatternComposer().compose(_layers(), ["overlay", "multiply"], [1.0, 0.5])
    cand = out.to_candidate()
    assert cand["composition_hash"] == out.composition_hash
    assert cand["physical_efficacy_claimed"] is False
    assert cand["claim_state"] == "EXPLORATORY"

"""Schema validation + sampler reproducibility/independence tests.

synthetic_pipeline_validation_only.
"""

import copy

import jsonschema
import pytest

from ruthless_pipeline.transformations.distribution import (
    Sampler,
    TransformationDistributionSpec,
    canonical_json,
    manifest_sha256,
    sub_seed,
)


def test_valid_spec_constructs(spec_dict):
    spec = TransformationDistributionSpec.from_dict(spec_dict)
    assert spec.distribution_id == "rac-eot-test-dist-v1"
    spec.validate()  # does not raise


def test_invalid_spec_rejected(spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["parameter_manifest"]["geometry"]["scale"] = {"type": "bogus", "params": {"x": 1}}
    with pytest.raises(jsonschema.ValidationError):
        TransformationDistributionSpec.from_dict(bad)


def test_missing_required_group_rejected(spec_dict):
    bad = copy.deepcopy(spec_dict)
    del bad["parameter_manifest"]["print_capture"]
    with pytest.raises(jsonschema.ValidationError):
        TransformationDistributionSpec.from_dict(bad)


def test_scalar_only_surface_rejected(spec_dict):
    bad = copy.deepcopy(spec_dict)
    bad["robustness_surface"]["scalar_only_permitted"] = True
    with pytest.raises(jsonschema.ValidationError):
        TransformationDistributionSpec.from_dict(bad)


def test_reproducibility_bitwise(spec):
    sampler = Sampler(spec)
    a = sampler.sample(7)
    b = Sampler(TransformationDistributionSpec.from_dict(spec.to_dict())).sample(7)
    assert canonical_json(a) == canonical_json(b)


def test_independence_across_indices(spec):
    sampler = Sampler(spec)
    s0 = sampler.sample(0)
    s1 = sampler.sample(1)
    assert canonical_json(s0) != canonical_json(s1)
    # per-dimension draws differ (geometry.scale as representative)
    assert s0["geometry"]["scale"] != s1["geometry"]["scale"]


def test_fixed_and_choice_types(spec):
    sampler = Sampler(spec)
    s = sampler.sample(3)
    assert s["geometry"]["translation"] == 0.0
    assert s["imaging"]["resize_interpolation"] in ("nearest", "bilinear")


def test_sub_seed_deterministic_and_index_sensitive(spec_dict):
    m = spec_dict["parameter_manifest"]
    a = sub_seed("d", m, 1, 0)
    assert a == sub_seed("d", m, 1, 0)
    assert a != sub_seed("d", m, 1, 1)
    assert a != sub_seed("d", m, 2, 0)
    assert a != sub_seed("d2", m, 1, 0)


def test_manifest_hash_stable(spec_dict):
    assert manifest_sha256(spec_dict["parameter_manifest"]) == manifest_sha256(
        copy.deepcopy(spec_dict["parameter_manifest"])
    )


def test_sample_array_bitwise(spec):
    sampler = Sampler(spec)
    import numpy as np

    assert np.array_equal(sampler.sample_array(5, (16, 16)), sampler.sample_array(5, (16, 16)))
    assert not np.array_equal(sampler.sample_array(5, (16, 16)), sampler.sample_array(6, (16, 16)))

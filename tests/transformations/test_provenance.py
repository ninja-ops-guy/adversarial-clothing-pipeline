"""Provenance manifest emission + replay tests.

synthetic_pipeline_validation_only.
"""

import copy

import pytest

from ruthless_pipeline.transformations.distribution import canonical_json
from ruthless_pipeline.transformations.provenance import (
    SampleManifest,
    emit_manifest,
    replay_manifest,
)


def test_emit_fields(spec):
    m = emit_manifest(spec, 11)
    assert m.distribution_id == spec.distribution_id
    assert m.parameter_manifest_sha256 == spec.manifest_sha256
    assert m.seed == spec.seed
    assert m.sample_index == 11
    assert set(m.resolved_parameters) == {"geometry", "imaging", "garment", "print_capture"}
    assert len(m.sha256()) == 64


def test_roundtrip_dict(spec):
    m = emit_manifest(spec, 4)
    m2 = SampleManifest.from_dict(copy.deepcopy(m.to_dict()))
    assert m == m2
    assert m.sha256() == m2.sha256()


def test_replay_reproduces_identical_output(spec):
    m = emit_manifest(spec, 23)
    replayed = replay_manifest(spec, m)
    assert canonical_json(replayed) == canonical_json(m.resolved_parameters)
    # replay equals direct re-emit
    assert canonical_json(replayed) == canonical_json(emit_manifest(spec, 23).resolved_parameters)


def test_replay_rejects_tampered_manifest(spec):
    m = emit_manifest(spec, 5)
    tampered = SampleManifest(
        distribution_id=m.distribution_id,
        parameter_manifest_sha256=m.parameter_manifest_sha256,
        seed=m.seed,
        sample_index=m.sample_index,
        resolved_parameters={g: dict(d) for g, d in m.resolved_parameters.items()},
    )
    tampered.resolved_parameters["geometry"]["scale"] = 999.0
    with pytest.raises(ValueError):
        replay_manifest(spec, tampered)


def test_replay_rejects_spec_mismatch(spec, spec_dict):
    m = emit_manifest(spec, 5)
    other = copy.deepcopy(spec_dict)
    other["seed"] = 999
    from ruthless_pipeline.transformations.distribution import TransformationDistributionSpec

    with pytest.raises(ValueError):
        replay_manifest(TransformationDistributionSpec.from_dict(other), m)

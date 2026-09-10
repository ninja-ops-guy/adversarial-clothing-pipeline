"""Tests for SPEC-5 imposed-structure provenance (lane A)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.errors import OptimizerConstraintsError
from ruthless_pipeline.ctm.ids import pattern_id_from_genome
from ruthless_pipeline.ctm.optimizer_constraints import (
    OPTIMIZER_CONSTRAINTS_SCHEMA_VERSION,
    OptimizerConstraints,
    experimental_unit_id,
    same_experimental_unit,
)

GENOME_A = {
    "spectral": {"dominant_frequency": 4.0},
    "topology": {"components": 3},
    "color": {"palette_size": 5},
    "geometry": {"center_of_mass": [0.5, 0.5]},
}

TV_CONSTRAINTS = OptimizerConstraints(
    regularizers=({"name": "total_variation", "parameters": {"weight": 0.1}},),
)
UNREGULARIZED = OptimizerConstraints()


def test_constraints_hash_deterministic_and_versioned():
    a = TV_CONSTRAINTS.constraints_sha256()
    b = OptimizerConstraints.from_dict(TV_CONSTRAINTS.to_dict()).constraints_sha256()
    assert a == b
    assert len(a) == 64 and a == a.lower()
    assert TV_CONSTRAINTS.to_dict()["schema_version"] == (
        OPTIMIZER_CONSTRAINTS_SCHEMA_VERSION
    )


def test_identical_genomes_different_constraints_are_different_units():
    unit_tv = experimental_unit_id(GENOME_A, TV_CONSTRAINTS)
    unit_plain = experimental_unit_id(GENOME_A, UNREGULARIZED)
    assert unit_tv != unit_plain
    assert not same_experimental_unit(GENOME_A, TV_CONSTRAINTS, GENOME_A, UNREGULARIZED)


def test_identical_genome_same_constraints_same_unit():
    tv2 = OptimizerConstraints(
        regularizers=({"name": "total_variation", "parameters": {"weight": 0.1}},),
    )
    assert experimental_unit_id(GENOME_A, TV_CONSTRAINTS) == experimental_unit_id(
        GENOME_A, tv2
    )


def test_unit_id_stable_across_dict_key_order():
    shuffled = {k: GENOME_A[k] for k in reversed(list(GENOME_A))}
    assert experimental_unit_id(GENOME_A, TV_CONSTRAINTS) == experimental_unit_id(
        shuffled, TV_CONSTRAINTS
    )


def test_none_constraints_is_distinct_explicit_unit_class():
    assert experimental_unit_id(GENOME_A, None) != experimental_unit_id(
        GENOME_A, UNREGULARIZED
    )


def test_unit_id_differs_from_pattern_id():
    # Experimental-unit identity is genome + constraints, not just genome.
    assert experimental_unit_id(GENOME_A, TV_CONSTRAINTS) != pattern_id_from_genome(
        GENOME_A
    )


def test_constraint_parameter_change_changes_unit():
    stronger_tv = OptimizerConstraints(
        regularizers=({"name": "total_variation", "parameters": {"weight": 0.5}},),
    )
    assert experimental_unit_id(GENOME_A, TV_CONSTRAINTS) != experimental_unit_id(
        GENOME_A, stronger_tv
    )


def test_structural_constraints_recorded():
    oc = OptimizerConstraints(
        structural_constraints=(
            {"name": "palette_fixing", "parameters": {"palette": "cmyk-4"}},
            {"name": "symmetry_enforcement", "parameters": {"axis": "bilateral"}},
        )
    )
    d = oc.to_dict()
    assert len(d["structural_constraints"]) == 2
    assert oc.constraints_sha256() != UNREGULARIZED.constraints_sha256()


def test_malformed_blocks_fail_closed():
    with pytest.raises(OptimizerConstraintsError, match="name"):
        OptimizerConstraints(regularizers=({"parameters": {}},))
    with pytest.raises(OptimizerConstraintsError, match="parameters"):
        OptimizerConstraints(regularizers=({"name": "tv", "parameters": [1]},))
    with pytest.raises(OptimizerConstraintsError, match="schema_version"):
        OptimizerConstraints(schema_version="rac-ctm-optimizer-constraints/0.9")

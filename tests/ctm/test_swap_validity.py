"""Tests for SPEC-1 factor-swap validity contract (lane A)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.errors import SwapValidityError
from ruthless_pipeline.ctm.swap_validity import (
    FACTOR_RELATIONSHIPS,
    SWAP_VALIDITY_SCHEMA_VERSION,
    SwapValidity,
    check_pooling,
    derive_interpretation_class,
    is_observational_only,
    require_controlled_effect_eligible,
)

DUMMY_CONSTRAINT_REF = "c" * 64


def _main_effect(**overrides):
    kwargs = dict(
        varied_factor="topology",
        held_factors=("color",),
        factor_relationships={
            "topology": "optimized_variable",
            "color": "hard_constraint",
        },
        swap_scope="within_optimization_neighborhood",
        constraint_set_ref=DUMMY_CONSTRAINT_REF,
    )
    kwargs.update(overrides)
    return SwapValidity(**kwargs)


def _invalidation():
    # Voronoi-style: repainting under a hard palette constraint is an
    # out-of-optimum swap -> invalidation test, not a main-effect probe.
    return SwapValidity(
        varied_factor="color",
        held_factors=("topology",),
        factor_relationships={
            "color": "hard_constraint",
            "topology": "optimized_variable",
        },
        swap_scope="out_of_optimum",
        constraint_set_ref=DUMMY_CONSTRAINT_REF,
    )


# -- positive / derivation ---------------------------------------------------

def test_main_effect_probe_derived():
    assert _main_effect().interpretation_class == "main_effect_probe"


def test_out_of_optimum_derives_invalidation_test():
    assert _invalidation().interpretation_class == "invalidation_test"


def test_reoptimized_swap_derives_own_class():
    sv = _main_effect(swap_scope="reoptimized_after_swap")
    assert sv.interpretation_class == "reoptimized_swap"


def test_factor_relationship_enum_is_exact():
    assert FACTOR_RELATIONSHIPS == frozenset({
        "optimized_variable", "hard_constraint", "bounded_constraint",
        "soft_regularizer", "derived_dependency", "unconstrained", "posthoc_only",
    })


def test_schema_validation_roundtrip():
    _main_effect().validate_against_schema()
    _invalidation().validate_against_schema()


def test_serialization_is_deterministic():
    a = _main_effect()
    b = SwapValidity.from_dict(a.to_dict())
    assert a.canonical_bytes() == b.canonical_bytes()
    assert a.swap_validity_sha256() == b.swap_validity_sha256()
    assert a.to_dict()["schema_version"] == SWAP_VALIDITY_SCHEMA_VERSION


# -- negative / fail closed ----------------------------------------------------

def test_out_of_optimum_cannot_serialize_as_main_effect_probe():
    payload = _invalidation().to_dict()
    payload["interpretation_class"] = "main_effect_probe"  # user-asserted lie
    with pytest.raises(SwapValidityError, match="derived, never user-asserted"):
        SwapValidity.from_dict(payload)


def test_unknown_factor_relationship_fails_closed():
    with pytest.raises(SwapValidityError, match="unknown factor relationship"):
        _main_effect(factor_relationships={"topology": "kind_of_optimized"})


def test_missing_varied_factor_relationship_fails_closed():
    with pytest.raises(SwapValidityError, match="missing the varied factor"):
        SwapValidity(
            varied_factor="topology",
            factor_relationships={"color": "hard_constraint"},
            constraint_set_ref=DUMMY_CONSTRAINT_REF,
        )


def test_missing_held_factor_relationship_fails_closed():
    with pytest.raises(SwapValidityError, match="missing held factor"):
        SwapValidity(
            varied_factor="topology",
            held_factors=("spectrum",),
            factor_relationships={"topology": "optimized_variable"},
            constraint_set_ref=DUMMY_CONSTRAINT_REF,
        )


def test_bad_constraint_ref_fails_closed():
    with pytest.raises(SwapValidityError, match="constraint_set_ref"):
        _main_effect(constraint_set_ref="not-a-sha")


def test_varied_factor_not_optimized_variable_is_invalidation():
    sv = SwapValidity(
        varied_factor="spectrum",
        factor_relationships={"spectrum": "posthoc_only"},
        constraint_set_ref=DUMMY_CONSTRAINT_REF,
    )
    assert sv.interpretation_class == "invalidation_test"


# -- pooling -------------------------------------------------------------------

def test_pooling_same_class_ok():
    assert check_pooling([_main_effect(), _main_effect()]) == "main_effect_probe"


def test_pooling_invalidation_with_main_effect_refused():
    with pytest.raises(SwapValidityError, match="invalidation_test"):
        check_pooling([_main_effect(), _invalidation()])


def test_pooling_reoptimized_needs_interaction_model():
    reopt = _main_effect(swap_scope="reoptimized_after_swap")
    with pytest.raises(SwapValidityError, match="interaction model"):
        check_pooling([_main_effect(), reopt])
    assert (
        check_pooling([_main_effect(), reopt], interaction_model=True)
        == "main_effect_probe"
    )


def test_pooling_empty_refused():
    with pytest.raises(SwapValidityError, match="empty"):
        check_pooling([])


# -- promotion gate -------------------------------------------------------------

def test_controlled_effect_promotion_ok_for_main_effect():
    require_controlled_effect_eligible(_main_effect())


def test_controlled_effect_promotion_refuses_missing_semantics():
    with pytest.raises(SwapValidityError, match="absent"):
        require_controlled_effect_eligible(None)


def test_controlled_effect_promotion_refuses_invalidation_test():
    with pytest.raises(SwapValidityError, match="invalidation_test"):
        require_controlled_effect_eligible(_invalidation())


def test_observational_claims_may_proceed_without_semantics():
    assert is_observational_only(None) is True
    assert is_observational_only(_invalidation()) is True
    assert is_observational_only(_main_effect()) is False


def test_derive_rejects_unknown_scope():
    with pytest.raises(SwapValidityError, match="unknown swap_scope"):
        derive_interpretation_class(
            swap_scope="sideways",
            varied_factor_relationship="optimized_variable",
            held_relationships=(),
        )

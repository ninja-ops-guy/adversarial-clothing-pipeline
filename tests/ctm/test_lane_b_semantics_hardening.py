"""Corrective SPEC-11 tests: mechanism class is not a generality threshold."""
from ruthless_pipeline.ctm.target_semantics import (
    MECHANISM_CLASSES,
    MechanismTag,
    is_architecture_accident_bound,
)


def test_only_architecture_accident_class_is_bound():
    for mechanism_class in MECHANISM_CLASSES:
        expected = mechanism_class == "architecture_accident"
        assert is_architecture_accident_bound(mechanism_class) is expected
        assert MechanismTag(
            mechanism_class=mechanism_class
        ).architecture_accident_bound is expected

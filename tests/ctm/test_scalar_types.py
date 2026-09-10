"""Tests for SPEC-2 scalar-class typing / analysis-role separation (lane A)."""
from __future__ import annotations

import dataclasses

import pytest

from ruthless_pipeline.ctm.errors import ScalarTypingError
from ruthless_pipeline.ctm.scalar_types import (
    ANALYSIS_ROLES,
    SCALAR_CLASSES,
    TypedScalar,
    require_class_consistency,
)


def _tolerance():
    # Voronoi's "≤0.17" palette-repaint tolerance used as a predictor.
    return TypedScalar(
        value_id="voronoi.palette_tolerance",
        scalar_class="perturbation_tolerance",
        analysis_role="predictor",
        relation_type="association",
        outcome_id="transfer.delta_detection_rate",
    )


def test_scalar_class_enum_exact():
    assert SCALAR_CLASSES == frozenset({
        "pattern_feature", "evaluation_metric", "perturbation_tolerance",
        "effect_size", "covariate",
    })


def test_analysis_role_enum_exact():
    assert ANALYSIS_ROLES == frozenset({
        "predictor", "outcome", "adjustment_covariate", "descriptive_only",
    })


def test_tolerance_legal_as_predictor_and_stays_tolerance():
    s = _tolerance()
    assert s.analysis_role == "predictor"
    assert s.scalar_class == "perturbation_tolerance"
    d = s.to_dict()
    assert d["scalar_class"] == "perturbation_tolerance"
    assert d["analysis_role"] == "predictor"  # both axes always rendered


def test_reclass_always_refused():
    s = _tolerance()
    with pytest.raises(ScalarTypingError, match="immutable"):
        s.reclass("pattern_feature")


def test_scalar_class_frozen_on_instance():
    s = _tolerance()
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.scalar_class = "pattern_feature"


def test_with_analysis_role_preserves_class():
    s = _tolerance().with_analysis_role("descriptive_only")
    assert s.analysis_role == "descriptive_only"
    assert s.scalar_class == "perturbation_tolerance"


def test_metric_cannot_become_causal_mechanism():
    with pytest.raises(ScalarTypingError, match="causal_mechanism"):
        TypedScalar(
            value_id="m",
            scalar_class="evaluation_metric",
            analysis_role="predictor",
            relation_type="causal_mechanism",
        )


def test_tolerance_cannot_be_causal_mechanism():
    with pytest.raises(ScalarTypingError, match="causal_mechanism"):
        TypedScalar(
            value_id="t",
            scalar_class="perturbation_tolerance",
            relation_type="causal_mechanism",
        )


def test_unknown_class_and_role_fail_closed():
    with pytest.raises(ScalarTypingError, match="unknown scalar_class"):
        TypedScalar(value_id="x", scalar_class="vibe")
    with pytest.raises(ScalarTypingError, match="unknown analysis_role"):
        TypedScalar(value_id="x", scalar_class="covariate", analysis_role="hero")


def test_outcome_role_requires_outcome_id():
    with pytest.raises(ScalarTypingError, match="outcome_id"):
        TypedScalar(
            value_id="m",
            scalar_class="evaluation_metric",
            analysis_role="outcome",
        )


def test_roundtrip_deterministic():
    a = _tolerance()
    b = TypedScalar.from_dict(a.to_dict())
    assert a.canonical_bytes() == b.canonical_bytes()
    assert a.typed_scalar_sha256() == b.typed_scalar_sha256()


def test_class_consistency_gate():
    s = _tolerance()
    require_class_consistency(s, "perturbation_tolerance")
    with pytest.raises(ScalarTypingError, match="immutable"):
        require_class_consistency(s, "pattern_feature")

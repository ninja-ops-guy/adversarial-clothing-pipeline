"""synthetic_pipeline_validation_only — constraint primitive tests."""

from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.optimization.constraints import (
    BoxConstraint,
    SimplexConstraint,
    style_family_membership,
)


def test_box_projection_and_contains():
    box = BoxConstraint(np.array([-1.0, 0.0]), np.array([1.0, 2.0]))
    x = box.project(np.array([5.0, -3.0]))
    assert np.allclose(x, [1.0, 0.0])
    assert box.contains(x)
    assert not box.contains(np.array([1.5, 0.0]))


def test_box_scalar_bounds():
    box = BoxConstraint(-1.0, 1.0)
    assert np.allclose(box.project(np.array([2.0, -2.0])), [1.0, -1.0])


def test_box_invalid_rejected():
    with pytest.raises(ValueError):
        BoxConstraint(np.array([1.0]), np.array([-1.0]))


def test_simplex_projection():
    simplex = SimplexConstraint(dim=4)
    x = simplex.project(np.array([2.0, -1.0, 0.5, 0.25]))
    assert simplex.contains(x)
    assert float(np.sum(x)) == pytest.approx(1.0)
    assert np.all(x >= 0.0)


def test_simplex_projection_already_inside():
    simplex = SimplexConstraint(dim=3)
    x = np.array([0.2, 0.3, 0.5])
    assert np.allclose(simplex.project(x), x)


def test_simplex_dimension_check():
    simplex = SimplexConstraint(dim=3)
    with pytest.raises(ValueError):
        simplex.project(np.zeros(4))


def test_style_family_membership_hook():
    feats = {"product": "hat", "motifs": ["human_eye", "data", "slash"]}
    assert style_family_membership(feats, "signal_shadow")
    assert not style_family_membership({"product": "shirt", "motifs": []}, "signal_shadow")
    with pytest.raises(ValueError):
        style_family_membership(feats, "not_a_family")

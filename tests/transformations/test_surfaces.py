"""Robustness surface shape/determinism tests.

synthetic_pipeline_validation_only.
"""

import numpy as np
import pytest

from ruthless_pipeline.transformations.surfaces import RobustnessSurface, robustness_surface


def _eval_fn(params):
    # deterministic scalar response depending on swept dims
    return params["geometry"]["scale"] * 2.0 - params["imaging"]["blur"]


def test_surface_shape_and_cells(spec):
    surf = robustness_surface(
        _eval_fn,
        spec,
        grid_axes=["geometry.scale", "imaging.blur"],
        axis_values=[[0.8, 1.0, 1.2], [0.0, 1.0]],
        seeds=[1234, 99],
        sample_indices=[0, 1],
    )
    assert surf.responses.shape == (3, 2)
    assert surf.grid_axes == ["geometry.scale", "imaging.blur"]
    assert surf.scalar_only_permitted is False
    # cell values follow the deterministic response surface
    expected = np.array([[2 * s - b for b in (0.0, 1.0)] for s in (0.8, 1.0, 1.2)])
    assert np.allclose(surf.responses, expected)
    # summary is additive only
    d = surf.to_dict()
    assert d["responses"] == surf.responses.tolist()
    assert "summary" in d and set(d["summary"]) == {"mean", "std", "min", "max"}


def test_surface_deterministic(spec):
    kw = dict(
        grid_axes=["geometry.scale", "imaging.blur"],
        axis_values=[[0.9, 1.1], [0.5, 1.5]],
        seeds=[7, 8],
        sample_indices=[2, 3],
    )
    a = robustness_surface(_eval_fn, spec, **kw)
    b = robustness_surface(_eval_fn, spec, **kw)
    assert np.array_equal(a.responses, b.responses)
    assert a.to_dict() == b.to_dict()


def test_surface_requires_two_axes(spec):
    with pytest.raises(ValueError):
        robustness_surface(_eval_fn, spec, ["geometry.scale"], [[1.0]], [1], [0])


def test_surface_rejects_scalar_only_flag():
    with pytest.raises(ValueError):
        RobustnessSurface(
            grid_axes=["a"],
            axis_values=[[1.0]],
            response_metric="m",
            cell_value_type="scalar",
            scalar_only_permitted=True,
            responses=np.zeros((1,)),
        )


def test_surface_shape_mismatch_rejected():
    with pytest.raises(ValueError):
        RobustnessSurface(
            grid_axes=["a", "b"],
            axis_values=[[1.0, 2.0], [1.0]],
            response_metric="m",
            cell_value_type="scalar",
            scalar_only_permitted=False,
            responses=np.zeros((3, 3)),
        )

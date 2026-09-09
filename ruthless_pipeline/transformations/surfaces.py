"""Robustness surface evaluation over sampled transformation dimensions.

synthetic_pipeline_validation_only.

Per the frozen contract, robustness output is a per-dimension response grid
(``robustness_surface``), never a scalar-only average: ``scalar_only_permitted``
is always False and per-cell response values are retained. Summary stats are
allowed only in addition to the grid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Sequence

import numpy as np

from .distribution import Sampler, TransformationDistributionSpec


@dataclass
class RobustnessSurface:
    """Per-dimension response grid matching the schema robustness_surface spec."""

    grid_axes: List[str]
    axis_values: List[List[float]]
    response_metric: str
    cell_value_type: str
    scalar_only_permitted: bool  # always False — schema const
    responses: np.ndarray
    seeds: List[int] = field(default_factory=list)
    sample_indices: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.scalar_only_permitted:
            raise ValueError("a robustness surface may never be scalar-only")
        expected = tuple(len(v) for v in self.axis_values)
        if self.responses.shape != expected:
            raise ValueError(f"responses shape {self.responses.shape} != grid {expected}")

    def summary_stats(self) -> Dict[str, float]:
        """Additive summary only — the grid itself is the primary output."""
        return {
            "mean": float(self.responses.mean()),
            "std": float(self.responses.std()),
            "min": float(self.responses.min()),
            "max": float(self.responses.max()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_axes": list(self.grid_axes),
            "axis_values": [list(v) for v in self.axis_values],
            "response_metric": self.response_metric,
            "cell_value_type": self.cell_value_type,
            "scalar_only_permitted": False,
            "responses": self.responses.tolist(),
            "seeds": list(self.seeds),
            "sample_indices": list(self.sample_indices),
            "summary": self.summary_stats(),
        }


def _set_dimension(params: Dict[str, Dict[str, Any]], path: str, value: float) -> None:
    group, dim = path.split(".", 1)
    params[group][dim] = value


def robustness_surface(
    eval_fn: Callable[[Dict[str, Dict[str, Any]]], float],
    spec: TransformationDistributionSpec,
    grid_axes: Sequence[str],
    axis_values: Sequence[Sequence[float]],
    seeds: Sequence[int],
    sample_indices: Sequence[int],
    response_metric: str = "eval_fn_response",
    cell_value_type: str = "scalar",
) -> RobustnessSurface:
    """Evaluate eval_fn over a grid of swept dimensions.

    For each (seed, sample_index) in the seeds/indices grid the baseline
    parameter set is resolved via the deterministic Sampler; the two swept
    ``grid_axes`` dimensions are then overridden with the grid values and
    ``eval_fn(resolved_params) -> float`` is recorded per cell. The surface
    response at each cell is the mean over the (seed, index) replicates; the
    full grid of cell values is retained (never collapsed to a scalar).

    Exactly 2 grid axes are supported (2-D response grid).
    """
    if len(grid_axes) != 2 or len(axis_values) != 2:
        raise ValueError("robustness_surface requires exactly 2 grid axes")
    if len(seeds) != len(sample_indices):
        raise ValueError("seeds and sample_indices grids must be aligned")

    axis_vals = [list(map(float, vals)) for vals in axis_values]
    responses = np.zeros((len(axis_vals[0]), len(axis_vals[1])), dtype=np.float64)

    for seed, idx in zip(seeds, sample_indices):
        seeded_spec = TransformationDistributionSpec(
            distribution_id=spec.distribution_id,
            parameter_manifest=spec.parameter_manifest,
            seed=int(seed),
            sampling_reproducibility_note=spec.sampling_reproducibility_note,
            robustness_surface=spec.robustness_surface,
        )
        base = Sampler(seeded_spec).sample(int(idx))
        for i, v0 in enumerate(axis_vals[0]):
            for j, v1 in enumerate(axis_vals[1]):
                params = {g: dict(d) for g, d in base.items()}
                _set_dimension(params, grid_axes[0], v0)
                _set_dimension(params, grid_axes[1], v1)
                responses[i, j] += float(eval_fn(params))
    responses /= max(len(list(zip(seeds, sample_indices))), 1)

    return RobustnessSurface(
        grid_axes=list(grid_axes),
        axis_values=axis_vals,
        response_metric=response_metric,
        cell_value_type=cell_value_type,
        scalar_only_permitted=False,
        responses=responses,
        seeds=list(map(int, seeds)),
        sample_indices=list(map(int, sample_indices)),
    )

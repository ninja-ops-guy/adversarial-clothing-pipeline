"""Transformation distribution spec + reproducible sampler.

synthetic_pipeline_validation_only.

A sample is fully reproducible from the tuple
(distribution_id, parameter_manifest, seed, sample_index). The per-sample
sub-seed is::

    sha256(distribution_id | canonical_json(manifest) | seed | sample_index)

fed into ``numpy.random.SeedSequence`` / ``numpy.random.default_rng``. There
is no hidden entropy source: same inputs give bitwise-identical parameters,
and different sample indices give independent draws.

Validated against the FROZEN contract
``schemas/transformation_distribution.schema.json``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "transformation_distribution.schema.json"
)

# Fixed traversal order for parameter sampling within one sample. Determinism
# requires that every sample consumes the generator in exactly this order.
_GROUPS: Tuple[str, ...] = ("geometry", "imaging", "garment", "print_capture")
_DIMENSIONS: Dict[str, Tuple[str, ...]] = {
    "geometry": (
        "scale",
        "camera_distance",
        "perspective",
        "yaw",
        "pitch",
        "roll",
        "translation",
    ),
    "imaging": ("blur", "resize_interpolation", "compression", "exposure", "contrast"),
    "garment": ("stretch", "wrinkle", "fold", "bend", "partial_occlusion"),
    "print_capture": ("gamut_mapping", "resolution_loss"),
}

REPRODUCIBILITY_NOTE = (
    "Any sample index is fully reproducible from (distribution_id, "
    "parameter_manifest, seed, sample_index) with no hidden entropy source; "
    "per-sample sub-seed = sha256(distribution_id | canonical_json(manifest) "
    "| seed | sample_index)."
)


def load_schema() -> Dict[str, Any]:
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def canonical_json(obj: Any) -> str:
    """Canonical JSON encoding used for hashing (sorted keys, tight separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def manifest_sha256(parameter_manifest: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(parameter_manifest).encode("utf-8")).hexdigest()


def sub_seed(distribution_id: str, parameter_manifest: Dict[str, Any], seed: int, sample_index: int) -> bytes:
    """Per-sample sub-seed bytes per the frozen reproducibility contract."""
    material = "|".join(
        [str(distribution_id), canonical_json(parameter_manifest), str(int(seed)), str(int(sample_index))]
    )
    return hashlib.sha256(material.encode("utf-8")).digest()


def _generator_from_subseed(ss: bytes) -> np.random.Generator:
    pool = [int.from_bytes(ss[i : i + 4], "big") for i in range(0, 32, 4)]
    return np.random.default_rng(np.random.SeedSequence(pool))


def _draw_distribution(spec: Dict[str, Any], rng: np.random.Generator) -> Any:
    dtype = spec["type"]
    params = spec["params"]
    if dtype == "fixed":
        return params["value"]
    if dtype == "uniform":
        return float(rng.uniform(float(params["min"]), float(params["max"])))
    if dtype == "normal":
        return float(rng.normal(float(params["mean"]), float(params["std"])))
    if dtype == "lognormal":
        return float(rng.lognormal(float(params["mean"]), float(params["std"])))
    if dtype == "choice":
        values = list(params["values"])
        return values[int(rng.integers(0, len(values)))]
    raise ValueError(f"unknown distribution type: {dtype!r}")


@dataclass(frozen=True)
class TransformationDistributionSpec:
    """Schema-validated transformation distribution spec."""

    distribution_id: str
    parameter_manifest: Dict[str, Any]
    seed: int
    sampling_reproducibility_note: str = REPRODUCIBILITY_NOTE
    robustness_surface: Dict[str, Any] = field(
        default_factory=lambda: {
            "grid_axes": ["geometry.scale", "imaging.blur"],
            "response_metric": "eval_fn_response",
            "cell_value_type": "scalar",
            "scalar_only_permitted": False,
        }
    )
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "distribution_id": self.distribution_id,
            "parameter_manifest": self.parameter_manifest,
            "seed": self.seed,
            "sampling_reproducibility_note": self.sampling_reproducibility_note,
            "robustness_surface": self.robustness_surface,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransformationDistributionSpec":
        validate_spec_dict(data)
        return cls(
            distribution_id=data["distribution_id"],
            parameter_manifest=data["parameter_manifest"],
            seed=int(data["seed"]),
            sampling_reproducibility_note=data["sampling_reproducibility_note"],
            robustness_surface=data["robustness_surface"],
            schema_version=data["schema_version"],
        )

    def validate(self) -> None:
        validate_spec_dict(self.to_dict())

    @property
    def manifest_sha256(self) -> str:
        return manifest_sha256(self.parameter_manifest)


def validate_spec_dict(data: Dict[str, Any]) -> None:
    """Validate a spec dict against the frozen JSON schema (fail-closed)."""
    if jsonschema is None:  # pragma: no cover
        raise RuntimeError("jsonschema is required to validate transformation specs")
    jsonschema.validate(instance=data, schema=load_schema())


class Sampler:
    """Reproducible per-index sampler for a TransformationDistributionSpec."""

    def __init__(self, spec: TransformationDistributionSpec):
        spec.validate()
        self.spec = spec

    def sample(self, sample_index: int) -> Dict[str, Dict[str, Any]]:
        """Resolve the full parameter set for one sample index.

        Same (distribution_id, manifest, seed, index) -> identical parameters;
        different index -> independent draw.
        """
        ss = sub_seed(
            self.spec.distribution_id,
            self.spec.parameter_manifest,
            self.spec.seed,
            int(sample_index),
        )
        rng = _generator_from_subseed(ss)
        resolved: Dict[str, Dict[str, Any]] = {}
        for group in _GROUPS:
            resolved[group] = {}
            for dim in _DIMENSIONS[group]:
                dim_spec = self.spec.parameter_manifest[group][dim]
                resolved[group][dim] = _draw_distribution(dim_spec, rng)
        # Passthrough (not sampled): optional calibration transform reference.
        cal_ref = self.spec.parameter_manifest["print_capture"].get("calibration_transform_ref")
        if cal_ref is not None:
            resolved["print_capture"]["calibration_transform_ref"] = cal_ref
        return resolved

    def sample_array(self, sample_index: int, shape: Tuple[int, ...], base: float = 0.5) -> np.ndarray:
        """Deterministic synthetic base array for a sample index (float in [0,1])."""
        ss = sub_seed(
            self.spec.distribution_id + "::base",
            self.spec.parameter_manifest,
            self.spec.seed,
            int(sample_index),
        )
        rng = _generator_from_subseed(ss)
        return np.clip(rng.normal(base, 0.1, size=shape), 0.0, 1.0)


def dimension_path_list() -> List[str]:
    return [f"{g}.{d}" for g in _GROUPS for d in _DIMENSIONS[g]]

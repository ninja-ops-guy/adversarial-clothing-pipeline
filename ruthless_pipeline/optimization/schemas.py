"""ObjectiveSpec: validated loader for schemas/optimization_objective.schema.json.

The schema is a FROZEN Barrier 1 contract; this module only reads and
validates against it. Applies to FUTURE generations only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

import jsonschema

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "optimization_objective.schema.json"
)


class DetectorAggregation(Enum):
    """Per-detector aggregation modes allowed by the frozen contract."""

    MEAN = "MEAN"
    CVAR = "CVAR"
    WORST_CASE = "WORST_CASE"


@dataclass(frozen=True)
class ObjectiveSpec:
    """Validated, immutable view of an optimization objective contract."""

    objective_id: str
    seed: int
    aggregation: DetectorAggregation | None = None
    alpha: float | None = None
    lambda_print: float = 0.0
    lambda_style: float = 0.0
    lambda_deformation: float = 0.0
    lambda_reg: float = 0.0
    future_generations_only: bool = True
    raw: Mapping[str, Any] = field(repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        if self.aggregation is DetectorAggregation.CVAR:
            if self.alpha is None:
                raise ValueError("CVaR aggregation requires alpha in (0, 1]")
            alpha = float(self.alpha)
            if not math.isfinite(alpha) or not 0.0 < alpha <= 1.0:
                raise ValueError(f"CVaR alpha must be in (0, 1]; got {self.alpha!r}")
            object.__setattr__(self, "alpha", alpha)
        if not self.future_generations_only:
            raise ValueError("future_generations_only is hard-frozen to true")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], schema: Mapping[str, Any] | None = None) -> "ObjectiveSpec":
        schema = schema if schema is not None else load_schema()
        jsonschema.validate(instance=data, schema=schema)
        terms = data["terms"]
        det = terms.get("detector_loss")
        aggregation = DetectorAggregation(det["aggregation"]) if det else None
        alpha = det.get("alpha") if det else None
        return cls(
            objective_id=data["objective_id"],
            seed=int(data["seed"]),
            aggregation=aggregation,
            alpha=alpha,
            lambda_print=float(terms.get("printability_loss", {}).get("lambda_print", 0.0)),
            lambda_style=float(terms.get("style_loss", {}).get("lambda_style", 0.0)),
            lambda_deformation=float(terms.get("deformation_loss", {}).get("lambda_deformation", 0.0)),
            lambda_reg=float(terms.get("regularization", {}).get("lambda_reg", 0.0)),
            future_generations_only=bool(data["future_generations_only"]),
            raw=dict(data),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "ObjectiveSpec":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def weights(self) -> dict[str, float]:
        """Per-term weights; detector_loss weight is fixed to 1.0 by contract."""
        return {
            "detector_loss": 1.0,
            "printability_loss": self.lambda_print,
            "style_loss": self.lambda_style,
            "deformation_loss": self.lambda_deformation,
            "regularization": self.lambda_reg,
        }


def load_schema(path: str | Path | None = None) -> dict[str, Any]:
    with open(path or SCHEMA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)

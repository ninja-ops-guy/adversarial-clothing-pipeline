"""synthetic_pipeline_validation_only — shared synthetic fixtures."""

from __future__ import annotations

import numpy as np
import pytest

from ruthless_pipeline.optimization.objective_registry import Objective
from ruthless_pipeline.optimization.schemas import ObjectiveSpec


def synthetic_objective_dict(**overrides):
    data = {
        "schema_version": "1.0",
        "objective_id": "SYNTH-OPT-001",
        "terms": {
            "detector_loss": {"aggregation": "MEAN", "log_separately": True},
            "printability_loss": {"lambda_print": 0.5, "log_separately": True},
            "style_loss": {"lambda_style": 0.25, "log_separately": True},
            "deformation_loss": {"lambda_deformation": 0.1, "log_separately": True},
            "regularization": {"lambda_reg": 0.05, "log_separately": True},
        },
        "seed": 1234,
        "future_generations_only": True,
    }
    data.update(overrides)
    return data


@pytest.fixture
def spec() -> ObjectiveSpec:
    return ObjectiveSpec.from_dict(synthetic_objective_dict())


def make_quadratic_objective(spec: ObjectiveSpec, center=(0.3, -0.2)) -> Objective:
    """Synthetic quadratic terms with a known global minimum at ``center``."""
    c = np.asarray(center, dtype=float)
    obj = Objective(spec)
    obj.register_term("detector_loss", lambda x: (float(np.sum((x - c) ** 2)), {"kind": "synthetic"}))
    obj.register_term("printability_loss", lambda x: (float(np.sum(x ** 2)), {}))
    obj.register_term("style_loss", lambda x: (float(abs(x[0])), {}))
    obj.register_term("deformation_loss", lambda x: (float(abs(x[1])), {}))
    obj.register_term("regularization", lambda x: (float(np.sum(np.abs(x))), {}))
    return obj

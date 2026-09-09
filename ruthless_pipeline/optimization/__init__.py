"""RAC future-generation optimization infrastructure (pure numpy, model-free).

This namespace is Wave 3 infrastructure for FUTURE generations only. It never
produces scientific certification and never touches frozen D2-0004/D2-0005
surfaces. All synthetic validation lives under ``tests/optimization/``.
"""

from .schemas import DetectorAggregation, ObjectiveSpec
from .objective_registry import (
    NaNRefusalError,
    Objective,
    ObjectiveEvaluation,
)
from .optimizer import (
    CandidatePoolSearchOptimizer,
    Optimizer,
    OptimizerResult,
)
from .gradient_backend import (
    DivergenceRefusalError,
    GradientOptimizer,
    finite_difference_gradient,
)
from .blackbox_backend import OnePlusOneESOptimizer
from .trajectory import ResumeIntegrityError, TrajectoryRecorder
from .constraints import BoxConstraint, SimplexConstraint, style_family_membership
from .pareto import CandidateClass, classify, dominates, pareto_front
from .style import StyleOptimizationRecord, StyleFamilyScorer, style_pareto_curve

__all__ = [
    "BoxConstraint",
    "CandidateClass",
    "CandidatePoolSearchOptimizer",
    "DetectorAggregation",
    "DivergenceRefusalError",
    "GradientOptimizer",
    "NaNRefusalError",
    "Objective",
    "ObjectiveEvaluation",
    "ObjectiveSpec",
    "OnePlusOneESOptimizer",
    "Optimizer",
    "OptimizerResult",
    "ResumeIntegrityError",
    "SimplexConstraint",
    "StyleFamilyScorer",
    "StyleOptimizationRecord",
    "TrajectoryRecorder",
    "classify",
    "dominates",
    "finite_difference_gradient",
    "pareto_front",
    "style_family_membership",
    "style_pareto_curve",
]

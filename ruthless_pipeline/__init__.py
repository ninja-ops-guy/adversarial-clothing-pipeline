__version__ = "3.0.0"

from .nap import BlackBoxMode, BlackBoxNAPConfig, EnhancedBlackBoxNAP
from .deformation import NeuralDeformationConfig, DeformationObservation, NeuralDeformationModule, synthetic_observation
from .physics import DifferentiablePhysicsConfig, DifferentiablePhysicsPipeline
from .benchmark import BenchmarkConfig, CallableEvaluator, ComparativeBenchmark

__all__ = [
    "BlackBoxMode", "BlackBoxNAPConfig", "EnhancedBlackBoxNAP",
    "NeuralDeformationConfig", "DeformationObservation", "NeuralDeformationModule", "synthetic_observation",
    "DifferentiablePhysicsConfig", "DifferentiablePhysicsPipeline",
    "BenchmarkConfig", "CallableEvaluator", "ComparativeBenchmark",
    "GarmentSceneBatch", "GarmentTextureComposer", "TorchvisionDetectionEvaluator", "DifferentiableScoreEvaluator",
]

from .scene import GarmentSceneBatch, GarmentTextureComposer
from .evaluators import TorchvisionDetectionEvaluator, DifferentiableScoreEvaluator

__version__ = "3.1.0"

from .nap import BlackBoxMode, BlackBoxNAPConfig, EnhancedBlackBoxNAP
from .capgen import (
    EnvironmentAdaptiveConfig,
    EnvironmentAdaptivePatchGenerator,
    EnvironmentAdaptiveResult,
    extract_base_colors,
    initialize_pattern_logits,
    render_palette_patch,
)
from .deformation import NeuralDeformationConfig, DeformationObservation, NeuralDeformationModule, synthetic_observation
from .physics import DifferentiablePhysicsConfig, DifferentiablePhysicsPipeline
from .benchmark import BenchmarkConfig, CallableEvaluator, ComparativeBenchmark
from .scene import GarmentSceneBatch, GarmentTextureComposer
from .evaluators import DetectionBatch, TorchvisionDetectionEvaluator, DifferentiableScoreEvaluator
from .certification import (
    ArtifactBundle,
    ArtifactRef,
    Certificate,
    CertificateDecision,
    CertificationProtocol,
    EvidenceState,
    ModelManifest,
    ModelRegistry,
    PassCriteria,
    PatternManifest,
    issue_certificate,
    load_protocol,
    verify_certificate_bundle,
)

__all__ = [
    "BlackBoxMode", "BlackBoxNAPConfig", "EnhancedBlackBoxNAP",
    "EnvironmentAdaptiveConfig", "EnvironmentAdaptivePatchGenerator", "EnvironmentAdaptiveResult",
    "extract_base_colors", "initialize_pattern_logits", "render_palette_patch",
    "NeuralDeformationConfig", "DeformationObservation", "NeuralDeformationModule", "synthetic_observation",
    "DifferentiablePhysicsConfig", "DifferentiablePhysicsPipeline",
    "BenchmarkConfig", "CallableEvaluator", "ComparativeBenchmark",
    "GarmentSceneBatch", "GarmentTextureComposer", "DetectionBatch",
    "TorchvisionDetectionEvaluator", "DifferentiableScoreEvaluator",
    "ArtifactBundle", "ArtifactRef", "Certificate", "CertificateDecision",
    "CertificationProtocol", "EvidenceState", "ModelManifest", "ModelRegistry",
    "PassCriteria", "PatternManifest", "issue_certificate", "load_protocol", "verify_certificate_bundle",
]

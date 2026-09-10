"""Public package surface for the Ruthless Adversarial Pipeline.

The project exposes a convenience API from :mod:`ruthless_pipeline`, but most
of those objects live in optional/heavy ML modules.  Keep the public surface
stable while resolving those objects lazily so lightweight certification and
provenance tooling does not import Torch, torchvision, SciPy, or Pillow merely
by importing the package namespace.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "3.1.0"

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BlackBoxMode": (".nap", "BlackBoxMode"),
    "BlackBoxNAPConfig": (".nap", "BlackBoxNAPConfig"),
    "EnhancedBlackBoxNAP": (".nap", "EnhancedBlackBoxNAP"),
    "EnvironmentAdaptiveConfig": (".capgen", "EnvironmentAdaptiveConfig"),
    "EnvironmentAdaptivePatchGenerator": (".capgen", "EnvironmentAdaptivePatchGenerator"),
    "EnvironmentAdaptiveResult": (".capgen", "EnvironmentAdaptiveResult"),
    "extract_base_colors": (".capgen", "extract_base_colors"),
    "initialize_pattern_logits": (".capgen", "initialize_pattern_logits"),
    "render_palette_patch": (".capgen", "render_palette_patch"),
    "CandidateArtifact": (".candidate_optimizer", "CandidateArtifact"),
    "CandidateGenerationConfig": (".candidate_optimizer", "CandidateGenerationConfig"),
    "DetectorDrivenCandidateOptimizer": (".candidate_optimizer", "DetectorDrivenCandidateOptimizer"),
    "NeuralDeformationConfig": (".deformation", "NeuralDeformationConfig"),
    "DeformationObservation": (".deformation", "DeformationObservation"),
    "NeuralDeformationModule": (".deformation", "NeuralDeformationModule"),
    "synthetic_observation": (".deformation", "synthetic_observation"),
    "DifferentiablePhysicsConfig": (".physics", "DifferentiablePhysicsConfig"),
    "DifferentiablePhysicsPipeline": (".physics", "DifferentiablePhysicsPipeline"),
    "BenchmarkConfig": (".benchmark", "BenchmarkConfig"),
    "CallableEvaluator": (".benchmark", "CallableEvaluator"),
    "ComparativeBenchmark": (".benchmark", "ComparativeBenchmark"),
    "GarmentSceneBatch": (".scene", "GarmentSceneBatch"),
    "GarmentTextureComposer": (".scene", "GarmentTextureComposer"),
    "DetectionBatch": (".evaluators", "DetectionBatch"),
    "TorchvisionDetectionEvaluator": (".evaluators", "TorchvisionDetectionEvaluator"),
    "DifferentiableScoreEvaluator": (".evaluators", "DifferentiableScoreEvaluator"),
    "ArtifactBundle": (".certification", "ArtifactBundle"),
    "ArtifactRef": (".certification", "ArtifactRef"),
    "Certificate": (".certification", "Certificate"),
    "CertificateDecision": (".certification", "CertificateDecision"),
    "CertificationProtocol": (".certification", "CertificationProtocol"),
    "EvidenceState": (".certification", "EvidenceState"),
    "ModelManifest": (".certification", "ModelManifest"),
    "ModelRegistry": (".certification", "ModelRegistry"),
    "PassCriteria": (".certification", "PassCriteria"),
    "PatternManifest": (".certification", "PatternManifest"),
    "issue_certificate": (".certification", "issue_certificate"),
    "load_protocol": (".certification", "load_protocol"),
    "verify_certificate_bundle": (".certification", "verify_certificate_bundle"),
}

__all__ = [
    "BlackBoxMode", "BlackBoxNAPConfig", "EnhancedBlackBoxNAP",
    "EnvironmentAdaptiveConfig", "EnvironmentAdaptivePatchGenerator", "EnvironmentAdaptiveResult",
    "extract_base_colors", "initialize_pattern_logits", "render_palette_patch",
    "CandidateArtifact", "CandidateGenerationConfig", "DetectorDrivenCandidateOptimizer",
    "NeuralDeformationConfig", "DeformationObservation", "NeuralDeformationModule", "synthetic_observation",
    "DifferentiablePhysicsConfig", "DifferentiablePhysicsPipeline",
    "BenchmarkConfig", "CallableEvaluator", "ComparativeBenchmark",
    "GarmentSceneBatch", "GarmentTextureComposer", "DetectionBatch",
    "TorchvisionDetectionEvaluator", "DifferentiableScoreEvaluator",
    "ArtifactBundle", "ArtifactRef", "Certificate", "CertificateDecision",
    "CertificationProtocol", "EvidenceState", "ModelManifest", "ModelRegistry",
    "PassCriteria", "PatternManifest", "issue_certificate", "load_protocol", "verify_certificate_bundle",
]


def __getattr__(name: str) -> Any:
    """Resolve a public convenience export on first access.

    The resolved object is cached in ``globals()`` so subsequent access has the
    same behavior and cost as a normal eager import.
    """

    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = target
    module = import_module(module_name, __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))

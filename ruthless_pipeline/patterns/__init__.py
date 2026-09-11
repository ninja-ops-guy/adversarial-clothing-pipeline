"""RAC Pattern Generator Library (public API).

Adapted from noRecognition v0.9.8 with evidence-integrity adaptations:
deterministic generation, canonical provenance hashing, fail-closed typed
errors, and EXPLORATORY-only candidate artifacts.
"""
from .base import (
    CODE_SCHEMA_VERSION,
    GeneratedPattern,
    GeneratorParams,
    GeneratorRegistrationError,
    MissingLandmarksError,
    PatternCompositionError,
    PatternGenerator,
    PatternGeneratorError,
    PatternNondeterminismError,
    PatternNotImplementedError,
    PatternParamError,
    ProvenanceMismatchError,
    StubPatternGenerator,
)
from .structural_biometric import (
    DazzleSurgicalLinesGenerator,
    HyperfaceLikeGenerator,
    KeyFeatureBlackoutGenerator,
)
from .feature_disruption import (
    AdversarialPatchGenerator,
    FeatureCollageGenerator,
    LandmarkNoiseGenerator,
    SaliencyEyeAttackGenerator,
    SwappedLandmarksGenerator,
)
from .composer import ComposedPattern, PatternComposer
from .registry import GeneratorRegistry
from .utility import DEFERRED_P3, DEFERRED_P3_NOTE, guard_p3_registration

P0_GENERATORS = (
    HyperfaceLikeGenerator,
    DazzleSurgicalLinesGenerator,
    KeyFeatureBlackoutGenerator,
    SaliencyEyeAttackGenerator,
    AdversarialPatchGenerator,
    SwappedLandmarksGenerator,
    LandmarkNoiseGenerator,
    FeatureCollageGenerator,
)

__all__ = [
    "CODE_SCHEMA_VERSION",
    "GeneratedPattern",
    "GeneratorParams",
    "PatternGenerator",
    "StubPatternGenerator",
    "PatternGeneratorError",
    "PatternParamError",
    "MissingLandmarksError",
    "PatternNondeterminismError",
    "ProvenanceMismatchError",
    "PatternNotImplementedError",
    "PatternCompositionError",
    "GeneratorRegistrationError",
    "HyperfaceLikeGenerator",
    "DazzleSurgicalLinesGenerator",
    "KeyFeatureBlackoutGenerator",
    "SaliencyEyeAttackGenerator",
    "AdversarialPatchGenerator",
    "SwappedLandmarksGenerator",
    "LandmarkNoiseGenerator",
    "FeatureCollageGenerator",
    "ComposedPattern",
    "PatternComposer",
    "GeneratorRegistry",
    "DEFERRED_P3",
    "DEFERRED_P3_NOTE",
    "guard_p3_registration",
    "P0_GENERATORS",
]

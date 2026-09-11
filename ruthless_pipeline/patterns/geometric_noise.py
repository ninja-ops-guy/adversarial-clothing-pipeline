"""Geometric/algorithmic noise generators (spec sections 5, 6).

P0 scope: STUBS ONLY. These classes are registered but raise
PatternNotImplementedError from generate(). The spec's fft_noise and
simulated_optimized_noise are P1; the remainder are P2 (spec section 6).
cv2 is intentionally not used anywhere in this package (not installed);
the spec's cv2-based algorithms (optical_flow_warp, colorspace_jitter)
are P1 and deferred.
"""
from __future__ import annotations

from .base import StubPatternGenerator


class FFTNoiseGenerator(StubPatternGenerator):
    """P1 stub: frequency-domain modification (spec section 5.2)."""
    name = "fft_noise"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P1"


class SimulatedOptimizedNoiseGenerator(StubPatternGenerator):
    """P1 stub: posterized Perlin noise with adversarial colormaps (5.4)."""
    name = "simulated_optimized_noise"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P1"


class SimpleShapesGenerator(StubPatternGenerator):
    name = "simple_shapes"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P2"


class FractalNoiseGenerator(StubPatternGenerator):
    name = "fractal_noise"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P2"


class PerlinNoiseGenerator(StubPatternGenerator):
    name = "perlin_noise"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P2"


class HFNoiseGenerator(StubPatternGenerator):
    name = "hf_noise"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P2"


class CheckerboardGenerator(StubPatternGenerator):
    name = "checkerboard"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P2"


class GradientGenerator(StubPatternGenerator):
    name = "gradient"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P2"


class OpArtChevronsGenerator(StubPatternGenerator):
    name = "op_art_chevrons"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P2"


class InterferenceLinesGenerator(StubPatternGenerator):
    name = "interference_lines"
    version = "1.0.0"
    category = "geometric_noise"
    priority = "P2"


P1_GENERATORS = ("fft_noise", "simulated_optimized_noise")
P2_GENERATORS = ("simple_shapes", "fractal_noise", "perlin_noise", "hf_noise",
                 "checkerboard", "gradient", "op_art_chevrons", "interference_lines")

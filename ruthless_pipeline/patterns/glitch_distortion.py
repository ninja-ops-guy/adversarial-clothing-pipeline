"""Glitch/distortion generators (spec sections 5, 6).

P0 scope: STUBS ONLY (PatternNotImplementedError from generate()).
The spec's optical_flow_warp and colorspace_jitter require cv2, which is
deliberately not a dependency of this package; they remain P1 stubs.
"""
from __future__ import annotations

from .base import StubPatternGenerator


class OpticalFlowWarpGenerator(StubPatternGenerator):
    """P1 stub: Farneback optical-flow liquify (spec 5.3; needs cv2 -> deferred)."""
    name = "optical_flow_warp"
    version = "1.0.0"
    category = "glitch_distortion"
    priority = "P1"


class ColorspaceJitterGenerator(StubPatternGenerator):
    """P1 stub: YCrCb chrominance noise (spec 5.5; needs cv2 -> deferred)."""
    name = "colorspace_jitter"
    version = "1.0.0"
    category = "glitch_distortion"
    priority = "P1"


class SelectiveBlurGenerator(StubPatternGenerator):
    name = "selective_blur"
    version = "1.0.0"
    category = "glitch_distortion"
    priority = "P2"


class PixelSortGlitchGenerator(StubPatternGenerator):
    name = "pixel_sort_glitch"
    version = "1.0.0"
    category = "glitch_distortion"
    priority = "P2"


class RGBChannelShiftGenerator(StubPatternGenerator):
    name = "rgb_channel_shift"
    version = "1.0.0"
    category = "glitch_distortion"
    priority = "P2"


class WarpedFaceGenerator(StubPatternGenerator):
    name = "warped_face"
    version = "1.0.0"
    category = "glitch_distortion"
    priority = "P2"


P1_GENERATORS = ("optical_flow_warp", "colorspace_jitter")
P2_GENERATORS = ("selective_blur", "pixel_sort_glitch", "rgb_channel_shift", "warped_face")

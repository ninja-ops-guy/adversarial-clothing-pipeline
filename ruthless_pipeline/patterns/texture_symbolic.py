"""Texture/symbolic generators (spec section 6).

P0 scope: STUBS ONLY (PatternNotImplementedError from generate()).
"""
from __future__ import annotations

from .base import StubPatternGenerator


class TiledLogoGenerator(StubPatternGenerator):
    name = "tiled_logo"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class VortexGenerator(StubPatternGenerator):
    name = "vortex"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class PhotonegativePatchGenerator(StubPatternGenerator):
    name = "photonegative_patch"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class PopArtCollageGenerator(StubPatternGenerator):
    name = "pop_art_collage"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class RandomTextGenerator(StubPatternGenerator):
    name = "random_text"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class QRCodeGenerator(StubPatternGenerator):
    name = "qr_code"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class ASCIIFaceGenerator(StubPatternGenerator):
    name = "ascii_face"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class TrypophobiaGenerator(StubPatternGenerator):
    name = "trypophobia"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class AnimalPrintGenerator(StubPatternGenerator):
    name = "animal_print"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


class RecursiveFaceTileGenerator(StubPatternGenerator):
    name = "recursive_face_tile"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P2"


P2_GENERATORS = ("tiled_logo", "vortex", "photonegative_patch", "pop_art_collage",
                 "random_text", "qr_code", "ascii_face", "trypophobia",
                 "animal_print", "recursive_face_tile")

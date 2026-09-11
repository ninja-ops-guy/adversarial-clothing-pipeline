"""Utility/helper and legacy pattern generators (spec sections 5-7).

P0 scope: STUBS ONLY, plus the P3 deferral guard.

P3 generators (bad_words, web_attack_strings) are content attacks with
legal/ethical concerns (spec section 7). They are DEFERRED and must not be
registered; guard_p3_registration() refuses them fail-closed.
"""
from __future__ import annotations

from typing import Any

from .base import GeneratorRegistrationError, StubPatternGenerator

#: P3 content-attack generators deferred pending legal/ethical review.
DEFERRED_P3 = ("bad_words", "web_attack_strings")
DEFERRED_P3_NOTE = "deferred pending legal/ethical review"


def guard_p3_registration(generator_class: Any) -> None:
    """Refuse registration of deferred P3 generators (fail closed)."""
    name = getattr(generator_class, "name", None)
    if name is None and not isinstance(generator_class, type):
        name = getattr(generator_class, "name", None)
    if name in DEFERRED_P3:
        raise GeneratorRegistrationError(
            f"refusing to register P3 generator '{name}': {DEFERRED_P3_NOTE}")


class FaceIDStructuredLightGenerator(StubPatternGenerator):
    """P1 stub: simulated IR dot grid for depth-sensor disruption (spec 5.1)."""
    name = "faceid_structured_light"
    version = "1.0.0"
    category = "structural_biometric"
    priority = "P1"


class BlackoutPatchesGenerator(StubPatternGenerator):
    name = "blackout_patches"
    version = "1.0.0"
    category = "utility"
    priority = "P2"


P1_GENERATORS = ("faceid_structured_light",)
P2_GENERATORS = ("blackout_patches",)

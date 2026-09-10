"""CTM bridge (lane B1) error hierarchy. Every failure mode is a typed refusal.

Mirrors the style of ruthless_pipeline/pattern_genome/errors.py.
"""
from __future__ import annotations


class CTMBridgeError(Exception):
    """Base class for all CTM bridge failures."""


class RegistryConflictError(CTMBridgeError):
    """Registry write collision with different content under the same pattern_id."""


class RegistrationError(CTMBridgeError):
    """Digital genome registration failed (hash mismatch, invalid genome, bad input)."""


class ComparisonError(CTMBridgeError):
    """Genome comparison could not be performed (missing registry entry, bad genome)."""


class PendingUserAction(CTMBridgeError):
    """A physical/calibration path requires human action. Carries the JSON packet."""

    def __init__(self, packet: dict):
        self.packet = packet
        super().__init__(packet.get("reason", "pending user action"))

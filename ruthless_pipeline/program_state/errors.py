"""Typed fail-closed errors for canonical program state derivation."""

from __future__ import annotations


class ProgramStateError(ValueError):
    """Base class for all program-state refusals (fail closed)."""


class SourceMissingError(ProgramStateError):
    """A required canonical source is absent or unreadable."""


class SourceContradictionError(ProgramStateError):
    """Canonical sources contradict each other; refuse to derive a state."""


class StaleProgramStateError(ProgramStateError):
    """Committed program_state artifacts do not match a fresh derivation."""


class ProgramStateSchemaError(ProgramStateError):
    """Derived state failed validation against the program-state schema."""

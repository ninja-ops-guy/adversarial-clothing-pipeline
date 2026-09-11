"""Canonical program state (SW-01): deterministic derivation from sources.

Lazy attribute re-exports so ``python -m ruthless_pipeline.program_state.compile``
does not trigger double-import warnings.
"""

from __future__ import annotations

__all__ = [
    "EVIDENCE_CLASS",
    "GENERATOR",
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "STATE_PATH",
    "SUMMARY_PATH",
    "ProgramStateError",
    "ProgramStateSchemaError",
    "SourceContradictionError",
    "SourceMissingError",
    "StaleProgramStateError",
    "canonical_state_bytes",
    "check_state",
    "derive_state",
    "main",
    "render_summary_markdown",
    "write_state",
]


def __getattr__(name: str):
    if name in __all__:
        if name in {
            "ProgramStateError",
            "ProgramStateSchemaError",
            "SourceContradictionError",
            "SourceMissingError",
            "StaleProgramStateError",
        }:
            from . import errors

            return getattr(errors, name)
        from . import compile as _compile

        return getattr(_compile, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

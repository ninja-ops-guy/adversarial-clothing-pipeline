"""Shared schema-version guard for governed JSON contracts.

Every governed artifact family in this repository (generation records, trial
store lines, capture sessions, candidate pools, selection reports, runtime
locks, physical trial manifests, cumulative trial stores) stamps a top-level
``schema_version`` string. Parsers must fail closed: a missing, non-string,
or mismatched version is a hard error, never a silent parse. This module
centralizes that guard so scripts do not re-implement ad-hoc (and
inconsistent) checks.

Usage::

    payload = load_versioned_json(path, expected="1.0", label="trial store")
    require_schema_version(record, "1.0", label=f"trial store line {n}")

The historical incident class this prevents: a producer bumping its emitted
schema (e.g. the print-test-kit 1.3 -> 1.4 bump) while a consumer silently
parsed the new shape against old assumptions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SchemaVersionError(ValueError):
    """Raised when a payload's schema_version is missing or unsupported.

    Subclasses ValueError so existing fail-closed call sites that catch
    ValueError keep working unchanged.
    """


def require_schema_version(
    payload: Any,
    expected: str,
    *,
    label: str = "payload",
) -> Any:
    """Fail closed unless ``payload`` is a mapping whose top-level
    ``schema_version`` exactly equals ``expected``.

    Raises SchemaVersionError with a message naming the label, the expected
    version, and the actual value. Returns the payload unchanged on success
    so call sites can chain.
    """
    if not isinstance(payload, dict):
        raise SchemaVersionError(
            f"{label}: expected a JSON object with schema_version {expected!r}; "
            f"got {type(payload).__name__}"
        )
    actual = payload.get("schema_version")
    if actual is None:
        raise SchemaVersionError(
            f"{label}: missing schema_version (expected {expected!r}); "
            "refusing to parse an unversioned contract"
        )
    if not isinstance(actual, str):
        raise SchemaVersionError(
            f"{label}: schema_version must be a string, got "
            f"{type(actual).__name__} ({actual!r}); expected {expected!r}"
        )
    if actual != expected:
        raise SchemaVersionError(
            f"{label}: unsupported schema_version {actual!r}; "
            f"this parser supports exactly {expected!r}"
        )
    return payload


def load_versioned_json(
    path: str | Path,
    expected: str,
    *,
    label: str | None = None,
) -> dict[str, Any]:
    """Load a JSON object from ``path`` and enforce its schema_version.

    Malformed JSON propagates as json.JSONDecodeError (a ValueError), so the
    caller still fails closed on truncated/corrupt files. Version problems
    raise SchemaVersionError.
    """
    path = Path(path)
    payload = json.loads(path.read_text())
    return require_schema_version(payload, expected, label=label or str(path))

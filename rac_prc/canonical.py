from __future__ import annotations

import hashlib
import json
import math
from typing import Any

FORMAT_ID = "rac-canonical-json-v1"


def _validate_numbers(value: Any) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical evidence JSON forbids NaN and infinities")
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical evidence JSON requires string object keys")
            _validate_numbers(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _validate_numbers(item)


def canonical_bytes(value: Any) -> bytes:
    """Serialize RAC evidence deterministically without rounding scientific values.

    This is RAC's own versioned canonical form, not a claim of RFC 8785/JCS
    compliance. Cross-language implementations must implement FORMAT_ID exactly.
    """
    _validate_numbers(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

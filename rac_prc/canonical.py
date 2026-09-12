from __future__ import annotations

import hashlib
import json
import math


class RACCanonicalSerializer:
    """Defines the frozen RAC-CANONICAL-JSON-v1 serialization contract."""

    VERSION = "RAC-CANONICAL-JSON-v1"

    @classmethod
    def serialize(cls, data) -> str:
        if isinstance(data, dict):
            return "{" + ",".join(
                f"{json.dumps(k, ensure_ascii=True)}:{cls.serialize(v)}"
                for k, v in sorted(data.items())
            ) + "}"
        if isinstance(data, list):
            return "[" + ",".join(cls.serialize(x) for x in data) + "]"
        if isinstance(data, float):
            if not math.isfinite(data):
                raise ValueError("RAC-CANONICAL-JSON-v1 refuses NaN and infinities")
            if data == 0.0:
                data = 0.0
            return f"{data:.17g}"
        if isinstance(data, bool):
            return "true" if data else "false"
        if data is None:
            return "null"
        if isinstance(data, str):
            return json.dumps(data, ensure_ascii=True)
        if isinstance(data, int):
            return str(data)
        raise TypeError(f"unsupported canonical type: {type(data).__name__}")

    @classmethod
    def compute_sha256(cls, data) -> str:
        return hashlib.sha256(cls.serialize(data).encode("utf-8")).hexdigest()

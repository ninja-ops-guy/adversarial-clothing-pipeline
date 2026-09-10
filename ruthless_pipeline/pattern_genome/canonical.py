"""Canonical JSON and content hashing for Pattern Genome."""
from __future__ import annotations
import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from typing import Any
from .errors import PatternGenomeNonFiniteError

def _reject_non_finite(obj: Any, path: str = "") -> None:
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise PatternGenomeNonFiniteError(f"non-finite float at {path or '<root>'}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _reject_non_finite(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _reject_non_finite(v, f"{path}[{i}]")

def _to_builtin(obj: Any) -> Any:
    if is_dataclass(obj):
        return _to_builtin(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_builtin(v) for v in obj]
    return obj

def canonical_json(genome: Any) -> bytes:
    d = _to_builtin(genome)
    _reject_non_finite(d)
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def genome_sha256(genome: Any) -> str:
    """Hash canonical genome content excluding self-identifying fields."""
    d = _to_builtin(genome)
    if isinstance(d, dict):
        d.pop("genome_sha256", None)
        d["genome_id"] = ""
    return sha256_bytes(canonical_json(d))

"""Generator registry and versioning (spec section 9, minus timestamps).

EVIDENCE-INTEGRITY ADAPTATION: the spec records ``datetime.now()`` at
registration; that is replaced by the static marker registered_from="static"
so registry state and exported logs are fully deterministic.

Keys are ``name@version``. Re-registering the SAME class under the same key
is idempotent; registering a DIFFERENT class under the same key raises
GeneratorRegistrationError. Deferred P3 generators are refused.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type

from ruthless_pipeline.pattern_genome.canonical import canonical_json

from .base import GeneratorRegistrationError, PatternGenerator
from .utility import guard_p3_registration


def _semver_key(version: str) -> Tuple[int, ...]:
    parts = []
    for chunk in str(version).split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


class GeneratorRegistry:
    """Central registry of all pattern generators."""

    def __init__(self) -> None:
        self.generators: Dict[str, Dict[str, Any]] = {}
        self.usage_stats: Dict[str, List[str]] = {}

    def register(self, generator_class: Type[PatternGenerator]) -> None:
        """Register a generator class (fail closed on conflict/P3)."""
        guard_p3_registration(generator_class)
        instance = generator_class() if isinstance(generator_class, type) else generator_class
        key = f"{instance.name}@{instance.version}"
        existing = self.generators.get(key)
        if existing is not None:
            if existing["class"] is not generator_class:
                raise GeneratorRegistrationError(
                    f"conflicting duplicate registration: {key}")
            return  # idempotent re-registration of the same class
        self.generators[key] = {
            "class": generator_class,
            "instance": instance,
            "registered_from": "static",
        }

    def get(self, name: str, version: Optional[str] = None) -> PatternGenerator:
        """Retrieve generator by name and optional version (latest if omitted)."""
        if version is not None:
            key = f"{name}@{version}"
            if key not in self.generators:
                raise GeneratorRegistrationError(f"no such generator: {key}")
            return self.generators[key]["instance"]
        keys = [k for k in self.generators if k.startswith(f"{name}@")]
        if not keys:
            raise GeneratorRegistrationError(f"no such generator: {name}")
        latest = sorted(keys, key=lambda k: _semver_key(k.split("@", 1)[1]))[-1]
        return self.generators[latest]["instance"]

    def list_by_priority(self, priority: str) -> List[PatternGenerator]:
        """List all registered generators of the given priority."""
        return [g["instance"] for g in self.generators.values()
                if g["instance"].priority == priority]

    def record_usage(self, generator_name: str, experiment_id: str) -> None:
        """Track generator usage (in-memory, deterministic, exportable)."""
        self.usage_stats.setdefault(generator_name, []).append(experiment_id)

    def export_usage_log(self) -> bytes:
        """Export the usage log as canonical JSON bytes."""
        return canonical_json({k: list(v) for k, v in sorted(self.usage_stats.items())})

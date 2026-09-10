"""CTM pattern identity.

NEW canonical definition (owned by CTM bridge lane B1; documented loudly):

    pattern_id = "RAC-CTM-PAT-" + sha256(
        canonical genome bytes WITHOUT self-referential fields
        + b"rac-pattern-genome/1.0"
    )[:16].lower()

Self-referential fields excluded from the hash are ``genome_id`` and
``genome_sha256`` (the genome's own identity material). Canonical bytes are
produced by ruthless_pipeline.pattern_genome.canonical.canonical_json
(sort_keys, separators=(",",":"), allow_nan=False) — this module does NOT
reimplement canonical JSON; it imports it.

Deterministic: identical genome content -> identical pattern_id, independent
of dict key ordering.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from ruthless_pipeline.pattern_genome.schema import SCHEMA_VERSION as GENOME_SCHEMA_VERSION

PATTERN_ID_PREFIX = "RAC-CTM-PAT-"
_SELF_REFERENTIAL_FIELDS = ("genome_id", "genome_sha256")


def _strip_self_referential(genome) -> dict:
    d = asdict(genome) if is_dataclass(genome) else dict(genome)
    for field in _SELF_REFERENTIAL_FIELDS:
        d.pop(field, None)
    return d


def genome_content_sha256(genome) -> str:
    """SHA-256 of canonical genome bytes (sans self-referential fields) plus the
    genome schema version string. Full 64-char lowercase hex digest."""
    content = canonical_json(_strip_self_referential(genome)) + GENOME_SCHEMA_VERSION.encode("utf-8")
    return sha256_bytes(content)


def pattern_id_from_genome(genome) -> str:
    """Derive the CTM pattern_id for a genome (dataclass or dict). Deterministic."""
    return PATTERN_ID_PREFIX + genome_content_sha256(genome)[:16].lower()

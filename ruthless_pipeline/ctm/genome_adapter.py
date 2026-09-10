"""Register a digital candidate as a CTM pattern genome.

Pipeline: sha256(candidate_bytes) -> extract_genome -> validate_genome ->
canonical genome bytes -> pattern_id -> write
ctm_registry/patterns/<pattern_id>/{genome.json, provenance.json, master.sha256.json}.

Fail-closed: candidate_sha256 mismatch, invalid genome, or a registry write
collision with DIFFERENT content all raise typed errors. Idempotent:
re-registering identical content produces byte-identical files, the same
pattern_id, and a record with already_present=True.

Measurement only. physical_efficacy_claimed is always false; evidence class is
hard-frozen to derived_digital_measurement.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path

from ruthless_pipeline.pattern_genome.canonical import canonical_json
from ruthless_pipeline.pattern_genome.canonical import genome_sha256 as pg_genome_sha256
from ruthless_pipeline.pattern_genome.config import PatternGenomeConfig
from ruthless_pipeline.pattern_genome.extractor import extract_genome
from ruthless_pipeline.pattern_genome.validation import validate_genome

from .errors import CTMBridgeError, RegistrationError, RegistryConflictError
from .ids import pattern_id_from_genome

DEFAULT_REGISTRY_ROOT = "ctm_registry"
DEFAULT_EXTRACTED_UTC = "2026-01-01T00:00:00Z"
EVIDENCE_CLASS = "derived_digital_measurement"


@dataclass(frozen=True)
class RegistrationRecord:
    pattern_id: str
    genome_id: str
    genome_sha256: str
    candidate_sha256: str
    paths: dict = field(default_factory=dict)
    already_present: bool = False


def _sidecar_bytes(candidate_label: str, candidate_sha256: str, byte_length: int) -> bytes:
    sidecar = {
        "candidate_label": candidate_label,
        "candidate_sha256": candidate_sha256,
        "byte_length": byte_length,
        "evidence_class": EVIDENCE_CLASS,
        "physical_efficacy_claimed": False,
    }
    return canonical_json(sidecar) + b"\n"


def _write_idempotent(path: Path, content: bytes) -> bool:
    """Write content to path. Returns True if identical content already present.

    Raises RegistryConflictError if the path exists with different content."""
    if path.exists():
        if path.read_bytes() == content:
            return True
        raise RegistryConflictError(
            f"registry collision at {path}: existing content differs (fail-closed)")
    path.write_bytes(content)
    return False


def register_digital_genome(
    candidate_bytes: bytes,
    *,
    candidate_label: str,
    source_commit: str,
    runtime_lock_sha256: str,
    config: PatternGenomeConfig,
    registry_root: str = DEFAULT_REGISTRY_ROOT,
    extracted_utc: str = DEFAULT_EXTRACTED_UTC,
) -> RegistrationRecord:
    if not isinstance(candidate_bytes, (bytes, bytearray)) or not candidate_bytes:
        raise RegistrationError("candidate_bytes must be non-empty bytes")
    if not candidate_label or not str(candidate_label).strip():
        raise RegistrationError("candidate_label is required")
    candidate_bytes = bytes(candidate_bytes)
    candidate_sha = sha256(candidate_bytes).hexdigest()

    try:
        genome = extract_genome(
            candidate_bytes,
            candidate_sha256=candidate_sha,
            source_artifact_ref=candidate_label,
            source_commit=source_commit,
            runtime_lock_sha256=runtime_lock_sha256,
            config=config,
            extracted_utc=extracted_utc,
        )
        validate_genome(genome)
    except RegistrationError:
        raise
    except Exception as exc:
        raise RegistrationError(f"genome extraction/validation failed: {exc}") from exc

    pattern_id = pattern_id_from_genome(genome)
    genome_bytes = canonical_json(genome) + b"\n"
    prov_bytes = canonical_json(asdict(genome.provenance)) + b"\n"
    sidecar_bytes = _sidecar_bytes(candidate_label, candidate_sha, len(candidate_bytes))

    pattern_dir = Path(registry_root) / "patterns" / pattern_id
    try:
        pattern_dir.mkdir(parents=True, exist_ok=True)
        already = True
        paths = {}
        for name, content in (
            ("genome.json", genome_bytes),
            ("provenance.json", prov_bytes),
            ("master.sha256.json", sidecar_bytes),
        ):
            path = pattern_dir / name
            already = _write_idempotent(path, content) and already
            paths[name] = str(path)
    except RegistryConflictError:
        raise
    except OSError as exc:
        raise CTMBridgeError(f"registry write failed: {exc}") from exc

    return RegistrationRecord(
        pattern_id=pattern_id,
        genome_id=genome.genome_id,
        genome_sha256=pg_genome_sha256(genome),
        candidate_sha256=candidate_sha,
        paths=paths,
        already_present=already,
    )


def load_registered_genome(registry_root: str, pattern_id: str) -> dict:
    """Load a registered genome.json as a dict. Fail-closed on absence."""
    path = Path(registry_root) / "patterns" / pattern_id / "genome.json"
    if not path.exists():
        raise RegistrationError(f"no registered genome for pattern_id {pattern_id!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_registered_pattern_ids(registry_root: str) -> list:
    """Sorted (deterministic) list of registered pattern_ids."""
    patterns_dir = Path(registry_root) / "patterns"
    if not patterns_dir.is_dir():
        return []
    return sorted(p.name for p in patterns_dir.iterdir() if p.is_dir())

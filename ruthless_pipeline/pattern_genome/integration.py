"""Pre-held-out Pattern Genome integration helpers.

This module attaches deterministic Pattern Genome v1 sidecars to candidate
artifacts without allowing genome features to influence selection. It is
deliberately upstream of any held-out access.

The freeze timestamp is derived from the source commit timestamp when git
metadata is available. This keeps regenerated genome artifacts byte-stable
for the same candidate/config/runtime/source commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Iterable

from .canonical import canonical_json, genome_sha256
from .config import PatternGenomeConfig, load_config
from .errors import PatternGenomeProvenanceError
from .extractor import extract_genome
from .validation import validate_genome


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_source_commit(explicit: str | None = None, *, repo_root: str | Path | None = None) -> str:
    """Resolve an immutable source commit, refusing ambiguous provenance."""
    if explicit and explicit.strip():
        return explicit.strip()
    env_sha = os.environ.get("GITHUB_SHA", "").strip()
    if env_sha:
        return env_sha
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    try:
        value = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as exc:
        raise PatternGenomeProvenanceError(
            "cannot resolve source commit; pass --genome-source-commit"
        ) from exc
    if not value:
        raise PatternGenomeProvenanceError("resolved source commit is empty")
    return value


def resolve_commit_utc(source_commit: str, *, repo_root: str | Path | None = None) -> str:
    """Return deterministic UTC timestamp bound to the source commit."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(root), "show", "-s", "--format=%cI", source_commit],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        # External/non-local commit ids remain deterministic without pretending
        # to know wall-clock extraction time.
        return "1970-01-01T00:00:00Z"
    if raw.endswith("+00:00"):
        return raw[:-6] + "Z"
    return raw or "1970-01-01T00:00:00Z"


def freeze_candidate_genome(
    candidate_path: str | Path,
    *,
    artifact_ref: str,
    output_path: str | Path,
    config: PatternGenomeConfig,
    runtime_lock_path: str | Path,
    source_commit: str,
    extracted_utc: str,
) -> dict:
    """Extract, validate, write, and re-hash one immutable genome sidecar."""
    candidate_path = Path(candidate_path)
    if not candidate_path.is_file():
        raise FileNotFoundError(candidate_path)
    runtime_lock_path = Path(runtime_lock_path)
    if not runtime_lock_path.is_file():
        raise FileNotFoundError(runtime_lock_path)

    candidate_bytes = candidate_path.read_bytes()
    candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
    genome = extract_genome(
        candidate_bytes,
        candidate_sha256=candidate_sha,
        source_artifact_ref=artifact_ref,
        source_commit=source_commit,
        runtime_lock_sha256=_sha256_file(runtime_lock_path),
        config=config,
        extracted_utc=extracted_utc,
    )
    validate_genome(genome)
    blob = canonical_json(genome)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(blob + b"\n")
    persisted = output_path.read_bytes()
    return {
        "artifact_id": genome.genome_id,
        "sha256": hashlib.sha256(persisted).hexdigest(),
        "genome_content_sha256": genome_sha256(genome),
        "candidate_sha256": candidate_sha,
        "uri": str(output_path),
        "schema_version": genome.schema_version,
        "evidence_class": genome.provenance.evidence_class,
    }


def freeze_pool_genomes(
    candidates: Iterable[dict],
    *,
    pool_dir: str | Path,
    output_dir: str | Path,
    config_path: str | Path,
    runtime_lock_path: str | Path,
    source_commit: str | None = None,
    repo_root: str | Path | None = None,
) -> dict:
    """Freeze one genome for every candidate and emit a content-addressed index."""
    pool_dir = Path(pool_dir)
    output_dir = Path(output_dir)
    config = load_config(config_path)
    resolved_commit = resolve_source_commit(source_commit, repo_root=repo_root)
    extracted_utc = resolve_commit_utc(resolved_commit, repo_root=repo_root)

    records: dict[str, dict] = {}
    for item in candidates:
        candidate_id = str(item["candidate_id"])
        png = item.get("png")
        if not png:
            raise PatternGenomeProvenanceError(f"{candidate_id}: candidate record missing png")
        path = pool_dir / png
        ref = freeze_candidate_genome(
            path,
            artifact_ref=f"candidate://{candidate_id}/{png}",
            output_path=output_dir / f"{candidate_id}.json",
            config=config,
            runtime_lock_path=runtime_lock_path,
            source_commit=resolved_commit,
            extracted_utc=extracted_utc,
        )
        declared_sha = item.get("png_sha256")
        if declared_sha and declared_sha != ref["candidate_sha256"]:
            raise PatternGenomeProvenanceError(
                f"{candidate_id}: pool png_sha256 does not match candidate bytes"
            )
        records[candidate_id] = ref

    index = {
        "schema_version": "rac-pattern-genome-index/1.0",
        "selection_influence": "NONE_MEASUREMENT_ONLY",
        "heldout_access": False,
        "source_commit": resolved_commit,
        "extractor_config_sha256": config.config_sha256,
        "runtime_lock_sha256": _sha256_file(runtime_lock_path),
        "candidate_count": len(records),
        "candidates": {k: records[k] for k in sorted(records)},
    }
    index_blob = json.dumps(index, sort_keys=True, separators=(",", ":")).encode("utf-8")
    index_path = output_dir / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_bytes(index_blob + b"\n")
    index["index_sha256"] = hashlib.sha256(index_path.read_bytes()).hexdigest()
    index["index_path"] = str(index_path)
    return index

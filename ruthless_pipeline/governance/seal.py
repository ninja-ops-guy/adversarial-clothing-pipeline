"""Deterministic cohort sealing and verification (Governance Pass 3)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping


class SealError(RuntimeError):
    pass


def _canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class CohortSeal:
    seal_id: str
    cohort_id: str
    experiment_id: str
    constraint_id: str
    code_commit: str
    seed: int
    diagnostic_threshold_hash: str
    manifest_hash: str
    artifact_hashes: dict[str, str]
    seal_hash: str
    state: str = "SEALED"


def _validate_manifest(manifest: Mapping[str, object]) -> None:
    required = {
        "cohort_id", "experiment_id", "constraint_id", "code_commit", "seed",
        "diagnostic_threshold_hash", "specimen_ids", "artifacts",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise SealError(f"missing manifest fields: {', '.join(missing)}")
    if not isinstance(manifest["seed"], int):
        raise SealError("seed must be an integer")
    specimen_ids = manifest["specimen_ids"]
    if not isinstance(specimen_ids, list) or len(specimen_ids) != len(set(specimen_ids)):
        raise SealError("specimen_ids must be a duplicate-free list")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, dict):
        raise SealError("artifacts must map path to sha256")
    threshold_hash = manifest["diagnostic_threshold_hash"]
    if not isinstance(threshold_hash, str) or len(threshold_hash) != 64:
        raise SealError("diagnostic_threshold_hash must be sha256")


def seal_cohort(manifest: Mapping[str, object], artifact_bytes: Mapping[str, bytes]) -> CohortSeal:
    _validate_manifest(manifest)
    expected = manifest["artifacts"]
    assert isinstance(expected, dict)
    if set(expected) != set(artifact_bytes):
        raise SealError("artifact set differs from manifest")
    observed: dict[str, str] = {}
    for path, data in artifact_bytes.items():
        digest = sha256(data).hexdigest()
        observed[path] = digest
        if expected[path] != digest:
            raise SealError(f"artifact hash mismatch: {path}")
    manifest_hash = sha256(_canonical(dict(manifest))).hexdigest()
    body = {
        "cohort_id": manifest["cohort_id"],
        "experiment_id": manifest["experiment_id"],
        "constraint_id": manifest["constraint_id"],
        "code_commit": manifest["code_commit"],
        "seed": manifest["seed"],
        "diagnostic_threshold_hash": manifest["diagnostic_threshold_hash"],
        "manifest_hash": manifest_hash,
        "artifact_hashes": observed,
        "state": "SEALED",
    }
    seal_hash = sha256(_canonical(body)).hexdigest()
    return CohortSeal(seal_id=f"RAC-SEAL-{seal_hash[:16].upper()}", seal_hash=seal_hash, **body)


def verify_seal(seal: CohortSeal, manifest: Mapping[str, object], artifact_bytes: Mapping[str, bytes]) -> None:
    rebuilt = seal_cohort(manifest, artifact_bytes)
    if asdict(rebuilt) != asdict(seal):
        raise SealError("seal does not match current manifest/artifacts")

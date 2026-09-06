from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class EvidenceState(StrEnum):
    DESIGN = "RAC-D0"
    SURROGATE = "RAC-D1"
    DIGITAL_HELDOUT = "RAC-D2"
    PHYSICAL = "RAC-P1"
    DURABILITY = "RAC-P2"
    GOLDEN_SAMPLE = "RAC-M1"
    LOT_CONFORMITY = "RAC-M2"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    sha256: str
    media_type: str = "application/octet-stream"


@dataclass
class PatternManifest:
    pattern_id: str
    version: str
    task: str
    source_commit: str
    optimizer: str
    optimizer_version: str
    seed: int
    master: ArtifactRef
    protocol_id: str
    surrogate_model_set: str
    heldout_model_set: str
    textile_profile: str | None = None
    print_profile: str | None = None
    evidence_state: EvidenceState = EvidenceState.DESIGN
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.pattern_id.startswith("RAC-"):
            raise ValueError("pattern_id must start with RAC-")
        if not self.version or not self.source_commit:
            raise ValueError("version and source_commit are required")
        if len(self.master.sha256) != 64:
            raise ValueError("master.sha256 must be a SHA-256 hex digest")
        if self.surrogate_model_set == self.heldout_model_set:
            raise ValueError("surrogate and held-out model sets must be distinct")

    def canonical_json(self) -> bytes:
        self.validate()
        payload = asdict(self)
        payload["evidence_state"] = self.evidence_state.value
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    @property
    def manifest_sha256(self) -> str:
        return sha256_bytes(self.canonical_json())

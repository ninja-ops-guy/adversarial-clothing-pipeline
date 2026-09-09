"""Deterministic trajectory recording with hashed checkpoints.

Every step logs: iteration index, params hash (sha256), per-term objective
values, and weighted total. No timestamps or wall-clock data — trajectories
are fully deterministic for a fixed seed.

Checkpoints are written as a JSON state file plus a sha256 manifest.
``resume`` re-hashes the state and restores the exact recorded state;
any tampering raises ResumeIntegrityError.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


class ResumeIntegrityError(RuntimeError):
    """Raised when a checkpoint fails sha256 manifest verification."""


def hash_params(params: np.ndarray) -> str:
    """Deterministic sha256 over a float64 parameter vector."""
    arr = np.ascontiguousarray(np.asarray(params, dtype=np.float64))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class TrajectoryStep:
    iteration: int
    params_hash: str
    term_values: dict[str, float]
    total: float


@dataclass
class TrajectoryRecorder:
    """Append-only deterministic optimization trajectory log."""

    objective_id: str = "unspecified"
    seed: int = 0
    steps: list[TrajectoryStep] = field(default_factory=list)
    optimizer_state: dict[str, Any] = field(default_factory=dict)

    def record(
        self,
        iteration: int,
        params: np.ndarray,
        term_values: dict[str, float],
        total: float,
    ) -> TrajectoryStep:
        step = TrajectoryStep(
            iteration=int(iteration),
            params_hash=hash_params(params),
            term_values={k: float(v) for k, v in sorted(term_values.items())},
            total=float(total),
        )
        self.steps.append(step)
        return step

    # ------------------------------------------------------------------
    def _state_payload(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "seed": self.seed,
            "steps": [asdict(s) for s in self.steps],
            "optimizer_state": self.optimizer_state,
        }

    def state_hash(self) -> str:
        return sha256_hex(canonical_json_bytes(self._state_payload()))

    def checkpoint(self, directory: str | Path) -> tuple[Path, Path]:
        """Write trajectory_state.json + sha256 manifest; returns both paths."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        state_bytes = canonical_json_bytes(self._state_payload())
        state_path = directory / "trajectory_state.json"
        state_path.write_bytes(state_bytes)
        manifest = {
            "files": {state_path.name: sha256_hex(state_bytes)},
            "state_hash": sha256_hex(state_bytes),
        }
        manifest_path = directory / "trajectory_manifest.sha256.json"
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        return state_path, manifest_path

    @classmethod
    def resume(cls, directory: str | Path) -> "TrajectoryRecorder":
        """Load a checkpoint, verifying the sha256 manifest first."""
        directory = Path(directory)
        state_path = directory / "trajectory_state.json"
        manifest_path = directory / "trajectory_manifest.sha256.json"
        if not state_path.exists() or not manifest_path.exists():
            raise ResumeIntegrityError(f"checkpoint files missing in {directory}")
        manifest = json.loads(manifest_path.read_bytes())
        state_bytes = state_path.read_bytes()
        actual = sha256_hex(state_bytes)
        expected = manifest.get("files", {}).get(state_path.name)
        if expected != actual or manifest.get("state_hash") != actual:
            raise ResumeIntegrityError(
                "checkpoint sha256 mismatch; refusing to resume from tampered state"
            )
        payload = json.loads(state_bytes)
        recorder = cls(
            objective_id=payload["objective_id"],
            seed=int(payload["seed"]),
            optimizer_state=dict(payload.get("optimizer_state", {})),
        )
        recorder.steps = [
            TrajectoryStep(
                iteration=int(s["iteration"]),
                params_hash=s["params_hash"],
                term_values={k: float(v) for k, v in s["term_values"].items()},
                total=float(s["total"]),
            )
            for s in payload["steps"]
        ]
        return recorder

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TrajectoryRecorder):
            return NotImplemented
        return self._state_payload() == other._state_payload()

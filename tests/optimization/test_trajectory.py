"""synthetic_pipeline_validation_only — checkpoint hashing + resume integrity."""

from __future__ import annotations

import json

import numpy as np
import pytest

from ruthless_pipeline.optimization.trajectory import (
    ResumeIntegrityError,
    TrajectoryRecorder,
    hash_params,
    sha256_hex,
)


def _recorder(n_steps=5):
    rec = TrajectoryRecorder(objective_id="traj", seed=99)
    for i in range(n_steps):
        x = np.array([0.1 * i, -0.2 * i])
        rec.record(i, x, {"detector_loss": 1.0 / (i + 1), "regularization": 0.01 * i}, 1.0 / (i + 1))
    rec.optimizer_state = {"sigma": 0.3, "x": [0.4, -0.8]}
    return rec


def test_params_hash_deterministic():
    x = np.array([0.123456, -7.0])
    assert hash_params(x) == hash_params(x.copy())
    assert hash_params(x) != hash_params(x + 1e-12)
    assert len(hash_params(x)) == 64


def test_checkpoint_writes_sha256_manifest(tmp_path):
    rec = _recorder()
    state_path, manifest_path = rec.checkpoint(tmp_path)
    assert state_path.exists() and manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    digest = sha256_hex(state_path.read_bytes())
    assert manifest["files"]["trajectory_state.json"] == digest
    assert manifest["state_hash"] == digest


def test_resume_restores_exact_state(tmp_path):
    rec = _recorder()
    rec.checkpoint(tmp_path)
    restored = TrajectoryRecorder.resume(tmp_path)
    assert restored == rec
    assert restored.optimizer_state == rec.optimizer_state
    assert [s.params_hash for s in restored.steps] == [s.params_hash for s in rec.steps]


def test_resume_then_continue_identical_trajectory(tmp_path):
    rec = _recorder(3)
    rec.checkpoint(tmp_path)
    restored = TrajectoryRecorder.resume(tmp_path)
    # Continue both from step 3 identically.
    fresh = _recorder(3)
    for target in (restored, fresh):
        for i in range(3, 6):
            x = np.array([0.1 * i, -0.2 * i])
            target.record(i, x, {"detector_loss": 1.0 / (i + 1)}, 1.0 / (i + 1))
    assert restored == fresh
    assert [s.total for s in restored.steps] == [s.total for s in fresh.steps]


def test_tampered_checkpoint_refused(tmp_path):
    rec = _recorder()
    state_path, _ = rec.checkpoint(tmp_path)
    payload = json.loads(state_path.read_text())
    payload["steps"][0]["total"] = 999.0  # tamper
    state_path.write_text(json.dumps(payload))
    with pytest.raises(ResumeIntegrityError):
        TrajectoryRecorder.resume(tmp_path)


def test_tampered_manifest_refused(tmp_path):
    rec = _recorder()
    _, manifest_path = rec.checkpoint(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["state_hash"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ResumeIntegrityError):
        TrajectoryRecorder.resume(tmp_path)


def test_missing_checkpoint_files_refused(tmp_path):
    with pytest.raises(ResumeIntegrityError):
        TrajectoryRecorder.resume(tmp_path)


def test_no_timestamps_deterministic_bytes(tmp_path):
    rec1, rec2 = _recorder(), _recorder()
    p1, _ = rec1.checkpoint(tmp_path / "a")
    p2, _ = rec2.checkpoint(tmp_path / "b")
    assert p1.read_bytes() == p2.read_bytes()

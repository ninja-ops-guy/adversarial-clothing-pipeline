"""Tests for SPEC-12 evaluation-surface audit block (lane A).

Covers: v1.1 positive round-trip/lock, v1.0 backward compatibility
(byte-identical lock semantics), and fail-closed audit validation.
"""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.manifests import (
    CTM_MANIFEST_SCHEMA_VERSION,
    CTM_MANIFEST_SCHEMA_VERSION_V11,
    CTMExperimentManifest,
    LockMismatchError,
    lock_manifest,
    verify_lock,
)

FIXED_UTC = "2026-01-01T00:00:00Z"
FIXED_LOCK_UTC = "2026-01-01T00:01:00Z"
DUMMY_SHA = "a" * 64


def _audit(**overrides):
    audit = {
        "decision_thresholds": [0.5],
        "threshold_regime": "fixed",
        "frames_per_sample": 1,
        "firewall_attestation_ref": DUMMY_SHA,
        "goodhart_guard": "candidate selection saw only surrogate outcomes at "
        "threshold 0.5; no threshold was tuned against held-out outcomes",
    }
    audit.update(overrides)
    return audit


def _v11(**overrides):
    kwargs = dict(
        experiment_id="CTM-E-000101",
        title="v1.1 audited synthetic rehearsal",
        design={"doe": {"cells": 2}},
        seed=7,
        created_utc=FIXED_UTC,
        schema_version=CTM_MANIFEST_SCHEMA_VERSION_V11,
        evaluation_audit=_audit(),
    )
    kwargs.update(overrides)
    return CTMExperimentManifest(**kwargs)


def _v10():
    return CTMExperimentManifest(
        experiment_id="CTM-E-000100",
        title="v1.0 legacy rehearsal",
        design={"doe": {"cells": 2}},
        seed=7,
        created_utc=FIXED_UTC,
    )


# -- v1.1 positive -----------------------------------------------------------

def test_v11_roundtrip_and_lock(tmp_path):
    m = _v11()
    assert "evaluation_audit" in m.to_dict()
    lock = lock_manifest(m, tmp_path, locked_utc=FIXED_LOCK_UTC)
    assert lock["manifest_sha256"] == m.manifest_sha256()
    assert verify_lock(tmp_path)["manifest_sha256"] == m.manifest_sha256()
    # Idempotent re-lock
    lock_manifest(m, tmp_path, locked_utc=FIXED_LOCK_UTC)


def test_v11_deterministic_canonical_bytes():
    assert _v11().canonical_bytes() == _v11().canonical_bytes()
    assert _v11().manifest_sha256() == _v11().manifest_sha256()


def test_v11_swept_regime_legal():
    m = _v11(
        evaluation_audit=_audit(
            decision_thresholds=[0.3, 0.5, 0.7], threshold_regime="swept"
        )
    )
    assert m.to_dict()["evaluation_audit"]["threshold_regime"] == "swept"


# -- v1.0 backward compatibility ----------------------------------------------

def test_v10_manifest_has_no_audit_and_locks_identically(tmp_path):
    m = _v10()
    assert "evaluation_audit" not in m.to_dict()
    assert m.schema_version == CTM_MANIFEST_SCHEMA_VERSION
    lock = lock_manifest(m, tmp_path, locked_utc=FIXED_LOCK_UTC)
    assert lock["schema_version"] == CTM_MANIFEST_SCHEMA_VERSION
    assert verify_lock(tmp_path) == lock


def test_v10_canonical_bytes_unchanged_by_spec12():
    # The audit block is omitted entirely from v1.0 encodings, so pre-SPEC-12
    # bytes/hashes are bit-identical.
    m = _v10()
    assert b"evaluation_audit" not in m.canonical_bytes()


def test_v10_rejects_audit_block():
    with pytest.raises(ValueError, match="rac-ctm-experiment/1.1"):
        _v10_with_audit = CTMExperimentManifest(
            experiment_id="CTM-E-000102",
            title="bad",
            design={},
            seed=1,
            created_utc=FIXED_UTC,
            evaluation_audit=_audit(),
        )


def test_v11_requires_audit_block():
    with pytest.raises(ValueError, match="requires an evaluation_audit"):
        CTMExperimentManifest(
            experiment_id="CTM-E-000103",
            title="bad",
            design={},
            seed=1,
            created_utc=FIXED_UTC,
            schema_version=CTM_MANIFEST_SCHEMA_VERSION_V11,
        )


# -- fail-closed audit validation ----------------------------------------------

def test_missing_audit_keys_fail_closed():
    with pytest.raises(ValueError, match="missing required keys"):
        _v11(evaluation_audit={"threshold_regime": "fixed"})


def test_empty_thresholds_fail_closed():
    with pytest.raises(ValueError, match="decision_thresholds"):
        _v11(evaluation_audit=_audit(decision_thresholds=[]))


def test_unknown_regime_fail_closed():
    with pytest.raises(ValueError, match="threshold_regime"):
        _v11(evaluation_audit=_audit(threshold_regime="vibes"))


def test_swept_with_single_threshold_refused():
    with pytest.raises(ValueError, match=">=2"):
        _v11(
            evaluation_audit=_audit(
                decision_thresholds=[0.5], threshold_regime="swept"
            )
        )


def test_frames_per_sample_validation():
    with pytest.raises(ValueError, match="frames_per_sample"):
        _v11(evaluation_audit=_audit(frames_per_sample=0))
    with pytest.raises(ValueError, match="frames_per_sample"):
        _v11(evaluation_audit=_audit(frames_per_sample=True))


def test_firewall_attestation_ref_must_be_sha256():
    with pytest.raises(ValueError, match="firewall_attestation_ref"):
        _v11(evaluation_audit=_audit(firewall_attestation_ref="trust me"))


def test_goodhart_guard_required():
    with pytest.raises(ValueError, match="goodhart_guard"):
        _v11(evaluation_audit=_audit(goodhart_guard="  "))


def test_v11_lock_still_detects_drift(tmp_path):
    m = _v11()
    lock_manifest(m, tmp_path, locked_utc=FIXED_LOCK_UTC)
    (tmp_path / "manifest.json").write_bytes(b'{"tampered":true}\n')
    with pytest.raises(LockMismatchError):
        verify_lock(tmp_path)

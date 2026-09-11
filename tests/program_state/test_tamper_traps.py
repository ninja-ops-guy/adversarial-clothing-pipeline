"""Tamper traps: contradictory or drifted inputs must fail closed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ruthless_pipeline.program_state.compile import (
    check_state,
    derive_state,
    write_state,
)
from ruthless_pipeline.program_state.errors import (
    ProgramStateError,
    SourceContradictionError,
)

from .conftest import make_repo


def test_contradictory_generation_record_fails_closed(tmp_path: Path) -> None:
    make_repo(tmp_path)
    record = tmp_path / "generations" / "RAC-PER-D2-0007.json"
    payload = json.loads(record.read_text())
    payload["lock_status"] = "EVIDENCE_SEALED"  # armed:false contradiction
    record.write_text(json.dumps(payload, indent=2, sort_keys=True))
    with pytest.raises(SourceContradictionError):
        derive_state(tmp_path)


def test_unknown_lock_status_fails_closed(tmp_path: Path) -> None:
    make_repo(tmp_path)
    record = tmp_path / "generations" / "RAC-PER-D2-0005.json"
    payload = json.loads(record.read_text())
    payload["lock_status"] = "DEFINITELY_REAL"
    record.write_text(json.dumps(payload, indent=2, sort_keys=True))
    with pytest.raises(ProgramStateError):
        derive_state(tmp_path)


def test_freeze_candidate_arming_contradiction(tmp_path: Path) -> None:
    make_repo(tmp_path)
    freeze = tmp_path / "docs" / "D2-0005_FREEZE_CANDIDATE.json"
    freeze.write_text(json.dumps({"arming": {"armed": True}}))
    with pytest.raises(SourceContradictionError):
        derive_state(tmp_path)


def test_source_pin_tamper_changes_state_and_check_fails(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    state = derive_state(tmp_path)
    pin = state["sources"]["generations/RAC-PER-D2-0007.json"]
    assert len(pin) == 64
    record = tmp_path / "generations" / "RAC-PER-D2-0007.json"
    payload = json.loads(record.read_text())
    payload["note"] = "tampered"
    record.write_text(json.dumps(payload, indent=2, sort_keys=True))
    after = derive_state(tmp_path)
    assert after["sources"]["generations/RAC-PER-D2-0007.json"] != pin
    assert check_state(tmp_path), "tampered source must make the state stale"


def test_release_tamper_is_reported(tmp_path: Path) -> None:
    make_repo(tmp_path)
    release_dir = tmp_path / "releases" / "SYNTH-001"
    release_dir.mkdir(parents=True)
    (release_dir / "artifact.txt").write_text("payload")
    from ruthless_pipeline.certification.release_format import ReleaseManifest

    # Manifest pins a digest that does not match the file on disk (tampered).
    manifest = ReleaseManifest(entries={"artifact.txt": "0" * 64})
    manifest.write(release_dir)
    state = derive_state(tmp_path)
    rel = state["releases"][0]
    assert rel["verified"] is False
    assert rel["tampered"] == ["artifact.txt"]

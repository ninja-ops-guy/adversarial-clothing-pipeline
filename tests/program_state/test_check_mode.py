"""CI-gate behaviour: --check fails closed on stale or contradictory state."""

from __future__ import annotations

import json
from pathlib import Path

from ruthless_pipeline.program_state.compile import check_state, main, write_state

from .conftest import make_repo


def test_check_passes_on_fresh_state(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    assert main(["--root", str(tmp_path), "--check"]) == 0


def test_check_fails_on_missing_committed_state(tmp_path: Path) -> None:
    make_repo(tmp_path)
    findings = check_state(tmp_path)
    assert any("missing committed state" in f for f in findings)
    assert main(["--root", str(tmp_path), "--check"]) == 1


def test_check_fails_on_stale_state(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    # Drift a canonical source after the state was committed.
    status = tmp_path / "d2-latest-status.json"
    payload = json.loads(status.read_text())
    payload["decision"] = "PASS"
    status.write_text(json.dumps(payload, indent=2, sort_keys=True))
    findings = check_state(tmp_path)
    assert any("stale committed state" in f for f in findings)
    assert any("stale generated summary" in f for f in findings)
    assert main(["--root", str(tmp_path), "--check"]) == 1


def test_check_fails_closed_on_contradiction(tmp_path: Path) -> None:
    make_repo(tmp_path)
    record = tmp_path / "generations" / "RAC-PER-D2-0007.json"
    payload = json.loads(record.read_text())
    # Contradictory record: armed:false but a post-PREREGISTERED lock status.
    payload["lock_status"] = "RUNNING"
    record.write_text(json.dumps(payload, indent=2, sort_keys=True))
    findings = check_state(tmp_path)
    assert any("derivation failed" in f for f in findings)
    assert main(["--root", str(tmp_path), "--check"]) == 1


def test_check_fails_on_hand_edited_summary(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    summary = tmp_path / "program_state" / "SUMMARY.md"
    summary.write_text(summary.read_text() + "\nhand edit\n")
    findings = check_state(tmp_path)
    assert any("stale generated summary" in f for f in findings)

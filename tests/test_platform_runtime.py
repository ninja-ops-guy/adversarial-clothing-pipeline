from __future__ import annotations

import json
from pathlib import Path

import pytest

from ruthless_pipeline import platform_runtime as runtime


def test_workspace_path_rejects_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime, "WORKSPACE_ROOT", tmp_path / "workspace")
    runtime.WORKSPACE_ROOT.mkdir()
    with pytest.raises(ValueError, match="within the runtime workspace"):
        runtime._workspace_path("../outside.json")
    with pytest.raises(ValueError, match="within the runtime workspace"):
        runtime._workspace_path("/tmp/outside.json")


def test_validate_capture_command_is_allowlisted_and_workspace_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "WORKSPACE_ROOT", tmp_path / "workspace")
    runtime.WORKSPACE_ROOT.mkdir()
    session = runtime.WORKSPACE_ROOT / "session.json"
    session.write_text(json.dumps({"sealed": True}))
    command = runtime.build_job_command("validate_capture", {"session": "session.json"})
    assert command[1:] == [
        "scripts/validate_capture_session.py",
        str(session.resolve()),
        "--verify-files",
    ]


def test_analyze_capture_never_accepts_arbitrary_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "WORKSPACE_ROOT", tmp_path / "workspace")
    runtime.WORKSPACE_ROOT.mkdir()
    session = runtime.WORKSPACE_ROOT / "session.json"
    session.write_text("{}")
    command = runtime.build_job_command(
        "analyze_capture",
        {
            "session": "session.json",
            "output": "results/inference.json",
            "include_motion": False,
            "command": "rm -rf /",
        },
    )
    assert "rm -rf /" not in command
    assert command[1] == "scripts/analyze_capture_session.py"
    assert "--include-motion" not in command


def test_ingest_capture_rejects_invalid_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "WORKSPACE_ROOT", tmp_path / "workspace")
    runtime.WORKSPACE_ROOT.mkdir()
    for name in ("session.json", "inference.json"):
        (runtime.WORKSPACE_ROOT / name).write_text("{}")
    with pytest.raises(ValueError, match="source must be one of"):
        runtime.build_job_command(
            "ingest_capture",
            {"session": "session.json", "inference": "inference.json", "source": "shell"},
        )


def test_unknown_job_refuses_execution() -> None:
    with pytest.raises(ValueError, match="unknown research job"):
        runtime.build_job_command("arbitrary_shell", {})


def test_catalog_exposes_physical_research_path() -> None:
    assert {"p1_readiness", "validate_capture", "analyze_capture", "ingest_capture"}.issubset(runtime.JOB_CATALOG)


def test_workspace_listing_stays_local_and_returns_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "WORKSPACE_ROOT", tmp_path / "workspace")
    result = runtime.WORKSPACE_ROOT / "sessions" / "one" / "p1-output" / "statistics.json"
    result.parent.mkdir(parents=True)
    result.write_text('{"status":"PASS"}\n')
    files = runtime.list_workspace("sessions/one")
    assert len(files) == 1
    assert files[0]["path"] == "sessions/one/p1-output/statistics.json"
    assert files[0]["bytes"] == result.stat().st_size
    with pytest.raises(ValueError, match="within the runtime workspace"):
        runtime.list_workspace("../outside")

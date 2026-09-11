"""Regression tests for the zero-dependency repository JSON integrity gate."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_json_integrity.py"


def _run(root: Path) -> tuple[subprocess.CompletedProcess[str], dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc, json.loads(proc.stdout)


def test_json_integrity_gate_accepts_valid_json(tmp_path):
    (tmp_path / "manifest.json").write_text('{"ok": true}\n')
    proc, report = _run(tmp_path)
    assert proc.returncode == 0
    assert report["status"] == "PASS"
    assert report["scanned_json_files"] == 1
    assert report["findings"] == []


def test_json_integrity_gate_rejects_connector_placeholder(tmp_path):
    (tmp_path / "artifact.json").write_text("__CONTENT_7__\n")
    proc, report = _run(tmp_path)
    assert proc.returncode == 1
    assert report["status"] == "FAIL"
    assert report["findings"] == [
        {
            "detail": "file contains an unresolved __CONTENT_<n>__ placeholder",
            "kind": "CONNECTOR_PLACEHOLDER",
            "path": "artifact.json",
        }
    ]


def test_json_integrity_gate_rejects_malformed_json(tmp_path):
    (tmp_path / "bad.json").write_text('{"broken": }\n')
    proc, report = _run(tmp_path)
    assert proc.returncode == 1
    assert report["status"] == "FAIL"
    finding = report["findings"][0]
    assert finding["path"] == "bad.json"
    assert finding["kind"] == "INVALID_JSON"


def test_json_integrity_gate_ignores_generated_dependency_trees(tmp_path):
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "bad.json").write_text("__CONTENT_9__\n")
    (tmp_path / "good.json").write_text("{}\n")
    proc, report = _run(tmp_path)
    assert proc.returncode == 0
    assert report["status"] == "PASS"
    assert report["scanned_json_files"] == 1

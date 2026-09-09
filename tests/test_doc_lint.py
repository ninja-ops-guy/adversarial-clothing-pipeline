"""Tests for the documentation staleness linter (scripts/lint_docs.py)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ruthless_pipeline.certification import doc_lint

ROOT = Path(__file__).resolve().parents[1]


def _make_root(tmp_path: Path) -> Path:
    """Minimal synthetic repo with truthful machine-readable sources."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "generations").mkdir()
    (tmp_path / "schemas").mkdir()
    (tmp_path / "manuscript" / "backlog").mkdir(parents=True)
    (tmp_path / "d2-latest-status.json").write_text(json.dumps({
        "candidate_id": "RAC-PER-D2-0004",
        "decision": "FAIL",
        "evidence_state": "RAC-D0",
        "heldout": {
            "baseline_detection_rate": 1.0,
            "candidate_detection_rate": 1.0,
            "baseline_mean": 0.9947303864690993,
            "candidate_mean": 0.8959943834278319,
            "mean_delta": -0.0987360030412674,
            "n": 36,
        },
    }))
    (tmp_path / "generations" / "RAC-PER-D2-0004.json").write_text(json.dumps({
        "generation_id": "RAC-PER-D2-0004", "status": "READY_FOR_FRESH_HELDOUT_RUN",
    }))
    (tmp_path / "generations" / "RAC-PER-D2-0005.json").write_text(json.dumps({
        "generation_id": "RAC-PER-D2-0005", "lock_status": "PREREGISTERED",
    }))
    (tmp_path / "docs" / "D2-0005_FREEZE_CANDIDATE.json").write_text(json.dumps({
        "generation_id": "RAC-PER-D2-0005", "arming": {"armed": False},
    }))
    (tmp_path / "schemas" / "product_studio_manifest.contract.json").write_text(json.dumps({
        "contract_id": "product_studio_manifest", "accepted_schema_version": "1.4",
    }))
    (tmp_path / "README.md").write_text("# ok\n")
    return tmp_path


def _write_doc(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_clean_repo_has_no_findings(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/OK.md", (
        "D2-0004 closed FAIL / RAC-D0; held-out detection 1.00 -> 1.00, "
        "mean 0.99473 -> 0.89599. D2-0005 is NOT armed.\n"
    ))
    result = doc_lint.lint_repo(root)
    assert result.ok, [f.to_dict() for f in result.findings]


def test_seeded_stale_d2_0004_status_detected(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/STALE.md", "Work continues while D2-0004 is open.\n")
    result = doc_lint.lint_repo(root)
    assert not result.ok
    assert any(f.check == doc_lint.CHECK_STALE_D2_0004 for f in result.findings)


def test_seeded_stale_d2_0005_armed_detected(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/STALE.md", "D2-0005 is armed and ready to fire.\n")
    result = doc_lint.lint_repo(root)
    assert any(f.check == doc_lint.CHECK_STALE_D2_0005_ARMED for f in result.findings)


def test_inline_allow_marker_suppresses(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/HISTORY.md", (
        '<!-- doclint:allow check="stale-d2-0004-status" reason="frozen history" -->\n'
        "At the time, D2-0004 is open and unrun.\n"
    ))
    result = doc_lint.lint_repo(root)
    assert result.ok
    assert len(result.allowed) == 1


def test_json_allowlist_suppresses_with_reason(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/HISTORY.md", "Back then D2-0004 is open.\n")
    (root / ".doclint-allow.json").write_text(json.dumps({"allow": [{
        "path": "docs/HISTORY.md",
        "check": "stale-d2-0004-status",
        "reason": "intentional history",
    }]}))
    result = doc_lint.lint_repo(root)
    assert result.ok
    assert len(result.allowed) == 1


def test_allowlist_match_filter_is_scoped(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/HISTORY.md", (
        "Entry one: D2-0004 is open.\n"
        "Entry two: D2-0004 is still open today.\n"
    ))
    (root / ".doclint-allow.json").write_text(json.dumps({"allow": [{
        "path": "docs/HISTORY.md",
        "check": "stale-d2-0004-status",
        "match": "Entry one",
        "reason": "only the first line is history",
    }]}))
    result = doc_lint.lint_repo(root)
    assert not result.ok
    assert len(result.allowed) == 1
    assert any("Entry two" in f.excerpt for f in result.findings)


def test_broken_backticked_path_detected(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/LINKS.md", "See `scripts/does_not_exist.py` for details.\n")
    result = doc_lint.lint_repo(root)
    assert any(f.check == doc_lint.CHECK_BROKEN_PATH for f in result.findings)


def test_broken_relative_markdown_link_detected(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/LINKS.md", "[missing](sub/dir/none.md)\n")
    result = doc_lint.lint_repo(root)
    assert any(f.check == doc_lint.CHECK_BROKEN_PATH for f in result.findings)


def test_markdown_link_escape_repo_detected(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/LINKS.md", "[esc](../../outside.md)\n")
    result = doc_lint.lint_repo(root)
    assert any(
        f.check == doc_lint.CHECK_BROKEN_PATH and "escapes repository" in f.message
        for f in result.findings
    )


def test_schema_version_drift_detected(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/STUDIO.md", (
        "The Product Studio production manifest uses schema version 9.9 everywhere.\n"
    ))
    result = doc_lint.lint_repo(root)
    assert any(f.check == doc_lint.CHECK_SCHEMA_DRIFT for f in result.findings)


def test_stale_ci_run_detected(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/CI.md", "CI run 12345678 is in progress now.\n")
    result = doc_lint.lint_repo(root)
    assert any(f.check == doc_lint.CHECK_STALE_CI_RUN for f in result.findings)


def test_untraceable_quantitative_claim_detected(tmp_path: Path):
    root = _make_root(tmp_path)
    _write_doc(root, "docs/CLAIM.md", (
        "Held-out detection fell to 0.50 with held-out mean 0.1234, a collapse.\n"
    ))
    result = doc_lint.lint_repo(root)
    assert any(f.check == doc_lint.CHECK_QUANT_CLAIM for f in result.findings)


def test_cli_exit_codes(tmp_path: Path):
    root = _make_root(tmp_path)
    ok = subprocess.run(
        [sys.executable, "scripts/lint_docs.py", "--root", str(root)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
    report = tmp_path / "report.json"
    _write_doc(root, "docs/STALE.md", "D2-0004 is open.\n")
    bad = subprocess.run(
        [sys.executable, "scripts/lint_docs.py", "--root", str(root),
         "--report", str(report)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert bad.returncode == 1
    data = json.loads(report.read_text())
    assert data["ok"] is False
    assert data["finding_count"] >= 1
    assert all("check" in f and "path" in f and "line" in f for f in data["findings"])


@pytest.mark.skipif(not (ROOT / "d2-latest-status.json").exists(), reason="repo checkout required")
def test_current_repo_lints_clean():
    result = doc_lint.lint_repo(ROOT)
    assert result.ok, [f.to_dict() for f in result.findings]


def test_uppercase_armed_false_is_recognized_as_negation(tmp_path: Path):
    """Regression: 'ARMED = false' (uppercase) must not be flagged as armed."""
    root = _make_root(tmp_path)
    _write_doc(root, "docs/STATE.md", (
        "- D2-0005: PREREGISTERED, READY_TO_ARM = NO, ARMED = false — untouched.\n"
    ))
    result = doc_lint.lint_repo(root)
    assert not any(
        f.check == doc_lint.CHECK_STALE_D2_0005_ARMED for f in result.findings
    ), [f.to_dict() for f in result.findings]


def test_uppercase_armed_claim_still_detected(tmp_path: Path):
    """Guard: an affirmative uppercase ARMED claim is still flagged."""
    root = _make_root(tmp_path)
    _write_doc(root, "docs/STALE.md", "D2-0005 is ARMED and running.\n")
    result = doc_lint.lint_repo(root)
    assert any(f.check == doc_lint.CHECK_STALE_D2_0005_ARMED for f in result.findings)

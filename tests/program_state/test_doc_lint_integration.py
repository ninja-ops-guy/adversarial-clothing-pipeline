"""doc_lint integration: generated truth vs Markdown contradiction checks."""

from __future__ import annotations

import json
from pathlib import Path

from ruthless_pipeline.certification import doc_lint
from ruthless_pipeline.program_state.compile import write_state

from .conftest import make_repo


def _lint(tmp_path: Path) -> doc_lint.LintResult:
    return doc_lint.lint_repo(tmp_path)


def test_stale_program_state_is_a_doclint_finding(tmp_path: Path) -> None:
    make_repo(tmp_path)
    (tmp_path / "docs" / "STATUS.md").write_text("# status\n")
    write_state(tmp_path)
    status = tmp_path / "d2-latest-status.json"
    payload = json.loads(status.read_text())
    payload["decision"] = "PASS"
    status.write_text(json.dumps(payload, indent=2, sort_keys=True))
    result = _lint(tmp_path)
    stale = [f for f in result.findings if f.check == doc_lint.CHECK_PROGRAM_STATE_STALE]
    assert stale, "stale committed program state must fail doc_lint"
    assert any(f.path == "program_state/program_state.json" for f in stale)


def test_armed_claim_contradiction_detected(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    (tmp_path / "docs" / "ROADMAP.md").write_text(
        "# roadmap\n\nRAC-PER-D2-0007 is armed and ready to run.\n"
    )
    result = _lint(tmp_path)
    hits = [
        f for f in result.findings if f.check == doc_lint.CHECK_UNARMED_ARMED_CLAIM
    ]
    assert len(hits) == 1
    assert hits[0].path == "docs/ROADMAP.md"


def test_negated_armed_claim_is_allowed(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    (tmp_path / "docs" / "ROADMAP.md").write_text(
        "# roadmap\n\nRAC-PER-D2-0007 is not armed; arming awaits review.\n"
    )
    result = _lint(tmp_path)
    assert not [
        f for f in result.findings if f.check == doc_lint.CHECK_UNARMED_ARMED_CLAIM
    ]


def test_contradictory_source_fails_doc_lint_closed(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    record = tmp_path / "generations" / "RAC-PER-D2-0005.json"
    payload = json.loads(record.read_text())
    payload["lock_status"] = "ARMED"  # contradicts armed:false -> fail closed
    record.write_text(json.dumps(payload, indent=2, sort_keys=True))
    (tmp_path / "docs" / "STATUS.md").write_text("# status\n")
    result = _lint(tmp_path)
    stale = [f for f in result.findings if f.check == doc_lint.CHECK_PROGRAM_STATE_STALE]
    assert stale and "fail closed" in stale[0].message


def test_allowlist_covers_program_state_findings(tmp_path: Path) -> None:
    make_repo(tmp_path)
    write_state(tmp_path)
    status = tmp_path / "d2-latest-status.json"
    payload = json.loads(status.read_text())
    payload["decision"] = "PASS"
    status.write_text(json.dumps(payload, indent=2, sort_keys=True))
    (tmp_path / ".doclint-allow.json").write_text(json.dumps({
        "allow": [{
            "path": "program_state/program_state.json",
            "check": doc_lint.CHECK_PROGRAM_STATE_STALE,
            "reason": "synthetic test fixture",
        }]
    }))
    result = _lint(tmp_path)
    assert not [
        f
        for f in result.findings
        if f.check == doc_lint.CHECK_PROGRAM_STATE_STALE
        and f.path == "program_state/program_state.json"
    ]

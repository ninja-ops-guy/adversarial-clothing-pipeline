"""Tests for the outcome-independent D2-0006 infrastructure:

- ``d20006_governance.classify_release_closure`` / ``build_branch_memo``
  (branch router),
- ``validate_preregistration_document`` (template slot validation),
- ``check_readiness`` (readiness checklist gate),
- the CLI entry points ``scripts/d20006_branch_router.py`` and
  ``scripts/validate_d20006_readiness.py``.

All releases here are synthetic sealed bundles built with the repo's
``release_format`` helpers; no held-out data, generation files, or frozen
surfaces are touched.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ruthless_pipeline.certification.d20006_governance import (
    DECISION_REGION_BRANCHES,
    DEFAULT_POLICY_PATH,
    DEFAULT_TEMPLATE_PATH,
    MANDATORY_SLOTS,
    GovernanceError,
    build_branch_memo,
    check_readiness,
    classify_release_closure,
    load_policy_document,
    memo_to_json,
    validate_preregistration_document,
)
from ruthless_pipeline.certification.release_format import (
    ReleaseManifest,
    compute_content_hash,
)

ROOT = Path(__file__).resolve().parents[1]
UTC = "2026-09-09T00:00:00Z"
COMMIT = "a" * 40


def _seal(release: Path) -> None:
    """Seal a release directory per RESEARCH_RELEASE_FORMAT §3/§4."""
    manifest = ReleaseManifest.build(release)
    content_hash = compute_content_hash(manifest)
    release_meta = {
        "release_id": release.name,
        "created_utc": UTC,
        "source_commit": COMMIT,
        "content_hash": content_hash,
    }
    (release / "RELEASE.json").write_text(json.dumps(release_meta, indent=2) + "\n")
    (release / "REVISIONS.json").write_text(json.dumps({"entries": []}) + "\n")
    ReleaseManifest.build(release).write(release)


def _make_release(
    root: Path,
    *,
    name: str = "RAC-EXP-2026-900",
    generation_id: str = "RAC-PER-D2-0005",
    decision_region: str | None = "SUCCESS",
    failure: dict | None = None,
    outcome_count: int = 1,
) -> Path:
    release = root / name
    outcome_dir = release / "stages" / "optimization_telemetry" / "outcome"
    outcome_dir.mkdir(parents=True)
    (release / "experiment.json").write_text(
        json.dumps({"experiment_id": name, "generation_id": generation_id}) + "\n"
    )
    (release / "REPORT.md").write_text("# Report\n")
    if decision_region is not None:
        for i in range(outcome_count):
            suffix = "" if outcome_count == 1 else f"-{i}"
            (outcome_dir / f"decision-region{suffix}.json").write_text(
                json.dumps({"decision_region": decision_region}) + "\n"
            )
    if failure is not None:
        (release / "FAILURE.json").write_text(json.dumps(failure, indent=2) + "\n")
    _seal(release)
    return release


def _infra_failure() -> dict:
    return {
        "failure_stage": "generation",
        "failure_reason": "CI runner crash before any evidence bundle was built",
        "detected_utc": UTC,
        "invalidates": [],
        "classification": {"category": "infrastructure_failure"},
    }


@pytest.fixture()
def policy() -> dict:
    return load_policy_document(DEFAULT_POLICY_PATH)


# --------------------------------------------------------------------------
# Branch router
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "region,branch", sorted(DECISION_REGION_BRANCHES.items())
)
def test_router_maps_each_decision_region_to_its_branch(
    tmp_path: Path, policy: dict, region: str, branch: str
) -> None:
    release = _make_release(tmp_path, decision_region=region)
    closure = classify_release_closure(release)
    memo = build_branch_memo(closure, policy)
    assert memo["branch_id"] == branch
    assert memo["trigger"] == {"kind": "decision_region", "decision_region": region}
    # Evidence hashes come from the sealed artifacts, nowhere else.
    outcome = release / "stages" / "optimization_telemetry" / "outcome" / "decision-region.json"
    assert memo["triggering_evidence"]["outcome_artifact_sha256"] == hashlib.sha256(
        outcome.read_bytes()
    ).hexdigest()
    assert memo["triggering_evidence"]["release_content_hash"] == closure["content_hash"]
    assert memo["policy_document"]["sha256"] == policy["sha256"]
    # Rationale slots are filled only with sealed values.
    assert release.name in memo["rationale"]
    assert closure["content_hash"] in memo["rationale"]
    assert COMMIT in memo["rationale"]


def test_router_memo_is_deterministic(tmp_path: Path, policy: dict) -> None:
    release = _make_release(tmp_path, decision_region="NULL")
    memo1 = memo_to_json(build_branch_memo(classify_release_closure(release), policy))
    memo2 = memo_to_json(build_branch_memo(classify_release_closure(release), policy))
    assert memo1 == memo2
    assert memo1 == json.dumps(json.loads(memo1), indent=2, sort_keys=True) + "\n"


def test_router_handles_infrastructure_failure_branch(tmp_path: Path, policy: dict) -> None:
    release = _make_release(tmp_path, decision_region=None, failure=_infra_failure())
    closure = classify_release_closure(release)
    assert closure["infrastructure_failure"] is True
    memo = build_branch_memo(closure, policy)
    assert memo["branch_id"] == "2.5"
    assert "INFRASTRUCTURE FAILURE" in memo["branch_name"]
    assert memo["triggering_evidence"]["failure_json_sha256"] == hashlib.sha256(
        (release / "FAILURE.json").read_bytes()
    ).hexdigest()
    assert "exactly ONE re-run" in memo["rationale"]
    assert "CI runner crash" in memo["rationale"]


def test_router_rejects_scientific_failure_as_infra(tmp_path: Path) -> None:
    """A D2-0004-style scientific failure (outcome observed) is NOT branch 2.5."""
    failure = _infra_failure()
    failure["classification"]["category"] = "cross_architecture_transfer_failure"
    release = _make_release(tmp_path, decision_region=None, failure=failure)
    with pytest.raises(GovernanceError, match="infrastructure_failure"):
        classify_release_closure(release)


def test_router_rejects_failure_plus_outcome(tmp_path: Path) -> None:
    release = _make_release(tmp_path, decision_region="SUCCESS", failure=_infra_failure())
    with pytest.raises(GovernanceError, match="outcome-never-observed"):
        classify_release_closure(release)


def test_router_rejects_unclassifiable_release(tmp_path: Path) -> None:
    release = _make_release(tmp_path, decision_region=None)
    with pytest.raises(GovernanceError, match="unclassifiable"):
        classify_release_closure(release)


def test_router_rejects_unknown_decision_region(tmp_path: Path) -> None:
    release = _make_release(tmp_path, decision_region="SOMEWHAT_SUCCESSFUL")
    with pytest.raises(GovernanceError, match="preregistered"):
        classify_release_closure(release)


def test_router_rejects_multiple_outcome_artifacts(tmp_path: Path) -> None:
    release = _make_release(tmp_path, decision_region="SUCCESS", outcome_count=2)
    with pytest.raises(GovernanceError, match="exactly one"):
        classify_release_closure(release)


def test_router_rejects_tampered_release(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    (release / "REPORT.md").write_text("# Hand-edited after sealing\n")
    with pytest.raises(GovernanceError, match="fails verification"):
        classify_release_closure(release)


def test_router_rejects_malformed_content_hash(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    meta = json.loads((release / "RELEASE.json").read_text())
    meta["content_hash"] = "not-a-digest"
    (release / "RELEASE.json").write_text(json.dumps(meta, indent=2) + "\n")
    # Re-seal so verify_release passes but the recorded content_hash is bad.
    ReleaseManifest.build(release).write(release)
    with pytest.raises(GovernanceError, match="content_hash"):
        classify_release_closure(release)


def test_router_rejects_wrong_generation(tmp_path: Path) -> None:
    release = _make_release(tmp_path, generation_id="RAC-PER-D2-0004")
    with pytest.raises(GovernanceError, match="RAC-PER-D2-0004"):
        classify_release_closure(release, expect_generation_id="RAC-PER-D2-0005")
    # With the check disabled the same release classifies fine.
    closure = classify_release_closure(release, expect_generation_id=None)
    assert closure["decision_region"] == "SUCCESS"


def test_router_rejects_unrecognized_policy_document(tmp_path: Path) -> None:
    fake = tmp_path / "fake-policy.md"
    fake.write_text("# not the frozen tree\n")
    with pytest.raises(GovernanceError, match="frozen-tree markers"):
        load_policy_document(fake)


def test_shipped_policy_document_is_routable(policy: dict) -> None:
    assert len(policy["sha256"]) == 64


# --------------------------------------------------------------------------
# Template validation
# --------------------------------------------------------------------------


def _fill_template(text: str) -> str:
    filled = text.replace("`{{SLOT}}`", "a slot placeholder")
    values = {
        "HYPOTHESIS": "H1: same-sign effect replicates on the fresh held-out set",
        "PROTOCOL_VERSION": "RAC-PERSON-DETECT-1.2",
        "SURROGATE_MODEL_SET": "PERSON-SUR-v4",
        "HELDOUT_MODEL_SET": "PERSON-HO-v4 (fresh, disjoint from PERSON-HO-v3)",
        "POOL_SEED": "2027",
        "DECISION_REGIONS": "success/null/negative/inconclusive per the sealed interval",
        "RUNTIME_LOCK_REFERENCE": "benchmarks/runtime_lock.json",
        "SELECTED_BRANCH": "2.1",
        "BRANCH_MEMO_SHA256": "b" * 64,
        "BUDGET_CAPS": "100 candidates, 18-condition grid, fixed seeds",
        "TREE_COMMIT_SHA": "c" * 40,
    }
    for slot, value in values.items():
        filled = filled.replace("{{" + slot + "}}", value)
    return filled


def test_shipped_template_with_unfilled_slots_fails_validation() -> None:
    text = DEFAULT_TEMPLATE_PATH.read_text()
    problems = validate_preregistration_document(text)
    assert any("unfilled template slots" in p for p in problems)


def test_template_covers_all_mandatory_slots() -> None:
    text = DEFAULT_TEMPLATE_PATH.read_text()
    for slot in MANDATORY_SLOTS:
        assert "{{" + slot + "}}" in text, slot


def test_filled_template_passes_validation() -> None:
    filled = _fill_template(DEFAULT_TEMPLATE_PATH.read_text())
    assert validate_preregistration_document(filled) == []


def test_open_field_markers_fail_validation() -> None:
    filled = _fill_template(DEFAULT_TEMPLATE_PATH.read_text())
    assert any(
        "TBD" in p for p in validate_preregistration_document(filled + "\nBudgets: TBD\n")
    )
    blocked = filled + "\nDirectional hypothesis field: BLOCKED until D2-0005 closes\n"
    assert any("BLOCKED" in p for p in validate_preregistration_document(blocked))


def test_missing_infra_clause_fails_validation() -> None:
    filled = _fill_template(DEFAULT_TEMPLATE_PATH.read_text())
    stripped = filled.replace("Infrastructure-failure clause", "Infra note").replace(
        "§2.5", "section two-five"
    )
    problems = validate_preregistration_document(stripped)
    assert any("§2.5" in p for p in problems)


def test_deleted_mandatory_section_fails_validation() -> None:
    filled = _fill_template(DEFAULT_TEMPLATE_PATH.read_text())
    stripped = filled.replace("- **Decision regions:**", "- **Regions:**").replace(
        "## 4. Decision regions", "## 4. Regions"
    )
    problems = validate_preregistration_document(stripped)
    assert any("Decision regions" in p for p in problems)


# --------------------------------------------------------------------------
# Readiness gate
# --------------------------------------------------------------------------


def _ready_inputs(tmp_path: Path, policy: dict) -> dict:
    release = _make_release(tmp_path, decision_region="SUCCESS")
    memo = build_branch_memo(classify_release_closure(release), policy)
    memo_path = tmp_path / "memo.json"
    memo_path.write_text(memo_to_json(memo))
    doc_path = tmp_path / "PREREGISTRATION_D2-0006.md"
    doc_path.write_text(_fill_template(DEFAULT_TEMPLATE_PATH.read_text()))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return {
        "d20005_release_dir": release,
        "branch_memo_path": memo_path,
        "preregistration_doc_path": doc_path,
        "repo_root": repo_root,
    }


def test_readiness_refuses_when_nothing_is_provided(tmp_path: Path) -> None:
    report = check_readiness(repo_root=tmp_path)
    assert report["ready"] is False
    unmet = {p["name"] for p in report["prerequisites"] if not p["satisfied"]}
    assert unmet == {
        "d20005_closed_or_discontinued",
        "branch_selection_memo",
        "d20006_preregistration_complete",
    }


def test_readiness_happy_path(tmp_path: Path, policy: dict) -> None:
    report = check_readiness(**_ready_inputs(tmp_path, policy))
    assert report["ready"] is True, report


def test_readiness_refuses_d2004_release_as_d2005_closure(
    tmp_path: Path, policy: dict
) -> None:
    inputs = _ready_inputs(tmp_path, policy)
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    inputs["d20005_release_dir"] = _make_release(
        wrong, name="RAC-EXP-2026-001", generation_id="RAC-PER-D2-0004"
    )
    report = check_readiness(**inputs)
    assert report["ready"] is False
    assert any(
        p["name"] == "d20005_closed_or_discontinued" and not p["satisfied"]
        for p in report["prerequisites"]
    )


def test_readiness_accepts_formal_discontinuation(tmp_path: Path, policy: dict) -> None:
    inputs = _ready_inputs(tmp_path, policy)
    discontinuation = tmp_path / "DISCONTINUATION_D2-0005.md"
    discontinuation.write_text(
        "# D2-0005 formally discontinued\nGovernance decision with reasons, in writing.\n"
    )
    inputs.pop("d20005_release_dir")
    inputs["d20005_discontinuation_path"] = discontinuation
    report = check_readiness(**inputs)
    assert report["ready"] is True, report


def test_readiness_refuses_empty_discontinuation(tmp_path: Path, policy: dict) -> None:
    inputs = _ready_inputs(tmp_path, policy)
    inputs.pop("d20005_release_dir")
    empty = tmp_path / "empty.md"
    empty.write_text("")
    inputs["d20005_discontinuation_path"] = empty
    report = check_readiness(**inputs)
    assert report["ready"] is False


def test_readiness_refuses_stale_memo(tmp_path: Path, policy: dict) -> None:
    inputs = _ready_inputs(tmp_path, policy)
    memo = json.loads(inputs["branch_memo_path"].read_text())
    memo["policy_document"]["sha256"] = "0" * 64
    inputs["branch_memo_path"].write_text(json.dumps(memo, indent=2, sort_keys=True))
    report = check_readiness(**inputs)
    assert report["ready"] is False
    assert any(
        p["name"] == "branch_selection_memo" and not p["satisfied"]
        for p in report["prerequisites"]
    )


def test_readiness_refuses_unfilled_preregistration(tmp_path: Path, policy: dict) -> None:
    inputs = _ready_inputs(tmp_path, policy)
    inputs["preregistration_doc_path"].write_text(DEFAULT_TEMPLATE_PATH.read_text())
    report = check_readiness(**inputs)
    assert report["ready"] is False


def test_readiness_refuses_when_d20006_generation_file_exists(
    tmp_path: Path, policy: dict
) -> None:
    inputs = _ready_inputs(tmp_path, policy)
    generations = inputs["repo_root"] / "generations"
    generations.mkdir()
    (generations / "RAC-PER-D2-0006.json").write_text("{}\n")
    report = check_readiness(**inputs)
    assert report["ready"] is False
    assert any(
        p["name"] == "no_d20006_generation_or_trigger_surface" and not p["satisfied"]
        for p in report["prerequisites"]
    )


def test_real_repo_has_no_d20006_generation_surface() -> None:
    report = check_readiness(repo_root=ROOT)
    gen_check = next(
        p for p in report["prerequisites"] if p["name"] == "no_d20006_generation_or_trigger_surface"
    )
    assert gen_check["satisfied"] is True
    assert report["ready"] is False  # D2-0005 is not closed; nothing else is met


# --------------------------------------------------------------------------
# CLI entry points
# --------------------------------------------------------------------------


def _run_cli(script: str, args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        text=True,
        capture_output=True,
        cwd=cwd,
    )


def test_router_cli_emits_memo(tmp_path: Path) -> None:
    release = _make_release(tmp_path, decision_region="INCONCLUSIVE")
    out = tmp_path / "memo.json"
    proc = _run_cli(
        "d20006_branch_router.py", ["--release", str(release), "--out", str(out)]
    )
    assert proc.returncode == 0, proc.stderr
    memo = json.loads(out.read_text())
    assert memo["branch_id"] == "2.4"


def test_router_cli_fails_closed(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    (release / "REPORT.md").write_text("# tampered\n")
    proc = _run_cli("d20006_branch_router.py", ["--release", str(release)])
    assert proc.returncode == 2
    assert "fail closed" in proc.stderr


def test_readiness_cli_exit_codes(tmp_path: Path, policy: dict) -> None:
    proc = _run_cli("validate_d20006_readiness.py", [])
    assert proc.returncode == 1
    assert "NOT READY" in proc.stderr

    inputs = _ready_inputs(tmp_path, policy)
    proc = _run_cli(
        "validate_d20006_readiness.py",
        [
            "--d20005-release",
            str(inputs["d20005_release_dir"]),
            "--branch-memo",
            str(inputs["branch_memo_path"]),
            "--preregistration",
            str(inputs["preregistration_doc_path"]),
        ],
    )
    # repo_root defaults to the real repo (no D2-0006 generation file).
    assert proc.returncode == 0, proc.stderr
    assert "READY" in proc.stderr

    bad_policy = tmp_path / "bad.md"
    bad_policy.write_text("# nope\n")
    proc = _run_cli("validate_d20006_readiness.py", ["--policy", str(bad_policy)])
    assert proc.returncode == 2

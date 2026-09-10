"""Tests for tools/p1_no_spend_readiness_gate.py (P1 no-spend readiness gate).

Gate-local logic is exercised against synthetic fixture trees so the tests
never mutate the frozen repo surfaces. Two integration tests run the real
gate against the repo itself (freeze integrity + full verdict).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import p1_no_spend_readiness_gate as gate

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestVerdictLogic:
    def _checks(self, **statuses):
        return {name: {"status": s, "refusal_reason": "r"} for name, s in statuses.items()}

    def test_all_pass_gives_pass(self):
        assert gate.derive_verdict(self._checks(a=gate.PASS, b=gate.PASS))["P1_NO_SPEND_READINESS"] == "PASS"

    def test_finding_fails_closed(self):
        verdict = gate.derive_verdict(self._checks(a=gate.PASS, b=gate.FINDING))
        assert verdict["P1_NO_SPEND_READINESS"] == "FAIL"
        assert verdict["findings"] == ["b"]

    def test_refusal_fails_closed_and_explicit(self):
        verdict = gate.derive_verdict(self._checks(a=gate.REFUSED))
        assert verdict["P1_NO_SPEND_READINESS"] == "FAIL"
        assert verdict["refusals"] == {"a": "r"}


class TestPendingMarkers:
    def test_canonical_literals_recognized(self):
        payload = {"a": "PENDING_USER_ACTION", "b": [{"c": "PENDING_TEMPLATE_DOWNLOAD"}]}
        assert gate._pending_paths(payload) == {"a", "b[0].c"}

    def test_fabricated_value_is_not_pending(self):
        assert gate._pending_paths({"hash": "0" * 64}) == set()

    def test_noncanonical_marker_flagged(self):
        assert gate._suspicious_pending_markers({"x": "PENDING"}) == ["x='PENDING'"]
        assert gate._suspicious_pending_markers({"x": "TBD"}) == ["x='TBD'"]

    def test_canonical_and_prose_not_flagged(self):
        assert gate._suspicious_pending_markers({"x": "PENDING_USER_SIZE_SELECTION"}) == []
        prose = "values are PENDING_USER_ACTION until UA-1 completes; never fabricated."
        assert gate._suspicious_pending_markers({"note": prose}) == []
        assert gate._suspicious_pending_markers({"x": "FILL-IN: your size"}) == []


@pytest.fixture()
def mini_repo(tmp_path: Path) -> Path:
    """Minimal fixture tree: freeze manifest pinning two files, one UA file."""
    (tmp_path / "physical/p1").mkdir(parents=True)
    (tmp_path / "print-alpha/MANIFESTS").mkdir(parents=True)
    (tmp_path / "a.txt").write_text("alpha\n")
    (tmp_path / "b.txt").write_text("beta\n")
    ua = {"vendor": {"sha": gate.PENDING_LITERAL, "size": "PENDING_USER_SIZE_SELECTION"}}
    (tmp_path / "print-alpha/MANIFESTS/sku-manifest.json").write_text(json.dumps(ua))
    freeze = {
        "schema_version": gate.SCHEMA_VERSION,
        "artifact_sha256": {
            "a.txt": gate._sha256_file(tmp_path / "a.txt"),
            "b.txt": gate._sha256_file(tmp_path / "b.txt"),
        },
        "missing_surfaces": [],
        "expected_pending_fields": {"print-alpha/MANIFESTS/sku-manifest.json": ["vendor.sha", "vendor.size"]},
    }
    (tmp_path / gate.FREEZE_PATH).write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n")
    return tmp_path


class TestFreezeIntegrity:
    def test_clean_tree_passes(self, mini_repo):
        assert gate.check_freeze_integrity(mini_repo)["status"] == gate.PASS

    def test_tampered_pinned_file_is_finding(self, mini_repo):
        (mini_repo / "a.txt").write_text("tampered\n")
        result = gate.check_freeze_integrity(mini_repo)
        assert result["status"] == gate.FINDING
        assert result["mismatches"][0]["path"] == "a.txt"

    def test_missing_pinned_file_is_finding(self, mini_repo):
        (mini_repo / "b.txt").unlink()
        assert gate.check_freeze_integrity(mini_repo)["status"] == gate.FINDING

    def test_missing_freeze_is_refusal(self, tmp_path):
        result = gate.check_freeze_integrity(tmp_path)
        assert result["status"] == gate.REFUSED
        assert result["refusal_reason"]


class TestUaFieldGuard:
    def test_pending_set_exact_match_passes(self, mini_repo):
        assert gate.check_ua_fields_pending(mini_repo)["status"] == gate.PASS

    def test_silently_resolved_field_is_finding(self, mini_repo):
        path = mini_repo / "print-alpha/MANIFESTS/sku-manifest.json"
        payload = json.loads(path.read_text())
        payload["vendor"]["sha"] = "0" * 64  # fabricated default substitution
        path.write_text(json.dumps(payload))
        result = gate.check_ua_fields_pending(mini_repo)
        assert result["status"] == gate.FINDING
        assert result["problems"][0]["silently_resolved"] == ["vendor.sha"]

    def test_silently_added_pending_field_is_finding(self, mini_repo):
        path = mini_repo / "print-alpha/MANIFESTS/sku-manifest.json"
        payload = json.loads(path.read_text())
        payload["vendor"]["extra"] = gate.PENDING_LITERAL
        path.write_text(json.dumps(payload))
        result = gate.check_ua_fields_pending(mini_repo)
        assert result["status"] == gate.FINDING
        assert result["problems"][0]["silently_added"] == ["vendor.extra"]


class TestAgainstRepo:
    def test_freeze_integrity_on_repo(self):
        assert gate.check_freeze_integrity(REPO_ROOT)["status"] == gate.PASS

    def test_surface_completeness_on_repo(self):
        assert gate.check_surface_completeness(REPO_ROOT)["status"] == gate.PASS

    def test_ua_guard_on_repo(self):
        assert gate.check_ua_fields_pending(REPO_ROOT)["status"] == gate.PASS
        assert gate.check_pending_literals_canonical(REPO_ROOT)["status"] == gate.PASS

    def test_pairing_and_schedule_on_repo(self):
        assert gate.check_pairing_contract(REPO_ROOT)["status"] == gate.PASS
        assert gate.check_schedule_frozen(REPO_ROOT)["status"] == gate.PASS

    def test_scientific_boundaries_on_repo(self):
        assert gate.check_scientific_boundaries(REPO_ROOT)["status"] == gate.PASS

    def test_full_gate_passes(self):
        report = gate.run_gate(REPO_ROOT)
        assert report["P1_NO_SPEND_READINESS"] == "PASS"
        assert report["findings"] == []
        assert report["refusals"] == {}
        assert report["spend_authorized"] is False
        assert report["physical_efficacy_claimed"] is False
        assertions = report["boundary_assertions"]
        assert assertions == {
            "D2_0004_MODIFIED": False,
            "D2_0005_ARMED": False,
            "NEW_HELDOUT_ACCESS": False,
            "SCIENTIFIC_THRESHOLDS_CHANGED": False,
            "PHYSICAL_EFFICACY_CLAIMED": False,
        }

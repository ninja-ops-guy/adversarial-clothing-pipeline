"""Tests for the Print Alpha order worksheet (Lane D)."""

from __future__ import annotations

import json

import jsonschema
import pytest

from scripts_print_alpha.order_worksheet import build_worksheet
from scripts_print_alpha.validate_manifests import MANIFEST_DIR, PENDING


class TestOrderWorksheet:
    def test_builds_from_repo_manifests(self):
        ws = build_worksheet()
        assert ws["worksheet_id"] == "RAC-PRINT-ALPHA-001-ORDER-WORKSHEET"
        assert ws["physical_efficacy_claimed"] is False
        assert ws["evidence_class"] == "experimental_print_specimen"
        assert ws["status"] == "USER_ACTION_REQUIRED"

    def test_binds_all_five_manifest_hashes(self):
        ws = build_worksheet()
        assert len(ws["source_manifests"]) == 5
        for digest in ws["source_manifests"].values():
            assert len(digest) == 64

    def test_pending_fields_never_fabricated(self):
        ws = build_worksheet()
        assert ws["pending_user_action_fields"] > 0
        # every placement control/candidate remains literally pending
        for placement in ws["order"]["placements"]:
            assert placement["control_file"] == PENDING
            assert placement["candidate_file"] == PENDING

    def test_user_action_refs_carried(self):
        ws = build_worksheet()
        assert "UA-1" in ws["user_action_refs"]

    def test_readiness_verdict_recorded_when_present(self):
        readiness = MANIFEST_DIR.parent.parent / "artifacts" / "print-alpha" / "readiness.json"
        ws = build_worksheet(readiness if readiness.exists() else None)
        assert ws["readiness_verdict"] in ("USER_ACTION_REQUIRED", "READY_TO_ORDER", "NOT_READY", "NOT_EVALUATED")

    def test_guards_fire_before_worksheet(self, monkeypatch):
        """A mapping manifest violating a guard must abort worksheet build."""
        import scripts_print_alpha.order_worksheet as ow

        original = ow._load

        def poisoned(name):
            data = original(name)
            if name == "mapping-manifest.json":
                data = json.loads(json.dumps(data))
                data["source_manifest_sha256"] = "0" * 64  # stale pin
            return data

        monkeypatch.setattr(ow, "_load", poisoned)
        with pytest.raises(jsonschema.ValidationError, match="stale production mapping"):
            ow.build_worksheet()

    def test_deterministic(self):
        a = json.dumps(build_worksheet(), sort_keys=True)
        b = json.dumps(build_worksheet(), sort_keys=True)
        assert a == b

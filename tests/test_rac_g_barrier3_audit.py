"""Tests for tools/rac_g_barrier3_audit.py (RAC-G final audit, Lane B closure).

The audit runs against a freshly generated Barrier 3 package in tmp space so
the tests neither mutate nor depend on the committed artifacts/barrier3 tree.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruthless_pipeline.integration import barrier3
from tools import rac_g_barrier3_audit as audit

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def fresh_package():
    with tempfile.TemporaryDirectory(prefix="racg-audit-test-") as tmp:
        package = Path(tmp) / "package"
        barrier3.run_barrier3(barrier3.Barrier3Config(), package)
        barrier3.write_replay_report(barrier3.verify_replay(package, package), package)
        barrier3.write_barrier3_report(package)
        yield package


class TestVerdictLogic:
    def _checks(self, **statuses):
        return {
            name: {"status": status, "refusal_reason": "r", "reason": "d"}
            for name, status in statuses.items()
        }

    def test_all_pass_gives_pass(self):
        verdict = audit.derive_verdict(self._checks(a=audit.PASS, b=audit.PASS))
        assert verdict["verdict"] == "PASS"

    def test_deferred_gives_nonblocking_gaps(self):
        verdict = audit.derive_verdict(self._checks(a=audit.PASS, b=audit.DEFERRED))
        assert verdict["verdict"] == "PASS_WITH_NONBLOCKING_GAPS"
        assert "b" in verdict["nonblocking_gaps"]

    def test_finding_fails_closed(self):
        verdict = audit.derive_verdict(self._checks(a=audit.PASS, b=audit.FINDING))
        assert verdict["verdict"] == "FAIL"
        assert verdict["findings"] == ["b"]

    def test_refusal_fails_closed_and_is_explicit(self):
        verdict = audit.derive_verdict(self._checks(a=audit.REFUSED))
        assert verdict["verdict"] == "FAIL"
        assert verdict["refusals"] == {"a": "r"}

    def test_refusal_never_counts_as_pass(self):
        verdict = audit.derive_verdict(self._checks(a=audit.REFUSED, b=audit.DEFERRED))
        assert verdict["verdict"] == "FAIL"


class TestRefusalCapture:
    def test_missing_package_refused_not_passed(self, tmp_path):
        result = audit.check_committed_package_integrity(tmp_path / "nope")
        assert result["status"] == audit.REFUSED
        assert result["refusal_reason"]

    def test_missing_handoff_refused(self, tmp_path):
        result = audit.check_handoff_pin(tmp_path)
        assert result["status"] == audit.REFUSED
        assert "missing" in result["refusal_reason"]


class TestAgainstFreshPackage:
    def test_quantitative_checks_pass_on_fresh_package(self, fresh_package):
        assert audit.check_aggregation_references(fresh_package)["status"] == audit.PASS
        assert audit.check_pareto_oracle(fresh_package)["status"] == audit.PASS
        assert audit.check_eot_reproduction(fresh_package)["status"] == audit.PASS
        assert audit.check_committed_package_integrity(fresh_package)["status"] == audit.PASS
        assert audit.check_committed_gate_report(fresh_package)["status"] == audit.PASS

    def test_tamper_and_provenance_attacks_detected(self, fresh_package):
        assert audit.check_tamper_detection(fresh_package)["status"] == audit.PASS
        assert audit.check_provenance_attacks(fresh_package)["status"] == audit.PASS

    def test_tampered_package_flips_gate_check(self, fresh_package, tmp_path):
        import shutil

        shadow = tmp_path / "shadow"
        shutil.copytree(fresh_package, shadow)
        target = shadow / "stage-artifacts" / "stage3-detector-science.json"
        payload = json.loads(target.read_text())
        cid = sorted(payload["detector_loss"])[0]
        payload["detector_loss"][cid] += 0.25
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        assert audit.check_aggregation_references(shadow)["status"] == audit.FINDING

    def test_full_audit_passes_with_documented_gap(self, fresh_package):
        report = audit.run_audit(REPO_ROOT, fresh_package, tests_green=True)
        assert report["verdict"] in ("PASS", "PASS_WITH_NONBLOCKING_GAPS")
        assert "finite_difference" in report["nonblocking_gaps"]
        block = report["trust_block"]
        assert block["SOURCE_COMMIT"] == audit.SOURCE_COMMIT
        assert block["D2_0005_ARMED"] is False
        assert block["PHYSICAL_EFFICACY_CLAIMED"] is False

    def test_handoff_pin_passes_against_repo(self):
        assert audit.check_handoff_pin(REPO_ROOT)["status"] == audit.PASS

    def test_scientific_boundaries_hold(self, fresh_package):
        assert audit.check_scientific_boundaries(REPO_ROOT, fresh_package)["status"] == audit.PASS

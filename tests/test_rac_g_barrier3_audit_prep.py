"""Tests for tools/rac_g_barrier3_audit_prep.py (Lane B preparation).

The prep tool readiness-checks the independent verification surface against a
real Barrier 3 artifact package. Its final verdict is hard-pinned NOT_ISSUED:
the final RAC-G audit starts only after the Barrier 3 completion handoff is
committed, pushed, refetched, and byte-confirmed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruthless_pipeline.integration.barrier3 import (
    Barrier3Config,
    run_barrier3,
    verify_replay,
    write_replay_report,
)
from tools.rac_g_barrier3_audit_prep import (
    FINAL_VERDICT,
    check_aggregation_references,
    check_eot_reproduction,
    check_fabrication_guard,
    check_pareto_oracle,
    check_promotion_attacks,
    check_provenance_attacks,
    check_release_replay,
    check_seed_replay,
    check_tamper_detection,
)


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    a = tmp_path_factory.mktemp("racg-a")
    b = tmp_path_factory.mktemp("racg-b")
    config = Barrier3Config()
    run_barrier3(config, a)
    run_barrier3(config, b)
    write_replay_report(verify_replay(a, b), a)
    return a, b


class TestIndependentChecks:
    def test_aggregation_reference(self, runs):
        result = check_aggregation_references(runs[0])
        assert result["status"] == "PREPARED_PASS", result

    def test_pareto_oracle(self, runs):
        result = check_pareto_oracle(runs[0])
        assert result["status"] == "PREPARED_PASS"
        assert result["front_size"] >= 1

    def test_seed_replay_independent(self, runs):
        result = check_seed_replay(runs[0], runs[1])
        assert result["status"] == "PREPARED_PASS", result

    def test_seed_replay_detects_divergence(self, runs, tmp_path):
        other = tmp_path / "other"
        run_barrier3(Barrier3Config(master_seed=999), other)
        result = check_seed_replay(runs[0], other)
        assert result["status"] == "PREPARED_FINDING"
        assert result["mismatches"]

    def test_eot_reproduction(self, runs):
        result = check_eot_reproduction(runs[0])
        assert result["status"] == "PREPARED_PASS", result

    def test_tamper_detection(self, runs):
        result = check_tamper_detection(runs[0])
        assert result["status"] == "PREPARED_PASS", result

    def test_provenance_attacks(self, runs):
        result = check_provenance_attacks(runs[0])
        assert result["status"] == "PREPARED_PASS", result

    def test_fabrication_guard(self):
        assert check_fabrication_guard()["status"] == "PREPARED_PASS"

    def test_promotion_attacks(self):
        assert check_promotion_attacks()["status"] == "PREPARED_PASS"

    def test_release_replay(self, runs):
        result = check_release_replay(runs[0])
        assert result["status"] == "PREPARED_PASS"

    def test_final_verdict_pinned_not_issued(self):
        assert FINAL_VERDICT == "NOT_ISSUED"

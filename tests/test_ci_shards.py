"""Tests for scripts/ci_shards.py deterministic partitioning (E1)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ci_shards import aggregate, partition, shard_of, verify_partition

NODEIDS = [f"tests/test_mod_{i}.py::test_case_{j}" for i in range(20) for j in range(7)]


class TestShardAssignment:
    def test_deterministic(self):
        assert shard_of("tests/test_a.py::test_x", 4) == shard_of("tests/test_a.py::test_x", 4)

    def test_in_range(self):
        for n in NODEIDS:
            assert 0 <= shard_of(n, 5) < 5


class TestPartition:
    def test_complete_and_disjoint(self):
        for n_shards in (1, 2, 4, 8):
            report = verify_partition(NODEIDS, n_shards)
            assert report["complete"], n_shards
            assert report["disjoint"], n_shards
            assert report["no_shard_omitted"], n_shards
            assert sum(report["shard_sizes"]) == len(NODEIDS)

    def test_stable_across_input_order(self):
        shuffled = list(reversed(NODEIDS))
        assert partition(NODEIDS, 4) == partition(shuffled, 4)


class TestAggregate:
    def _summary(self, shard, shards, **over):
        base = {
            "shard": shard,
            "shards": shards,
            "tests": 10,
            "passed": 9,
            "failures": 0,
            "errors": 0,
            "skipped": 1,
            "xfail": 0,
            "xpass": 0,
            "exit_code": 0,
        }
        base.update(over)
        return base

    def test_all_shards_required(self, tmp_path):
        for i, s in enumerate([self._summary(0, 3), self._summary(1, 3)]):
            (tmp_path / f"shard-{i}.json").write_text(__import__("json").dumps(s))
        result = aggregate([str(tmp_path / "shard-0.json"), str(tmp_path / "shard-1.json")])
        assert result["aggregate_complete"] is False
        assert result["all_green"] is False

    def test_full_green(self, tmp_path):
        import json

        paths = []
        for i in range(3):
            p = tmp_path / f"shard-{i}.json"
            p.write_text(json.dumps(self._summary(i, 3)))
            paths.append(str(p))
        result = aggregate(paths)
        assert result["aggregate_complete"] is True
        assert result["all_green"] is True
        assert result["totals"]["tests"] == 30
        assert result["totals"]["skipped"] == 3

    def test_failure_propagates(self, tmp_path):
        import json

        paths = []
        for i in range(2):
            p = tmp_path / f"shard-{i}.json"
            p.write_text(json.dumps(self._summary(i, 2, failures=1 if i == 1 else 0)))
            paths.append(str(p))
        result = aggregate(paths)
        assert result["all_green"] is False
        assert result["totals"]["failures"] == 1

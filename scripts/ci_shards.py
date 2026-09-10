#!/usr/bin/env python3
"""Deterministic CI test sharding (Lane E item E1).

The full suite exceeds a single 600 s local verification window. This tool
partitions the collected test nodeids into N deterministic shards:

- assignment: shard(nodeid) = int(sha256(nodeid)[:8], 16) % N — stable across
  runs, machines, and collection order;
- every collected test belongs to exactly one shard (verified);
- ``run`` executes one shard with junit XML output; ``aggregate`` merges
  per-shard JSON summaries and requires all shards present, with exact
  pass/fail/skip/xfail/xpass reporting.

Usage:
    python3 scripts/ci_shards.py list --shards 4 --shard 0
    python3 scripts/ci_shards.py verify --shards 4
    python3 scripts/ci_shards.py run --shards 4 --shard 0 --json-out shard-0.json
    python3 scripts/ci_shards.py aggregate shard-0.json shard-1.json ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def shard_of(nodeid: str, n_shards: int) -> int:
    """Deterministic shard assignment; stable across runs and machines."""
    return int(hashlib.sha256(nodeid.encode("utf-8")).hexdigest()[:8], 16) % n_shards


def partition(nodeids: list[str], n_shards: int) -> list[list[str]]:
    """Partition nodeids; shard order by nodeid for stable shard contents."""
    shards: list[list[str]] = [[] for _ in range(n_shards)]
    for nodeid in sorted(nodeids):
        shards[shard_of(nodeid, n_shards)].append(nodeid)
    return shards


def collect_nodeids() -> list[str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    nodeids = [
        line.strip()
        for line in proc.stdout.splitlines()
        if "::" in line and not line.startswith((" ", "<"))
    ]
    if not nodeids:
        raise RuntimeError(f"pytest collection failed:\n{proc.stdout}\n{proc.stderr}")
    return nodeids


def verify_partition(nodeids: list[str], n_shards: int) -> dict:
    shards = partition(nodeids, n_shards)
    flat = [n for shard in shards for n in shard]
    return {
        "total_tests": len(nodeids),
        "assigned": len(flat),
        "complete": sorted(flat) == sorted(nodeids),
        "disjoint": len(set(flat)) == len(flat),
        "no_shard_omitted": all(len(shard) > 0 for shard in shards),
        "shard_sizes": [len(shard) for shard in shards],
    }


def _parse_summary_line(text: str) -> dict[str, int]:
    """Parse pytest -rA short summary lines for xfail/xpass counts."""
    counts = {"xfail": 0, "xpass": 0}
    for line in text.splitlines():
        if line.startswith(("XFAIL", "XPASS")):
            key = "xfail" if line.startswith("XFAIL") else "xpass"
            counts[key] += 1
    return counts


def run_shard(n_shards: int, shard: int, json_out: str | None) -> dict:
    nodeids = partition(collect_nodeids(), n_shards)[shard]
    junit = Path(f"shard-{shard}.junit.xml")
    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider",
            f"--junitxml={junit}",
            *nodeids,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    tree = ET.parse(junit)
    root = tree.getroot()
    suites = list(root.iter("testsuite"))
    summary = {
        "shard": shard,
        "shards": n_shards,
        "tests": sum(int(s.get("tests", 0)) for s in suites),
        "failures": sum(int(s.get("failures", 0)) for s in suites),
        "errors": sum(int(s.get("errors", 0)) for s in suites),
        "skipped": sum(int(s.get("skipped", 0)) for s in suites),
        "exit_code": proc.returncode,
    }
    summary.update(_parse_summary_line(proc.stdout))
    summary["passed"] = (
        summary["tests"] - summary["failures"] - summary["errors"] - summary["skipped"]
    )
    junit.unlink(missing_ok=True)
    if json_out:
        Path(json_out).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def aggregate(paths: list[str]) -> dict:
    """Merge per-shard summaries; requires every shard present exactly once."""
    summaries = [json.loads(Path(p).read_text()) for p in paths]
    n_shards = summaries[0]["shards"]
    seen = sorted(s["shard"] for s in summaries)
    aggregate_ok = seen == list(range(n_shards)) and all(s["shards"] == n_shards for s in summaries)
    totals = {
        key: sum(int(s.get(key, 0)) for s in summaries)
        for key in ("tests", "passed", "failures", "errors", "skipped", "xfail", "xpass")
    }
    return {
        "shards_expected": n_shards,
        "shards_present": seen,
        "aggregate_complete": aggregate_ok,
        "totals": totals,
        "all_green": aggregate_ok
        and totals["failures"] == 0
        and totals["errors"] == 0
        and all(s["exit_code"] == 0 for s in summaries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("list", "verify", "run"):
        p = sub.add_parser(name)
        p.add_argument("--shards", type=int, required=True)
        if name in ("list", "run"):
            p.add_argument("--shard", type=int, required=True)
        if name == "run":
            p.add_argument("--json-out", default=None)
    agg = sub.add_parser("aggregate")
    agg.add_argument("summaries", nargs="+")
    args = parser.parse_args()

    if args.cmd == "list":
        for nodeid in partition(collect_nodeids(), args.shards)[args.shard]:
            print(nodeid)
        return 0
    if args.cmd == "verify":
        report = verify_partition(collect_nodeids(), args.shards)
        print(json.dumps(report, indent=2))
        return 0 if report["complete"] and report["disjoint"] and report["no_shard_omitted"] else 1
    if args.cmd == "run":
        summary = run_shard(args.shards, args.shard, args.json_out)
        print(json.dumps(summary, indent=2))
        return summary["exit_code"]
    result = aggregate(args.summaries)
    print(json.dumps(result, indent=2))
    return 0 if result["all_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

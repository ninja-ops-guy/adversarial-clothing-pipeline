#!/usr/bin/env python3
"""Profile the non-inference portions of the research pipeline.

Times, with ``time.perf_counter`` and several repetitions:

* status ingestion (``read_d2_status`` on the published status JSON),
* release verification (``verify_release`` re-hashing the sealed release),
* manuscript export inputs (parse of evidence/exports/figures JSON),
* the documentation linter (full docs scan),
* the D2-0005 rehearsal harness end-to-end (synthetic, outcome-free),
* a fast pytest segment (subprocess wall time).

No model weights are loaded and no inference runs. Prints a JSON report to
stdout (or ``--report PATH``). All numbers are machine- and load-dependent;
they are envelope measurements, not benchmarks.

Usage:
    PYTHONPATH=. python scripts/profile_pipeline.py [--root PATH] [--report PATH]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import-safe CLI entrypoint (E2)

import argparse
import json
import subprocess
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _time(fn, repeats: int) -> dict:
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return {
        "repeats": repeats,
        "min_s": min(samples),
        "median_s": sorted(samples)[len(samples) // 2],
        "max_s": max(samples),
    }


def profile(root: Path) -> dict:
    from ruthless_pipeline.certification.doc_lint import lint_repo
    from ruthless_pipeline.certification.experiment_status import read_d2_status
    from ruthless_pipeline.certification.release_format import verify_release
    from ruthless_pipeline.certification.rehearsal_d20005 import run_rehearsal

    results: dict[str, dict] = {}

    status_path = root / "d2-latest-status.json"
    results["status_ingest"] = _time(lambda: read_d2_status(status_path), 200)

    release_dir = root / "releases" / "RAC-EXP-2026-001"
    results["release_verification"] = _time(lambda: verify_release(release_dir), 5)

    def _manuscript_parse() -> int:
        n = 0
        for pattern in ("manuscript/evidence/**/*.json", "manuscript/exports/*.json",
                        "manuscript/figures/*.json"):
            for path in root.glob(pattern):
                json.loads(path.read_text(encoding="utf-8"))
                n += 1
        return n

    results["manuscript_export_inputs"] = _time(_manuscript_parse, 20)

    results["doc_lint_full_scan"] = _time(lambda: lint_repo(root), 5)

    def _rehearsal() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_rehearsal(Path(tmp))

    results["rehearsal_harness_end_to_end"] = _time(_rehearsal, 3)

    def _pytest_segment() -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:warnings",
             "tests/test_doc_lint.py", "tests/test_release_format.py",
             "tests/test_schema_version_guard.py"],
            cwd=root, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"profiled pytest segment failed: {proc.stdout[-500:]}")

    results["pytest_fast_segment"] = _time(_pytest_segment, 1)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root (default: cwd)")
    parser.add_argument("--report", default=None, help="write JSON report to this path")
    args = parser.parse_args(argv)

    results = profile(Path(args.root).resolve())
    payload = json.dumps(results, indent=2, sort_keys=True)
    print(payload)
    if args.report:
        Path(args.report).write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

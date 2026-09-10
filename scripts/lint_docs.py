#!/usr/bin/env python3
"""Documentation staleness linter CLI.

Scans docs/**, README.md, and manuscript/backlog/** for stale experiment
statuses, broken relative paths, schema-version drift, stale CI run numbers,
and untraceable quantitative claims. Exits non-zero on any non-allowlisted
finding. Emits a human summary and (optionally) a machine-readable JSON
report.

Usage:
    PYTHONPATH=. python scripts/lint_docs.py [--root PATH] [--report PATH]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import-safe CLI entrypoint (E2)

import argparse
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ruthless_pipeline.certification.doc_lint import format_summary, lint_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root (default: cwd)")
    parser.add_argument("--report", default=None, help="write JSON report to this path")
    args = parser.parse_args(argv)

    result = lint_repo(args.root)
    print(format_summary(result))
    if args.report:
        Path(args.report).write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

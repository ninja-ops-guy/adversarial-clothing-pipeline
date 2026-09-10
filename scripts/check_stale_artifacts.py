"""Detect stale derived artifacts across the repository (drift watch).

Usage::

    PYTHONPATH=. python scripts/check_stale_artifacts.py [--report PATH]

Recomputes every derived surface (provenance graph, dashboard export,
schema registry, deliverable inventory, manuscript figure/export source
pins, the frozen cluster-results hash pin, and the doc_lint documentation
checks) and emits a deterministic machine-readable JSON report listing
exactly what must be regenerated. Exit code is 0 when every surface is
FRESH and 1 when any surface is STALE or MISSING.

This tool DETECTS ONLY. It never regenerates, overwrites, or repairs any
artifact — regeneration of scientific evidence (in particular anything
touching D2-0004/D2-0005) requires its own review and is never automatic.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import-safe CLI entrypoint (E2)

import argparse
import json

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ruthless_pipeline.certification.stale_artifacts import (  # noqa: E402
    STATUS_FRESH,
    check_repo,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="optional path to write the JSON report (stdout always gets it)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root to check (defaults to this repo)",
    )
    args = parser.parse_args(argv)

    report = check_repo(args.repo_root)
    payload = report.to_dict()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.report is not None:
        args.report.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    for surface in payload["surfaces"]:
        if surface["status"] != STATUS_FRESH:
            sys.stderr.write(
                f"STALE[{surface['status']}] {surface['surface']}: "
                f"{len(surface['findings'])} finding(s); regenerate: "
                f"{'; '.join(surface['regenerate']) or 'manual review'}\n"
            )
    return 1 if payload["stale"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

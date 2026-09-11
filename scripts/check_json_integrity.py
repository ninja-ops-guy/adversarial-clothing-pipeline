"""Fail closed on malformed or connector-placeholder JSON in the repository.

This gate is intentionally dependency-free so CI can run it immediately after
checkout, before ML runtime installation and the full pytest matrix. It catches
push/integration corruption such as a committed file whose entire contents are
``__CONTENT_<n>__`` as well as ordinary malformed or non-UTF-8 JSON.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"

_EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)
_CONNECTOR_PLACEHOLDER = re.compile(r"^__CONTENT_\d+__\s*$")


def _eligible(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return not any(part in _EXCLUDED_PARTS for part in rel.parts)


def scan_json(root: str | Path) -> dict[str, object]:
    """Return a deterministic integrity report for repository ``*.json`` files."""
    base = Path(root).resolve()
    findings: list[dict[str, str]] = []
    scanned = 0

    for path in sorted(base.rglob("*.json")):
        if not path.is_file() or not _eligible(path, base):
            continue
        scanned += 1
        rel = path.relative_to(base).as_posix()
        raw = path.read_bytes()

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            findings.append(
                {
                    "path": rel,
                    "kind": "INVALID_UTF8",
                    "detail": str(exc),
                }
            )
            continue

        if _CONNECTOR_PLACEHOLDER.fullmatch(text):
            findings.append(
                {
                    "path": rel,
                    "kind": "CONNECTOR_PLACEHOLDER",
                    "detail": "file contains an unresolved __CONTENT_<n>__ placeholder",
                }
            )
            continue

        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            findings.append(
                {
                    "path": rel,
                    "kind": "INVALID_JSON",
                    "detail": f"line {exc.lineno} column {exc.colno}: {exc.msg}",
                }
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "root": str(base),
        "scanned_json_files": scanned,
        "status": "FAIL" if findings else "PASS",
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root to scan (defaults to this repo)",
    )
    args = parser.parse_args(argv)
    report = scan_json(args.repo_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

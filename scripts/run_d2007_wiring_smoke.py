"""Run the D2-0007 Stage-0 landmark-free wiring smoke test (sequencing gate).

Usage::

    PYTHONPATH=. python scripts/run_d2007_wiring_smoke.py [--out PATH] [--verify PATH]

Runs the deterministic landmark-free wiring path
(``ruthless_pipeline.patterns.wiring.run_wiring_smoke``) over the fixed
smoke seeds and writes a machine-checkable, schema-versioned, content-hashed
smoke summary JSON (default ``artifacts/d2007_wiring_smoke/smoke_summary.json``).
Verdict PASS means only that PATTERNS outputs became governed RAC candidates
with complete provenance — NOT that any detection rate moved. No efficacy is
measured; the scoring surface is a synthetic development fixture
(hypothesis-screening infrastructure, never evidence).

``--verify PATH`` re-verifies a previously written summary fail-closed
(structural checks + full regeneration of every candidate from the registry)
and exits non-zero on any tamper or mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ruthless_pipeline.patterns.wiring import (  # noqa: E402
    WiringSmokeError,
    run_wiring_smoke,
    verify_smoke_summary,
    write_smoke_summary,
)

DEFAULT_OUT = REPO_ROOT / "artifacts" / "d2007_wiring_smoke" / "smoke_summary.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--verify",
        type=Path,
        default=None,
        help="verify an existing smoke summary instead of running",
    )
    args = parser.parse_args(argv)

    if args.verify is not None:
        summary = json.loads(args.verify.read_text())
        try:
            verify_smoke_summary(summary)
        except WiringSmokeError as exc:
            print(f"VERIFY FAIL: {exc}")
            return 1
        print(f"VERIFY OK: {args.verify} "
              f"(summary_sha256={summary['summary_sha256']})")
        return 0

    summary = run_wiring_smoke()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    file_sha = write_smoke_summary(summary, args.out)
    print(json.dumps({
        "written": str(args.out),
        "verdict": summary["verdict"],
        "summary_sha256": summary["summary_sha256"],
        "file_sha256": file_sha,
        "candidates": len(summary["candidates"]),
        "exposure_ledger_sha256": summary["exposure_ledger_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

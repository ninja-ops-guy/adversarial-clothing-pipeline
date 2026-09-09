#!/usr/bin/env python3
"""CLI for the Barrier 3 synthetic integrated rehearsal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.rehearsal_barrier3 import (
    DEFAULT_CREATED_UTC,
    RESULT_LINE,
    STAGES,
    build_default_manifest,
    run_rehearsal,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest", help="Existing Barrier 3 run manifest JSON")
    parser.add_argument("--run-id", default="BARRIER3-D20005-SYNTHETIC-001")
    parser.add_argument("--root-seed", type=int, default=20260909)
    parser.add_argument("--created-utc", default=DEFAULT_CREATED_UTC)
    parser.add_argument("--crash-after", choices=STAGES)
    args = parser.parse_args()

    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text())
    else:
        manifest = build_default_manifest(
            run_id=args.run_id,
            root_seed=args.root_seed,
            created_utc=args.created_utc,
        )
    result = run_rehearsal(args.output_dir, manifest, crash_after=args.crash_after)
    print(json.dumps(result, sort_keys=True))
    print(RESULT_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

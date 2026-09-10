#!/usr/bin/env python3
"""Run the Barrier 3 synthetic integration proof, twice, and verify replay.

Writes the artifact package (artifacts/barrier3/ layout):

  run-manifest.json / input-hashes.json / runtime-environment.json
  stage-artifacts/ / objective-telemetry.json / provenance.json
  hashes.sha256 / replay-report.json / barrier3-report.json

Two equivalent runs are executed into temporary directories; their
scientific-equivalence projections are compared (runtime-environment.json
excluded by design), then run A's artifacts plus the replay report and the
final gate report are written to the output directory.

Synthetic integration proof only: no held-out models, no measured evidence,
physical_efficacy_claimed=False throughout. Exit nonzero on any gate failure.

Usage:
    PYTHONPATH=. python3 scripts/run_barrier3_integration.py [--output-dir artifacts/barrier3]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruthless_pipeline.integration import barrier3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="artifacts/barrier3")
    parser.add_argument("--master-seed", type=int, default=barrier3.Barrier3Config.master_seed)
    args = parser.parse_args()

    config = barrier3.Barrier3Config(master_seed=args.master_seed)
    out = Path(args.output_dir)

    with tempfile.TemporaryDirectory(prefix="barrier3-a-") as dir_a, tempfile.TemporaryDirectory(
        prefix="barrier3-b-"
    ) as dir_b:
        barrier3.run_barrier3(config, dir_a)
        barrier3.run_barrier3(config, dir_b)
        replay = barrier3.verify_replay(dir_a, dir_b)

        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(dir_a, out)

    barrier3.write_replay_report(replay, out)
    report = barrier3.write_barrier3_report(out)

    print(f"run:               {report['run_id']}")
    print(f"artifact integrity: {report['artifact_integrity']}")
    print(f"provenance:         {report['provenance']}")
    print(f"deterministic replay: {report['deterministic_replay']}")
    print(f"barrier3_closed:    {report['barrier3_closed']}")
    return 0 if report["barrier3_closed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

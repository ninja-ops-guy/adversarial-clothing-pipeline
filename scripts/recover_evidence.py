"""CLI: recover a completed/partial workflow run's NON-scientific stages.

Verifies every recorded stage's artifacts against the run journal
(hash + completeness), classifies each stage DONE / INCOMPLETE / CORRUPT,
and resumes ONLY unfinished non-scientific stages (publication, packaging,
report/export). Any path that would invoke inference, model loading,
benchmark execution, or candidate generation is a HARD REFUSAL
(InferenceRefusalError); corrupt sealed scientific evidence fails closed.

Exit codes:
    0  run already complete, or recovery completed and everything verifies
    1  corrupt scientific evidence / unsafe write / unrecoverable stage
    2  recovery refused: would require scientific compute (inference etc.)

Usage:
    python scripts/recover_evidence.py --run-dir /tmp/d20005-rehearsal [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification import evidence_recovery
from ruthless_pipeline.certification.evidence_recovery import (
    InferenceRefusalError,
    RecoveryError,
)

RESULT_LINE = "RESULT: synthetic_pipeline_validation_only — not RAC evidence"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True,
                        help="workflow run directory containing rehearsal_journal.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="classify and report planned actions without writing")
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    try:
        report = evidence_recovery.recover_run(run_dir, dry_run=args.dry_run)
    except InferenceRefusalError as exc:
        print(json.dumps({"refused": True, "reason": str(exc)}, indent=2))
        print(RESULT_LINE)
        return 2
    except RecoveryError as exc:
        print(json.dumps({"recovered": False, "error": str(exc)}, indent=2))
        print(RESULT_LINE)
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    print(RESULT_LINE)
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

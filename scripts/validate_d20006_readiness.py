"""D2-0006 readiness checklist validator.

Refuses to mark D2-0006 "ready" until every explicit prerequisite of the
interpretation-policy amendment path (policy §6) is met:

1. D2-0005 closed (a sealed, verifiable D2-0005 release) OR formally
   discontinued (a written discontinuation record);
2. a branch-selection memo exists, produced by ``d20006_branch_router.py``
   against the CURRENT frozen policy document;
3. the D2-0006 preregistration document exists with all mandatory slots
   filled and the §2.5 infrastructure-failure clause adopted by reference;
4. no D2-0006 generation file or trigger surface exists (policy §5) —
   readiness never coexists with an armable surface.

Exit code 0 iff ready; 1 otherwise; 2 if the policy document itself is
invalid. This tool validates only; it creates nothing.

Usage:
    python scripts/validate_d20006_readiness.py \
        [--policy docs/PREREGISTRATION_D2-0006_DRAFT.md] \
        [--d20005-release releases/RAC-EXP-YYYY-NNN | \
         --d20005-discontinuation docs/DISCONTINUATION_D2-0005.md] \
        [--branch-memo memo.json] [--preregistration docs/PREREGISTRATION_D2-0006.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ruthless_pipeline.certification.d20006_governance import (
    DEFAULT_POLICY_PATH,
    GovernanceError,
    check_readiness,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--d20005-release", help="sealed D2-0005 release directory")
    group.add_argument(
        "--d20005-discontinuation",
        help="formal D2-0005 discontinuation record (markdown)",
    )
    parser.add_argument("--branch-memo", help="branch-selection memo JSON")
    parser.add_argument(
        "--preregistration", help="completed D2-0006 preregistration document"
    )
    args = parser.parse_args(argv)

    try:
        report = check_readiness(
            policy_path=Path(args.policy),
            d20005_release_dir=Path(args.d20005_release) if args.d20005_release else None,
            d20005_discontinuation_path=(
                Path(args.d20005_discontinuation) if args.d20005_discontinuation else None
            ),
            branch_memo_path=Path(args.branch_memo) if args.branch_memo else None,
            preregistration_doc_path=(
                Path(args.preregistration) if args.preregistration else None
            ),
        )
    except GovernanceError as exc:
        print(f"ERROR: readiness cannot be evaluated (fail closed): {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    if report["ready"]:
        print("D2-0006 readiness: READY (all prerequisites satisfied)", file=sys.stderr)
        return 0
    unmet = [p["name"] for p in report["prerequisites"] if not p["satisfied"]]
    print(f"D2-0006 readiness: NOT READY — unmet prerequisites: {unmet}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

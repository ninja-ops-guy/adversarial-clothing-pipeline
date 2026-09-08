"""D2-0006 branch router (outcome-independent infrastructure).

Given a SEALED research release (per ``docs/RESEARCH_RELEASE_FORMAT.md``) of
a closed experiment and the frozen interpretation-policy document
(``docs/PREREGISTRATION_D2-0006_DRAFT.md``), emit a deterministic
branch-selection memo JSON: which branch of the frozen five-branch
interpretation-policy tree fires, with triggering evidence hashes and a
rationale whose every slot is filled from the sealed artifacts only.

This tool fails closed on any missing, tampered, or ambiguous input. It
never creates a generation file, a directional hypothesis, or a trigger
path; it arms nothing.

Usage:
    python scripts/d20006_branch_router.py --release releases/RAC-EXP-YYYY-NNN \
        [--policy docs/PREREGISTRATION_D2-0006_DRAFT.md] \
        [--generation-id RAC-PER-D2-0005] [--out memo.json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ruthless_pipeline.certification.d20006_governance import (
    D20005_GENERATION_ID,
    DEFAULT_POLICY_PATH,
    GovernanceError,
    build_branch_memo,
    classify_release_closure,
    load_policy_document,
    memo_to_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        required=True,
        help="path to the sealed release directory of the closed experiment",
    )
    parser.add_argument(
        "--policy",
        default=str(DEFAULT_POLICY_PATH),
        help="path to the frozen interpretation-policy document",
    )
    parser.add_argument(
        "--generation-id",
        default=D20005_GENERATION_ID,
        help="generation whose closure is being routed (default: %(default)s); "
        "pass an empty string to disable the check",
    )
    parser.add_argument("--out", help="write the memo JSON here (default: stdout)")
    args = parser.parse_args(argv)

    try:
        policy = load_policy_document(Path(args.policy))
        closure = classify_release_closure(
            Path(args.release),
            expect_generation_id=args.generation_id or None,
        )
        memo = build_branch_memo(closure, policy)
    except GovernanceError as exc:
        print(f"ERROR: branch routing refused (fail closed): {exc}", file=sys.stderr)
        return 2

    text = memo_to_json(memo)
    if args.out:
        Path(args.out).write_text(text)
        print(f"branch-selection memo written: {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    print(
        f"selected branch {memo['branch_id']}: {memo['branch_name']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

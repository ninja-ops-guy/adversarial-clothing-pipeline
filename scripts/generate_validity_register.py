"""Generate / validate the Canonical Validity Register (SW-18).

Modes:
    --write-seed   Regenerate registry/validity_risks.json deterministically
                   from the seeded threats-to-validity extracted from
                   docs/papers/* (fails if the existing file differs, unless
                   --force is given; content is deterministic so regeneration
                   is normally a no-op).
    (default)      Validate the register and print the register report. The
                   report ALWAYS lists open (unresolved) risks.
    --check-docs   Additionally scan docs/papers/*.md, manuscript/**/*.md and
                   docs/*.md for RAC-RISK-<hex16> reference tokens and fail if
                   any referenced risk ID does not resolve against the register
                   (the paper/evidence-card reference mechanism).

Exit codes: 0 ok; 2 contract violation (fail-closed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ruthless_pipeline.certification.validity_register import (
    UnknownRiskError,
    ValidityRegister,
    ValidityRegisterError,
    seed_register,
    validate_risk_references,
)

DEFAULT_REGISTER = "registry/validity_risks.json"

DOC_GLOBS = ("docs/papers/*.md", "docs/*.md", "manuscript/**/*.md")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and validate the RAC canonical validity register."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--register", default=DEFAULT_REGISTER)
    parser.add_argument(
        "--write-seed",
        action="store_true",
        help="write the deterministic seeded register",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow --write-seed to overwrite a differing existing register",
    )
    parser.add_argument(
        "--check-docs",
        action="store_true",
        help="validate RAC-RISK reference tokens in docs/papers and manuscript",
    )
    parser.add_argument(
        "--report-out",
        default=None,
        help="optional output path for the markdown register report",
    )
    return parser.parse_args(argv)


def _load_register(path: Path) -> ValidityRegister:
    if not path.is_file():
        raise ValidityRegisterError(f"register not found: {path}")
    return ValidityRegister.from_json(path.read_text(encoding="utf-8"))


def _check_doc_references(root: Path, register: ValidityRegister) -> list[str]:
    problems: list[str] = []
    seen: set[Path] = set()
    for pattern in DOC_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8")
            try:
                validate_risk_references(text, register)
            except UnknownRiskError as exc:
                problems.append(f"{path.relative_to(root)}: {exc}")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.repo_root)
    register_path = root / args.register

    try:
        if args.write_seed:
            seeded = seed_register()
            text = seeded.to_json() + "\n"
            if register_path.is_file() and not args.force:
                existing = register_path.read_text(encoding="utf-8")
                if existing != text:
                    raise ValidityRegisterError(
                        f"{args.register} differs from the deterministic seed; "
                        "refusing to overwrite without --force"
                    )
            register_path.parent.mkdir(parents=True, exist_ok=True)
            register_path.write_text(text, encoding="utf-8")
            register = seeded
        else:
            register = _load_register(register_path)

        problems: list[str] = []
        if args.check_docs:
            problems = _check_doc_references(root, register)

        report = register.report_markdown()
        if args.report_out:
            Path(args.report_out).write_text(report, encoding="utf-8")
        sys.stdout.write(report)

        if problems:
            for problem in problems:
                print(f"dangling risk reference: {problem}", file=sys.stderr)
            return 2
        return 0
    except ValidityRegisterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

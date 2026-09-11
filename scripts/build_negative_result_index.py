"""Build and query the Negative Result / Failure Index (SW-08).

The index is GENERATED from canonical evidence (generations/, releases/,
registry/experiments.json, manuscript/evidence/) — never from manual copies.
Every query result carries content-addressed evidence refs back to the
canonical artifacts it was derived from.

Usage:
    # print the full generated index (canonical JSON, deterministic)
    python -m scripts.build_negative_result_index --repo-root .

    # write it to a file
    python -m scripts.build_negative_result_index --out index.json

    # queries (combinable; results are intersected)
    python -m scripts.build_negative_result_index \
        --category cross_architecture_transfer_failure
    python -m scripts.build_negative_result_index --experiment RAC-EXP-2026-001
    python -m scripts.build_negative_result_index --generator-family <family>
    python -m scripts.build_negative_result_index --outcome-kind negative

Exit codes: 0 success; 2 contract violation (typed error, fail-closed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ruthless_pipeline.certification.negative_result_index import (
    NegativeResultIndex,
    NegativeResultIndexError,
    NegativeOutcomeRecord,
    build_index,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and query the RAC negative-result / failure index "
        "from canonical evidence."
    )
    parser.add_argument("--repo-root", default=".", help="repository root")
    parser.add_argument(
        "--out",
        default=None,
        help="optional output path for the full generated index (canonical JSON)",
    )
    parser.add_argument("--category", default=None, help="failure category filter")
    parser.add_argument(
        "--generator-family", default=None, help="generator family filter"
    )
    parser.add_argument("--experiment", default=None, help="experiment ID filter")
    parser.add_argument("--generation", default=None, help="generation ID filter")
    parser.add_argument("--outcome-kind", default=None, help="outcome kind filter")
    return parser.parse_args(argv)


def _query(index: NegativeResultIndex, args: argparse.Namespace) -> list[NegativeOutcomeRecord]:
    result: list[NegativeOutcomeRecord] | None = None

    def intersect(records: list[NegativeOutcomeRecord]) -> None:
        nonlocal result
        if result is None:
            result = list(records)
        else:
            keep = {r.record_id for r in records}
            result = [r for r in result if r.record_id in keep]

    if args.category is not None:
        intersect(index.by_category(args.category))
    if args.generator_family is not None:
        intersect(index.by_generator_family(args.generator_family))
    if args.experiment is not None:
        intersect(index.by_experiment(args.experiment))
    if args.generation is not None:
        intersect(index.by_generation(args.generation))
    if args.outcome_kind is not None:
        intersect(index.by_outcome_kind(args.outcome_kind))
    if result is None:
        result = list(index.records)
    return result


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        index = build_index(Path(args.repo_root))
        selected = _query(index, args)
    except NegativeResultIndexError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.out:
        Path(args.out).write_text(index.to_json() + "\n", encoding="utf-8")

    payload = {
        "index_sha256": index.index_sha256(),
        "summary": index.summary(),
        "query": {
            key: value
            for key, value in (
                ("category", args.category),
                ("generator_family", args.generator_family),
                ("experiment", args.experiment),
                ("generation", args.generation),
                ("outcome_kind", args.outcome_kind),
            )
            if value is not None
        },
        "result_count": len(selected),
        "results": [record.to_dict() for record in selected],
    }
    import json

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

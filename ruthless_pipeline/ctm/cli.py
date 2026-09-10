"""CTM bridge CLI. Run as: python -m ruthless_pipeline.ctm.cli ...

Digital path is FUNCTIONAL: `genome compare digital <candidate_file>` extracts
the file's genome, compares it against the most recent registered digital
genome (lexicographically greatest pattern_id for determinism) or a genome
selected with --pattern-id, prints a JSON ComparisonReport, exit 0.

Physical path FAILS CLOSED: `genome compare physical <target>` prints a JSON
user-action packet {status: PENDING_USER_ACTION, ...} and exits 3 — physical
capture/calibration requires human action (UA-3/UA-1). physical_efficacy_claimed
is always false. Unknown args -> argparse exit 2.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ruthless_pipeline.pattern_genome.config import load_config
from ruthless_pipeline.pattern_genome.extractor import extract_genome
from ruthless_pipeline.pattern_genome.validation import validate_genome

from .compare import compare_genomes
from .errors import CTMBridgeError
from .genome_adapter import (
    DEFAULT_EXTRACTED_UTC,
    DEFAULT_REGISTRY_ROOT,
    list_registered_pattern_ids,
    load_registered_genome,
)
from .ids import pattern_id_from_genome

EXIT_PENDING_USER_ACTION = 3
DEFAULT_CONFIG_PATH = "configs/pattern_genome_v1.json"


def _physical_packet(target: str) -> dict:
    return {
        "status": "PENDING_USER_ACTION",
        "reason": "physical capture/calibration required (UA-3/UA-1); "
                  "no physical measurement pipeline is available in this wave",
        "target": target,
        "claim_state": "EXPLORATORY",
        "physical_efficacy_claimed": False,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ruthless_pipeline.ctm.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    genome = sub.add_parser("genome", help="genome operations")
    genome_sub = genome.add_subparsers(dest="genome_command", required=True)
    cmp_p = genome_sub.add_parser("compare", help="compare a candidate against the registry")
    cmp_p.add_argument("kind", choices=["digital", "physical"])
    cmp_p.add_argument("target", help="candidate file (digital) or target name (physical)")
    cmp_p.add_argument("--pattern-id", default=None, help="registered pattern to compare against")
    cmp_p.add_argument("--registry-root", default=DEFAULT_REGISTRY_ROOT)
    cmp_p.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    cmp_p.add_argument("--source-commit", default="0" * 40)
    cmp_p.add_argument("--runtime-lock-sha256", default="0" * 64)
    return parser


def _run_digital(args) -> int:
    candidate_path = Path(args.target)
    if not candidate_path.is_file():
        print(json.dumps({"status": "ERROR", "reason": f"candidate file not found: {args.target}"}))
        return 1
    candidate_bytes = candidate_path.read_bytes()
    import hashlib
    config = load_config(args.config)
    try:
        genome = extract_genome(
            candidate_bytes,
            candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
            source_artifact_ref=str(candidate_path),
            source_commit=args.source_commit,
            runtime_lock_sha256=args.runtime_lock_sha256,
            config=config,
            extracted_utc=DEFAULT_EXTRACTED_UTC,
        )
        validate_genome(genome)
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "reason": f"genome extraction failed: {exc}"}))
        return 1

    if args.pattern_id:
        pattern_id = args.pattern_id
    else:
        registered = list_registered_pattern_ids(args.registry_root)
        if not registered:
            print(json.dumps({
                "status": "ERROR",
                "reason": f"registry at {args.registry_root!r} has no registered digital "
                          "genomes; register one first (fail-closed)",
            }))
            return 1
        pattern_id = registered[-1]  # lexicographically greatest: deterministic "most recent" stand-in
    try:
        baseline = load_registered_genome(args.registry_root, pattern_id)
    except CTMBridgeError as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}))
        return 1

    report = compare_genomes(genome, baseline, evidence_tier="DIGITAL")
    out = report.to_dict()
    out["pattern_id"] = pattern_id
    out["candidate_pattern_id"] = pattern_id_from_genome(genome)
    print(json.dumps(out, sort_keys=True, indent=2))
    return 0


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "genome" and args.genome_command == "compare":
        if args.kind == "physical":
            print(json.dumps(_physical_packet(args.target), sort_keys=True, indent=2))
            return EXIT_PENDING_USER_ACTION
        return _run_digital(args)
    return 2  # unreachable: argparse enforces subcommands


if __name__ == "__main__":
    sys.exit(main())

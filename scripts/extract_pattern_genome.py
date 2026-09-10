#!/usr/bin/env python3
"""Extract a Pattern Genome from a candidate image.

Deterministic. Fail-closed. Evidence class: derived_digital_measurement.
"""
from __future__ import annotations
import argparse
import hashlib
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ruthless_pipeline.pattern_genome import canonical_json, extract_genome, load_config, validate_genome

def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a Pattern Genome from a candidate image.")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--config", default=str(Path(_REPO_ROOT) / "configs" / "pattern_genome_v1.json"))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--runtime-lock", required=True, help="Runtime lock manifest SHA-256")
    parser.add_argument("--source-ref", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--extracted-utc", default="2026-01-01T00:00:00Z")
    args = parser.parse_args()
    candidate_path = Path(args.candidate)
    if not candidate_path.exists():
        print(f"ERROR: candidate not found: {candidate_path}", file=sys.stderr); return 1
    candidate_bytes = candidate_path.read_bytes()
    candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
    source_ref = args.source_ref or f"file://{candidate_path.name}#{candidate_sha[:16]}"
    config = load_config(args.config)
    try:
        genome = extract_genome(
            candidate_bytes, candidate_sha256=candidate_sha, source_artifact_ref=source_ref,
            source_commit=args.source_commit, runtime_lock_sha256=args.runtime_lock,
            config=config, extracted_utc=args.extracted_utc)
        validate_genome(genome)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr); return 1
    genome_bytes = canonical_json(genome)
    if args.output:
        out_dir = Path(args.output); out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{genome.genome_id}.json"; out_path.write_bytes(genome_bytes)
        print(f"WROTE: {out_path}")
    else:
        sys.stdout.buffer.write(genome_bytes); sys.stdout.buffer.write(b"\n")
    print("RESULT: derived_digital_measurement — not physical efficacy evidence", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())

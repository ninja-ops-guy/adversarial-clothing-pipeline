"""Build (or verify) the repository artifact provenance graph.

Usage::

    python scripts/build_provenance_graph.py            # build + write
    python scripts/build_provenance_graph.py --verify   # verify only

Build mode writes ``artifacts/provenance/graph.json`` (schema
``rac-provenance-graph`` version ``1.0``; deterministic bytes — two runs
over the same tree produce identical sha256).

Verify mode first requires the committed output artifact to be byte-identical
to a deterministic rebuild, then recomputes every hash edge and reports BROKEN
(hash mismatch), MISSING (target absent), and MUTABLE (missing hash pin where
one is expected) edges. The known D2-0004 unattested gaps are MISSING-by-design
and never count as failures. Exit code is non-zero for a missing/stale/corrupt
committed artifact or any unexpected BROKEN / MUTABLE / MISSING edge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ruthless_pipeline.certification.provenance_graph import (  # noqa: E402
    build_graph,
    graph_sha256,
    verify_graph,
    write_graph,
)

DEFAULT_OUT = REPO_ROOT / "artifacts" / "provenance" / "graph.json"


def _verify_committed_artifact(graph: dict, out_path: Path) -> bool:
    """Require ``out_path`` to equal the canonical deterministic rebuild.

    This is intentionally separate from edge verification. Edge verification
    operates on a freshly built in-memory graph and therefore cannot, by
    itself, detect a stale, truncated, placeholder, or otherwise corrupted
    committed ``graph.json``.
    """
    if not out_path.is_file():
        print(f"COMMITTED_GRAPH_MISSING: {out_path}")
        return False

    with tempfile.TemporaryDirectory(prefix="rac-provenance-verify-") as tmp:
        expected_path = Path(tmp) / "graph.json"
        expected_sha = write_graph(graph, expected_path)
        expected_bytes = expected_path.read_bytes()

    actual_bytes = out_path.read_bytes()
    actual_sha = hashlib.sha256(actual_bytes).hexdigest()
    if actual_bytes != expected_bytes:
        print(
            "COMMITTED_GRAPH_MISMATCH: committed artifact is stale or corrupt\n"
            f"  path: {out_path}\n"
            f"  expected_sha256: {expected_sha}\n"
            f"  actual_sha256:   {actual_sha}"
        )
        return False

    print(f"committed graph bytes: VERIFIED ({actual_sha})")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="verify committed bytes, then recompute every hash edge",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="graph artifact path to write or verify",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root to walk (defaults to this repo)",
    )
    args = parser.parse_args(argv)

    graph = build_graph(args.repo_root)
    digest = graph_sha256(graph)

    if args.verify:
        if not _verify_committed_artifact(graph, args.out):
            return 1
        report = verify_graph(graph, args.repo_root)
        summary = report["summary"]
        print(f"graph sha256: {digest}")
        print(
            "edges: {V} VERIFIED, {B} BROKEN, {M} MISSING, {U} MUTABLE".format(
                V=summary["VERIFIED"],
                B=summary["BROKEN"],
                M=summary["MISSING"],
                U=summary["MUTABLE"],
            )
        )
        if report["unexpected_edges"]:
            print("UNEXPECTED edges:")
            for edge_id in report["unexpected_edges"]:
                print(f"  - {edge_id}")
            return 1
        print("verification OK: committed artifact current; no unexpected edges")
        return 0

    digest = write_graph(graph, args.out)
    print(
        json.dumps(
            {
                "written": str(args.out),
                "sha256": digest,
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

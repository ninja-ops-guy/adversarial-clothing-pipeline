"""Build (or verify) the repository artifact provenance graph.

Usage::

    python scripts/build_provenance_graph.py            # build + write
    python scripts/build_provenance_graph.py --verify   # verify only

Build mode writes ``artifacts/provenance/graph.json`` (schema
``rac-provenance-graph`` version ``1.0``; deterministic bytes — two runs
over the same tree produce identical sha256).

Verify mode recomputes every hash edge and reports BROKEN (hash mismatch),
MISSING (target absent), and MUTABLE (missing hash pin where one is
expected) edges. The known D2-0004 unattested gaps are MISSING-by-design
and never count as failures. Exit code is non-zero if any unexpected
BROKEN / MUTABLE / MISSING edge is found.
"""

from __future__ import annotations

import argparse
import json
import sys
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="recompute every hash edge and report BROKEN/MISSING/MUTABLE",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="output path for the graph JSON (build mode)",
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
        print("verification OK: no unexpected BROKEN/MISSING/MUTABLE edges")
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

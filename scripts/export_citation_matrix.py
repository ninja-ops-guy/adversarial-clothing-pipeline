"""Export the citation/evidence matrix for Papers 1-5 (Wave I, item 11).

Emits ``manuscript/exports/citation_evidence_matrix.json``: one row per
planned paper (1-5), one cell per column family (``claims``, ``figures``,
``tables``). Each cell is either:

- **verified** — every value traces to an artifact of a CLOSED RAC release,
  cited by repo-relative path with the artifact's recomputed SHA-256; or
- **blank** — an explicit ``reason`` string. Blank-on-missing is the rule:
  nothing here invents, estimates, or reconstructs a scientific datum.

Closed releases eligible as sources (the only ones that exist today):

- ``RAC-PER-D2-0003`` — closed, retained negative; status JSON archived
  byte-identical at ``manuscript/evidence/RAC-PER-D2-0003/``; root
  ``benchmark-results.json`` remains its benchmark artifact.
- ``RAC-PER-D2-0004`` — closed, FAIL / RAC-D0; log-attested closure at
  ``manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json`` (the
  CI-validated bundle was never archived; see
  ``docs/AMENDMENT_D2-0004_INFRA-001.md`` and ``releases/RAC-EXP-2026-001/``).

Governance rule enforced by :func:`validate_matrix`: a populated cell whose
source path is not one of those closed-release artifacts fails validation,
and any source path that smells synthetic/simulated fails validation
(synthetic artifacts can never be measured sources).

Stdlib-only; deterministic canonical JSON output. Usage::

    python scripts/export_citation_matrix.py \
        --output manuscript/exports/citation_evidence_matrix.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "1.0"
MATRIX_FILENAME = "citation_evidence_matrix.json"

PAPERS: tuple[int, ...] = (1, 2, 3, 4, 5)
COLUMNS: tuple[str, ...] = ("claims", "figures", "tables")

#: Closed RAC releases and the repo-relative artifact paths that attest them.
#: This mapping is the allow-list: populated cells may cite ONLY these paths.
CLOSED_RELEASES: Mapping[str, Mapping[str, Any]] = {
    "RAC-PER-D2-0003": {
        "status": "closed",
        "closure": "archived",
        "decision": "FAIL / RAC-D0 (retained negative)",
        "artifacts": (
            "manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json",
            "benchmark-results.json",
        ),
    },
    "RAC-PER-D2-0004": {
        "status": "closed",
        "closure": "log_attested",
        "decision": "FAIL / RAC-D0 (retained negative)",
        "artifacts": ("manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json",),
    },
}

#: Paths that must never appear as a measured/verified source: synthetic or
#: simulated pipeline artifacts are validation-only, never evidence.
_FORBIDDEN_SOURCE_RE = re.compile(r"synthetic|simulated|dry[_-]?run|mock", re.IGNORECASE)

# Blank-cell reasons (stable strings; also consumed by tests).
REASON_PAPER2 = (
    "No closed RAC release exists for the P1 physical study: fabrication of "
    "calibration target RAC-CALT-P1-0001 is PENDING_USER_ACTION and no "
    "physical session has run; all P1 values stay [AWAITING: ...]."
)
REASON_PAPER3 = (
    "Capture Lab methodology paper: methods/infrastructure description only; "
    "it makes no measured claims and cites no closed RAC release artifacts."
)
REASON_PAPER4 = (
    "Research-OS / certification-infrastructure paper: system description "
    "only; it reports no experimental results and cites no closed RAC "
    "release artifacts."
)
REASON_PAPER5 = (
    "D2-0005 has not closed (status: awaiting_d2-0005_closure); every "
    "Paper 5 datum stays blank until the preregistered two-arm release "
    "closes per docs/PREREGISTRATION_D2-0005.md."
)

_D2_0003_STATUS = CLOSED_RELEASES["RAC-PER-D2-0003"]["artifacts"][0]
_D2_0003_BENCHMARK = CLOSED_RELEASES["RAC-PER-D2-0003"]["artifacts"][1]
_D2_0004_LOG = CLOSED_RELEASES["RAC-PER-D2-0004"]["artifacts"][0]


class CitationMatrixError(ValueError):
    """Raised when the citation/evidence matrix violates its contract."""


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _source(repo_root: Path, release: str, rel_path: str, attests: str) -> dict[str, str]:
    """One verified source reference pinned to the file's recomputed sha256."""
    path = repo_root / rel_path
    if not path.is_file():
        raise CitationMatrixError(f"closed-release artifact missing: {rel_path}")
    if rel_path not in CLOSED_RELEASES[release]["artifacts"]:
        raise CitationMatrixError(
            f"{rel_path} is not an attested artifact of closed release {release}"
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "release": release,
        "path": rel_path,
        "sha256": digest,
        "attests": attests,
    }


def _verified(sources: list[dict[str, str]], note: str) -> dict[str, Any]:
    return {"status": "verified", "sources": sources, "note": note}


def _blank(reason: str) -> dict[str, Any]:
    return {"status": "blank", "reason": reason, "sources": []}


def build_matrix(repo_root: str | Path) -> dict[str, Any]:
    """Build the papers 1-5 x claims/figures/tables evidence matrix.

    Only Paper 1 has closed-release evidence today (D2-0003 archived,
    D2-0004 log-attested). Papers 2-5 are blank with explicit reasons; no
    new scientific datum is populated anywhere.
    """
    repo_root = Path(repo_root)
    d3, d4 = "RAC-PER-D2-0003", "RAC-PER-D2-0004"
    paper1 = {
        "claims": _verified(
            [
                _source(repo_root, d3, _D2_0003_STATUS,
                        "D2-0003 closed retained-negative decision, protocol, "
                        "model sets, held-out outcome (archived)"),
                _source(repo_root, d4, _D2_0004_LOG,
                        "D2-0004 closed FAIL / RAC-D0 decision, log-attested "
                        "closure under amendment D2-0004-INFRA-001"),
            ],
            "Generation-ladder closure claims (D2-0003, D2-0004) trace to the "
            "two closed releases. D2-0005/D2-0006 claims remain [AWAITING] "
            "placeholders in manuscript/backlog/paper1.md and are not data.",
        ),
        "figures": _verified(
            [
                _source(repo_root, d3, _D2_0003_BENCHMARK,
                        "F1 transfer-scatter surrogate detection rate for "
                        "RAC-PER-D2-0003; F2 timeline closure timestamp"),
                _source(repo_root, d3, _D2_0003_STATUS,
                        "F1/F2 held-out detection rate for RAC-PER-D2-0003"),
                _source(repo_root, d4, _D2_0004_LOG,
                        "F2 generation-timeline point for RAC-PER-D2-0004 "
                        "(log-attested; F1 surrogate-only rate not attested)"),
            ],
            "Populated F1/F2 figure points (manuscript/figures/) derive "
            "exclusively from these closed-release artifacts. F3-F8 remain "
            "awaiting_data scaffolds with empty data arrays.",
        ),
        "tables": _verified(
            [
                _source(repo_root, d3, _D2_0003_STATUS,
                        "paper1 longitudinal table row RAC-PER-D2-0003 "
                        "(status, protocol, model sets, held-out outcome)"),
                _source(repo_root, d3, _D2_0003_BENCHMARK,
                        "paper1 longitudinal table row RAC-PER-D2-0003 "
                        "(candidate sha256, surrogate detection rate)"),
                _source(repo_root, d4, _D2_0004_LOG,
                        "paper1 longitudinal table row RAC-PER-D2-0004 "
                        "(log-attested fields; non-attested fields blank)"),
            ],
            "manuscript/exports/paper1_longitudinal.csv carries one row per "
            "closed generation; every populated cell already cites these "
            "paths with the same sha256 values recomputed here.",
        ),
    }
    rows = [
        {"paper": 1, "subject": "Longitudinal D2 program", "cells": paper1},
        {"paper": 2, "subject": "Physical P1 garment study",
         "cells": {c: _blank(REASON_PAPER2) for c in COLUMNS}},
        {"paper": 3, "subject": "Capture Lab methodology",
         "cells": {c: _blank(REASON_PAPER3) for c in COLUMNS}},
        {"paper": 4, "subject": "Research OS / certification infrastructure",
         "cells": {c: _blank(REASON_PAPER4) for c in COLUMNS}},
        {"paper": 5, "subject": "D2-0005 mean-vs-CVaR objective ablation",
         "cells": {c: _blank(REASON_PAPER5) for c in COLUMNS}},
    ]
    matrix: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "matrix": "citation_evidence_matrix",
        "generator": "scripts/export_citation_matrix.py",
        "columns": list(COLUMNS),
        "closed_releases": {
            release: {
                "status": info["status"],
                "closure": info["closure"],
                "decision": info["decision"],
                "artifacts": [
                    {
                        "path": rel_path,
                        "sha256": hashlib.sha256(
                            (repo_root / rel_path).read_bytes()
                        ).hexdigest(),
                    }
                    for rel_path in info["artifacts"]
                ],
            }
            for release, info in CLOSED_RELEASES.items()
        },
        "blank_rule": (
            "A cell is blank unless every value it would carry traces to a "
            "closed RAC release artifact listed in closed_releases; blanks "
            "carry an explicit reason and are never filled with invented, "
            "estimated, or reconstructed data."
        ),
        "rows": rows,
    }
    validate_matrix(matrix, repo_root)
    return matrix


def validate_matrix(matrix: Mapping[str, Any], repo_root: str | Path) -> None:
    """Fail-closed validation of the citation/evidence matrix.

    - schema version, paper rows 1-5, and all three columns are present;
    - every verified source path belongs to a CLOSED RAC release allow-list
      and its sha256 recomputes against the working tree;
    - no synthetic/simulated path may appear as a source (promotion guard);
    - blank cells must carry a non-empty reason and zero sources.
    """
    repo_root = Path(repo_root)
    if matrix.get("schema_version") != SCHEMA_VERSION:
        raise CitationMatrixError(
            f"schema_version must be {SCHEMA_VERSION!r}: {matrix.get('schema_version')!r}"
        )
    allowed = {
        rel_path
        for info in CLOSED_RELEASES.values()
        for rel_path in info["artifacts"]
    }
    rows = matrix.get("rows")
    if not isinstance(rows, list) or sorted(r["paper"] for r in rows) != list(PAPERS):
        raise CitationMatrixError(f"rows must cover papers {PAPERS} exactly")
    for row in rows:
        cells = row.get("cells")
        if not isinstance(cells, Mapping) or sorted(cells) != sorted(COLUMNS):
            raise CitationMatrixError(
                f"paper {row.get('paper')} must have cells {COLUMNS}"
            )
        for column, cell in cells.items():
            status = cell.get("status")
            sources = cell.get("sources")
            if not isinstance(sources, list):
                raise CitationMatrixError(
                    f"paper {row['paper']} {column}: sources list is required"
                )
            if status == "verified":
                if not sources:
                    raise CitationMatrixError(
                        f"paper {row['paper']} {column}: verified cell needs sources"
                    )
                for source in sources:
                    path = source.get("path", "")
                    if _FORBIDDEN_SOURCE_RE.search(path):
                        raise CitationMatrixError(
                            f"paper {row['paper']} {column}: synthetic/simulated "
                            f"artifact {path!r} can never be a measured source"
                        )
                    if path not in allowed:
                        raise CitationMatrixError(
                            f"paper {row['paper']} {column}: {path!r} does not "
                            "trace to a closed RAC release (allow-list: "
                            f"{sorted(allowed)})"
                        )
                    if source.get("release") not in CLOSED_RELEASES:
                        raise CitationMatrixError(
                            f"paper {row['paper']} {column}: unknown release "
                            f"{source.get('release')!r}"
                        )
                    digest = hashlib.sha256((repo_root / path).read_bytes()).hexdigest()
                    if not _is_sha256(source.get("sha256")) or source["sha256"] != digest:
                        raise CitationMatrixError(
                            f"paper {row['paper']} {column}: sha256 for {path!r} "
                            "does not recompute"
                        )
            elif status == "blank":
                if sources:
                    raise CitationMatrixError(
                        f"paper {row['paper']} {column}: blank cell must have no sources"
                    )
                if not cell.get("reason"):
                    raise CitationMatrixError(
                        f"paper {row['paper']} {column}: blank cell needs a reason"
                    )
            else:
                raise CitationMatrixError(
                    f"paper {row['paper']} {column}: status must be verified|blank"
                )


def matrix_json(matrix: Mapping[str, Any]) -> str:
    """Canonical JSON (sort_keys, compact separators, trailing newline)."""
    return json.dumps(matrix, sort_keys=True, separators=(",", ":")) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--output",
        default=str(Path("manuscript") / "exports" / MATRIX_FILENAME),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate an existing matrix file instead of writing",
    )
    args = parser.parse_args()
    repo_root = Path(args.repo_root)
    output = Path(args.output)
    if args.check:
        validate_matrix(json.loads(output.read_text()), repo_root)
        print(json.dumps({"status": "valid", "path": str(output)}, sort_keys=True))
        return 0
    matrix = build_matrix(repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(matrix_json(matrix))
    print(json.dumps({"status": "written", "path": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

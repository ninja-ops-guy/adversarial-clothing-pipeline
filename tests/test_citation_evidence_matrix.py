"""Wave I item 11 tests: citation/evidence matrix + blank-safety guard.

(a) The committed manuscript/exports/citation_evidence_matrix.json is
    deterministic, schema-versioned, and every populated cell traces to a
    closed RAC release (D2-0003 archived, D2-0004 log-attested) with a
    recomputed sha256; anything else fails validation.
(b) Blank-safety guard: manuscript/exports/* and manuscript/figures/F*.json
    contain no value whose source-artifact hash does not recompute, and no
    simulated/synthetic artifact path may appear as a measured source
    (promotion guard).
(c) No new scientific datum: paper5 exports and unpopulated figure scaffolds
    stay blank/null.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator, Mapping

import pytest

from scripts.export_citation_matrix import (
    COLUMNS,
    MATRIX_FILENAME,
    PAPERS,
    build_matrix,
    matrix_json,
    validate_matrix,
    CitationMatrixError,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = REPO_ROOT / "manuscript" / "exports"
FIGURES_DIR = REPO_ROOT / "manuscript" / "figures"
MATRIX_PATH = EXPORTS_DIR / MATRIX_FILENAME

# Synthetic/simulated artifacts are pipeline-validation only; they must never
# appear anywhere as a measured/verified source (promotion guard).
FORBIDDEN_SOURCE_RE = re.compile(r"synthetic|simulated|dry[_-]?run|mock", re.IGNORECASE)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- (a) citation evidence matrix -------------------------------------------


def test_committed_matrix_is_deterministic_and_valid() -> None:
    assert MATRIX_PATH.is_file(), "matrix must be committed under manuscript/exports/"
    rebuilt = build_matrix(REPO_ROOT)
    assert MATRIX_PATH.read_text() == matrix_json(rebuilt)
    validate_matrix(json.loads(MATRIX_PATH.read_text()), REPO_ROOT)


def test_matrix_covers_papers_and_columns() -> None:
    matrix = build_matrix(REPO_ROOT)
    assert [row["paper"] for row in matrix["rows"]] == list(PAPERS)
    for row in matrix["rows"]:
        assert sorted(row["cells"]) == sorted(COLUMNS)


def test_matrix_only_paper1_is_verified() -> None:
    matrix = build_matrix(REPO_ROOT)
    for row in matrix["rows"]:
        for cell in row["cells"].values():
            if row["paper"] == 1:
                assert cell["status"] == "verified" and cell["sources"]
            else:
                assert cell["status"] == "blank" and cell["reason"] and not cell["sources"]


def test_matrix_rejects_non_closed_release_source() -> None:
    matrix = build_matrix(REPO_ROOT)
    cell = matrix["rows"][0]["cells"]["claims"]
    cell["sources"] = [
        {
            "release": "RAC-PER-D2-0005",
            "path": "docs/DESIGN_ANALYSIS_D2-0005.md",
            "sha256": _sha256(REPO_ROOT / "docs/DESIGN_ANALYSIS_D2-0005.md"),
            "attests": "design analysis is not a closed release",
        }
    ]
    with pytest.raises(CitationMatrixError, match="closed RAC release|unknown release"):
        validate_matrix(matrix, REPO_ROOT)


def test_matrix_rejects_synthetic_source_path() -> None:
    matrix = build_matrix(REPO_ROOT)
    cell = matrix["rows"][0]["cells"]["claims"]
    cell["sources"] = [
        {
            "release": "RAC-PER-D2-0003",
            "path": "artifacts/p1_synthetic_dry_run/session-manifest.json",
            "sha256": "0" * 64,
            "attests": "synthetic must never be a measured source",
        }
    ]
    with pytest.raises(CitationMatrixError, match="synthetic"):
        validate_matrix(matrix, REPO_ROOT)


def test_matrix_rejects_stale_sha256() -> None:
    matrix = build_matrix(REPO_ROOT)
    source = matrix["rows"][0]["cells"]["claims"]["sources"][0]
    source["sha256"] = "0" * 64
    with pytest.raises(CitationMatrixError, match="recompute"):
        validate_matrix(matrix, REPO_ROOT)


def test_matrix_rejects_blank_without_reason() -> None:
    matrix = build_matrix(REPO_ROOT)
    matrix["rows"][1]["cells"]["claims"] = {"status": "blank", "sources": []}
    with pytest.raises(CitationMatrixError, match="reason"):
        validate_matrix(matrix, REPO_ROOT)


# --- (b) blank-safety guard over exports + figure JSONs ----------------------


def _walk(node: Any) -> Iterator[Any]:
    yield node
    if isinstance(node, Mapping):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _check_source_path(path_value: str, context: str) -> None:
    assert not FORBIDDEN_SOURCE_RE.search(path_value), (
        f"{context}: synthetic/simulated path {path_value!r} may never appear "
        "as a measured source"
    )


def _check_json_artifact(path: Path) -> None:
    payload = json.loads(path.read_text())
    for node in _walk(payload):
        if not isinstance(node, Mapping):
            continue
        # Figure-data provenance blocks: {rel_path: sha256, ...}.
        if "source_artifacts" in node:
            artifacts = node["source_artifacts"]
            assert isinstance(artifacts, Mapping) and artifacts, (
                f"{path.name}: source_artifacts must be a non-empty mapping"
            )
            for rel_path, digest in artifacts.items():
                _check_source_path(rel_path, f"{path.name} source_artifacts")
                assert _SHA256_RE.match(digest or ""), (
                    f"{path.name}: bad sha256 for {rel_path}"
                )
                assert _sha256(REPO_ROOT / rel_path) == digest, (
                    f"{path.name}: source_artifacts hash for {rel_path} does "
                    "not recompute"
                )
        # SourcedValue-style blocks: {value, source, sha256}.
        if "source" in node and "sha256" in node:
            source, digest = node["source"], node["sha256"]
            if source or digest:
                _check_source_path(source, f"{path.name} source")
                assert _SHA256_RE.match(digest or "")
                assert _sha256(REPO_ROOT / source) == digest, (
                    f"{path.name}: sha256 for source {source} does not recompute"
                )


def test_exports_and_figures_hashes_recompute() -> None:
    json_files = sorted(EXPORTS_DIR.glob("*.json")) + sorted(FIGURES_DIR.glob("F*.json"))
    assert json_files, "expected export/figure JSONs to guard"
    for path in json_files:
        _check_json_artifact(path)


def test_paper1_longitudinal_csv_sources_recompute() -> None:
    csv_path = EXPORTS_DIR / "paper1_longitudinal.csv"
    with csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "paper1_longitudinal.csv must carry the closed-generation rows"
    checked = 0
    for row in rows:
        for key, value in row.items():
            if not key.endswith("_sha256") or not value:
                continue
            source_key = f"{key[:-7]}_source"
            if source_key not in row:
                # e.g. the candidate_sha256 VALUE column (a hash datum, not a
                # file-provenance column); its provenance is carried by the
                # adjacent candidate_sha256_source/_sha256 columns.
                continue
            source = row[source_key]
            assert source, f"{key} populated without its *_source column"
            _check_source_path(source, f"{csv_path.name} {key}")
            assert _SHA256_RE.match(value)
            assert _sha256(REPO_ROOT / source) == value, (
                f"{csv_path.name}: {key} hash for {source} does not recompute"
            )
            checked += 1
    assert checked > 0


def test_no_new_scientific_datum_in_awaiting_exports() -> None:
    # Paper 5 comparison: every measured/statistical field stays JSON null.
    comparison = json.loads((EXPORTS_DIR / "paper5_comparison.json").read_text())
    assert comparison["status"] == "awaiting_d2-0005_closure"
    for key, value in comparison["statistics"].items():
        if isinstance(value, Mapping):
            assert all(v is None for v in value.values()) or all(
                v is None for pair in value.values() for v in (pair if isinstance(pair, list) else [pair])
            ), key
        elif isinstance(value, list):
            assert all(v is None for v in value), key
        else:
            assert value is None, key
    # Paper 5 arms CSV: header only, zero data rows.
    arms_lines = (EXPORTS_DIR / "paper5_arms.csv").read_text().strip().splitlines()
    assert len(arms_lines) == 1
    # Unpopulated figure scaffolds stay awaiting_data with empty data.
    for figure in FIGURES_DIR.glob("F*.json"):
        payload = json.loads(figure.read_text())
        if payload.get("status") == "awaiting_data":
            assert payload["data"] == []

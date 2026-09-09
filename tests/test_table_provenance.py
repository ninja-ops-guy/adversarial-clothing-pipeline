"""Quantitative table provenance tests.

Every numeric cell in a generated documentation table must trace to an
authoritative machine-readable artifact, so that a manual transcription
error becomes a test failure rather than silent drift. Where a table is
intentionally manual (no machine source exists — e.g. machine-dependent
profiling envelopes), the document must carry an explicit
``<!-- provenance: MANUAL ... -->`` marker instead; absence of both a
machine source match AND a manual marker is a failure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DESIGN_DOC = REPO_ROOT / "docs" / "DESIGN_ANALYSIS_D2-0005.md"
DESIGN_RESULTS = REPO_ROOT / "artifacts" / "design_analysis_d20005" / "results.json"
PERF_DOC = REPO_ROOT / "docs" / "PERFORMANCE_AND_COST.md"
CLUSTER_RESULTS = (
    REPO_ROOT / "artifacts" / "design_analysis_d20005_cluster" / "results.json"
)
CLUSTER_MD = (
    REPO_ROOT / "artifacts" / "design_analysis_d20005_cluster" / "results.md"
)

PROVENANCE_RE = re.compile(r"<!--\s*provenance:\s*(?P<body>.*?)-->", re.DOTALL)

TABLE_HEADER_PREFIX = "| Delta_true | discordance | n |"


def _markdown_tables(text: str, header_prefix: str) -> list[list[list[str]]]:
    """Return parsed pipe tables (list of rows of stripped cells) whose
    header row starts with ``header_prefix``."""
    lines = text.splitlines()
    tables: list[list[list[str]]] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith(header_prefix):
            rows: list[list[str]] = []
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):  # skip ruler
                    rows.append(cells)
                j += 1
            tables.append(rows[1:])  # drop the header itself
            i = j
        else:
            i += 1
    return tables


def _fmt_delta(value: float) -> str:
    return f"{value:+.1f}"


def _fmt3(value: float) -> str:
    return f"{value:.3f}"


def _expected_row(cell: dict) -> list[str]:
    return [
        _fmt_delta(cell["true_delta"]),
        cell["structure"],
        str(cell["n"]),
        _fmt3(cell["p_success"]),
        _fmt3(cell["p_null"]),
        _fmt3(cell["p_negative"]),
        _fmt3(cell["p_inconclusive"]),
        _fmt3(cell["mean_interval_width"]),
        str(cell["bootstrap_resamples"]),
    ]


# --- D2-0005 design-analysis doc table vs the authoritative artifact -----------


def test_design_doc_carries_machine_provenance_marker():
    text = DESIGN_DOC.read_text(encoding="utf-8")
    markers = PROVENANCE_RE.findall(text)
    assert any(
        "source=artifacts/design_analysis_d20005/results.json" in body
        and "derived=machine" in body
        for body in markers
    ), "results table must carry a machine-derivation provenance comment"


def test_design_doc_grid_table_matches_results_json():
    payload = json.loads(DESIGN_RESULTS.read_text(encoding="utf-8"))
    text = DESIGN_DOC.read_text(encoding="utf-8")
    tables = _markdown_tables(text, TABLE_HEADER_PREFIX)
    # grid table + confirmation block
    assert len(tables) == 2, f"expected 2 results tables, found {len(tables)}"
    grid_rows, confirmation_rows = tables
    expected_grid = [_expected_row(cell) for cell in payload["cells"]]
    assert grid_rows == expected_grid
    expected_confirmation = [
        _expected_row(cell) for cell in payload["confirmation_cells"]
    ]
    assert confirmation_rows == expected_confirmation


def test_design_doc_excluded_cells_match_results_json():
    payload = json.loads(DESIGN_RESULTS.read_text(encoding="utf-8"))
    text = DESIGN_DOC.read_text(encoding="utf-8")
    for cell in payload["excluded_cells"]:
        needle = (
            f"Delta_true = {_fmt_delta(cell['true_delta'])}, "
            f"{cell['structure']}, n = {cell['n']}"
        )
        assert needle in text, f"excluded cell not disclosed in doc: {needle}"


def test_design_doc_grid_constants_match_artifact():
    payload = json.loads(DESIGN_RESULTS.read_text(encoding="utf-8"))
    text = DESIGN_DOC.read_text(encoding="utf-8")
    assert f"sim_seed {payload['sim_seed']}" in text
    assert (
        f"grid bootstrap resamples {payload['grid_bootstrap_resamples']}" in text
    )
    assert (
        f"{payload['datasets_per_cell']} datasets per cell" in text
    )


def test_seeded_transcription_error_is_detected():
    # Sanity: mutating one digit in the doc table must break the match.
    payload = json.loads(DESIGN_RESULTS.read_text(encoding="utf-8"))
    text = DESIGN_DOC.read_text(encoding="utf-8")
    tables = _markdown_tables(text, TABLE_HEADER_PREFIX)
    expected = [_expected_row(cell) for cell in payload["cells"]]
    corrupted = [row[:] for row in tables[0]]
    corrupted[0][3] = "9.999" if corrupted[0][3] != "9.999" else "8.888"
    assert corrupted != expected


# --- cluster simulation artifact pair (results.md vs results.json) ---------------


def test_cluster_results_md_is_exactly_rendered_from_results_json():
    # The committed markdown table must be byte-identical to the renderer
    # output over the authoritative JSON — any hand edit becomes a failure.
    from scripts.design_analysis_d20005_cluster import render_markdown_table

    payload = json.loads(CLUSTER_RESULTS.read_text(encoding="utf-8"))
    assert CLUSTER_MD.read_text(encoding="utf-8") == render_markdown_table(payload)


# --- PERFORMANCE_AND_COST.md: intentionally manual --------------------------------


def test_performance_doc_carries_manual_provenance_marker():
    text = PERF_DOC.read_text(encoding="utf-8")
    markers = PROVENANCE_RE.findall(text)
    assert any(
        "MANUAL" in body and "derived=manual" in body for body in markers
    ), (
        "measured timings are not machine-derivable; the doc must flag the "
        "table MANUAL with an explicit provenance comment"
    )


def test_performance_doc_states_reproduction_command():
    text = PERF_DOC.read_text(encoding="utf-8")
    assert "scripts/profile_pipeline.py" in text
    assert "Reproduce with:" in text

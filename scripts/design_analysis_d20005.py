"""PRE-ARMING design-analysis (power / operating characteristics) for D2-0005.

GOVERNANCE STATUS: NO D2-0005 outcome data exists. The generation skeleton is
frozen with ``lock_status: PREREGISTERED`` and its trigger fields are NOT
armed. This simulation characterizes what question the frozen design can
answer — it is a capability characterization of the preregistered analysis,
NOT tuning. It MUST NOT be used to propose changing the preregistered
thresholds (0.20 interval-width gate, alpha = 0.5 CVaR level, decision
regions) on the basis of expected favorable outcomes. The only legitimate
follow-ups, if the design proves badly underpowered, are the two
scientifically correct PRE-ARMING options:

(a) amend the DESIGN before arming (a documented, hash-committed amendment
    per the section 7 deviations policy of docs/PREREGISTRATION_D2-0005.md), or
(b) deliberately declare D2-0005 an exploratory / pilot-sized prospective
    experiment.

What this driver does
---------------------
For each grid cell (true paired difference Delta_true, discordance structure,
observation-unit count n) it draws ``DATASETS_PER_CELL`` synthetic paired
outcome datasets with SHA-256-seeded deterministic draws (same hash-draw
style as ``paired_arm_statistics._hash_draw``; no ``random`` module state),
then classifies each dataset with the ACTUAL preregistered analysis path:
``paired_arm_statistics.bootstrap_paired_difference_interval`` +
``paired_arm_statistics.classify_decision`` (the exact functions
``paired_arm_statistics.paired_arm_statistics`` calls internally, with the
preregistered z = 1.959963984540054, bootstrap seed 20260907, and
INCONCLUSIVE_WIDTH_MAX = 0.20). Decisions are tallied into
P(SUCCESS) / P(NULL) / P(NEGATIVE) / P(INCONCLUSIVE).

Disclosure (also in docs/DESIGN_ANALYSIS_D2-0005.md): the main grid uses
GRID_BOOTSTRAP_RESAMPLES = 1000 bootstrap resamples per dataset (the
preregistered execution uses 10000) to keep the grid computable; a
confirmation block re-runs the symmetric-discordance n = 72 cells at the
full preregistered 10000 resamples. Intervals are memoized on the sorted
discordance-count vector (n, n_m_only, n_concordant, n_c_only, resamples),
which fully determines the preregistered bootstrap interval; memoization
does not change any value.

Outputs: a canonical-JSON results artifact (sort_keys, separators (",",
":"), trailing newline) and a markdown results table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
from dataclasses import dataclass
from pathlib import Path

from ruthless_pipeline.certification.paired_arm_statistics import (
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_Z,
    INCONCLUSIVE_WIDTH_MAX,
    bootstrap_paired_difference_interval,
    classify_decision,
)

SCHEMA_VERSION = "1.0"

# Fixed simulation seed (documented in docs/DESIGN_ANALYSIS_D2-0005.md).
SIM_SEED = 20261204

# Grid definition.
GRID_DELTAS = (-0.1, 0.0, 0.1, 0.2, 0.3, 0.5)
GRID_STRUCTURES = ("symmetric", "m_dominated", "sparse")
GRID_UNIT_COUNTS = (36, 72, 144)
DATASETS_PER_CELL = 500

# Disclosed deviation from the preregistered execution: the grid uses 1000
# bootstrap resamples; confirmation cells use the full preregistered 10000.
GRID_BOOTSTRAP_RESAMPLES = 1000
CONFIRMATION_STRUCTURES = ("symmetric",)
CONFIRMATION_UNIT_COUNTS = (72,)

# Baseline Arm-M detection rate p_M per structure (Arm-C rate is p_M - Delta).
BASE_RATE_DEFAULT = 0.5
BASE_RATE_SPARSE = 0.3

DECISIONS = ("success", "null", "negative", "inconclusive")


@dataclass(frozen=True)
class JointModel:
    """Per-unit joint outcome probabilities for one grid cell.

    p_both: both arms detect; p_m_only / p_c_only: discordant cells;
    p_neither: both miss. p_both + p_m_only = p_M, p_both + p_c_only = p_C,
    so p_m_only - p_c_only = Delta_true exactly.
    """

    p_both: float
    p_m_only: float
    p_c_only: float
    p_neither: float
    rate_m: float
    rate_c: float


def joint_probabilities(true_delta: float, structure: str) -> JointModel:
    """Joint outcome model for a (Delta_true, structure) cell.

    Structures:
    - ``symmetric``: arms conditionally independent given the marginals
      (maximum-entropy pairing; discordance nearly balanced between
      M-only and C-only).
    - ``m_dominated``: nested pairing — for Delta >= 0 every Arm-C detection
      is also an Arm-M detection (p_c_only = 0, all discordance M-only);
      for Delta < 0 the nesting reverses. Maximum concordance given the
      marginals, hence the smallest discordant-pair variance.
    - ``sparse``: symmetric/independent pairing at a low baseline rate
      (p_M = 0.3), stressing the analysis in the low-rate regime.

    Raises ValueError for an unknown structure, a non-finite or out-of-range
    Delta, or marginals that fall outside [0, 1] (infeasible cell).
    """
    if structure not in GRID_STRUCTURES:
        raise ValueError(f"unknown discordance structure: {structure!r}")
    if not isinstance(true_delta, (int, float)) or isinstance(true_delta, bool):
        raise ValueError(f"true_delta must be a real number in [-1, 1]; got {true_delta!r}")
    if not -1.0 <= true_delta <= 1.0:
        raise ValueError(f"true_delta must be in [-1, 1]; got {true_delta!r}")
    rate_m = BASE_RATE_SPARSE if structure == "sparse" else BASE_RATE_DEFAULT
    rate_c = rate_m - true_delta
    if not 0.0 <= rate_c <= 1.0:
        raise ValueError(
            f"infeasible cell: rate_c = {rate_c} outside [0, 1] for "
            f"true_delta={true_delta!r} structure={structure!r}"
        )
    if structure == "m_dominated":
        # Nested: the smaller-rate arm's detections are a subset of the
        # larger-rate arm's (zero discordance on the subset side).
        p_both = min(rate_m, rate_c)
        p_m_only = rate_m - p_both
        p_c_only = rate_c - p_both
    else:
        # Conditional independence given the marginals.
        p_both = rate_m * rate_c
        p_m_only = rate_m * (1.0 - rate_c)
        p_c_only = (1.0 - rate_m) * rate_c
    p_neither = 1.0 - p_both - p_m_only - p_c_only
    return JointModel(p_both, p_m_only, p_c_only, p_neither, rate_m, rate_c)


def _validate_unit_count(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError(f"observation-unit count must be an int; got {n!r}")
    if n < 1:
        raise ValueError(f"observation-unit count must be >= 1; got {n!r}")
    return n


def _hash_uniform(sim_seed: int, cell_id: str, dataset: int, unit: int) -> float:
    """Deterministic uniform in [0, 1) from SHA-256 (no random module state)."""
    digest = hashlib.sha256(
        f"design-analysis-d20005|{sim_seed}|{cell_id}|{dataset}|{unit}".encode("ascii")
    ).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def draw_dataset(
    true_delta: float,
    structure: str,
    n: int,
    dataset_index: int,
    sim_seed: int = SIM_SEED,
) -> tuple[int, int, int]:
    """Draw one synthetic paired dataset; return (n_m_only, n_concordant, n_c_only).

    Per unit, a SHA-256-seeded uniform selects one of the four joint states
    (both / M-only / C-only / neither) under the cell's joint model. The
    preregistered bootstrap depends only on the sorted discordance-count
    vector, so counts are a sufficient statistic for the dataset.
    """
    _validate_unit_count(n)
    model = joint_probabilities(true_delta, structure)
    cell_id = f"{true_delta!r}|{structure}|{n}"
    cut_both = model.p_both
    cut_m = cut_both + model.p_m_only
    cut_c = cut_m + model.p_c_only
    n_m_only = 0
    n_c_only = 0
    n_concordant = 0
    for unit in range(n):
        u = _hash_uniform(sim_seed, cell_id, dataset_index, unit)
        if u < cut_both:
            n_concordant += 1
        elif u < cut_m:
            n_m_only += 1
        elif u < cut_c:
            n_c_only += 1
        else:
            n_concordant += 1
    return n_m_only, n_concordant, n_c_only


def _deltas_from_counts(n: int, n_m_only: int, n_concordant: int, n_c_only: int) -> tuple[int, ...]:
    if n_m_only + n_concordant + n_c_only != n:
        raise ValueError("discordance counts must sum to the observation-unit count")
    # Both-detected and both-missed units are concordant (delta 0); the
    # preregistered bootstrap is invariant to unit ordering, so the blocked
    # arrangement is exact, not an approximation.
    return (1,) * n_m_only + (0,) * n_concordant + (-1,) * n_c_only


class _IntervalCache:
    """Memoize preregistered bootstrap intervals on their sufficient statistic."""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, int, int, int, int], tuple[float, float]] = {}

    def interval(
        self,
        n: int,
        n_m_only: int,
        n_concordant: int,
        n_c_only: int,
        resamples: int,
    ) -> tuple[float, float]:
        key = (n, n_m_only, n_concordant, n_c_only, resamples)
        found = self._cache.get(key)
        if found is None:
            found = bootstrap_paired_difference_interval(
                _deltas_from_counts(n, n_m_only, n_concordant, n_c_only),
                resamples=resamples,
                z=DEFAULT_Z,
                seed=DEFAULT_BOOTSTRAP_SEED,
            )
            self._cache[key] = found
        return found


def simulate_cell(
    true_delta: float,
    structure: str,
    n: int,
    *,
    datasets: int | None = None,
    resamples: int | None = None,
    sim_seed: int = SIM_SEED,
    cache: _IntervalCache | None = None,
) -> dict:
    """Simulate one grid cell; return decision probabilities (canonical dict)."""
    datasets = DATASETS_PER_CELL if datasets is None else datasets
    resamples = GRID_BOOTSTRAP_RESAMPLES if resamples is None else resamples
    _validate_unit_count(n)
    joint_probabilities(true_delta, structure)  # validate delta/structure feasibility
    if datasets < 1:
        raise ValueError(f"datasets per cell must be >= 1; got {datasets!r}")
    if resamples < 100:
        raise ValueError(f"bootstrap requires at least 100 resamples; got {resamples!r}")
    cache = cache if cache is not None else _IntervalCache()
    tallies = {decision: 0 for decision in DECISIONS}
    width_sum = 0.0
    for dataset_index in range(datasets):
        n_m_only, n_concordant, n_c_only = draw_dataset(
            true_delta, structure, n, dataset_index, sim_seed
        )
        interval = cache.interval(n, n_m_only, n_concordant, n_c_only, resamples)
        decision, _ = classify_decision(interval, width_max=INCONCLUSIVE_WIDTH_MAX)
        tallies[decision] += 1
        width_sum += interval[1] - interval[0]
    return {
        "datasets": datasets,
        "bootstrap_resamples": resamples,
        "mean_interval_width": round(width_sum / datasets, 6),
        "n": n,
        "p_inconclusive": round(tallies["inconclusive"] / datasets, 6),
        "p_negative": round(tallies["negative"] / datasets, 6),
        "p_null": round(tallies["null"] / datasets, 6),
        "p_success": round(tallies["success"] / datasets, 6),
        "structure": structure,
        "true_delta": true_delta,
    }


def _cell_spec_list() -> tuple[list[tuple[float, str, int, int]], list[tuple[float, str, int, int]]]:
    """(grid_specs, confirmation_specs) as (delta, structure, n, resamples)."""
    grid_specs = [
        (delta, structure, n, GRID_BOOTSTRAP_RESAMPLES)
        for delta in GRID_DELTAS
        for structure in GRID_STRUCTURES
        for n in GRID_UNIT_COUNTS
    ]
    confirmation_specs = [
        (delta, structure, n, DEFAULT_BOOTSTRAP_RESAMPLES)
        for delta in GRID_DELTAS
        for structure in CONFIRMATION_STRUCTURES
        for n in CONFIRMATION_UNIT_COUNTS
    ]
    return grid_specs, confirmation_specs


def _simulate_cell_worker(spec: tuple[float, str, int, int]) -> dict:
    """Pool worker: simulate one cell, or return an exclusion record."""
    true_delta, structure, n, resamples = spec
    try:
        return simulate_cell(true_delta, structure, n, resamples=resamples)
    except ValueError as exc:
        return {
            "excluded": True,
            "n": n,
            "reason": str(exc),
            "structure": structure,
            "true_delta": true_delta,
        }


def _run_specs(specs: list[tuple[float, str, int, int]], workers: int) -> tuple[list[dict], list[dict]]:
    """Run cell specs (optionally in a process pool); order is preserved."""
    if workers > 1 and len(specs) > 1:
        with multiprocessing.Pool(processes=workers) as pool:
            results = pool.map(_simulate_cell_worker, specs)
    else:
        results = [_simulate_cell_worker(spec) for spec in specs]
    cells = [r for r in results if not r.get("excluded")]
    excluded = [
        {k: v for k, v in r.items() if k != "excluded"} for r in results if r.get("excluded")
    ]
    return cells, excluded


def run_grid(workers: int = 1) -> dict:
    """Run the full simulation grid plus the preregistered-10000 confirmation.

    Determinism is unaffected by ``workers``: every cell is a pure function of
    the fixed sim_seed and results are reassembled in canonical grid order.
    """
    grid_specs, confirmation_specs = _cell_spec_list()
    cells, excluded = _run_specs(grid_specs, workers)
    confirmation, confirmation_excluded = _run_specs(confirmation_specs, workers)
    excluded.extend(confirmation_excluded)
    return {
        "bootstrap_seed": DEFAULT_BOOTSTRAP_SEED,
        "cells": cells,
        "confirmation_cells": confirmation,
        "datasets_per_cell": DATASETS_PER_CELL,
        "excluded_cells": excluded,
        "generation": "RAC-PER-D2-0005",
        "grid_bootstrap_resamples": GRID_BOOTSTRAP_RESAMPLES,
        "grid_deltas": list(GRID_DELTAS),
        "grid_structures": list(GRID_STRUCTURES),
        "grid_unit_counts": list(GRID_UNIT_COUNTS),
        "inconclusive_width_max": INCONCLUSIVE_WIDTH_MAX,
        "preregistered_bootstrap_resamples": DEFAULT_BOOTSTRAP_RESAMPLES,
        "schema_version": SCHEMA_VERSION,
        "sim_seed": SIM_SEED,
        "z": DEFAULT_Z,
    }


def to_canonical_json(payload: dict) -> str:
    """Canonical frozen JSON: sort_keys, compact separators, trailing newline."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def _cell_row(cell: dict) -> str:
    return (
        f"| {cell['true_delta']:+.1f} | {cell['structure']} | {cell['n']} "
        f"| {cell['p_success']:.3f} | {cell['p_null']:.3f} | {cell['p_negative']:.3f} "
        f"| {cell['p_inconclusive']:.3f} | {cell['mean_interval_width']:.3f} "
        f"| {cell['bootstrap_resamples']} |"
    )


def render_markdown_table(payload: dict) -> str:
    """Render the results grid as a markdown table."""
    lines = [
        "| Delta_true | discordance | n | P(SUCCESS) | P(NULL) | P(NEGATIVE) "
        "| P(INCONCLUSIVE) | mean CI width | bootstrap R |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for cell in payload["cells"]:
        lines.append(_cell_row(cell))
    lines.append("")
    lines.append(
        "Confirmation block (full preregistered bootstrap_resamples = "
        f"{payload['preregistered_bootstrap_resamples']}):"
    )
    lines.append("")
    lines.append(lines[0])
    lines.append(lines[1])
    for cell in payload["confirmation_cells"]:
        lines.append(_cell_row(cell))
    if payload["excluded_cells"]:
        lines.append("")
        lines.append("Infeasible cells (marginal rate outside [0, 1]; excluded and disclosed):")
        lines.append("")
        for cell in payload["excluded_cells"]:
            lines.append(
                f"- Delta_true = {cell['true_delta']:+.1f}, {cell['structure']}, "
                f"n = {cell['n']}: {cell['reason']}"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-arming design-analysis simulation for preregistered D2-0005 "
        "(capability characterization only; NOT tuning)."
    )
    parser.add_argument("--output", default="artifacts/design_analysis_d20005/results.json")
    parser.add_argument("--markdown", default="artifacts/design_analysis_d20005/results.md")
    parser.add_argument(
        "--workers",
        type=int,
        default=min(2, multiprocessing.cpu_count()),
        help="process-pool size for the cell grid (results are identical for any value)",
    )
    args = parser.parse_args()

    payload = run_grid(workers=max(1, args.workers))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(to_canonical_json(payload), encoding="utf-8")
    markdown_path = Path(args.markdown)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown_table(payload), encoding="utf-8")
    print(f"wrote {output_path} and {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

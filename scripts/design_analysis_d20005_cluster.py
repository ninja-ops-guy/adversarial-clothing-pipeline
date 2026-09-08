"""PRE-ARMING cluster-aware design-analysis (operating characteristics) for D2-0005.

GOVERNANCE STATUS: NO D2-0005 outcome data exists. This simulation extends the
pre-arming operating-characteristic (OC) study of
``scripts/design_analysis_d20005.py`` / ``docs/DESIGN_ANALYSIS_D2-0005.md`` to
CLUSTERED data-generating processes. It characterizes what a proposed
cluster-robust analysis (``ruthless_pipeline/certification/
cluster_paired_arm_statistics.py``, DRAFT amendment path) can answer under
intracluster correlation, and contrasts it with the frozen unit-level
preregistered path on the SAME synthetic datasets. It is a capability
characterization of candidate designs BEFORE arming — NOT tuning against
observed outcomes (no outcomes exist) and NOT a threshold change: the 0.20
width gate, z, bootstrap seed, and decision regions are held fixed throughout.

What this driver does
---------------------
Data-generating process (clustered paired binary outcomes):
- A cell is (Delta_true, icc, K clusters, m members/cluster). The joint
  outcome model per member is the F0 ``symmetric`` discordance structure
  (arms conditionally independent given marginals, baseline p_M = 0.5, so
  p_m_only - p_c_only = Delta_true exactly).
- Intracluster correlation (CORRECTED, red-team finding F1): the labeled
  parameter ``icc`` IS the target intracluster correlation (realized
  pairwise correlation of member deltas). It is implemented as a per-member
  mixture with probability sqrt(icc): for cluster k a shared uniform U_k is
  drawn; for member j a coin C_kj and a private uniform V_kj are drawn. The
  member's effective uniform is U_k when C_kj < sqrt(icc), else V_kj. Two
  members therefore share their draw (identical joint state) with PAIRWISE
  probability (sqrt(icc))^2 = icc, so the realized intracluster correlation
  is ~= icc — verified empirically per cell (``mean_estimated_icc``) and by
  ``tests/test_design_analysis_d20005_cluster.py::
  test_realized_icc_matches_labeled_parameter``. The Wave H v1 DGP used the
  mixture probability directly as ``rho``, so the realized ICC was rho^2 and
  the grid axis was miscalibrated by a square; that defect is fixed here and
  the v1 grid is superseded. icc = 0 reproduces the F0 independent-unit DGP.
  All draws are SHA-256-seeded (same hash-draw style as
  ``paired_arm_statistics._hash_draw``; no ``random`` module state).

For each synthetic dataset TWO analyses are run on the SAME data:
1. CLUSTER path — the actual proposed module:
   ``cluster_paired_arm_statistics.cluster_paired_arm_statistics`` with the
   clusters as drawn (min_clusters = DEFAULT_MIN_CLUSTERS).
2. UNIT path — the unit-level analysis, executed via
   ``cluster_paired_arm_statistics`` on singleton clusters. NOTE (amended,
   findings F8): the new module corrects the frozen path's percentile
   lower-index off-by-one, so the singleton path is identical to the frozen
   ``paired_arm_statistics.paired_arm_statistics`` in every value EXCEPT that
   the interval lower bound may sit one order statistic lower (documented,
   intentional divergence; the frozen module is not modified). The
   equivalence up to this one-index divergence is enforced by
   ``tests/test_cluster_paired_arm_statistics.py::
   test_singleton_clusters_reproduce_unit_level_path`` and spot-checked on
   simulated datasets by
   ``tests/test_design_analysis_d20005_cluster.py``.
   Using the equivalent path lets the simulation reuse the memoized hash-draw
   rows; it changes no other value.

Per cell the driver tallies, for BOTH paths: P(SUCCESS/NULL/NEGATIVE/
INCONCLUSIVE), mean CI width, and coverage (fraction of datasets whose CI
contains Delta_true); the false-success rate is P(SUCCESS) at Delta_true <= 0.

Blocks:
- MAIN GRID (v2, amended after red-team): Delta_true x icc x K at the REAL
  protocol geometry m = MEMBERS_PER_CLUSTER = 36 members per cluster (18
  transformation views x 2 fixture crops of one base image — findings F2/F3:
  the v1 grid used m = 6, which has no protocol referent).
- MEMBERS SWEEP: fixed (Delta_true = +0.2, icc = 0.25, K = 18), varying m —
  documents how within-cluster replication saturates at the real geometry.
- CONFIRMATION: the Delta_true = +0.2, icc = 0.25 cells governing the
  cluster-count proposal re-run at the full preregistered 10000 bootstrap
  resamples (grid uses GRID_BOOTSTRAP_RESAMPLES = 1000, a disclosed deviation
  matching the F0 study).

Outputs: canonical-JSON artifact (sort_keys, separators (",", ":"), trailing
newline) and a markdown table; byte-identical regeneration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
from pathlib import Path

from ruthless_pipeline.certification.paired_arm_statistics import (
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_Z,
    INCONCLUSIVE_WIDTH_MAX,
)
from ruthless_pipeline.certification.cluster_paired_arm_statistics import (
    DEFAULT_MIN_CLUSTERS,
    _validated_clusters,
    cluster_paired_arm_statistics,
    intracluster_diagnostics,
)

SCHEMA_VERSION = "2.0"

# Fixed simulation seed (distinct from the F0 study's 20261204 and unchanged
# from Wave H v1; the v2 DGP and grid below supersede the v1 artifact).
SIM_SEED = 20261209

# Main grid definition (v2): the axis is the REALIZED intracluster
# correlation (icc), not the v1 mixing probability whose realized ICC was
# rho^2 (finding F1). The K grid is re-derived at the real per-cluster
# geometry m = 36 (18 views x 2 crops; findings F2/F3) and extends down to
# the fail-closed floor min_clusters = 8 because the corrected geometry
# collapses the cluster requirement far below the v1 m = 6 estimate.
# DISCLOSED TRIM (runtime bound): the icc axis is {0.0, 0.25, 0.5} —
# spanning independent units through the plausible same-image-view range;
# v1's highest-dependence scenario (realized ICC ~= 0.64 at label 0.8) is
# bracketed by icc = 0.5 plus the K sensitivity column, and the proposal
# text states the extrapolation explicitly rather than simulating it.
GRID_DELTAS = (-0.1, 0.0, 0.1, 0.2, 0.3)
GRID_ICCS = (0.0, 0.25, 0.5)
GRID_CLUSTER_COUNTS = (8, 12, 18, 24, 36, 72)
MEMBERS_PER_CLUSTER = 36  # real block: 18 transformation views x 2 crops
DATASETS_PER_CELL = 200

# Disclosed deviation (as in the F0 study): the grid uses 1000 bootstrap
# resamples; confirmation cells use the full preregistered 10000.
GRID_BOOTSTRAP_RESAMPLES = 1000

# Members-per-cluster sweep: how fast does within-cluster replication
# saturate at a realistic cluster count?
SWEEP_DELTA = 0.2
SWEEP_ICC = 0.25
SWEEP_CLUSTER_COUNT = 18
SWEEP_MEMBER_COUNTS = (2, 6, 18, 36)

# Confirmation block at the full preregistered resample count: the cells of
# the grid that govern the minimum-cluster-count proposal — the smallest
# simulated K meeting the P(SUCCESS) >= 0.8 rule at (Delta = +0.2,
# icc = 0.25) and its next-lower neighbor, which must be shown to fail.
CONFIRMATION_DELTAS = (0.2,)
CONFIRMATION_ICCS = (0.25,)
CONFIRMATION_CLUSTER_COUNTS = (36, 72)

BASE_RATE = 0.5
DECISIONS = ("success", "null", "negative", "inconclusive")


def joint_probabilities(true_delta: float) -> tuple[float, float, float, float]:
    """F0 ``symmetric`` joint model at p_M = 0.5.

    Returns (p_both, p_m_only, p_c_only, p_neither) with
    p_m_only - p_c_only = true_delta exactly. Raises ValueError for an
    out-of-range or infeasible Delta.
    """
    if not isinstance(true_delta, (int, float)) or isinstance(true_delta, bool):
        raise ValueError(f"true_delta must be a real number in [-1, 1]; got {true_delta!r}")
    if not -1.0 <= true_delta <= 1.0:
        raise ValueError(f"true_delta must be in [-1, 1]; got {true_delta!r}")
    rate_m = BASE_RATE
    rate_c = rate_m - true_delta
    if not 0.0 <= rate_c <= 1.0:
        raise ValueError(
            f"infeasible cell: rate_c = {rate_c} outside [0, 1] for true_delta={true_delta!r}"
        )
    p_both = rate_m * rate_c
    p_m_only = rate_m * (1.0 - rate_c)
    p_c_only = (1.0 - rate_m) * rate_c
    p_neither = 1.0 - p_both - p_m_only - p_c_only
    return p_both, p_m_only, p_c_only, p_neither


def _validate_rho(rho: float) -> float:
    if not isinstance(rho, (int, float)) or isinstance(rho, bool):
        raise ValueError(f"rho must be a real number in [0, 1]; got {rho!r}")
    if not 0.0 <= rho <= 1.0:
        raise ValueError(f"rho must be in [0, 1]; got {rho!r}")
    return float(rho)


def _validate_count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int; got {value!r}")
    if value < 1:
        raise ValueError(f"{name} must be >= 1; got {value!r}")
    return value


def _hash_uniform(sim_seed: int, cell_id: str, dataset: int, draw: str) -> float:
    """Deterministic uniform in [0, 1) from SHA-256 (no random module state)."""
    digest = hashlib.sha256(
        f"design-analysis-d20005-cluster|{sim_seed}|{cell_id}|{dataset}|{draw}".encode("ascii")
    ).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _joint_state(u: float, cuts: tuple[float, float, float]) -> tuple[bool, bool]:
    """Map a uniform to a paired outcome under the cell's joint model."""
    cut_both, cut_m, cut_c = cuts
    if u < cut_both:
        return True, True
    if u < cut_m:
        return True, False
    if u < cut_c:
        return False, True
    return False, False


def draw_clustered_dataset(
    true_delta: float,
    icc: float,
    n_clusters: int,
    members_per_cluster: int,
    dataset_index: int,
    sim_seed: int = SIM_SEED,
) -> dict:
    """Draw one clustered synthetic paired dataset.

    Returns ``{cluster_id: {member_id: (arm_m_detected, arm_c_detected)}}``.
    ``icc`` is the TARGET realized intracluster correlation (finding F1
    correction): member j of cluster k uses the cluster-shared uniform U_k
    with probability sqrt(icc) (mixture coin C_kj), else its private uniform
    V_kj, so two members share their draw with pairwise probability icc and
    the realized pairwise correlation of member deltas is ~= icc.
    """
    _validate_rho(icc)
    _validate_count(n_clusters, "cluster count")
    _validate_count(members_per_cluster, "members per cluster")
    model = joint_probabilities(true_delta)
    cuts = (model[0], model[0] + model[1], model[0] + model[1] + model[2])
    mixture = math.sqrt(icc)  # pairwise sharing = mixture^2 = icc (F1 fix)
    cell_id = f"v2|{true_delta!r}|{icc!r}|{n_clusters}|{members_per_cluster}"
    dataset: dict[str, dict[str, tuple[bool, bool]]] = {}
    for k in range(n_clusters):
        u_cluster = _hash_uniform(sim_seed, cell_id, dataset_index, f"U|{k}")
        members: dict[str, tuple[bool, bool]] = {}
        for j in range(members_per_cluster):
            coin = _hash_uniform(sim_seed, cell_id, dataset_index, f"C|{k}|{j}")
            if coin < mixture:
                u = u_cluster
            else:
                u = _hash_uniform(sim_seed, cell_id, dataset_index, f"V|{k}|{j}")
            members[f"member{j:03d}"] = _joint_state(u, cuts)
        dataset[f"cluster{k:04d}"] = members
    return dataset


def _classify_both_paths(dataset: dict, resamples: int) -> dict:
    """Run the cluster path and the (equivalent) unit path on one dataset."""
    cluster_stats = cluster_paired_arm_statistics(
        dataset, bootstrap_resamples=resamples, min_clusters=DEFAULT_MIN_CLUSTERS
    )
    singleton_dataset = {
        f"{cluster_id}|{member_id}": {member_id: outcome}
        for cluster_id, members in dataset.items()
        for member_id, outcome in members.items()
    }
    unit_stats = cluster_paired_arm_statistics(
        singleton_dataset, bootstrap_resamples=resamples, min_clusters=DEFAULT_MIN_CLUSTERS
    )
    return {"cluster": cluster_stats, "unit": unit_stats}


def _empty_cell_result(true_delta, icc, n_clusters, members, datasets, resamples) -> dict:
    return {
        "analyses": {
            path: {
                "coverage": 0.0,
                "mean_interval_width": 0.0,
                "p_inconclusive": 0.0,
                "p_negative": 0.0,
                "p_null": 0.0,
                "p_success": 0.0,
            }
            for path in ("cluster", "unit")
        },
        "datasets": datasets,
        "bootstrap_resamples": resamples,
        "icc": icc,
        "mean_estimated_icc": None,
        "members_per_cluster": members,
        "n_clusters": n_clusters,
        "true_delta": true_delta,
    }


def simulate_cell(
    true_delta: float,
    icc: float,
    n_clusters: int,
    members_per_cluster: int,
    *,
    datasets: int | None = None,
    resamples: int | None = None,
    sim_seed: int = SIM_SEED,
) -> dict:
    """Simulate one grid cell; return per-path OC metrics (canonical dict).

    ``icc`` is the target (labeled) intracluster correlation. The result
    includes ``mean_estimated_icc``: the mean ANOVA intracluster-rho estimate
    of the drawn datasets (finding F1 disclosure — the realized ICC of the
    corrected DGP is reported, not assumed).
    """
    datasets = DATASETS_PER_CELL if datasets is None else datasets
    resamples = GRID_BOOTSTRAP_RESAMPLES if resamples is None else resamples
    joint_probabilities(true_delta)  # validate feasibility
    _validate_rho(icc)
    _validate_count(n_clusters, "cluster count")
    _validate_count(members_per_cluster, "members per cluster")
    if datasets < 1:
        raise ValueError(f"datasets per cell must be >= 1; got {datasets!r}")
    if resamples < 100:
        raise ValueError(f"bootstrap requires at least 100 resamples; got {resamples!r}")
    result = _empty_cell_result(
        true_delta, icc, n_clusters, members_per_cluster, datasets, resamples
    )
    width_sum = {"cluster": 0.0, "unit": 0.0}
    covered = {"cluster": 0, "unit": 0}
    tallies = {path: {decision: 0 for decision in DECISIONS} for path in ("cluster", "unit")}
    icc_sum = 0.0
    icc_count = 0
    for dataset_index in range(datasets):
        dataset = draw_clustered_dataset(
            true_delta, icc, n_clusters, members_per_cluster, dataset_index, sim_seed
        )
        rho_hat, _, _ = intracluster_diagnostics(_validated_clusters(dataset))
        if rho_hat is not None:
            icc_sum += rho_hat
            icc_count += 1
        both = _classify_both_paths(dataset, resamples)
        for path in ("cluster", "unit"):
            stats = both[path]
            tallies[path][stats.decision] += 1
            width_sum[path] += stats.interval_width
            lo, hi = stats.risk_difference_interval
            if lo <= true_delta <= hi:
                covered[path] += 1
    for path in ("cluster", "unit"):
        block = result["analyses"][path]
        block["coverage"] = round(covered[path] / datasets, 6)
        block["mean_interval_width"] = round(width_sum[path] / datasets, 6)
        for decision in DECISIONS:
            block[f"p_{decision}"] = round(tallies[path][decision] / datasets, 6)
    if icc_count:
        result["mean_estimated_icc"] = round(icc_sum / icc_count, 6)
    return result


def _cell_spec_list() -> tuple[list[tuple], list[tuple], list[tuple]]:
    """(grid_specs, sweep_specs, confirmation_specs) as (delta, icc, K, m, resamples)."""
    grid_specs = [
        (delta, icc, n_clusters, MEMBERS_PER_CLUSTER, GRID_BOOTSTRAP_RESAMPLES)
        for delta in GRID_DELTAS
        for icc in GRID_ICCS
        for n_clusters in GRID_CLUSTER_COUNTS
    ]
    sweep_specs = [
        (SWEEP_DELTA, SWEEP_ICC, SWEEP_CLUSTER_COUNT, members, GRID_BOOTSTRAP_RESAMPLES)
        for members in SWEEP_MEMBER_COUNTS
    ]
    confirmation_specs = [
        (delta, icc, n_clusters, MEMBERS_PER_CLUSTER, DEFAULT_BOOTSTRAP_RESAMPLES)
        for delta in CONFIRMATION_DELTAS
        for icc in CONFIRMATION_ICCS
        for n_clusters in CONFIRMATION_CLUSTER_COUNTS
    ]
    return grid_specs, sweep_specs, confirmation_specs


def _simulate_cell_worker(spec: tuple) -> dict:
    true_delta, icc, n_clusters, members, resamples = spec
    try:
        return simulate_cell(true_delta, icc, n_clusters, members, resamples=resamples)
    except ValueError as exc:
        return {
            "excluded": True,
            "icc": icc,
            "members_per_cluster": members,
            "n_clusters": n_clusters,
            "reason": str(exc),
            "true_delta": true_delta,
        }


def _run_specs(specs: list[tuple], workers: int) -> tuple[list[dict], list[dict]]:
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
    """Run the main grid, the members sweep, and the 10000-resample confirmation.

    Determinism is unaffected by ``workers``: every cell is a pure function of
    the fixed sim_seed and results are reassembled in canonical grid order.
    """
    grid_specs, sweep_specs, confirmation_specs = _cell_spec_list()
    cells, excluded = _run_specs(grid_specs, workers)
    sweep, sweep_excluded = _run_specs(sweep_specs, workers)
    confirmation, confirmation_excluded = _run_specs(confirmation_specs, workers)
    excluded.extend(sweep_excluded)
    excluded.extend(confirmation_excluded)
    return {
        "bootstrap_seed": DEFAULT_BOOTSTRAP_SEED,
        "cells": cells,
        "confirmation_cells": confirmation,
        "datasets_per_cell": DATASETS_PER_CELL,
        "excluded_cells": excluded,
        "generation": "RAC-PER-D2-0005",
        "grid_bootstrap_resamples": GRID_BOOTSTRAP_RESAMPLES,
        "grid_cluster_counts": list(GRID_CLUSTER_COUNTS),
        "grid_deltas": list(GRID_DELTAS),
        "grid_iccs": list(GRID_ICCS),
        "inconclusive_width_max": INCONCLUSIVE_WIDTH_MAX,
        "members_per_cluster": MEMBERS_PER_CLUSTER,
        "members_sweep": {
            "cluster_count": SWEEP_CLUSTER_COUNT,
            "cells": sweep,
            "icc": SWEEP_ICC,
            "member_counts": list(SWEEP_MEMBER_COUNTS),
            "true_delta": SWEEP_DELTA,
        },
        "min_clusters": DEFAULT_MIN_CLUSTERS,
        "preregistered_bootstrap_resamples": DEFAULT_BOOTSTRAP_RESAMPLES,
        "schema_version": SCHEMA_VERSION,
        "sim_seed": SIM_SEED,
        "z": DEFAULT_Z,
    }


def to_canonical_json(payload: dict) -> str:
    """Canonical frozen JSON: sort_keys, compact separators, trailing newline."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def _cell_row(cell: dict) -> str:
    cluster = cell["analyses"]["cluster"]
    unit = cell["analyses"]["unit"]
    est = cell.get("mean_estimated_icc")
    est_str = "NA" if est is None else f"{est:.3f}"
    return (
        f"| {cell['true_delta']:+.1f} | {cell['icc']:.2f} | {est_str} "
        f"| {cell['n_clusters']} "
        f"| {cell['members_per_cluster']} "
        f"| {cluster['p_success']:.3f} | {cluster['p_inconclusive']:.3f} "
        f"| {cluster['coverage']:.3f} | {cluster['mean_interval_width']:.3f} "
        f"| {unit['p_success']:.3f} | {unit['p_inconclusive']:.3f} "
        f"| {unit['coverage']:.3f} | {unit['mean_interval_width']:.3f} "
        f"| {cell['bootstrap_resamples']} |"
    )


_TABLE_HEADER = (
    "| Delta_true | ICC (labeled) | ICC (realized, mean est.) | K clusters | m members "
    "| CLUSTER P(SUCCESS) | CLUSTER P(INCONCL) "
    "| CLUSTER coverage | CLUSTER width | UNIT P(SUCCESS) | UNIT P(INCONCL) | UNIT coverage "
    "| UNIT width | bootstrap R |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
)


def render_markdown_table(payload: dict) -> str:
    """Render the results grid as markdown tables."""
    lines = [
        "Cluster-robust (proposed) vs unit-level (frozen preregistered) analysis on the",
        "SAME clustered synthetic datasets. Coverage = fraction of CIs containing Delta_true.",
        "",
        "## Main grid",
        "",
        *_TABLE_HEADER,
    ]
    for cell in payload["cells"]:
        lines.append(_cell_row(cell))
    lines.append("")
    lines.append(
        "## Members-per-cluster sweep "
        f"(Delta_true = {payload['members_sweep']['true_delta']:+.1f}, "
        f"icc = {payload['members_sweep']['icc']:.2f}, "
        f"K = {payload['members_sweep']['cluster_count']})"
    )
    lines.append("")
    lines.extend(_TABLE_HEADER)
    for cell in payload["members_sweep"]["cells"]:
        lines.append(_cell_row(cell))
    lines.append("")
    lines.append(
        "## Confirmation block (full preregistered bootstrap_resamples = "
        f"{payload['preregistered_bootstrap_resamples']})"
    )
    lines.append("")
    lines.extend(_TABLE_HEADER)
    for cell in payload["confirmation_cells"]:
        lines.append(_cell_row(cell))
    if payload["excluded_cells"]:
        lines.append("")
        lines.append("Infeasible cells (excluded and disclosed):")
        lines.append("")
        for cell in payload["excluded_cells"]:
            lines.append(
                f"- Delta_true = {cell['true_delta']:+.1f}, icc = {cell['icc']:.2f}, "
                f"K = {cell['n_clusters']}, m = {cell['members_per_cluster']}: {cell['reason']}"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-arming cluster-aware design-analysis simulation for D2-0005 "
        "(capability characterization only; NOT tuning)."
    )
    parser.add_argument(
        "--output", default="artifacts/design_analysis_d20005_cluster/results.json"
    )
    parser.add_argument(
        "--markdown", default="artifacts/design_analysis_d20005_cluster/results.md"
    )
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

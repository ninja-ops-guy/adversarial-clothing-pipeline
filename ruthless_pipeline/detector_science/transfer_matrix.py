"""Cross-family transfer analysis over per-model scalar outcomes.

All computations are deterministic (sorted iteration, fixed tie-breaks).
Empty or insufficient data fails closed with ``InsufficientDataError``;
missing cells are reported as None — never interpolated or back-filled.

Record format (dict):
    source_family : str   family of the surrogate/source model
    target_family : str   family of the evaluated target model
    model_id      : str   target model (used by LOFO / diversity reports)
    family        : str   family of ``model_id`` (LOFO / diversity reports)
    condition_id  : str   evaluation condition (diversity report alignment)
    outcome       : float scalar outcome in [0, 1] (e.g. transfer success)

``build_transfer_matrix`` uses (source_family, target_family, outcome);
``leave_one_family_out`` uses (model_id, family, outcome);
``surrogate_diversity_report`` uses (model_id, family, condition_id, outcome).
"""

from __future__ import annotations

from typing import Iterable, Optional

import numpy as np


class InsufficientDataError(ValueError):
    """Raised when a computation lacks sufficient data (fail-closed)."""


def _records_list(records: Iterable[dict]) -> list:
    rows = list(records)
    if not rows:
        raise InsufficientDataError("no records supplied")
    return rows


def _require(row: dict, keys) -> None:
    missing = [k for k in keys if k not in row]
    if missing:
        raise InsufficientDataError(f"record missing keys {missing}: {row!r}")


def build_transfer_matrix(records: Iterable[dict]) -> dict:
    """Per-(source_family, target_family) transfer success matrix.

    Returns sorted family axes and a nested mapping of cell statistics.
    Cells without observations are None (never interpolated).
    """
    rows = _records_list(records)
    for row in rows:
        _require(row, ("source_family", "target_family", "outcome"))
    cells: dict[tuple, list] = {}
    for row in rows:
        key = (row["source_family"], row["target_family"])
        cells.setdefault(key, []).append(float(row["outcome"]))
    families = sorted({f for pair in cells for f in pair})
    matrix = {}
    for src in families:
        matrix[src] = {}
        for tgt in families:
            values = cells.get((src, tgt))
            if values is None:
                matrix[src][tgt] = None
            else:
                arr = np.asarray(sorted(values), dtype=float)  # sorted: order-independent
                matrix[src][tgt] = {
                    "n": int(arr.size),
                    "mean": float(arr.mean()),
                    "std": float(arr.std()),
                }
    return {"families": families, "matrix": matrix}


def leave_one_family_out(records: Iterable[dict]) -> dict:
    """Degradation summary when each family is held out in turn.

    For each held-out family F: degradation = mean(outcome | family != F)
    - mean(outcome | family == F). Positive values mean the held-out family
    performs worse than the remaining pool.
    """
    rows = _records_list(records)
    for row in rows:
        _require(row, ("model_id", "family", "outcome"))
    families = sorted({row["family"] for row in rows})
    if len(families) < 2:
        raise InsufficientDataError(
            "leave-one-family-out requires records from at least 2 families"
        )
    per_family = {}
    for held_out in families:
        in_vals = sorted(float(r["outcome"]) for r in rows if r["family"] == held_out)
        out_vals = sorted(float(r["outcome"]) for r in rows if r["family"] != held_out)
        if not in_vals or not out_vals:
            raise InsufficientDataError(
                f"family {held_out!r} lacks in/out observations for LOFO"
            )
        in_mean = float(np.asarray(in_vals).mean())
        out_mean = float(np.asarray(out_vals).mean())
        per_family[held_out] = {
            "held_out_family": held_out,
            "n_held_out": len(in_vals),
            "n_remaining": len(out_vals),
            "held_out_mean": in_mean,
            "remaining_mean": out_mean,
            "degradation": out_mean - in_mean,
        }
    return {"families": families, "held_out": per_family}


def _kendall_tau(x: np.ndarray, y: np.ndarray) -> float:
    """Kendall tau (tau-a style) via numpy; deterministic, ties contribute 0."""
    n = x.size
    if n < 2:
        raise InsufficientDataError("kendall tau requires at least 2 paired observations")
    dx = np.sign(x[:, None] - x[None, :])
    dy = np.sign(y[:, None] - y[None, :])
    iu = np.triu_indices(n, k=1)
    concordant_discordant = (dx[iu] * dy[iu]).sum()
    return float(concordant_discordant) / (n * (n - 1) / 2.0)


def surrogate_diversity_report(
    records: Iterable[dict],
    *,
    min_shared_conditions: int = 2,
) -> dict:
    """Per-family dispersion, pairwise Kendall-tau rank correlation, and
    top-disagreement model pairs over shared conditions.

    Deterministic: families, models, and pairs are sorted; equal disagreement
    scores tie-break on (model_a, model_b). Fail-closed when fewer than two
    models or no pair shares enough conditions.
    """
    rows = _records_list(records)
    for row in rows:
        _require(row, ("model_id", "family", "condition_id", "outcome"))

    by_model: dict[str, dict] = {}
    for row in rows:
        entry = by_model.setdefault(row["model_id"], {"family": row["family"], "outcomes": {}})
        entry["outcomes"][row["condition_id"]] = float(row["outcome"])
    models = sorted(by_model)
    if len(models) < 2:
        raise InsufficientDataError("diversity report requires at least 2 models")

    families = sorted({by_model[m]["family"] for m in models})
    per_family = {}
    for fam in families:
        vals = np.asarray(
            sorted(
                v
                for m in models
                if by_model[m]["family"] == fam
                for v in by_model[m]["outcomes"].values()
            ),
            dtype=float,
        )
        per_family[fam] = {
            "n_models": sum(1 for m in models if by_model[m]["family"] == fam),
            "n_observations": int(vals.size),
            "mean": float(vals.mean()),
            "std": float(vals.std()),
            "min": float(vals.min()),
            "max": float(vals.max()),
        }

    pairs = []
    for i, a in enumerate(models):
        for b in models[i + 1 :]:
            shared = sorted(set(by_model[a]["outcomes"]) & set(by_model[b]["outcomes"]))
            if len(shared) < min_shared_conditions:
                tau = None
                mad = None
            else:
                xa = np.asarray([by_model[a]["outcomes"][c] for c in shared], dtype=float)
                xb = np.asarray([by_model[b]["outcomes"][c] for c in shared], dtype=float)
                tau = _kendall_tau(xa, xb)
                mad = float(np.abs(xa - xb).mean())
            pairs.append(
                {
                    "model_a": a,
                    "model_b": b,
                    "family_a": by_model[a]["family"],
                    "family_b": by_model[b]["family"],
                    "n_shared_conditions": len(shared),
                    "kendall_tau": tau,
                    "mean_abs_difference": mad,
                }
            )
    comparable = [p for p in pairs if p["mean_abs_difference"] is not None]
    if not comparable:
        raise InsufficientDataError(
            "no model pair shares enough conditions for rank correlation"
        )
    top_disagreement = sorted(
        comparable,
        key=lambda p: (-p["mean_abs_difference"], p["model_a"], p["model_b"]),
    )
    return {
        "families": families,
        "models": models,
        "per_family_dispersion": per_family,
        "pairwise_rank_correlation": sorted(
            pairs, key=lambda p: (p["model_a"], p["model_b"])
        ),
        "top_disagreement_pairs": top_disagreement,
    }

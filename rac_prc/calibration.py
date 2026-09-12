from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy.stats import rankdata


def _finite_pair_arrays(predicted: Sequence[float], observed: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(predicted, dtype=float)
    y = np.asarray(observed, dtype=float)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("predicted and observed must be one-dimensional arrays of equal length")
    if len(x) == 0 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("calibration arrays must be non-empty and finite")
    return x, y


def calibration_metrics(predicted: Sequence[float], observed: Sequence[float]) -> dict[str, float | None]:
    x, y = _finite_pair_arrays(predicted, observed)
    residual = y - x
    metrics: dict[str, float | None] = {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(math.sqrt(float(np.mean(residual ** 2)))),
        "spearman_rho": None,
        "calibration_slope": None,
        "calibration_intercept": None,
    }
    if len(x) >= 2 and np.std(rankdata(x)) > 0 and np.std(rankdata(y)) > 0:
        metrics["spearman_rho"] = float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])
    if len(x) >= 2 and np.var(x) > 0:
        slope, intercept = np.polyfit(x, y, 1)
        metrics["calibration_slope"] = float(slope)
        metrics["calibration_intercept"] = float(intercept)
    return metrics

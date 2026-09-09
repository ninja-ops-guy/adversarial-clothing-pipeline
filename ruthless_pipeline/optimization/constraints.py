"""Constraint primitives: box, simplex, and style-family membership hooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Mapping

import numpy as np

DEFAULT_PROFILE_PATH = (
    Path(__file__).resolve().parents[2] / "design_profiles" / "ruthless_reference_v1.json"
)


class BoxConstraint:
    """Axis-aligned box [lower, upper] with elementwise projection."""

    def __init__(self, lower: np.ndarray | float, upper: np.ndarray | float):
        self.lower = np.asarray(lower, dtype=float)
        self.upper = np.asarray(upper, dtype=float)
        if np.any(self.lower > self.upper):
            raise ValueError("box lower bound exceeds upper bound")

    def project(self, x: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(x, dtype=float), self.lower, self.upper)

    def contains(self, x: np.ndarray, tol: float = 1e-12) -> bool:
        x = np.asarray(x, dtype=float)
        return bool(np.all(x >= self.lower - tol) and np.all(x <= self.upper + tol))


class SimplexConstraint:
    """Probability simplex {x >= 0, sum(x) = total} with Euclidean projection."""

    def __init__(self, dim: int, total: float = 1.0):
        if dim < 1 or total <= 0:
            raise ValueError("dim must be >= 1 and total > 0")
        self.dim = int(dim)
        self.total = float(total)

    def project(self, x: np.ndarray) -> np.ndarray:
        v = np.asarray(x, dtype=float).ravel()
        if v.size != self.dim:
            raise ValueError(f"expected dimension {self.dim}, got {v.size}")
        # Euclidean projection onto the simplex (Duchi et al. 2008).
        u = np.sort(v)[::-1]
        css = np.cumsum(u) - self.total
        rho = np.nonzero(u - css / np.arange(1, self.dim + 1) > 0)[0]
        if rho.size == 0:
            theta = 0.0
        else:
            theta = css[rho[-1]] / float(rho[-1] + 1)
        return np.maximum(v - theta, 0.0)

    def contains(self, x: np.ndarray, tol: float = 1e-9) -> bool:
        x = np.asarray(x, dtype=float)
        return bool(np.all(x >= -tol) and abs(float(np.sum(x)) - self.total) <= tol)


def load_style_profile(path: str | Path | None = None) -> dict:
    """Read-only load of a design profile (never written by this layer)."""
    with open(path or DEFAULT_PROFILE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def style_family_membership(
    features: Mapping,
    family: str,
    profile: Mapping | None = None,
    *,
    motif_weight: float = 0.5,
    threshold: float = 0.5,
) -> bool:
    """Predicate hook: does a candidate feature dict belong to a style family?

    Deterministic rule: membership holds iff the mean of (family motif
    overlap fraction, product match indicator) meets ``threshold``. The
    profile is read at runtime and never modified.
    """
    profile = profile if profile is not None else load_style_profile()
    families = profile.get("families", {})
    if family not in families:
        raise ValueError(f"unknown style family {family!r}")
    spec = families[family]
    candidate_motifs = set(features.get("motifs", []) or [])
    family_motifs = set(spec.get("motifs", []) or [])
    overlap = (
        len(candidate_motifs & family_motifs) / len(family_motifs) if family_motifs else 0.0
    )
    product = features.get("product")
    product_match = 1.0 if product in (spec.get("products", []) or []) else 0.0
    score = motif_weight * overlap + (1.0 - motif_weight) * product_match
    return bool(score >= threshold)


# Hook type for callers that want to plug a custom membership predicate.
StyleMembershipHook = Callable[[Mapping, str], bool]

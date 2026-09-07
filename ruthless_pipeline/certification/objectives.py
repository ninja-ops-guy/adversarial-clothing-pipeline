"""Surrogate-selection objectives for preregistered generation RAC-PER-D2-0005.

This module implements the preregistered Arm C objective from
``docs/PREREGISTRATION_D2-0005.md`` (section 5, "Preregistered precondition
(CVaR implementation)"): CVaR_alpha (expected shortfall) of the per-surrogate
detection rates. For alpha = 0.5 over the 6-model PERSON-SUR-v3 ensemble this
is the average of the worst half, i.e. the 3 highest per-surrogate rates.

Convention (matching the preregistration prose): alpha is the confidence
level of the shortfall — alpha -> 1 approaches the single-worst-surrogate
(minimax) objective and alpha -> 0 collapses to the ensemble mean. The
number of worst surrogates averaged is k = max(1, ceil((1 - alpha) * n)),
so alpha = 0.5 with n = 6 averages exactly the 3 highest rates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _validated_rates(rates) -> list[float]:
    """Return ``rates`` as a list of floats, enforcing non-empty finite values in [0, 1]."""
    values = [float(r) for r in rates]
    if not values:
        raise ValueError("rates must be non-empty")
    for value in values:
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"each rate must be finite and within [0, 1]; got {value!r}")
    return values


def _validate_alpha(alpha: float) -> float:
    alpha = float(alpha)
    if not math.isfinite(alpha) or not 0.0 < alpha <= 1.0:
        raise ValueError(f"alpha must be in (0, 1]; got {alpha!r}")
    return alpha


def cvar_tail_size(n: int, alpha: float) -> int:
    """Worst-k tail size: ``k = max(1, ceil((1 - alpha) * n))``.

    For the preregistered alpha = 0.5 and the 6-surrogate PERSON-SUR-v3
    ensemble this is exactly 3. Odd ensemble sizes follow the same ceil rule
    (n = 1 -> 1, n = 3 -> 2, n = 5 -> 3, n = 7 -> 4 at alpha = 0.5).
    """
    alpha = _validate_alpha(alpha)
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"n must be a positive integer; got {n!r}")
    return max(1, math.ceil((1.0 - alpha) * n))


def worst_tail_members(per_surrogate_rates: dict[str, float], alpha: float) -> tuple[str, ...]:
    """Canonical ids of the worst-k tail (the k highest per-surrogate rates).

    Ordered by rate descending; ties at the tail boundary (and elsewhere) are
    broken deterministically by canonical model id, ascending, so the same
    rate vector always yields the same tail membership regardless of input
    ordering. Note the objective *value* (mean of the worst-k rates) is itself
    tie-insensitive; the deterministic tie-break only pins which ids are
    reported as tail members.
    """
    if not per_surrogate_rates:
        raise ValueError("per_surrogate_rates must be non-empty")
    values = _validated_rates(per_surrogate_rates.values())
    k = cvar_tail_size(len(values), alpha)
    ordered = sorted(per_surrogate_rates.items(), key=lambda kv: (-float(kv[1]), str(kv[0])))
    return tuple(name for name, _ in ordered[:k])


def cvar(rates, alpha: float) -> float:
    """Population expected shortfall (CVaR_alpha) of per-surrogate detection rates.

    Returns the mean of the k highest (worst) rates, where
    ``k = max(1, ceil((1 - alpha) * n))``. For alpha = 0.5 and n = 6 this is the
    preregistered Arm C objective: the average of the 3 highest per-surrogate
    detection rates. alpha = 1.0 yields the single worst (max) rate; small
    alpha approaches the plain mean.

    Raises ValueError if alpha is not in (0, 1], rates is empty, or any rate is
    non-finite or outside [0, 1].
    """
    alpha = _validate_alpha(alpha)
    values = _validated_rates(rates)
    k = cvar_tail_size(len(values), alpha)
    worst = sorted(values, reverse=True)[:k]
    return sum(worst) / len(worst)


def mean_objective(rates) -> float:
    """Ensemble mean of per-surrogate detection rates (the Arm M / D2-0004 objective)."""
    values = _validated_rates(rates)
    return sum(values) / len(values)


@dataclass(frozen=True)
class ObjectiveSpec:
    """Preregistered surrogate-selection objective.

    ``name`` is one of {"mean", "cvar"}; ``alpha`` is required iff
    ``name == "cvar"`` and must be omitted otherwise.
    """

    name: str
    alpha: float | None = None

    def validate(self) -> None:
        if self.name not in {"mean", "cvar"}:
            raise ValueError(f"objective name must be one of {{'mean', 'cvar'}}; got {self.name!r}")
        if self.name == "cvar":
            if self.alpha is None:
                raise ValueError("alpha is required when name == 'cvar'")
            _validate_alpha(self.alpha)
        elif self.alpha is not None:
            raise ValueError("alpha must be None when name == 'mean'")

    def objective_key(self, per_surrogate_rates: dict[str, float]) -> float:
        """Objective value over a per-surrogate rate vector (lower is better).

        Dispatches on ``name``: "mean" -> :func:`mean_objective`,
        "cvar" -> :func:`cvar` with ``alpha``. Rates are ordered by surrogate
        id before aggregation so the key is deterministic.
        """
        self.validate()
        if not per_surrogate_rates:
            raise ValueError("per_surrogate_rates must be non-empty")
        rates = [per_surrogate_rates[key] for key in sorted(per_surrogate_rates)]
        if self.name == "cvar":
            return cvar(rates, float(self.alpha))
        return mean_objective(rates)

"""Independent numerical verification utilities for pipeline certification.

These are *generic, pipeline-agnostic* reference checks. They are implemented
independently of the pipeline's own math modules (e.g.
``ruthless_pipeline.certification.objectives``) so that a shared-code bug in
the pipeline cannot simultaneously break the implementation and its check.
Every guard fails closed: on any violation a :class:`VerificationError`
subclass is raised; nothing is silently coerced, clamped, or skipped.

Intended consumers: certification tests today; the optimization engine
(V3/EOT/Pareto/style) math modules later, without modification.

Boundary: these utilities never touch held-out models, D2-0004/D2-0005
selection rules, or measured physical evidence. They operate on caller-
supplied synthetic values only.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

__all__ = [
    "VerificationError",
    "NonFiniteValueError",
    "NondeterminismError",
    "SeedReproducibilityError",
    "DecompositionError",
    "CheckpointIntegrityError",
    "DominanceError",
    "canonical_json",
    "canonical_sha256",
    "checkpoint_sha256",
    "verify_checkpoint_integrity",
    "require_finite",
    "require_rates",
    "mean_reference",
    "cvar_tail_size_reference",
    "cvar_reference",
    "pareto_dominates",
    "pareto_front_indices",
    "verify_objective_decomposition",
    "check_deterministic_rerun",
    "check_seed_reproducibility",
    "check_transformation_seed_reproduction",
]


class VerificationError(Exception):
    """Base class for all fail-closed verification refusals."""


class NonFiniteValueError(VerificationError):
    """A NaN or infinite value reached a numerical boundary."""


class NondeterminismError(VerificationError):
    """A rerun of the same computation produced a different result."""


class SeedReproducibilityError(VerificationError):
    """A seeded computation was not reproducible from its seed."""


class DecompositionError(VerificationError):
    """An objective value did not decompose into its declared components."""


class CheckpointIntegrityError(VerificationError):
    """A checkpoint/artifact hash did not match its pin."""


class DominanceError(VerificationError):
    """Invalid input to a Pareto-dominance computation."""


def canonical_json(payload: Any) -> bytes:
    """Deterministic canonical encoding: sorted keys, fixed separators, UTF-8.

    Floats are rendered by ``json``'s shortest-repr, which is stable across
    CPython versions for IEEE-754 doubles.
    """
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    ).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    """SHA-256 of :func:`canonical_json`."""
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def checkpoint_sha256(path: str | Path) -> str:
    """Streaming SHA-256 of a checkpoint/artifact file."""
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checkpoint_integrity(path: str | Path, expected_sha256: str) -> str:
    """Fail closed unless the file at ``path`` hashes to ``expected_sha256``.

    Returns the actual digest on success. Refuses missing files, malformed
    expected digests, and mismatches — a corrupt checkpoint is never
    silently accepted.
    """
    expected = str(expected_sha256).strip().lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise CheckpointIntegrityError(
            f"expected_sha256 is not a SHA-256 hex digest: {expected_sha256!r}"
        )
    p = Path(path)
    if not p.is_file():
        raise CheckpointIntegrityError(f"checkpoint missing: {p}")
    actual = checkpoint_sha256(p)
    if actual != expected:
        raise CheckpointIntegrityError(
            f"checkpoint hash mismatch for {p}: expected {expected}, got {actual}"
        )
    return actual


def require_finite(values: Iterable[float], *, label: str = "values") -> list[float]:
    """Return ``values`` as floats, rejecting NaN and +/-Inf (fail closed)."""
    out = [float(v) for v in values]
    for index, value in enumerate(out):
        if not math.isfinite(value):
            raise NonFiniteValueError(
                f"{label}[{index}] must be finite; got {value!r}"
            )
    return out


def require_rates(rates: Iterable[float]) -> list[float]:
    """Finite values constrained to [0, 1] (detection-rate domain)."""
    out = require_finite(rates, label="rates")
    if not out:
        raise VerificationError("rates must be non-empty")
    for value in out:
        if not 0.0 <= value <= 1.0:
            raise VerificationError(f"each rate must be within [0, 1]; got {value!r}")
    return out


def mean_reference(rates: Iterable[float]) -> float:
    """Independent reference for the ensemble mean: plain sum / count."""
    values = require_rates(rates)
    return math.fsum(values) / len(values)


def cvar_tail_size_reference(n: int, alpha: float) -> int:
    """Reference worst-k tail size: ``k = max(1, ceil((1 - alpha) * n))``."""
    alpha = float(alpha)
    if not math.isfinite(alpha) or not 0.0 < alpha <= 1.0:
        raise VerificationError(f"alpha must be in (0, 1]; got {alpha!r}")
    if not isinstance(n, int) or n < 1:
        raise VerificationError(f"n must be a positive integer; got {n!r}")
    # Exact integer arithmetic where possible: ceil((1-a)*n) computed via
    # Fraction to avoid floating-point ceil boundary errors (e.g. 0.1*3).
    from fractions import Fraction

    frac = (1 - Fraction(str(alpha))) * n
    k = -(-frac.numerator // frac.denominator)  # ceil
    return max(1, int(k))


def cvar_reference(rates: Iterable[float], alpha: float) -> float:
    """Independent reference for CVaR_alpha (expected shortfall).

    Computed as the *direct sorted-tail mean*: sort a copy of the rates
    descending, take the worst k = max(1, ceil((1 - alpha) * n)), average
    with ``math.fsum``. This deliberately shares no code with the pipeline's
    ``objectives.cvar`` so a bug there cannot hide here.
    """
    values = require_rates(rates)
    k = cvar_tail_size_reference(len(values), alpha)
    tail = sorted(values, reverse=True)[:k]
    return math.fsum(tail) / k


def _as_point(point: Sequence[float], *, label: str) -> tuple[float, ...]:
    values = tuple(float(v) for v in point)
    if not values:
        raise DominanceError(f"{label} must be a non-empty vector")
    for value in values:
        if not math.isfinite(value):
            raise DominanceError(f"{label} must be finite; got {value!r}")
    return values


def pareto_dominates(
    a: Sequence[float], b: Sequence[float], *, senses: Sequence[str] | None = None
) -> bool:
    """Reference Pareto dominance: ``a`` dominates ``b`` iff ``a`` is no worse
    on every objective and strictly better on at least one.

    ``senses`` is one of "min"/"max" per objective (default: all "min").
    """
    pa = _as_point(a, label="a")
    pb = _as_point(b, label="b")
    if len(pa) != len(pb):
        raise DominanceError("points must have the same dimension")
    if senses is None:
        senses = tuple("min" for _ in pa)
    senses = tuple(senses)
    if len(senses) != len(pa) or any(s not in {"min", "max"} for s in senses):
        raise DominanceError("senses must be 'min'/'max' per objective")
    better_or_equal = True
    strictly_better = False
    for x, y, sense in zip(pa, pb, senses):
        if sense == "min":
            if x > y:
                better_or_equal = False
            elif x < y:
                strictly_better = True
        else:
            if x < y:
                better_or_equal = False
            elif x > y:
                strictly_better = True
    return better_or_equal and strictly_better


def pareto_front_indices(
    points: Sequence[Sequence[float]], *, senses: Sequence[str] | None = None
) -> tuple[int, ...]:
    """Reference non-dominated set: indices of points dominated by no other."""
    pts = [_as_point(p, label=f"points[{i}]") for i, p in enumerate(points)]
    front: list[int] = []
    for i, p in enumerate(pts):
        if any(
            j != i and pareto_dominates(q, p, senses=senses)
            for j, q in enumerate(pts)
        ):
            continue
        front.append(i)
    return tuple(front)


def verify_objective_decomposition(
    total: float,
    components: Iterable[float],
    *,
    weights: Iterable[float] | None = None,
    tolerance: float = 1e-12,
) -> float:
    """Fail closed unless ``total`` equals the (optionally weighted) sum of
    ``components`` within absolute ``tolerance``.

    Catches objectives whose reported aggregate silently diverges from the
    sum of their declared sub-terms. Returns the residual on success.
    """
    total = float(total)
    if not math.isfinite(total):
        raise DecompositionError(f"total must be finite; got {total!r}")
    parts = require_finite(components, label="components")
    if not parts:
        raise DecompositionError("components must be non-empty")
    if weights is None:
        expected = math.fsum(parts)
    else:
        ws = require_finite(weights, label="weights")
        if len(ws) != len(parts):
            raise DecompositionError("weights and components must have equal length")
        expected = math.fsum(w * c for w, c in zip(ws, parts))
    residual = abs(total - expected)
    if not residual <= float(tolerance):
        raise DecompositionError(
            f"objective decomposition mismatch: total={total!r}, "
            f"sum(components)={expected!r}, residual={residual!r} > {tolerance!r}"
        )
    return residual


def _freeze(result: Any) -> Any:
    """Convert a result into a canonical, comparable structure.

    torch tensors and numpy arrays are reduced to (shape, dtype, bytes);
    mappings/sequences are recursed; anything else is passed through ``repr``
    inside the canonical JSON so nondeterminism in any field is caught.
    """
    if hasattr(result, "detach") and hasattr(result, "cpu"):  # torch.Tensor
        t = result.detach().cpu().contiguous()
        return {
            "__tensor__": True,
            "shape": list(t.shape),
            "dtype": str(t.dtype),
            "sha256": hashlib.sha256(t.numpy().tobytes()).hexdigest(),
        }
    if hasattr(result, "tobytes") and hasattr(result, "shape"):  # numpy array
        return {
            "__ndarray__": True,
            "shape": list(result.shape),
            "dtype": str(result.dtype),
            "sha256": hashlib.sha256(result.tobytes()).hexdigest(),
        }
    if isinstance(result, dict):
        return {str(k): _freeze(v) for k, v in result.items()}
    if isinstance(result, (list, tuple)):
        return [_freeze(v) for v in result]
    if isinstance(result, float):
        if not math.isfinite(result):
            raise NonFiniteValueError(f"non-finite float in result: {result!r}")
        return result
    return result


def check_deterministic_rerun(
    fn: Callable[..., Any],
    *args: Any,
    runs: int = 2,
    **kwargs: Any,
) -> Any:
    """Call ``fn(*args, **kwargs)`` ``runs`` times; fail closed unless every
    run produces a canonically identical result. Returns the first result.
    """
    if runs < 2:
        raise VerificationError("runs must be >= 2 to detect nondeterminism")
    first = fn(*args, **kwargs)
    first_frozen = canonical_json(_freeze(first))
    for run in range(1, runs):
        again = fn(*args, **kwargs)
        if canonical_json(_freeze(again)) != first_frozen:
            raise NondeterminismError(
                f"{getattr(fn, '__name__', fn)!r} returned a different result on "
                f"rerun {run} of {runs}"
            )
    return first


def check_seed_reproducibility(
    fn: Callable[[int], Any],
    seed: int,
    *,
    runs: int = 2,
    other_seed: int | None = None,
) -> Any:
    """Fail closed unless ``fn(seed)`` is reproducible across ``runs`` calls.

    If ``other_seed`` is given, additionally require ``fn(other_seed)`` to
    differ from ``fn(seed)`` — catching implementations that silently ignore
    the seed. Returns ``fn(seed)``.
    """
    result = check_deterministic_rerun(fn, int(seed), runs=runs)
    if other_seed is not None:
        other = check_deterministic_rerun(fn, int(other_seed), runs=2)
        if canonical_json(_freeze(other)) == canonical_json(_freeze(result)):
            raise SeedReproducibilityError(
                f"seed {other_seed} produced output identical to seed {seed}; "
                "the seed is not driving the computation"
            )
    return result


def check_transformation_seed_reproduction(
    sampler_factory: Callable[[int], Callable[[int], Any]],
    seed: int,
    sample_index: int,
    *,
    runs: int = 2,
) -> Any:
    """Fail closed unless a transformation sample is reproducible from
    ``(seed, sample_index)`` alone.

    ``sampler_factory(seed)`` must return a *fresh* sampler mapping
    ``sample_index -> value``. The check requires:

    * rerun reproducibility: two fresh samplers from the same seed return a
      canonically identical value for ``sample_index`` (``runs`` repetitions);
    * order independence: a fresh sampler that has first drawn neighbouring
      indices still returns the identical value for ``sample_index`` — i.e.
      the sample is a pure function of ``(seed, sample_index)``, as required
      by the frozen (distribution, seed, index) -> sample contract.

    Returns the reproduced sample value.
    """
    seed = int(seed)
    sample_index = int(sample_index)

    def fresh_draw(index: int, *, after_neighbours: bool) -> Any:
        sampler = sampler_factory(seed)
        if after_neighbours:
            for neighbour in (sample_index + 1, max(0, sample_index - 1)):
                if neighbour != index:
                    sampler(neighbour)
        return sampler(index)

    direct = check_deterministic_rerun(
        lambda: fresh_draw(sample_index, after_neighbours=False), runs=runs
    )
    after = fresh_draw(sample_index, after_neighbours=True)
    if canonical_json(_freeze(after)) != canonical_json(_freeze(direct)):
        raise SeedReproducibilityError(
            f"sample (seed={seed}, index={sample_index}) changed after drawing "
            "other indices; samples are not reproducible from (seed, index) alone"
        )
    return direct

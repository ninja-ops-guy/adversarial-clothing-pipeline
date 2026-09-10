"""Distribution diagnostics for Governance Pass 6 sampler calibration.

These diagnostics operate on the full semantic projection. Independent-support
variables may accelerate an external sampler, but never redefine the population
tested here.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .sampling import (
    CalibrationMetrics,
    SamplingGovernanceError,
    SamplingRequest,
    SamplingResult,
    sample_key,
    validate_projection_sample,
)


def _empirical_distribution(
    samples: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    if not samples:
        raise SamplingGovernanceError("distribution diagnostics require samples")
    counts: dict[str, int] = {}
    for sample in samples:
        key = sample_key(sample)
        counts[key] = counts.get(key, 0) + 1
    total = float(len(samples))
    return {key: count / total for key, count in counts.items()}


def _total_variation(
    left: Mapping[str, float],
    right: Mapping[str, float],
) -> float:
    keys = set(left) | set(right)
    return 0.5 * sum(
        abs(left.get(key, 0.0) - right.get(key, 0.0))
        for key in keys
    )


def _category_distribution(
    samples: Sequence[Mapping[str, Any]],
    variables: Sequence[str],
) -> dict[str, float]:
    counts: dict[str, int] = {}
    for sample in samples:
        projection = {name: sample[name] for name in variables}
        key = sample_key(projection)
        counts[key] = counts.get(key, 0) + 1
    total = float(len(samples))
    return {key: count / total for key, count in counts.items()}


def _maximum_category_error(
    observed: Mapping[str, float],
    target: Mapping[str, float],
) -> float:
    return max(
        (
            abs(observed.get(key, 0.0) - target.get(key, 0.0))
            for key in set(observed) | set(target)
        ),
        default=0.0,
    )


def exact_distribution_diagnostics(
    request: SamplingRequest,
    result: SamplingResult,
    exact_population: Sequence[Mapping[str, Any]],
) -> CalibrationMetrics:
    """Compare a sampled cohort against a known exact projected population."""
    request.validate()
    result.validate(request)
    if not exact_population:
        raise SamplingGovernanceError("exact_population cannot be empty")

    population: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for index, sample in enumerate(exact_population):
        validate_projection_sample(
            sample,
            request.semantic_projection,
            context=f"exact_population[{index}]",
        )
        key = sample_key(sample)
        if key in seen:
            raise SamplingGovernanceError(
                "exact_population must contain distinct projected assignments"
            )
        seen.add(key)
        population.append(sample)

    target = {key: 1.0 / len(population) for key in seen}
    observed = _empirical_distribution(result.samples)
    total_variation = _total_variation(observed, target)

    maximum_marginal_error = 0.0
    for variable in request.semantic_projection:
        maximum_marginal_error = max(
            maximum_marginal_error,
            _maximum_category_error(
                _category_distribution(result.samples, (variable,)),
                _category_distribution(population, (variable,)),
            ),
        )

    maximum_pairwise_error = 0.0
    projection = request.semantic_projection
    for left_index in range(len(projection)):
        for right_index in range(left_index + 1, len(projection)):
            variables = (projection[left_index], projection[right_index])
            maximum_pairwise_error = max(
                maximum_pairwise_error,
                _maximum_category_error(
                    _category_distribution(result.samples, variables),
                    _category_distribution(population, variables),
                ),
            )

    metrics = CalibrationMetrics(
        total_variation=total_variation,
        maximum_marginal_error=maximum_marginal_error,
        maximum_pairwise_error=maximum_pairwise_error,
    )
    metrics.validate()
    return metrics


def repeated_seed_instability(
    request: SamplingRequest,
    results: Sequence[SamplingResult],
) -> float:
    """Return the maximum empirical TV distance between repeated-seed runs."""
    request.validate()
    if len(results) < 2:
        raise SamplingGovernanceError(
            "repeated-seed stability requires at least two sampling results"
        )
    distributions: list[dict[str, float]] = []
    for result in results:
        result.validate(request)
        distributions.append(_empirical_distribution(result.samples))

    instability = 0.0
    for left_index in range(len(distributions)):
        for right_index in range(left_index + 1, len(distributions)):
            instability = max(
                instability,
                _total_variation(
                    distributions[left_index],
                    distributions[right_index],
                ),
            )
    return instability

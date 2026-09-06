from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, median, pstdev


@dataclass(frozen=True)
class MetricSummary:
    n: int
    mean: float
    median: float
    stddev: float
    minimum: float
    maximum: float


def summarize_values(values: list[float]) -> MetricSummary:
    if not values:
        raise ValueError("at least one value is required")
    return MetricSummary(
        n=len(values),
        mean=mean(values),
        median=median(values),
        stddev=pstdev(values) if len(values) > 1 else 0.0,
        minimum=min(values),
        maximum=max(values),
    )


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0 or not 0 <= successes <= n:
        raise ValueError("require 0 <= successes <= n and n > 0")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)

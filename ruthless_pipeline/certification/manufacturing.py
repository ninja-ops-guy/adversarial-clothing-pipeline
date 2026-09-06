from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ConformityMeasurement:
    sample_id: str
    color_delta_e: float
    scale_error_pct: float
    placement_error_mm: float
    registration_error_mm: float


@dataclass(frozen=True)
class ConformityLimits:
    max_color_delta_e: float
    max_scale_error_pct: float
    max_placement_error_mm: float
    max_registration_error_mm: float


def evaluate_lot_conformity(
    measurements: list[ConformityMeasurement],
    limits: ConformityLimits,
) -> tuple[bool, list[str]]:
    if not measurements:
        return False, ["no production samples measured"]
    limit_values = (
        limits.max_color_delta_e,
        limits.max_scale_error_pct,
        limits.max_placement_error_mm,
        limits.max_registration_error_mm,
    )
    if any(not math.isfinite(v) or v < 0 for v in limit_values):
        raise ValueError("conformity limits must be finite and nonnegative")
    ids = [sample.sample_id for sample in measurements]
    if any(not sample_id for sample_id in ids):
        raise ValueError("sample_id is required")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate sample_id")
    failures: list[str] = []
    for sample in measurements:
        values = (
            sample.color_delta_e,
            sample.scale_error_pct,
            sample.placement_error_mm,
            sample.registration_error_mm,
        )
        if any(not math.isfinite(v) for v in values):
            failures.append(f"{sample.sample_id}: non-finite measurement")
            continue
        if sample.color_delta_e < 0:
            failures.append(f"{sample.sample_id}: color")
            continue
        if sample.color_delta_e > limits.max_color_delta_e:
            failures.append(f"{sample.sample_id}: color")
        if abs(sample.scale_error_pct) > limits.max_scale_error_pct:
            failures.append(f"{sample.sample_id}: scale")
        if abs(sample.placement_error_mm) > limits.max_placement_error_mm:
            failures.append(f"{sample.sample_id}: placement")
        if abs(sample.registration_error_mm) > limits.max_registration_error_mm:
            failures.append(f"{sample.sample_id}: registration")
    return not failures, failures

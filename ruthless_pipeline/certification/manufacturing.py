from __future__ import annotations

from dataclasses import dataclass


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
    failures: list[str] = []
    for sample in measurements:
        if sample.color_delta_e > limits.max_color_delta_e:
            failures.append(f"{sample.sample_id}: color")
        if abs(sample.scale_error_pct) > limits.max_scale_error_pct:
            failures.append(f"{sample.sample_id}: scale")
        if abs(sample.placement_error_mm) > limits.max_placement_error_mm:
            failures.append(f"{sample.sample_id}: placement")
        if abs(sample.registration_error_mm) > limits.max_registration_error_mm:
            failures.append(f"{sample.sample_id}: registration")
    return not failures, failures

"""SW-15: Simulator Benchmark & Sensitivity Harness (P2).

Benchmarks transformation/deformation/physics configurations for
determinism, runtime (deterministic operation-tick units, never wall-clock),
memory (output byte accounting), numerical stability, and output
sensitivity.

CRITICAL: this harness NEVER ranks by physical fidelity — no measured
comparisons exist. It distinguishes computational quality (this table) from
empirical validity (reserved for a future measured channel). The optional
``measured_predictive_validity`` field is RESERVED and validated: it may
only be null today; populating it raises :class:`ReservedFieldError`. A
future measured metric plugs in without schema redesign.

Determinism: all randomness via ``np.random.default_rng(seed)``; runtime is
counted in caller-driven operation ticks so tables are reproducible.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from ruthless_pipeline.future_evidence.errors import (
    FutureEvidenceError,
    ReservedFieldError,
)

SCHEMA_VERSION = "rac-sim-benchmark/1.0"
SCHEMA_ID = "https://rac.local/schemas/sim_benchmark_v1.schema.json"
SYNTHETIC_EVIDENCE_CLASS = "synthetic_pipeline_validation_only"

#: A benchmark row may distinguish computational quality from empirical
#: validity; this constant documents that no physical-fidelity ranking exists.
RANKS_PHYSICAL_FIDELITY = False


class TickCounter:
    """Deterministic runtime surrogate: caller ticks once per operation."""

    def __init__(self) -> None:
        self.ticks = 0

    def tick(self, n: int = 1) -> None:
        if n < 1:
            raise FutureEvidenceError("tick count must be >= 1")
        self.ticks += n


@dataclass(frozen=True)
class BenchmarkConfig:
    config_id: str
    family: str  # "transformation" | "deformation" | "physics"
    parameters: Dict[str, float]
    seed: int
    measured_predictive_validity: None = None  # RESERVED: must stay null


def _output_hash(output: np.ndarray) -> str:
    arr = np.ascontiguousarray(output, dtype=np.float64)
    return sha256_bytes(arr.tobytes())


def _to_output(value: Any) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64)
    if arr.size == 0:
        raise FutureEvidenceError("benchmark callable returned an empty output")
    return arr


def run_config_benchmark(
    config: BenchmarkConfig,
    simulate: Callable[[Dict[str, float], int, TickCounter], Any],
    *,
    n_reruns: int = 2,
    sensitivity_steps: int = 4,
    sensitivity_delta: float = 1e-6,
) -> Dict[str, Any]:
    """Benchmark one configuration.

    ``simulate(params, seed, ticker)`` must be a pure deterministic callable
    that ticks the counter once per elementary operation and returns an
    array-like output. Returns a deterministic benchmark row.
    """
    if config.measured_predictive_validity is not None:
        raise ReservedFieldError(
            "measured_predictive_validity is RESERVED for a future measured "
            "channel; it must be null today"
        )
    if config.family not in ("transformation", "deformation", "physics"):
        raise FutureEvidenceError(f"unknown benchmark family {config.family!r}")

    runs: List[np.ndarray] = []
    hashes: List[str] = []
    tick_counts: List[int] = []
    for _ in range(n_reruns):
        ticker = TickCounter()
        out = _to_output(simulate(dict(config.parameters), config.seed, ticker))
        runs.append(out)
        hashes.append(_output_hash(out))
        tick_counts.append(ticker.ticks)
    deterministic = len(set(hashes)) == 1 and len(set(tick_counts)) == 1
    runtime_units = tick_counts[0]
    memory_bytes = int(runs[0].nbytes)
    finite = bool(np.all(np.isfinite(runs[0])))

    # Output sensitivity: central finite difference per parameter.
    sensitivities: Dict[str, float] = {}
    base = runs[0]
    for name, value in sorted(config.parameters.items()):
        plus = dict(config.parameters)
        minus = dict(config.parameters)
        plus[name] = value + sensitivity_delta
        minus[name] = value - sensitivity_delta
        out_plus = _to_output(simulate(plus, config.seed, TickCounter()))
        out_minus = _to_output(simulate(minus, config.seed, TickCounter()))
        if out_plus.shape != base.shape or out_minus.shape != base.shape:
            raise FutureEvidenceError(
                f"sensitivity probe changed output shape for parameter {name!r}"
            )
        denom = 2.0 * sensitivity_delta
        sens = float(np.max(np.abs(out_plus - out_minus)) / denom)
        # Non-finite sensitivity marks an unstable region; store null so the
        # canonical row remains finite (canonical_json refuses NaN/inf).
        sensitivities[name] = sens if math.isfinite(sens) else None
    finite_sens = [s for s in sensitivities.values() if s is not None]
    max_sensitivity = max(finite_sens) if finite_sens else None

    # Numerical stability probe: small seeded perturbations stay finite and
    # bounded relative to base scale.
    rng = np.random.default_rng(config.seed + 1)
    stable = finite
    for _ in range(sensitivity_steps):
        perturbed = {
            k: v + float(rng.uniform(-1e-9, 1e-9))
            for k, v in sorted(config.parameters.items())
        }
        out = _to_output(simulate(perturbed, config.seed, TickCounter()))
        if not np.all(np.isfinite(out)):
            stable = False
            break
    unstable_parameters = [
        name
        for name, s in sensitivities.items()
        if s is None or s > 1e9
    ]

    row: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "config_id": config.config_id,
        "family": config.family,
        "parameters": dict(sorted(config.parameters.items())),
        "seed": config.seed,
        "deterministic": deterministic,
        "output_sha256": hashes[0] if deterministic else None,
        "runtime_units": runtime_units,
        "memory_bytes": memory_bytes,
        "numerically_stable": stable,
        "output_sensitivity": sensitivities,
        "max_output_sensitivity": max_sensitivity,
        "unstable_parameters": sorted(unstable_parameters),
        "measured_predictive_validity": None,
        "empirical_validity": "unassessed_no_measured_channel",
        "evidence_class": SYNTHETIC_EVIDENCE_CLASS,
    }
    row["row_id"] = "RAC-SBEN-" + sha256_bytes(canonical_json(row))[:16]
    return row


def benchmark_table(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Assemble a deterministic benchmark table (computational quality only).

    Rows are sorted by row_id for canonical determinism. The table NEVER
    ranks by physical fidelity; ranking keys are limited to computational
    quality metrics.
    """
    ordered = sorted(rows, key=lambda r: r["row_id"])
    table: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "rows": ordered,
        "n_configs": len(ordered),
        "ranks_physical_fidelity": False,
        "ranking_basis": "computational_quality_only",
        "unstable_config_ids": sorted(
            r["config_id"]
            for r in ordered
            if not r["numerically_stable"] or r["unstable_parameters"]
        ),
        "evidence_class": SYNTHETIC_EVIDENCE_CLASS,
    }
    table["table_id"] = "RAC-SBTB-" + sha256_bytes(canonical_json(table))[:16]
    return table

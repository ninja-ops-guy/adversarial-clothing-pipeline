"""D2-0005 per-candidate optimization telemetry contract (preregistered).

This module defines the frozen telemetry contract for the NEXT generation
(RAC-PER-D2-0005). It is a design artifact: it does not read, write, or
modify any existing generation file. A telemetry record has two phases:

1. PRE-HELD-OUT telemetry (``PreHeldOutTelemetry``) — recorded during
   surrogate-only optimization and FROZEN before any held-out detector
   inference. Its canonical JSON is the only input to ``frozen_sha256()``,
   so the frozen hash is a preregistered commitment to exactly what the
   optimizer knew before seeing held-out results.

2. HELD-OUT outcome (``HeldOutOutcome``) — append-only, attached ONLY after
   the generation closes. ``TelemetryRecord.append_outcome()`` returns a NEW
   record (the original is immutable) and refuses to attach a second outcome
   or an outcome referencing a different candidate hash. Because the frozen
   hash covers the pre-held-out portion only, appending the outcome never
   changes it; any retroactive edit of the frozen portion is detectable.

The record links into the experiment lineage contract
(certification.experiment.ExperimentArtifact) as the artifact referenced by
the "optimization_telemetry" StageRef: StageRef.sha256 is this record's
``frozen_sha256()``.

Conventions match the rest of ruthless_pipeline.certification: frozen
dataclasses, ``from __future__ import annotations``, ``validate()`` raising
ValueError, SHA-256 64-hex digests, canonical JSON (sort_keys, separators),
stdlib-only.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

CONTRACT_VERSION = "1.0"

# Held-out verdicts.
VERDICTS: tuple[str, ...] = ("PASS", "FAIL")

_GENERATION_ID_RE = re.compile(r"^RAC-PER-D2-\d{4}$")
_CALIBRATION_PROFILE_ID_RE = re.compile(r"^RAC-PCP-[A-Za-z0-9._-]+-[0-9]+$")


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _check_rate(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number in [0, 1]: {value!r}")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]: {value!r}")


def _check_non_negative(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative number: {value!r}")
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be a non-negative number: {value!r}")


def cross_model_disagreement(rates: dict[str, float]) -> dict[str, float]:
    """Disagreement summary across surrogate models.

    Returns population variance, spread (max - min), and the largest
    absolute pairwise delta. Requires at least two models; a single-model
    "ensemble" cannot evidence cross-model agreement.
    """
    if len(rates) < 2:
        raise ValueError("cross-model disagreement requires at least 2 surrogate models")
    for name, rate in rates.items():
        _check_rate(f"per-surrogate rate {name!r}", rate)
    values = list(rates.values())
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    spread = max(values) - min(values)
    max_pairwise = max(abs(a - b) for i, a in enumerate(values) for b in values[i + 1:])
    return {
        "model_count": float(len(values)),
        "mean": mean,
        "variance": variance,
        "spread": spread,
        "max_pairwise_delta": max_pairwise,
    }


@dataclass(frozen=True)
class CalibrationProfileRef:
    """Reference to a frozen print calibration profile (RAC-PCP).

    May be absent pre-production; when present it pins both the profile id
    and its SHA-256 digest.
    """

    profile_id: str
    sha256: str

    def validate(self) -> None:
        if not _CALIBRATION_PROFILE_ID_RE.match(self.profile_id or ""):
            raise ValueError(
                "profile_id must match RAC-PCP-<version>-<seq>: "
                f"{self.profile_id!r}"
            )
        if not _is_sha256(self.sha256):
            raise ValueError("calibration profile sha256 must be a 64-hex digest")


@dataclass(frozen=True)
class OptimizerConfig:
    """Full optimizer configuration: seeds, budgets, hyperparameters."""

    optimizer_id: str
    seed: int
    max_evaluations: int
    hyperparameters: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.optimizer_id:
            raise ValueError("optimizer_id is required")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError(f"seed must be an int: {self.seed!r}")
        if not isinstance(self.max_evaluations, int) or isinstance(self.max_evaluations, bool):
            raise ValueError("max_evaluations must be an int")
        if self.max_evaluations < 1:
            raise ValueError("max_evaluations must be >= 1")
        if not isinstance(self.hyperparameters, dict):
            raise ValueError("hyperparameters must be a dict")
        try:
            json.dumps(self.hyperparameters)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"hyperparameters must be JSON-serializable: {exc}")


@dataclass(frozen=True)
class PreHeldOutTelemetry:
    """Surrogate-only optimization telemetry, frozen before held-out inference.

    The coverage_metrics mapping must include "coverage_entropy", which is
    evaluated downstream against failure_taxonomy.COVERAGE_ENTROPY_MIN (0.60).
    spectral_band_energy maps band name (e.g. "low"/"mid"/"high") to energy.
    objective_trajectory summarizes the optimizer objective value trajectory
    (initial, final, best, evaluations).
    """

    candidate_sha256: str
    generation_id: str
    recorded_utc: str
    surrogate_mean_detection_rate: float
    surrogate_worst_case_detection_rate: float
    per_surrogate_detection_rates: dict[str, float]
    cross_model_disagreement: dict[str, float]
    transformation_sweep_variance: float
    spectral_band_energy: dict[str, float]
    pattern_fidelity: float
    printability: float
    objective_trajectory: dict[str, Any]
    coverage_metrics: dict[str, Any]
    optimizer_config: OptimizerConfig
    calibration_profile: CalibrationProfileRef | None = None
    contract_version: str = CONTRACT_VERSION

    def validate(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(
                f"unsupported contract_version: {self.contract_version!r} "
                f"(expected {CONTRACT_VERSION!r})"
            )
        if not _is_sha256(self.candidate_sha256):
            raise ValueError("candidate_sha256 must be a 64-hex digest")
        if not _GENERATION_ID_RE.match(self.generation_id or ""):
            raise ValueError(
                f"generation_id must match RAC-PER-D2-NNNN: {self.generation_id!r}"
            )
        if not self.recorded_utc:
            raise ValueError("recorded_utc (ISO-8601) is required")
        _check_rate("surrogate_mean_detection_rate", self.surrogate_mean_detection_rate)
        _check_rate(
            "surrogate_worst_case_detection_rate",
            self.surrogate_worst_case_detection_rate,
        )
        if len(self.per_surrogate_detection_rates) < 2:
            raise ValueError("per_surrogate_detection_rates requires at least 2 models")
        for name, rate in self.per_surrogate_detection_rates.items():
            if not name:
                raise ValueError("surrogate model names must be non-empty")
            _check_rate(f"per-surrogate rate {name!r}", rate)
        expected = cross_model_disagreement(self.per_surrogate_detection_rates)
        for key, value in expected.items():
            actual = self.cross_model_disagreement.get(key)
            if actual is None or not math.isclose(
                float(actual), value, rel_tol=1e-9, abs_tol=1e-12
            ):
                raise ValueError(
                    f"cross_model_disagreement[{key!r}] inconsistent with "
                    f"per_surrogate_detection_rates: {actual!r} != {value!r}"
                )
        _check_non_negative(
            "transformation_sweep_variance", self.transformation_sweep_variance
        )
        if not self.spectral_band_energy:
            raise ValueError("spectral_band_energy must not be empty")
        for band, energy in self.spectral_band_energy.items():
            if not band:
                raise ValueError("spectral band names must be non-empty")
            _check_non_negative(f"spectral_band_energy[{band!r}]", energy)
        _check_rate("pattern_fidelity", self.pattern_fidelity)
        _check_rate("printability", self.printability)
        for key in ("initial", "final", "best", "evaluations"):
            if key not in self.objective_trajectory:
                raise ValueError(f"objective_trajectory missing key: {key!r}")
        if "coverage_entropy" not in self.coverage_metrics:
            raise ValueError(
                "coverage_metrics must include 'coverage_entropy' "
                "(checked against failure_taxonomy.COVERAGE_ENTROPY_MIN)"
            )
        _check_non_negative(
            "coverage_entropy", float(self.coverage_metrics["coverage_entropy"])
        )
        self.optimizer_config.validate()
        if self.calibration_profile is not None:
            self.calibration_profile.validate()

    def canonical_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        return payload


@dataclass(frozen=True)
class HeldOutOutcome:
    """Append-only held-out outcome, attached only after the generation closes."""

    candidate_sha256: str
    heldout_detection_rates: dict[str, float]
    verdict: str
    recorded_utc: str
    benchmark_run_id: str

    def validate(self) -> None:
        if not _is_sha256(self.candidate_sha256):
            raise ValueError("candidate_sha256 must be a 64-hex digest")
        if not self.heldout_detection_rates:
            raise ValueError("heldout_detection_rates must not be empty")
        for name, rate in self.heldout_detection_rates.items():
            if not name:
                raise ValueError("held-out model names must be non-empty")
            _check_rate(f"held-out rate {name!r}", rate)
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}: {self.verdict!r}")
        if not self.recorded_utc:
            raise ValueError("recorded_utc (ISO-8601) is required")
        if not self.benchmark_run_id:
            raise ValueError("benchmark_run_id is required")


@dataclass(frozen=True)
class TelemetryRecord:
    """One candidate's telemetry: frozen pre-held-out part + optional outcome.

    ``frozen_sha256()`` is computed over the canonical JSON of the
    pre-held-out portion only, so appending the held-out outcome never
    changes the frozen hash. Link into the experiment lineage via an
    ExperimentArtifact "optimization_telemetry" StageRef whose sha256 is
    this value.
    """

    pre: PreHeldOutTelemetry
    outcome: HeldOutOutcome | None = None

    def validate(self) -> None:
        self.pre.validate()
        if self.outcome is not None:
            self.outcome.validate()
            if self.outcome.candidate_sha256 != self.pre.candidate_sha256:
                raise ValueError(
                    "held-out outcome references a different candidate hash "
                    "than the frozen pre-held-out telemetry"
                )

    def frozen_canonical_json(self) -> bytes:
        """Canonical JSON of the pre-held-out portion only."""
        return json.dumps(
            self.pre.canonical_dict(), sort_keys=True, separators=(",", ":")
        ).encode()

    def frozen_sha256(self) -> str:
        """SHA-256 over the frozen pre-held-out portion (computed, never stored)."""
        return hashlib.sha256(self.frozen_canonical_json()).hexdigest()

    def append_outcome(self, outcome: HeldOutOutcome) -> "TelemetryRecord":
        """Return a NEW record with the held-out outcome attached.

        Raises ValueError if an outcome is already attached (append-only) or
        if the outcome references a different candidate hash.
        """
        if self.outcome is not None:
            raise ValueError("held-out outcome already attached (append-only)")
        outcome.validate()
        if outcome.candidate_sha256 != self.pre.candidate_sha256:
            raise ValueError(
                "held-out outcome references a different candidate hash "
                "than the frozen pre-held-out telemetry"
            )
        return TelemetryRecord(pre=self.pre, outcome=outcome)

    def canonical_json(self) -> bytes:
        self.validate()
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "pre": asdict(self.pre),
            "outcome": asdict(self.outcome) if self.outcome is not None else None,
        }

    def to_json(self) -> str:
        return self.canonical_json().decode()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TelemetryRecord":
        pre_payload = dict(payload["pre"])
        opt = pre_payload.get("optimizer_config")
        if opt is not None:
            pre_payload["optimizer_config"] = OptimizerConfig(**opt)
        cal = pre_payload.get("calibration_profile")
        if cal is not None:
            pre_payload["calibration_profile"] = CalibrationProfileRef(**cal)
        pre = PreHeldOutTelemetry(**pre_payload)
        outcome_payload = payload.get("outcome")
        outcome = HeldOutOutcome(**outcome_payload) if outcome_payload is not None else None
        record = cls(pre=pre, outcome=outcome)
        record.validate()
        return record

    @classmethod
    def from_json(cls, text: str) -> "TelemetryRecord":
        return cls.from_dict(json.loads(text))


# JSON Schema (draft 2020-12) for the serialized TelemetryRecord. Also
# distributed as telemetry_contract.schema.json alongside this module.
JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://rac.example/schemas/telemetry_contract.schema.json",
    "title": "D2-0005 Optimization Telemetry Contract",
    "type": "object",
    "required": ["pre", "outcome"],
    "additionalProperties": False,
    "properties": {
        "pre": {"$ref": "#/$defs/preHeldOutTelemetry"},
        "outcome": {
            "anyOf": [{"$ref": "#/$defs/heldOutOutcome"}, {"type": "null"}]
        },
    },
    "$defs": {
        "sha256hex": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "rate": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rateMap": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": {"$ref": "#/$defs/rate"},
        },
        "calibrationProfileRef": {
            "type": "object",
            "required": ["profile_id", "sha256"],
            "additionalProperties": False,
            "properties": {
                "profile_id": {
                    "type": "string",
                    "pattern": "^RAC-PCP-[A-Za-z0-9._-]+-[0-9]+$",
                },
                "sha256": {"$ref": "#/$defs/sha256hex"},
            },
        },
        "optimizerConfig": {
            "type": "object",
            "required": ["optimizer_id", "seed", "max_evaluations", "hyperparameters"],
            "additionalProperties": False,
            "properties": {
                "optimizer_id": {"type": "string", "minLength": 1},
                "seed": {"type": "integer"},
                "max_evaluations": {"type": "integer", "minimum": 1},
                "hyperparameters": {"type": "object"},
            },
        },
        "preHeldOutTelemetry": {
            "type": "object",
            "required": [
                "contract_version",
                "candidate_sha256",
                "generation_id",
                "recorded_utc",
                "surrogate_mean_detection_rate",
                "surrogate_worst_case_detection_rate",
                "per_surrogate_detection_rates",
                "cross_model_disagreement",
                "transformation_sweep_variance",
                "spectral_band_energy",
                "pattern_fidelity",
                "printability",
                "objective_trajectory",
                "coverage_metrics",
                "optimizer_config",
                "calibration_profile",
            ],
            "additionalProperties": False,
            "properties": {
                "contract_version": {"const": CONTRACT_VERSION},
                "candidate_sha256": {"$ref": "#/$defs/sha256hex"},
                "generation_id": {"type": "string", "pattern": "^RAC-PER-D2-\\d{4}$"},
                "recorded_utc": {"type": "string", "minLength": 1},
                "surrogate_mean_detection_rate": {"$ref": "#/$defs/rate"},
                "surrogate_worst_case_detection_rate": {"$ref": "#/$defs/rate"},
                "per_surrogate_detection_rates": {
                    "allOf": [{"$ref": "#/$defs/rateMap"}, {"minProperties": 2}]
                },
                "cross_model_disagreement": {
                    "type": "object",
                    "required": [
                        "model_count",
                        "mean",
                        "variance",
                        "spread",
                        "max_pairwise_delta",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "model_count": {"type": "number", "minimum": 2},
                        "mean": {"$ref": "#/$defs/rate"},
                        "variance": {"type": "number", "minimum": 0.0},
                        "spread": {"type": "number", "minimum": 0.0},
                        "max_pairwise_delta": {"type": "number", "minimum": 0.0},
                    },
                },
                "transformation_sweep_variance": {"type": "number", "minimum": 0.0},
                "spectral_band_energy": {
                    "type": "object",
                    "minProperties": 1,
                    "additionalProperties": {"type": "number", "minimum": 0.0},
                },
                "pattern_fidelity": {"$ref": "#/$defs/rate"},
                "printability": {"$ref": "#/$defs/rate"},
                "objective_trajectory": {
                    "type": "object",
                    "required": ["initial", "final", "best", "evaluations"],
                    "properties": {
                        "initial": {"type": "number"},
                        "final": {"type": "number"},
                        "best": {"type": "number"},
                        "evaluations": {"type": "integer", "minimum": 1},
                    },
                    "additionalProperties": True,
                },
                "coverage_metrics": {
                    "type": "object",
                    "required": ["coverage_entropy"],
                    "properties": {
                        "coverage_entropy": {"type": "number", "minimum": 0.0}
                    },
                    "additionalProperties": True,
                },
                "optimizer_config": {"$ref": "#/$defs/optimizerConfig"},
                "calibration_profile": {
                    "anyOf": [
                        {"$ref": "#/$defs/calibrationProfileRef"},
                        {"type": "null"},
                    ]
                },
            },
        },
        "heldOutOutcome": {
            "type": "object",
            "required": [
                "candidate_sha256",
                "heldout_detection_rates",
                "verdict",
                "recorded_utc",
                "benchmark_run_id",
            ],
            "additionalProperties": False,
            "properties": {
                "candidate_sha256": {"$ref": "#/$defs/sha256hex"},
                "heldout_detection_rates": {"$ref": "#/$defs/rateMap"},
                "verdict": {"enum": list(VERDICTS)},
                "recorded_utc": {"type": "string", "minLength": 1},
                "benchmark_run_id": {"type": "string", "minLength": 1},
            },
        },
    },
}

SCHEMA_JSON = json.dumps(JSON_SCHEMA, sort_keys=True, indent=2) + "\n"

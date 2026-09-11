"""D2-0007 Stage-0 landmark-free wiring smoke gate.

This module is intentionally additive.  It does not alter any frozen D2
scientific surface and it never imports or evaluates PERSON-HO-v3.  Its job is
to prove the prospective D2-0007 path can execute:

    landmark-free fixture -> PATTERNS candidate -> surrogate scoring -> telemetry

The real surrogate evaluator is injected through ``score_candidate`` so this
contract can be exercised cheaply in CI while production callers can bind the
existing PERSON-SUR-v3 benchmark adapter.  The gate fails closed if a scorer
reports held-out access, the wrong model-set identity, missing/extra surrogate
members, non-finite rates, or a candidate that somehow contains landmarks.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Callable, Mapping, Sequence

from .base import GeneratorParams
from .feature_disruption import FeatureCollageGenerator

D2007_GENERATION_ID = "RAC-PER-D2-0007"
D2007_STAGE = "STAGE_0_LANDMARK_FREE_SMOKE"
SURROGATE_MODEL_SET_ID = "PERSON-SUR-v3"
HELDOUT_MODEL_SET_ID = "PERSON-HO-v3"
DEFAULT_SEED = 20270110
DEFAULT_OUTPUT_SIZE = (96, 128)


class D2007SmokeGateError(RuntimeError):
    """Stage-0 failed closed."""


@dataclass(frozen=True)
class SurrogateScoreResult:
    """Result returned by a D2-0007 surrogate scorer adapter."""

    model_set_id: str
    per_surrogate_detection_rates: Mapping[str, float]
    invalid_condition_fraction: float = 0.0
    heldout_access: bool = False


ScoreCandidate = Callable[[Any, Mapping[str, Any]], SurrogateScoreResult]


def _sha256_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_rates(
    result: SurrogateScoreResult,
    expected_surrogate_ids: Sequence[str],
) -> dict[str, float]:
    if result.heldout_access:
        raise D2007SmokeGateError("held-out access is forbidden during D2-0007 Stage 0")
    if result.model_set_id == HELDOUT_MODEL_SET_ID:
        raise D2007SmokeGateError("held-out model set cannot score D2-0007 Stage 0")
    if result.model_set_id != SURROGATE_MODEL_SET_ID:
        raise D2007SmokeGateError(
            f"unexpected model set {result.model_set_id!r}; expected {SURROGATE_MODEL_SET_ID!r}"
        )

    expected = tuple(str(v) for v in expected_surrogate_ids)
    if not expected or len(set(expected)) != len(expected):
        raise D2007SmokeGateError("expected surrogate ids must be non-empty and unique")

    observed = {str(k): float(v) for k, v in result.per_surrogate_detection_rates.items()}
    if set(observed) != set(expected):
        missing = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        raise D2007SmokeGateError(
            f"surrogate membership mismatch: missing={missing}, extra={extra}"
        )
    for model_id, rate in observed.items():
        if not math.isfinite(rate) or rate < 0.0 or rate > 1.0:
            raise D2007SmokeGateError(f"invalid detection rate for {model_id}: {rate!r}")

    invalid_fraction = float(result.invalid_condition_fraction)
    if not math.isfinite(invalid_fraction) or not 0.0 <= invalid_fraction <= 1.0:
        raise D2007SmokeGateError("invalid_condition_fraction must be within [0, 1]")
    if invalid_fraction > 0.10:
        raise D2007SmokeGateError(
            "Stage-0 invalid_condition_fraction exceeds preregistered 0.10 ceiling"
        )
    return {model_id: observed[model_id] for model_id in expected}


def build_landmark_free_candidate(
    *,
    seed: int = DEFAULT_SEED,
    output_size: tuple[int, int] = DEFAULT_OUTPUT_SIZE,
) -> tuple[Any, dict[str, Any]]:
    """Generate the deterministic landmark-free PATTERNS smoke candidate.

    The mask geometry deliberately contains no ``landmarks`` key.  This is the
    minimum fixture needed to prove the governed candidate path does not depend
    on facial landmarks before motif screening begins.
    """
    params = GeneratorParams(
        seed=int(seed),
        mask_geometry={
            "fixture_class": "D2-0007_STAGE0_LANDMARK_FREE",
            "coordinate_convention": "image_xy_pixels_origin_top_left",
        },
        output_size=(int(output_size[0]), int(output_size[1])),
    )
    pattern = FeatureCollageGenerator().generate(params)
    candidate = pattern.to_candidate()

    if "landmarks" in candidate["params"]["mask_geometry"]:
        raise D2007SmokeGateError("Stage-0 candidate unexpectedly contains landmarks")
    if candidate.get("claim_state") != "EXPLORATORY":
        raise D2007SmokeGateError("PATTERNS smoke candidate must remain EXPLORATORY")
    if candidate.get("physical_efficacy_claimed") is not False:
        raise D2007SmokeGateError("PATTERNS smoke candidate may not claim physical efficacy")
    return pattern.image, candidate


def run_landmark_free_smoke(
    *,
    score_candidate: ScoreCandidate,
    expected_surrogate_ids: Sequence[str],
    seed: int = DEFAULT_SEED,
    output_size: tuple[int, int] = DEFAULT_OUTPUT_SIZE,
) -> dict[str, Any]:
    """Execute D2-0007 Stage 0 and return hashable surrogate-only telemetry."""
    image, candidate = build_landmark_free_candidate(seed=seed, output_size=output_size)
    result = score_candidate(image, candidate)
    if not isinstance(result, SurrogateScoreResult):
        raise D2007SmokeGateError("score_candidate must return SurrogateScoreResult")
    rates = _validate_rates(result, expected_surrogate_ids)

    telemetry: dict[str, Any] = {
        "schema_version": "rac-d2007-stage0-smoke/1.0",
        "generation_id": D2007_GENERATION_ID,
        "stage": D2007_STAGE,
        "status": "PASS",
        "candidate_id": candidate["candidate_id"],
        "pattern_sha256": candidate["pattern_sha256"],
        "generator": candidate["generator"],
        "generator_version": candidate["generator_version"],
        "provenance_hash": candidate["provenance_hash"],
        "landmark_free": True,
        "model_set_id": result.model_set_id,
        "surrogate_only": True,
        "heldout_access": False,
        "per_surrogate_detection_rates": rates,
        "invalid_condition_fraction": float(result.invalid_condition_fraction),
        "screening_opened": False,
        "optimization_opened": False,
        "candidate_freeze_created": False,
        "alpha_002_promoted": False,
    }
    telemetry["telemetry_sha256"] = _sha256_json(telemetry)
    return telemetry

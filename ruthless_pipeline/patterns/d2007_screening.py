"""Governed RAC-PER-D2-0007 Stage-1 motif-screening core.

This module is deliberately surrogate-only and outcome-agnostic.  It turns the
pre-execution screening freeze into exactly 64 deterministic PATTERNS
compositions and applies the preregistered survivor rule to externally supplied
PERSON-SUR-v3 observations.

It does NOT construct detector evaluators, load held-out models, build body or
garment anchors, optimize candidates, freeze a winner, or promote a print
article.  Those state transitions belong to later D2-0007 stages.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping

from .base import GeneratorParams

GENERATION_ID = "RAC-PER-D2-0007"
STAGE = "STAGE_1_MOTIF_SCREENING"
SURROGATE_MODEL_SET_ID = "PERSON-SUR-v3"
HELDOUT_MODEL_SET_ID = "PERSON-HO-v3"


class D2007ScreeningError(RuntimeError):
    """Fail-closed D2-0007 Stage-1 governance or observation error."""


@dataclass(frozen=True)
class ScreeningObservation:
    generator_index: int
    generator: str
    composition_index: int
    derived_seed: int
    screening_candidate_id: str
    pattern_sha256: str
    baseline_detection_rates: Mapping[str, float]
    candidate_detection_rates: Mapping[str, float]
    invalid_condition_fraction: float

    def to_dict(self) -> dict[str, Any]:
        baseline = {str(k): float(v) for k, v in sorted(self.baseline_detection_rates.items())}
        candidate = {str(k): float(v) for k, v in sorted(self.candidate_detection_rates.items())}
        if set(baseline) != set(candidate):
            raise D2007ScreeningError("baseline/candidate surrogate membership mismatch")
        if not baseline:
            raise D2007ScreeningError("screening observation has no surrogate rates")
        for label, rates in (("baseline", baseline), ("candidate", candidate)):
            for model, value in rates.items():
                if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                    raise D2007ScreeningError(f"{label} rate for {model} is outside [0,1]")
        invalid = float(self.invalid_condition_fraction)
        if not math.isfinite(invalid) or not 0.0 <= invalid <= 1.0:
            raise D2007ScreeningError("invalid_condition_fraction is outside [0,1]")
        reductions = {model: baseline[model] - candidate[model] for model in baseline}
        return {
            "generator_index": int(self.generator_index),
            "generator": self.generator,
            "composition_index": int(self.composition_index),
            "derived_seed": int(self.derived_seed),
            "screening_candidate_id": self.screening_candidate_id,
            "pattern_sha256": self.pattern_sha256,
            "baseline_detection_rates": baseline,
            "candidate_detection_rates": candidate,
            "per_surrogate_detection_rate_reduction": reductions,
            "mean_detection_rate_reduction": statistics.fmean(reductions.values()),
            "improved_surrogate_count": sum(value > 0.0 for value in reductions.values()),
            "worst_surrogate_candidate_detection_rate": max(candidate.values()),
            "invalid_condition_fraction": invalid,
        }


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive_seed(*, root_seed: int, generator_index: int, composition_index: int) -> int:
    material = (
        f"{GENERATION_ID}|stage1|generator_index={int(generator_index)}|"
        f"composition_index={int(composition_index)}|root_seed={int(root_seed)}"
    )
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big") & ((1 << 63) - 1)


def validate_stage0_closure(closure: Mapping[str, Any], spec: Mapping[str, Any]) -> None:
    receipt = closure.get("receipt")
    gate = spec.get("stage0_gate")
    if not isinstance(receipt, Mapping) or not isinstance(gate, Mapping):
        raise D2007ScreeningError("Stage-0 closure/gate is malformed")
    if closure.get("generation_id") != GENERATION_ID or receipt.get("generation_id") != GENERATION_ID:
        raise D2007ScreeningError("Stage-0 closure belongs to the wrong generation")
    if closure.get("decision") != gate.get("required_decision") or receipt.get("status") != "PASS":
        raise D2007ScreeningError("Stage-0 PASS is required before screening")
    if receipt.get("telemetry_sha256") != gate.get("required_telemetry_sha256"):
        raise D2007ScreeningError("Stage-0 telemetry hash does not match the pre-execution gate")
    if receipt.get("surrogate_only") is not True or receipt.get("heldout_access") is not False:
        raise D2007ScreeningError("Stage-0 receipt violates the surrogate-only boundary")
    if receipt.get("screening_opened") is not False:
        raise D2007ScreeningError("Stage-0 receipt unexpectedly claims screening was already opened")


def validate_execution_spec(spec: Mapping[str, Any], *, repo_root: str | Path | None = None) -> None:
    if spec.get("schema_version") != "rac-d2007-stage1-screening-freeze/1.0":
        raise D2007ScreeningError("unsupported Stage-1 screening-freeze schema")
    if spec.get("generation_id") != GENERATION_ID or spec.get("stage") != STAGE:
        raise D2007ScreeningError("screening freeze targets the wrong generation/stage")
    if spec.get("status") != "PRE_EXECUTION_FROZEN_NOT_RUN":
        raise D2007ScreeningError("screening freeze must remain PRE_EXECUTION_FROZEN_NOT_RUN")

    boundary = spec.get("scientific_boundary", {})
    if boundary.get("model_set_id") != SURROGATE_MODEL_SET_ID:
        raise D2007ScreeningError("Stage 1 must use PERSON-SUR-v3")
    if boundary.get("heldout_model_set_id") != HELDOUT_MODEL_SET_ID:
        raise D2007ScreeningError("unexpected held-out model-set identity")
    if boundary.get("heldout_access_allowed") is not False:
        raise D2007ScreeningError("held-out access must be explicitly forbidden")

    from . import P0_GENERATORS

    frozen_order = list(spec.get("generator_order", ()))
    runtime_order = [cls.__name__ for cls in P0_GENERATORS]
    if frozen_order != runtime_order:
        raise D2007ScreeningError("P0 generator inventory/order drifted from Stage-1 freeze")

    budget = spec.get("budget", {})
    roots = [int(v) for v in budget.get("root_seeds", ())]
    if roots != [20270110, 20270111, 20270112]:
        raise D2007ScreeningError("root seed set drifted from preregistration")
    if int(budget.get("compositions_per_generator", -1)) != 8:
        raise D2007ScreeningError("compositions_per_generator must remain 8")
    if int(budget.get("total_compositions", -1)) != 64:
        raise D2007ScreeningError("total screening budget must remain 64")
    if int(budget.get("max_candidates_admitted_to_optimization", -1)) != 4:
        raise D2007ScreeningError("optimization admission cap must remain 4")
    if budget.get("optional_stopping") is not False or budget.get("budget_extension_allowed") is not False:
        raise D2007ScreeningError("optional stopping/budget extension must remain forbidden")

    serialized = spec.get("derived_seeds_by_generator", {})
    if set(serialized) != set(frozen_order):
        raise D2007ScreeningError("serialized seed schedule does not cover exactly the frozen generator set")
    for generator_index, generator in enumerate(frozen_order):
        expected = [
            derive_seed(
                root_seed=roots[composition_index % len(roots)],
                generator_index=generator_index,
                composition_index=composition_index,
            )
            for composition_index in range(8)
        ]
        actual = [int(v) for v in serialized.get(generator, ())]
        if actual != expected:
            raise D2007ScreeningError(f"derived seed schedule drift for {generator}")

    rule = spec.get("decision_rule", {})
    if float(rule.get("minimum_mean_absolute_detection_rate_reduction", -1)) != 0.15:
        raise D2007ScreeningError("mean reduction threshold drifted from preregistration")
    if int(rule.get("minimum_improved_surrogates", -1)) != 4:
        raise D2007ScreeningError("minimum improved-surrogate count drifted from preregistration")
    if float(rule.get("max_invalid_condition_fraction", -1)) != 0.10:
        raise D2007ScreeningError("invalid-condition ceiling drifted from preregistration")

    guards = spec.get("downstream_guards", {})
    required_forbidden = (
        "body_or_garment_anchor_support_before_survival",
        "optimization_before_screening_close",
        "candidate_freeze_during_screening",
        "heldout_access_before_stage6",
        "alpha_002_promotion_during_screening",
    )
    if any(guards.get(key) != "FORBIDDEN" for key in required_forbidden):
        raise D2007ScreeningError("one or more downstream Stage-1 guards are not fail-closed")
    if guards.get("d2_0005_mutation_or_candidate_injection") != "CRITICAL_REGRESSION":
        raise D2007ScreeningError("D2-0005 regression guard is missing")
    if guards.get("alpha_001_rebinding") != "CRITICAL_REGRESSION":
        raise D2007ScreeningError("Alpha-001 regression guard is missing")

    if repo_root is not None:
        root = Path(repo_root)
        for key in ("preregistration", "generation_record"):
            pin = spec.get(key, {})
            path = root / str(pin.get("path", ""))
            if not path.is_file() or _sha256_file(path) != pin.get("sha256"):
                raise D2007ScreeningError(f"{key} hash no longer matches the frozen parent surface")
        closure_path = root / str(spec["stage0_gate"]["path"])
        if not closure_path.is_file():
            raise D2007ScreeningError("persisted Stage-0 PASS closure is missing")
        validate_stage0_closure(load_json(closure_path), spec)


def generate_screening_candidate(
    spec: Mapping[str, Any], *, generator_index: int, composition_index: int
) -> tuple[Any, dict[str, Any]]:
    """Generate one of the exactly 64 frozen Stage-1 PATTERNS compositions."""
    validate_execution_spec(spec)
    from . import P0_GENERATORS

    frozen_order = list(spec["generator_order"])
    if not 0 <= int(generator_index) < len(frozen_order):
        raise D2007ScreeningError("generator_index is outside the frozen generator set")
    if not 0 <= int(composition_index) < int(spec["budget"]["compositions_per_generator"]):
        raise D2007ScreeningError("composition_index is outside the frozen per-generator budget")

    generator_cls = P0_GENERATORS[int(generator_index)]
    generator_name = generator_cls.__name__
    if generator_name != frozen_order[int(generator_index)]:
        raise D2007ScreeningError("runtime generator order disagrees with the frozen Stage-1 order")

    derived_seed = int(spec["derived_seeds_by_generator"][generator_name][int(composition_index)])
    geometry = deepcopy(spec["generator_local_geometry"])
    output_size = tuple(int(v) for v in geometry.pop("output_size"))
    geometry.pop("id", None)
    geometry.pop("purpose", None)
    params = GeneratorParams(
        seed=derived_seed,
        mask_geometry=geometry,
        output_size=output_size,
    )
    pattern = generator_cls().generate(params)
    candidate = pattern.to_candidate()
    screening_id = (
        f"RAC-D2-0007-S1-G{int(generator_index):02d}-C{int(composition_index):02d}-"
        f"{candidate['pattern_sha256'][:12]}"
    )
    candidate.update(
        {
            "screening_candidate_id": screening_id,
            "generation_id": GENERATION_ID,
            "stage": STAGE,
            "generator_index": int(generator_index),
            "composition_index": int(composition_index),
            "derived_seed": derived_seed,
            "model_exposure": SURROGATE_MODEL_SET_ID,
            "heldout_access": False,
            "body_garment_anchor_used": False,
            "evidence_scope": "surrogate-only hypothesis-screening candidate",
        }
    )
    return pattern.image, candidate


def build_observation(
    candidate: Mapping[str, Any], *, baseline_detection_rates: Mapping[str, float],
    candidate_detection_rates: Mapping[str, float], invalid_condition_fraction: float,
) -> ScreeningObservation:
    if candidate.get("generation_id") != GENERATION_ID or candidate.get("stage") != STAGE:
        raise D2007ScreeningError("candidate is outside the D2-0007 Stage-1 lineage")
    if candidate.get("heldout_access") is not False or candidate.get("body_garment_anchor_used") is not False:
        raise D2007ScreeningError("Stage-1 candidate violates exposure/anchor boundary")
    return ScreeningObservation(
        generator_index=int(candidate["generator_index"]),
        generator=str(candidate["generator"]),
        composition_index=int(candidate["composition_index"]),
        derived_seed=int(candidate["derived_seed"]),
        screening_candidate_id=str(candidate["screening_candidate_id"]),
        pattern_sha256=str(candidate["pattern_sha256"]),
        baseline_detection_rates=baseline_detection_rates,
        candidate_detection_rates=candidate_detection_rates,
        invalid_condition_fraction=float(invalid_condition_fraction),
    )


def close_screening(spec: Mapping[str, Any], observations: Iterable[ScreeningObservation]) -> dict[str, Any]:
    """Apply the frozen rule to a complete 64-observation Stage-1 screen."""
    validate_execution_spec(spec)
    rows = [observation.to_dict() for observation in observations]
    frozen_order = list(spec["generator_order"])
    expected_pairs = {(g, c) for g in range(len(frozen_order)) for c in range(8)}
    actual_pairs = {(int(row["generator_index"]), int(row["composition_index"])) for row in rows}
    if len(rows) != 64 or actual_pairs != expected_pairs:
        raise D2007ScreeningError("Stage-1 closure requires exactly the frozen 64 unique compositions")

    expected_models: set[str] | None = None
    for row in rows:
        model_ids = set(row["candidate_detection_rates"])
        if expected_models is None:
            expected_models = model_ids
        elif model_ids != expected_models:
            raise D2007ScreeningError("surrogate membership drifted between screening observations")
    if expected_models is None or len(expected_models) != 6:
        raise D2007ScreeningError("Stage-1 closure requires exactly six surrogate models")

    grouped: dict[int, list[dict[str, Any]]] = {index: [] for index in range(len(frozen_order))}
    for row in rows:
        grouped[int(row["generator_index"])].append(row)

    rule = spec["decision_rule"]
    min_mean = float(rule["minimum_mean_absolute_detection_rate_reduction"])
    min_models = int(rule["minimum_improved_surrogates"])
    max_invalid = float(rule["max_invalid_condition_fraction"])
    family_results: list[dict[str, Any]] = []
    for generator_index, generator_class_name in enumerate(frozen_order):
        family_rows = grouped[generator_index]
        if len(family_rows) != 8:
            raise D2007ScreeningError(f"{generator_class_name} does not have exactly eight observations")
        best = min(
            family_rows,
            key=lambda row: (
                -float(row["mean_detection_rate_reduction"]),
                float(row["worst_surrogate_candidate_detection_rate"]),
                int(row["composition_index"]),
            ),
        )
        survives = (
            float(best["mean_detection_rate_reduction"]) >= min_mean
            and int(best["improved_surrogate_count"]) >= min_models
            and float(best["invalid_condition_fraction"]) <= max_invalid
        )
        family_results.append(
            {
                "generator_index": generator_index,
                "generator_class": generator_class_name,
                "generator": best["generator"],
                "survives": survives,
                "best_composition": best,
            }
        )

    survivors = [family for family in family_results if family["survives"]]
    survivors.sort(
        key=lambda family: (
            -float(family["best_composition"]["mean_detection_rate_reduction"]),
            float(family["best_composition"]["worst_surrogate_candidate_detection_rate"]),
            int(family["generator_index"]),
            int(family["best_composition"]["derived_seed"]),
        )
    )
    cap = int(spec["budget"]["max_candidates_admitted_to_optimization"])
    admitted = survivors[:cap]
    return {
        "schema_version": "rac-d2007-stage1-screening-result/1.0",
        "generation_id": GENERATION_ID,
        "stage": STAGE,
        "status": "COMPLETE",
        "evidence_class": "internally_measured",
        "evidence_scope": "surrogate-only hypothesis screening; not transfer/efficacy evidence",
        "model_set_id": SURROGATE_MODEL_SET_ID,
        "heldout_access": False,
        "screening_budget_exhausted": True,
        "observed_composition_count": len(rows),
        "family_results": family_results,
        "survivor_count": len(survivors),
        "survivors": survivors,
        "admitted_to_anchor_engineering": admitted,
        "admitted_count": len(admitted),
        "body_garment_anchor_support_built": False,
        "optimization_opened": False,
        "candidate_freeze_created": False,
        "alpha_002_promoted": False,
        "preregistered_h0_screened_out": not bool(survivors),
        "observations": rows,
    }

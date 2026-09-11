from __future__ import annotations

import json
from pathlib import Path

import pytest

from ruthless_pipeline.patterns.d2007_screening import (
    D2007ScreeningError,
    ScreeningObservation,
    close_screening,
    derive_seed,
    generate_screening_candidate,
    validate_execution_spec,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "configs" / "d2007_stage1_screening_v1.json"
MODELS = (
    "yolov8n",
    "fasterrcnn_mobilenet_v3_320",
    "detr_resnet50",
    "ssdlite320_mobilenet_v3",
    "retinanet_resnet50_fpn_v2",
    "fcos_resnet50_fpn",
)


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _rates(value: float) -> dict[str, float]:
    return {model: value for model in MODELS}


def _observations(*, survivor_families: int = 0) -> list[ScreeningObservation]:
    spec = _spec()
    rows: list[ScreeningObservation] = []
    for generator_index, generator_class in enumerate(spec["generator_order"]):
        generator_name = generator_class.removesuffix("Generator")
        for composition_index in range(8):
            baseline = _rates(1.0)
            if generator_index < survivor_families and composition_index == 0:
                candidate = _rates(0.70)  # 0.30 absolute reduction on all six
            else:
                candidate = _rates(0.95)  # 0.05: below the frozen 0.15 threshold
            rows.append(
                ScreeningObservation(
                    generator_index=generator_index,
                    generator=generator_name,
                    composition_index=composition_index,
                    derived_seed=spec["derived_seeds_by_generator"][generator_class][composition_index],
                    screening_candidate_id=f"S1-{generator_index}-{composition_index}",
                    pattern_sha256=(f"{generator_index:02x}{composition_index:02x}" * 16)[:64],
                    baseline_detection_rates=baseline,
                    candidate_detection_rates=candidate,
                    invalid_condition_fraction=0.0,
                )
            )
    return rows


def test_execution_freeze_validates_against_parent_and_stage0_receipt() -> None:
    validate_execution_spec(_spec(), repo_root=ROOT)


def test_all_64_serialized_seeds_recompute() -> None:
    spec = _spec()
    roots = spec["budget"]["root_seeds"]
    seen: set[int] = set()
    for generator_index, generator in enumerate(spec["generator_order"]):
        seeds = spec["derived_seeds_by_generator"][generator]
        assert len(seeds) == 8
        for composition_index, actual in enumerate(seeds):
            expected = derive_seed(
                root_seed=roots[composition_index % 3],
                generator_index=generator_index,
                composition_index=composition_index,
            )
            assert actual == expected
            seen.add(actual)
    assert len(seen) == 64


def test_generated_candidate_is_surrogate_only_and_anchor_free() -> None:
    image_a, candidate_a = generate_screening_candidate(_spec(), generator_index=0, composition_index=0)
    image_b, candidate_b = generate_screening_candidate(_spec(), generator_index=0, composition_index=0)
    assert image_a.shape == (128, 128, 3)
    assert (image_a == image_b).all()
    assert candidate_a == candidate_b
    assert candidate_a["generation_id"] == "RAC-PER-D2-0007"
    assert candidate_a["stage"] == "STAGE_1_MOTIF_SCREENING"
    assert candidate_a["model_exposure"] == "PERSON-SUR-v3"
    assert candidate_a["heldout_access"] is False
    assert candidate_a["body_garment_anchor_used"] is False
    assert candidate_a["claim_state"] == "EXPLORATORY"
    assert candidate_a["physical_efficacy_claimed"] is False


def test_each_frozen_generator_can_generate_all_eight_compositions() -> None:
    spec = _spec()
    ids: set[str] = set()
    for generator_index in range(8):
        for composition_index in range(8):
            image, candidate = generate_screening_candidate(
                spec,
                generator_index=generator_index,
                composition_index=composition_index,
            )
            assert image.shape == (128, 128, 3)
            ids.add(candidate["screening_candidate_id"])
    assert len(ids) == 64


def test_screening_closure_requires_complete_fixed_budget() -> None:
    with pytest.raises(D2007ScreeningError, match="64 unique"):
        close_screening(_spec(), _observations()[:-1])


def test_no_signal_closes_as_preregistered_h0_without_opening_downstream_stages() -> None:
    result = close_screening(_spec(), _observations(survivor_families=0))
    assert result["status"] == "COMPLETE"
    assert result["survivor_count"] == 0
    assert result["admitted_count"] == 0
    assert result["preregistered_h0_screened_out"] is True
    assert result["heldout_access"] is False
    assert result["body_garment_anchor_support_built"] is False
    assert result["optimization_opened"] is False
    assert result["candidate_freeze_created"] is False
    assert result["alpha_002_promoted"] is False


def test_survivor_admission_is_bounded_at_four() -> None:
    result = close_screening(_spec(), _observations(survivor_families=5))
    assert result["survivor_count"] == 5
    assert result["admitted_count"] == 4
    assert [item["generator_index"] for item in result["admitted_to_anchor_engineering"]] == [0, 1, 2, 3]


def test_invalid_fraction_blocks_otherwise_strong_composition() -> None:
    rows = _observations(survivor_families=1)
    first = rows[0]
    rows[0] = ScreeningObservation(
        generator_index=first.generator_index,
        generator=first.generator,
        composition_index=first.composition_index,
        derived_seed=first.derived_seed,
        screening_candidate_id=first.screening_candidate_id,
        pattern_sha256=first.pattern_sha256,
        baseline_detection_rates=first.baseline_detection_rates,
        candidate_detection_rates=first.candidate_detection_rates,
        invalid_condition_fraction=0.11,
    )
    result = close_screening(_spec(), rows)
    assert result["family_results"][0]["survives"] is False


def test_four_of_six_cross_model_requirement_is_enforced() -> None:
    rows = _observations()
    first = rows[0]
    baseline = _rates(1.0)
    candidate = {model: (0.70 if index < 3 else 1.0) for index, model in enumerate(MODELS)}
    rows[0] = ScreeningObservation(
        generator_index=first.generator_index,
        generator=first.generator,
        composition_index=first.composition_index,
        derived_seed=first.derived_seed,
        screening_candidate_id=first.screening_candidate_id,
        pattern_sha256=first.pattern_sha256,
        baseline_detection_rates=baseline,
        candidate_detection_rates=candidate,
        invalid_condition_fraction=0.0,
    )
    result = close_screening(_spec(), rows)
    assert result["family_results"][0]["best_composition"]["improved_surrogate_count"] == 3
    assert result["family_results"][0]["survives"] is False

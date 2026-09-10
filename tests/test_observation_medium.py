"""Acceptance fixtures for the additive observation-medium registry (NR-02).

Covers the NR-02(c) acceptance criteria:
- synthetic fixture evidence cannot promote a worn-fabric claim,
- photographed-display evidence cannot promote a worn-fabric claim,
- unknown material/capture fields stay unknown (never silently upgraded),
- a change in rendering assumptions creates a versioned comparison rather
  than rewriting old results.
"""

import pytest

from ruthless_pipeline.certification.observation_medium import (
    DISPLAY_PHOTOGRAPHED_BY_CAMERA,
    IMAGE_COMPOSITE,
    PRINTED_FLAT_MATERIAL,
    UNKNOWN,
    WORN_FABRIC,
    assert_worn_fabric_claim_eligible,
    build_medium_annotation,
    compare_rendering_assumptions,
    describe,
    is_valid,
    normalize_medium,
    verify_annotation,
)
from ruthless_pipeline.certification.physical_capture_rehearsal import (
    PromotionRefusedError,
)

SYNTHETIC = "synthetic_pipeline_validation_only"
MEASURED = "measured_physical_capture"


# --- registry / normalization ---------------------------------------------


def test_registered_media():
    for m in (
        IMAGE_COMPOSITE,
        DISPLAY_PHOTOGRAPHED_BY_CAMERA,
        PRINTED_FLAT_MATERIAL,
        WORN_FABRIC,
        UNKNOWN,
    ):
        assert is_valid(m)
        assert describe(m)


def test_unknown_stays_unknown():
    assert normalize_medium(None) == UNKNOWN
    assert normalize_medium("") == UNKNOWN
    assert normalize_medium("   ") == UNKNOWN


def test_unregistered_medium_fails_closed():
    with pytest.raises(KeyError):
        normalize_medium("worn-fabric")  # typo, not coerced to unknown
    with pytest.raises(KeyError):
        describe("hologram")


# --- promotion guard -------------------------------------------------------


def test_synthetic_fixture_cannot_promote_worn_fabric_claim():
    with pytest.raises(PromotionRefusedError):
        assert_worn_fabric_claim_eligible(IMAGE_COMPOSITE, SYNTHETIC)
    # Even worn fabric + synthetic evidence class is refused.
    with pytest.raises(PromotionRefusedError):
        assert_worn_fabric_claim_eligible(WORN_FABRIC, SYNTHETIC)


def test_photographed_display_cannot_promote_worn_fabric_claim():
    with pytest.raises(PromotionRefusedError):
        assert_worn_fabric_claim_eligible(
            DISPLAY_PHOTOGRAPHED_BY_CAMERA, MEASURED
        )


def test_printed_flat_and_unknown_cannot_promote():
    with pytest.raises(PromotionRefusedError):
        assert_worn_fabric_claim_eligible(PRINTED_FLAT_MATERIAL, MEASURED)
    with pytest.raises(PromotionRefusedError):
        assert_worn_fabric_claim_eligible(UNKNOWN, MEASURED)
    with pytest.raises(PromotionRefusedError):
        assert_worn_fabric_claim_eligible(None, MEASURED)


def test_worn_fabric_measured_is_eligible():
    # The only eligible combination; still never sets physical_efficacy_claimed.
    assert_worn_fabric_claim_eligible(WORN_FABRIC, MEASURED)


# --- annotations ------------------------------------------------------------


def test_annotation_defaults_unknown_and_verifies():
    ann = build_medium_annotation(
        subject_ref="ptr-123", basis="medium not recorded at capture time"
    )
    assert ann["observation_medium"] == UNKNOWN
    assert ann["additive_only"] is True
    assert ann["modifies_subject"] is False
    assert ann["physical_efficacy_claimed"] is False
    verify_annotation(ann)


def test_annotation_requires_basis_and_subject():
    with pytest.raises(ValueError):
        build_medium_annotation(subject_ref="", basis="x")
    with pytest.raises(ValueError):
        build_medium_annotation(subject_ref="ptr-1", basis="")


def test_annotation_tamper_detected():
    ann = build_medium_annotation(
        subject_ref="ptr-1", basis="rig sheet", observation_medium=WORN_FABRIC
    )
    ann["observation_medium"] = IMAGE_COMPOSITE
    with pytest.raises(ValueError):
        verify_annotation(ann)


# --- versioned comparison on rendering-assumption change --------------------


def test_rendering_assumption_change_is_versioned_not_rewritten():
    old = build_medium_annotation(
        subject_ref="capture-7",
        basis="display render v1 assumptions",
        observation_medium=DISPLAY_PHOTOGRAPHED_BY_CAMERA,
        rendering_assumption_ref="render-assumptions-v1",
    )
    new = build_medium_annotation(
        subject_ref="capture-7",
        basis="display render v2 assumptions (tone-mapping corrected)",
        observation_medium=DISPLAY_PHOTOGRAPHED_BY_CAMERA,
        rendering_assumption_ref="render-assumptions-v2",
        supersedes_annotation_sha256=old["annotation_sha256"],
    )
    old_before = dict(old)
    comp = compare_rendering_assumptions(old, new)
    assert old == old_before  # old results never rewritten
    assert comp["old_results_rewritten"] is False
    assert comp["old_annotation_sha256"] == old["annotation_sha256"]
    assert comp["new_annotation_sha256"] == new["annotation_sha256"]


def test_comparison_requires_explicit_supersession():
    old = build_medium_annotation(subject_ref="c-1", basis="v1")
    new = build_medium_annotation(subject_ref="c-1", basis="v2")
    with pytest.raises(ValueError):
        compare_rendering_assumptions(old, new)


def test_comparison_requires_same_subject():
    old = build_medium_annotation(subject_ref="c-1", basis="v1")
    new = build_medium_annotation(
        subject_ref="c-2",
        basis="v2",
        supersedes_annotation_sha256=old["annotation_sha256"],
    )
    with pytest.raises(ValueError):
        compare_rendering_assumptions(old, new)

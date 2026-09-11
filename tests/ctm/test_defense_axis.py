"""Tests for SPEC-17 defense-intervention axis + SPEC-9 defense-dual (lane E)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.defense_axis import (
    DEFENSE_AXIS_SCHEMA_VERSION,
    DEFENSE_CLASSES,
    DUAL_STATUSES,
    NO_DEFENSE,
    DefenseAxisError,
    DefenseDual,
    DefenseObservation,
    DefenseRecord,
    collapse_to_base,
    compute_defended_delta,
    heterogeneity_by_defense_class,
    independent_replication_count,
    paired_brittleness_deltas,
    require_dual_evaluated_before_archival,
    require_not_independent_architecture,
    tensor_cell_id,
)

SHA = "a" * 64
SHA2 = "b" * 64


def _defense(**overrides):
    kwargs = dict(
        base_target_ref="target-yolov8-person",
        defense_id="patchguard-v1",
        defense_class="patch_detector",
        config_sha256=SHA,
        version="1.0.0",
    )
    kwargs.update(overrides)
    return DefenseRecord(**kwargs)


def _obs(defense=None, metrics=None, **overrides):
    kwargs = dict(
        pattern_ref="pattern-x",
        channel_id="channel-digital-ispA",
        condition_id="cond-frontal-1m",
        base_target_ref="target-yolov8-person",
        defense=defense,
        metrics=metrics if metrics is not None else {"asr": 0.8, "detection_rate": 0.9},
    )
    kwargs.update(overrides)
    return DefenseObservation(**kwargs)


# -- DefenseRecord --------------------------------------------------------------

def test_record_valid_deterministic_and_schema_conformant():
    rec = _defense()
    rec.validate_against_schema()
    assert rec.record_id == _defense().record_id
    assert rec.record_id.startswith("RAC-CTM-DEF-")
    assert rec.to_dict()["schema_version"] == DEFENSE_AXIS_SCHEMA_VERSION


@pytest.mark.parametrize("bad_class", ["nms_trick", "PATCH_DETECTOR", "", "magic"])
def test_record_unknown_defense_class_refused(bad_class):
    with pytest.raises(DefenseAxisError):
        _defense(defense_class=bad_class)


def test_record_classes_exactly_the_four_spec_values():
    assert DEFENSE_CLASSES == frozenset(
        {"patch_detector", "adversarial_training", "preprocessing", "other"}
    )


@pytest.mark.parametrize("bad_sha", ["A" * 64, "a" * 63, "z" * 64, 42, None])
def test_record_non_sha256_config_refused(bad_sha):
    with pytest.raises(DefenseAxisError):
        _defense(config_sha256=bad_sha)


def test_record_from_dict_roundtrip():
    rec = DefenseRecord.from_dict(_defense().to_dict())
    assert rec == _defense()


def test_record_from_dict_tampered_id_refused():
    payload = _defense().to_dict()
    payload["record_id"] = "RAC-CTM-DEF-" + "0" * 16
    with pytest.raises(DefenseAxisError):
        DefenseRecord.from_dict(payload)


def test_record_defended_target_ref_preserves_base():
    rec = _defense()
    assert rec.defended_target_ref.startswith("target-yolov8-person::def=")


# -- tensor cell identity ---------------------------------------------------------

def test_cell_identity_canonical_and_defense_bound():
    rec = _defense(base_target_ref="t")
    undef = tensor_cell_id(
        pattern_ref="p", base_target_ref="t", defense=None,
        channel_id="c", condition_id="k",
    )
    defended = tensor_cell_id(
        pattern_ref="p", base_target_ref="t", defense=rec,
        channel_id="c", condition_id="k",
    )
    assert undef != defended
    assert undef.startswith("RAC-CTM-CELL-")
    # config change = different cell
    other = tensor_cell_id(
        pattern_ref="p", base_target_ref="t",
        defense=_defense(base_target_ref="t", config_sha256=SHA2),
        channel_id="c", condition_id="k",
    )
    assert other != defended


def test_cell_rejects_cross_base_defense():
    with pytest.raises(DefenseAxisError):
        tensor_cell_id(
            pattern_ref="p", base_target_ref="other-target",
            defense=_defense(), channel_id="c", condition_id="k",
        )


def test_no_defense_sentinel():
    assert NO_DEFENSE == "none"


# -- replication counting -----------------------------------------------------------

def test_defended_variants_collapse_to_base_for_replication():
    d1 = _defense()
    d2 = _defense(defense_id="advtrain-v2", defense_class="adversarial_training")
    targets = ["target-yolov8-person", d1, d2, "target-faster-rcnn"]
    assert independent_replication_count(targets) == 2


def test_defended_target_ref_string_collapses():
    rec = _defense()
    assert collapse_to_base(rec.defended_target_ref) == "target-yolov8-person"
    assert collapse_to_base(rec) == "target-yolov8-person"
    assert collapse_to_base("plain-target") == "plain-target"


def test_independent_architecture_inflation_refused():
    with pytest.raises(DefenseAxisError):
        require_not_independent_architecture(
            _defense(), claimed_independent_count=3, prior_independent_count=2
        )
    # no raise when count is unchanged
    require_not_independent_architecture(
        _defense(), claimed_independent_count=2, prior_independent_count=2
    )


# -- paired deltas ------------------------------------------------------------------

def test_paired_delta_happy_path():
    base = _obs(metrics={"asr": 0.8})
    defended = _obs(defense=_defense(), metrics={"asr": 0.1})
    out = compute_defended_delta(base, defended, "asr")
    assert out["delta"] == pytest.approx(-0.7)
    assert out["paired"] is True
    assert out["pairing"] == "matched"
    assert out["defense_record_id"] == _defense().record_id


def test_delta_orientation_normalized():
    base = _obs(metrics={"asr": 0.8})
    defended = _obs(defense=_defense(), metrics={"asr": 0.1})
    out = compute_defended_delta(defended, base, "asr")
    assert out["delta"] == pytest.approx(-0.7)


def test_two_defended_observations_refused():
    a = _obs(defense=_defense())
    b = _obs(defense=_defense(defense_id="x", defense_class="preprocessing"))
    with pytest.raises(DefenseAxisError):
        compute_defended_delta(a, b, "asr")


def test_two_undefended_observations_refused():
    with pytest.raises(DefenseAxisError):
        compute_defended_delta(_obs(), _obs(), "asr")


@pytest.mark.parametrize(
    "mismatch",
    [
        {"pattern_ref": "other-pattern"},
        {"channel_id": "other-channel"},
        {"condition_id": "other-condition"},
        {"base_target_ref": "other-target"},
    ],
)
def test_unpaired_contrast_refused_by_default(mismatch):
    base = _obs()
    kwargs = dict(mismatch)
    if "base_target_ref" in kwargs:
        defended = _obs(
            defense=_defense(base_target_ref=kwargs["base_target_ref"]),
            base_target_ref=kwargs["base_target_ref"],
        )
    else:
        defended = _obs(defense=_defense(), **kwargs)
    with pytest.raises(DefenseAxisError):
        compute_defended_delta(base, defended, "asr")


def test_unpaired_contrast_labeled_when_allowed():
    base = _obs(channel_id="channel-A")
    defended = _obs(defense=_defense(), channel_id="channel-B")
    out = compute_defended_delta(base, defended, "asr", allow_unpaired=True)
    assert out["paired"] is False
    assert out["pairing"] == "unpaired_labeled"


def test_missing_metric_refused():
    base = _obs(metrics={"asr": 0.8})
    defended = _obs(defense=_defense(), metrics={"detection_rate": 0.5})
    with pytest.raises(DefenseAxisError):
        compute_defended_delta(base, defended, "asr")


def test_paired_brittleness_deltas_full():
    base = _obs(metrics={
        "asr": 0.8, "detection_rate": 0.9,
        "patch_scale_success": 0.7, "garment_scale_success": 0.3,
    })
    defended = _obs(defense=_defense(), metrics={
        "asr": 0.1, "detection_rate": 0.95,
        "patch_scale_success": 0.2, "garment_scale_success": 0.05,
    })
    out = paired_brittleness_deltas(base, defended)
    assert out["deltas"]["delta_asr_defended_vs_base"]["delta"] == pytest.approx(-0.7)
    assert (
        out["deltas"]["delta_detection_rate_defended_vs_base"]["delta"]
        == pytest.approx(0.05)
    )
    scale = out["deltas"]["patch_vs_garment_scale_gap_shift"]
    assert scale["base_value"] == pytest.approx(0.4)
    assert scale["defended_value"] == pytest.approx(0.15)


def test_brittleness_no_shared_metrics_refused():
    with pytest.raises(DefenseAxisError):
        paired_brittleness_deltas(
            _obs(metrics={"weird": 1.0}),
            _obs(defense=_defense(), metrics={"other": 2.0}),
        )


def test_heterogeneity_buckets_separate_unpaired():
    paired = compute_defended_delta(
        _obs(metrics={"asr": 0.8}), _obs(defense=_defense(), metrics={"asr": 0.1}), "asr"
    )
    unpaired = compute_defended_delta(
        _obs(channel_id="A", metrics={"asr": 0.8}),
        _obs(defense=_defense(), channel_id="B", metrics={"asr": 0.2}),
        "asr",
        allow_unpaired=True,
    )
    grouped = heterogeneity_by_defense_class([paired, unpaired])
    assert any(k.startswith("unpaired::") for k in grouped)
    assert any(not k.startswith("unpaired::") for k in grouped)


# -- SPEC-9 defense dual -------------------------------------------------------------

def test_dual_defaults_unevaluated():
    dual = DefenseDual(principle="topological stability", certification_form="stability bound")
    assert dual.status == "unevaluated"
    assert dual.to_dict()["principle"] == "topological stability"


def test_dual_status_enum_exact():
    assert DUAL_STATUSES == frozenset(
        {"unevaluated", "certified", "rejected", "not_applicable"}
    )
    with pytest.raises(DefenseAxisError):
        DefenseDual(principle="p", certification_form="c", status="maybe")


def _evaluated_dual():
    return DefenseDual(
        principle="topological stability",
        certification_form="transformation-group worst-case bound",
        status="certified",
    )


def test_rejected_attack_requires_evaluated_dual():
    with pytest.raises(DefenseAxisError):
        require_dual_evaluated_before_archival(
            "REJECTED",
            DefenseDual(principle="p", certification_form="c"),
            high_heterogeneity_threshold=0.5,
        )
    # evaluated dual passes
    require_dual_evaluated_before_archival(
        "REJECTED", _evaluated_dual(), high_heterogeneity_threshold=0.5
    )


def test_high_heterogeneity_requires_evaluated_dual():
    with pytest.raises(DefenseAxisError):
        require_dual_evaluated_before_archival(
            "CONFIRMED",
            DefenseDual(principle="p", certification_form="c"),
            heterogeneity=0.8,
            high_heterogeneity_threshold=0.5,
        )
    # below threshold: no requirement
    require_dual_evaluated_before_archival(
        "CONFIRMED",
        DefenseDual(principle="p", certification_form="c"),
        heterogeneity=0.3,
        high_heterogeneity_threshold=0.5,
    )


def test_confirmed_low_heterogeneity_heuristic_archivable_with_unevaluated_dual():
    require_dual_evaluated_before_archival(
        "CONFIRMED",
        DefenseDual(principle="p", certification_form="c"),
        heterogeneity=0.1,
        high_heterogeneity_threshold=0.5,
    )


def test_threshold_must_be_explicit_and_numeric():
    with pytest.raises(DefenseAxisError):
        require_dual_evaluated_before_archival(
            "REJECTED", _evaluated_dual(), high_heterogeneity_threshold="high"
        )

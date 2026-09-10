"""Tests for SPEC-11 mechanism-class tagging and head-class panel axis (lane B)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.target_semantics import (
    HEAD_CLASSES,
    MECHANISM_CLASSES,
    TARGET_SEMANTICS_SCHEMA_VERSION,
    MechanismTag,
    TargetSemantics,
    TargetSemanticsError,
    expected_generality,
    is_architecture_accident_bound,
    require_not_identity_collapse,
)

THRESH = "a" * 64
THRESH2 = "b" * 64


def _target(**overrides):
    kwargs = dict(
        target_id="yolov8n-coco",
        architecture="yolov8n",
        weights_ref="weights/yolov8n.pt",
        head_class="nms_based",
        threshold_config_sha256=THRESH,
    )
    kwargs.update(overrides)
    return TargetSemantics(**kwargs)


# -- positive / derivation ------------------------------------------------------

def test_mechanism_enum_is_exact_spec11():
    assert MECHANISM_CLASSES == frozenset({
        "task_invariant", "training_data", "pipeline_structure",
        "physics", "hardware", "architecture_accident",
    })


def test_head_class_enum_is_exact_spec11():
    assert HEAD_CLASSES == frozenset({"nms_based", "nms_free"})


def test_valid_target_record():
    rec = _target()
    assert rec.stratification_label() == "nms_based"
    assert rec.stratification_covariates == {"head_class": "nms_based"}
    rec.validate_against_schema()


def test_schema_validation_roundtrip_and_determinism():
    a = _target()
    b = TargetSemantics.from_dict(a.to_dict())
    assert a.canonical_bytes() == b.canonical_bytes()
    assert a.target_semantics_sha256() == b.target_semantics_sha256()


def test_threshold_config_binds_identity():
    a = _target()
    b = _target(threshold_config_sha256=THRESH2)
    assert a.target_identity_sha256() != b.target_identity_sha256()
    assert a.target_semantics_sha256() != b.target_semantics_sha256()


def test_head_class_is_covariate_not_identity():
    # Same target evaluated with a different head-class annotation keeps the
    # same identity hash: head_class never enters identity.
    a = _target(head_class="nms_based")
    b = _target(head_class="nms_free")
    assert a.target_identity_sha256() == b.target_identity_sha256()
    assert a.stratification_label() != b.stratification_label()


def test_identity_collapse_refused():
    for hc in HEAD_CLASSES:
        with pytest.raises(TargetSemanticsError):
            require_not_identity_collapse(hc)
        with pytest.raises(TargetSemanticsError):
            _target(target_id=hc)
    require_not_identity_collapse("yolov8n-coco")


# -- mechanism tags ---------------------------------------------------------------

def test_mechanism_tag_positive():
    tag = MechanismTag(mechanism_class="task_invariant")
    assert tag.architecture_accident_bound is False
    assert tag.to_dict()["architecture_accident_bound"] is False


def test_architecture_accident_has_lower_expected_generality():
    assert expected_generality("architecture_accident") < expected_generality("task_invariant")
    assert is_architecture_accident_bound("architecture_accident") is True
    assert is_architecture_accident_bound("task_invariant") is False
    # all six classes resolve deterministically
    for mc in MECHANISM_CLASSES:
        assert isinstance(expected_generality(mc), int)


# -- fail-closed validation ---------------------------------------------------------

def test_missing_mechanism_class_fails_closed():
    with pytest.raises(TargetSemanticsError):
        MechanismTag(mechanism_class="")


def test_invalid_mechanism_class_fails_closed():
    with pytest.raises(TargetSemanticsError):
        MechanismTag(mechanism_class="family_yolo")
    with pytest.raises(TargetSemanticsError):
        expected_generality("family_yolo")


def test_missing_head_class_fails_closed():
    with pytest.raises(TargetSemanticsError):
        _target(head_class="")


def test_invalid_head_class_fails_closed():
    with pytest.raises(TargetSemanticsError):
        _target(head_class="anchor_based")


def test_missing_threshold_config_fails_closed():
    with pytest.raises(TargetSemanticsError):
        _target(threshold_config_sha256="")


def test_malformed_threshold_config_fails_closed():
    with pytest.raises(TargetSemanticsError):
        _target(threshold_config_sha256="A" * 64)  # uppercase
    with pytest.raises(TargetSemanticsError):
        _target(threshold_config_sha256="a" * 63)  # wrong length


def test_missing_target_id_fails_closed():
    with pytest.raises(TargetSemanticsError):
        _target(target_id="")


def test_bad_schema_version_fails_closed():
    with pytest.raises(TargetSemanticsError):
        _target(schema_version="rac-ctm-target-semantics/0.9")


def test_user_asserted_identity_hash_disagreeing_fails_closed():
    d = _target().to_dict()
    d["target_identity_sha256"] = "0" * 64
    with pytest.raises(TargetSemanticsError):
        TargetSemantics.from_dict(d)


def test_version_string():
    assert TARGET_SEMANTICS_SCHEMA_VERSION == "rac-ctm-target-semantics/1.0"

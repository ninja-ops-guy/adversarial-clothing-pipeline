"""Corrective integration tests for the CTM Lane-A hardening pass."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.errors import OptimizerConstraintsError
from ruthless_pipeline.ctm.evaluation_surface import (
    GOODHART_EXPOSURE_SCHEMA_VERSION,
    derive_evaluation_surface,
    derive_manifest_evaluation_surface,
)
from ruthless_pipeline.ctm.manifests import (
    CTM_MANIFEST_SCHEMA_VERSION_V11,
    CTMExperimentManifest,
)
from ruthless_pipeline.ctm.optimizer_constraints import OptimizerConstraints

DUMMY_SHA = "a" * 64


def _audit(**overrides):
    value = {
        "decision_thresholds": [0.5],
        "threshold_regime": "fixed",
        "frames_per_sample": 1,
        "firewall_attestation_ref": DUMMY_SHA,
        "goodhart_guard": "narrative-only context; derivation must ignore this text",
    }
    value.update(overrides)
    return value


def test_fixed_single_frame_surface_is_derived_without_prose_parsing():
    surface = derive_evaluation_surface(_audit())
    assert surface.threshold_regime == "fixed"
    assert surface.threshold_count == 1
    assert surface.temporal_regime == "single_frame"
    assert surface.frames_per_sample == 1
    assert "fixed_threshold_selection_surface" in surface.potential_goodhart_surfaces
    assert "single_frame_selection_surface" in surface.potential_goodhart_surfaces
    assert surface.schema_version == GOODHART_EXPOSURE_SCHEMA_VERSION


def test_guard_text_cannot_change_machine_derived_surface():
    a = derive_evaluation_surface(_audit(goodhart_guard="claim A"))
    b = derive_evaluation_surface(_audit(goodhart_guard="opposite prose"))
    assert a.canonical_bytes() == b.canonical_bytes()


def test_swept_sequence_surface_is_distinct():
    surface = derive_evaluation_surface(
        _audit(
            decision_thresholds=[0.3, 0.5, 0.7],
            threshold_regime="swept",
            frames_per_sample=8,
        )
    )
    assert surface.threshold_count == 3
    assert surface.temporal_regime == "sequence"
    assert "threshold_sweep_selection_surface" in surface.potential_goodhart_surfaces
    assert "single_frame_selection_surface" not in surface.potential_goodhart_surfaces


def test_duplicate_values_do_not_fake_a_threshold_sweep():
    with pytest.raises(ValueError, match="distinct thresholds"):
        derive_evaluation_surface(
            _audit(decision_thresholds=[0.5, 0.5], threshold_regime="swept")
        )


def test_nonfinite_thresholds_fail_closed():
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite numbers"):
            derive_evaluation_surface(_audit(decision_thresholds=[bad]))


def test_manifest_adapter_derives_without_altering_manifest_payload():
    manifest = CTMExperimentManifest(
        experiment_id="CTM-E-000901",
        title="derived evaluation-surface test",
        design={"cells": 1},
        seed=1,
        created_utc="2026-09-10T00:00:00Z",
        schema_version=CTM_MANIFEST_SCHEMA_VERSION_V11,
        evaluation_audit=_audit(),
    )
    before = manifest.canonical_bytes()
    surface = derive_manifest_evaluation_surface(manifest)
    after = manifest.canonical_bytes()
    assert surface.threshold_regime == "fixed"
    assert before == after
    assert b"potential_goodhart_surfaces" not in after


def test_manifest_without_audit_has_no_derived_surface():
    manifest = CTMExperimentManifest(
        experiment_id="CTM-E-000902",
        title="legacy manifest",
        design={},
        seed=1,
        created_utc="2026-09-10T00:00:00Z",
    )
    with pytest.raises(ValueError, match="no evaluation_audit"):
        derive_manifest_evaluation_surface(manifest)


def test_unknown_regularizer_requires_parameterization():
    with pytest.raises(OptimizerConstraintsError, match="requires explicit"):
        OptimizerConstraints(regularizers=({"name": "new_regularizer", "parameters": {}},))


def test_unknown_structural_constraint_requires_parameterization():
    with pytest.raises(OptimizerConstraintsError, match="requires explicit"):
        OptimizerConstraints(
            structural_constraints=({"name": "new_structure", "parameters": {}},)
        )


def test_unknown_constraint_is_legal_when_explicitly_parameterized():
    constraints = OptimizerConstraints(
        structural_constraints=(
            {"name": "new_structure", "parameters": {"strength": 0.25}},
        )
    )
    assert constraints.to_dict()["structural_constraints"][0]["parameters"] == {
        "strength": 0.25
    }

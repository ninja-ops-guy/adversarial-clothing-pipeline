"""Tests for SPEC-13 cascade-stage scope labels (lane C)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.pipeline_stage import (
    CLAIM_SCOPE_SCHEMA_VERSION,
    PIPELINE_STAGES,
    ClaimScope,
    PipelineStageError,
    ScopeConformanceError,
    check_prose_scope,
    require_cross_domain_bridge,
    require_prose_conformant,
)


def _scope(**overrides):
    kwargs = dict(
        claim_id="claim-1",
        claim_kind="efficacy",
        pipeline_stages=("person_detection",),
    )
    kwargs.update(overrides)
    return ClaimScope(**kwargs)


# -- positive ----------------------------------------------------------------

def test_scope_roundtrip_schema_and_determinism():
    scope = _scope()
    scope.validate_against_schema()
    assert ClaimScope.from_dict(scope.to_dict()) == scope
    assert scope.claim_scope_sha256() == _scope().claim_scope_sha256()


def test_stage_enum_exact():
    assert PIPELINE_STAGES == frozenset({
        "person_detection", "face_detection", "face_recognition",
        "reid_tracking", "fusion",
    })


def test_multi_stage_with_basis_ok():
    scope = _scope(
        pipeline_stages=("person_detection", "face_detection"),
        multi_stage_basis="Independent panels on both stages; no fusion claim.",
    )
    scope.validate_against_schema()


def test_fusion_scope_allows_stage_mentions_in_prose():
    scope = _scope(pipeline_stages=("fusion",))
    assert check_prose_scope(
        "The garment disrupts person detection and face detection across the cascade.",
        scope,
    ) == []


def test_conformant_prose_passes():
    scope = _scope()
    require_prose_conformant(
        "The pattern reduces person detection rate in the digital tier.", scope
    )


def test_broad_term_with_stage_bound_ok():
    scope = _scope()
    assert check_prose_scope(
        "Evasion of person detection specifically, not of the full pipeline.", scope
    ) == []


def test_cross_domain_bridge_explicit_ok():
    scope = _scope(
        pipeline_stages=("face_recognition", "person_detection"),
        multi_stage_basis="Explicit bridge: shared texture-reliance mechanism.",
    )
    require_cross_domain_bridge(scope, source_stage="face_recognition", bridged=True)


# -- negative / fail-closed ---------------------------------------------------

def test_efficacy_claim_without_stage_fails():
    with pytest.raises(PipelineStageError):
        _scope(pipeline_stages=())


def test_transfer_claim_without_stage_fails():
    with pytest.raises(PipelineStageError):
        _scope(claim_kind="transfer", pipeline_stages=())


def test_unknown_stage_fails():
    with pytest.raises(PipelineStageError):
        _scope(pipeline_stages=("voice_recognition",))


def test_multi_stage_without_basis_fails():
    with pytest.raises(PipelineStageError):
        _scope(pipeline_stages=("person_detection", "face_detection"))


def test_fusion_mixed_with_stages_fails():
    with pytest.raises(PipelineStageError):
        _scope(pipeline_stages=("fusion", "person_detection"))


def test_prose_exceeding_scope_refused():
    scope = _scope()
    violations = check_prose_scope(
        "The garment defeats person detection and face recognition.", scope
    )
    assert violations
    with pytest.raises(ScopeConformanceError):
        require_prose_conformant(
            "The garment defeats person detection and face recognition.", scope
        )


def test_broad_term_without_stage_bound_flagged():
    scope = _scope()
    violations = check_prose_scope("This renders the wearer invisible.", scope)
    assert any("broad term" in v for v in violations)


def test_fr_result_cannot_inherit_person_detection_without_bridge():
    scope = _scope()  # person_detection scope, FR-sourced result
    with pytest.raises(ScopeConformanceError):
        require_cross_domain_bridge(
            scope, source_stage="face_recognition", bridged=False
        )


def test_version_string():
    assert CLAIM_SCOPE_SCHEMA_VERSION == "rac-ctm-claim-scope/1.0"

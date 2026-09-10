from __future__ import annotations

import pytest

from ruthless_pipeline.ctm import (
    CTMArtifactRole,
    CTMArtifactUse,
    CTMClaim,
    CTMClaimState,
    MatchedNullDesign,
    MatchedNullType,
    certify_ctm_claim,
)

H = "a" * 64
H2 = "b" * 64
H3 = "c" * 64


def art(artifact_id: str, role: CTMArtifactRole, **kw) -> CTMArtifactUse:
    return CTMArtifactUse(
        artifact_id=artifact_id,
        role=role,
        sha256=kw.get("sha256", H),
        heldout_access=kw.get("heldout_access", False),
        heldout_feedback_used=kw.get("heldout_feedback_used", False),
        selection_influence=kw.get(
            "selection_influence",
            "SURROGATE_ONLY" if role in {
                CTMArtifactRole.DOE,
                CTMArtifactRole.GENERATOR,
                CTMArtifactRole.ACCEPTANCE,
            } else "NOT_APPLICABLE",
        ),
    )


def graph(nodes, edges):
    return {"nodes": nodes, "edges": edges}


def clean_claim(state=CTMClaimState.CORRELATION, cohorts=1, null_ids=()):
    return CTMClaim(
        claim_id="CTM-CLAIM-001",
        state=state,
        feature_id="pattern_genome.high_frequency_ratio",
        outcome_id="transfer.delta_detection_rate",
        source_commit="deadbeef",
        independent_cohort_count=cohorts,
        matched_null_design_ids=tuple(null_ids),
        consumed_artifacts=(
            art("doe:001", CTMArtifactRole.DOE),
            art("generator:001", CTMArtifactRole.GENERATOR),
            art("acceptance:001", CTMArtifactRole.ACCEPTANCE),
        ),
    )


def matched_null(null_id="NULL-001"):
    return MatchedNullDesign(
        null_id=null_id,
        null_type=MatchedNullType.COLOR,
        candidate_sha256=H,
        null_sha256=H2,
        manipulated_feature="spectral.high_frequency_ratio",
        matched_properties=("color.lab_mean", "topology.fragmentation_index"),
        tolerance_contract_sha256=H3,
        design_commit="deadbeef",
    )


def test_clean_firewall_certifies_correlation():
    claim = clean_claim()
    g = graph(
        [
            {"id": "doe:001", "ctm_role": "doe", "sha256": H},
            {"id": "generator:001", "ctm_role": "generator", "sha256": H},
            {"id": "acceptance:001", "ctm_role": "acceptance", "sha256": H},
            {"id": "surrogate:001", "ctm_role": "surrogate_observation", "sha256": H2},
        ],
        [
            {"source": "doe:001", "target": "surrogate:001", "edge_type": "uses_surrogate_observation"},
            {"source": "generator:001", "target": "doe:001", "edge_type": "generated_from"},
            {"source": "acceptance:001", "target": "generator:001", "edge_type": "accepted_by"},
        ],
    )
    result = certify_ctm_claim(claim, provenance_graph=g)
    assert result.certified is True
    assert result.firewall.ok is True


def test_firewall_is_certification_failure_not_policy():
    claim = clean_claim()
    g = graph(
        [
            {"id": "doe:001", "ctm_role": "doe"},
            {"id": "generator:001", "ctm_role": "generator"},
            {"id": "acceptance:001", "ctm_role": "acceptance"},
            {"id": "heldout:001", "ctm_role": "heldout_observation", "sha256": H2},
        ],
        [
            {"source": "generator:001", "target": "heldout:001", "edge_type": "derived_from"},
        ],
    )
    with pytest.raises(ValueError, match="certification firewall failure"):
        certify_ctm_claim(claim, provenance_graph=g)


def test_indirect_heldout_path_is_detected():
    claim = clean_claim()
    g = graph(
        [
            {"id": "doe:001", "ctm_role": "doe"},
            {"id": "generator:001", "ctm_role": "generator"},
            {"id": "acceptance:001", "ctm_role": "acceptance"},
            {"id": "mid:001", "ctm_role": "genome", "sha256": H2},
            {"id": "heldout:001", "data_split": "heldout", "sha256": H3},
        ],
        [
            {"source": "doe:001", "target": "mid:001", "edge_type": "consumes"},
            {"source": "mid:001", "target": "heldout:001", "edge_type": "derived_from"},
        ],
    )
    with pytest.raises(ValueError, match="doe:001 -> mid:001 -> heldout:001"):
        certify_ctm_claim(claim, provenance_graph=g)


def test_direct_anti_optimization_flag_refuses_even_without_graph_edge():
    claim = CTMClaim(
        claim_id="CTM-CLAIM-002",
        state=CTMClaimState.CORRELATION,
        feature_id="f",
        outcome_id="y",
        source_commit="deadbeef",
        consumed_artifacts=(
            art("generator:bad", CTMArtifactRole.GENERATOR, heldout_access=True),
        ),
    )
    with pytest.raises(ValueError, match="anti-optimization invariant"):
        certify_ctm_claim(claim, provenance_graph=graph([], []))


def test_association_requires_replication():
    with pytest.raises(ValueError, match=">=2 independent cohorts"):
        clean_claim(state=CTMClaimState.ASSOCIATION, cohorts=1).validate()


def test_five_unmatched_cohorts_cannot_promote_to_controlled_effect():
    with pytest.raises(ValueError, match="matched-property null presence"):
        clean_claim(state=CTMClaimState.CONTROLLED_EFFECT, cohorts=5).validate()


def test_controlled_effect_requires_referenced_matched_null_to_exist():
    claim = clean_claim(
        state=CTMClaimState.CONTROLLED_EFFECT,
        cohorts=2,
        null_ids=("NULL-001",),
    )
    clean_roots = graph(
        [
            {"id": "doe:001", "ctm_role": "doe", "sha256": H},
            {"id": "generator:001", "ctm_role": "generator", "sha256": H},
            {"id": "acceptance:001", "ctm_role": "acceptance", "sha256": H},
        ],
        [],
    )
    with pytest.raises(ValueError, match="missing matched-null"):
        certify_ctm_claim(claim, provenance_graph=clean_roots, matched_nulls=())


def test_controlled_effect_with_matched_null_certifies():
    claim = clean_claim(
        state=CTMClaimState.CONTROLLED_EFFECT,
        cohorts=2,
        null_ids=("NULL-001",),
    )
    result = certify_ctm_claim(
        claim,
        provenance_graph=graph(
            [
                {"id": "doe:001", "ctm_role": "doe", "sha256": H},
                {"id": "generator:001", "ctm_role": "generator", "sha256": H},
                {"id": "acceptance:001", "ctm_role": "acceptance", "sha256": H},
            ],
            [],
        ),
        matched_nulls=(matched_null(),),
    )
    assert result.certified is True
    assert result.matched_nulls_verified == ("NULL-001",)


def test_null_candidate_and_control_must_differ():
    bad = MatchedNullDesign(
        null_id="NULL-BAD",
        null_type=MatchedNullType.SPECTRAL,
        candidate_sha256=H,
        null_sha256=H,
        manipulated_feature="color.lab_mean",
        matched_properties=("spectral.high_frequency_ratio",),
        tolerance_contract_sha256=H3,
        design_commit="deadbeef",
    )
    with pytest.raises(ValueError, match="must not be byte-identical"):
        bad.validate()


def test_manipulated_feature_cannot_be_listed_as_matched():
    bad = MatchedNullDesign(
        null_id="NULL-BAD",
        null_type=MatchedNullType.TOPOLOGY,
        candidate_sha256=H,
        null_sha256=H2,
        manipulated_feature="topology.fragmentation_index",
        matched_properties=("topology.fragmentation_index",),
        tolerance_contract_sha256=H3,
        design_commit="deadbeef",
    )
    with pytest.raises(ValueError, match="cannot also be declared matched"):
        bad.validate()


def test_missing_pre_outcome_root_is_certification_failure():
    with pytest.raises(ValueError, match="missing roots"):
        certify_ctm_claim(clean_claim(), provenance_graph=graph([], []))


def test_pre_outcome_hash_mismatch_is_certification_failure():
    claim = clean_claim()
    g = graph(
        [
            {"id": "doe:001", "ctm_role": "doe", "sha256": H2},
            {"id": "generator:001", "ctm_role": "generator", "sha256": H},
            {"id": "acceptance:001", "ctm_role": "acceptance", "sha256": H},
        ],
        [],
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        certify_ctm_claim(claim, provenance_graph=g)

from __future__ import annotations

import pytest

from ruthless_pipeline.residual_integration import (
    DEFAULT_FORBIDDEN_CAPABILITIES,
    RACImprovementDecision,
    RACImprovementSpec,
    RACEvidenceBundle,
    RACResidualContractError,
    build_residual_candidate,
    evaluate_improvement,
)


SHA = "a" * 64
REV = "b" * 40


def _spec() -> RACImprovementSpec:
    return RACImprovementSpec(
        spec_id="RAC-I-000001",
        hypothesis_id="RAC-H-000001",
        baseline_revision=REV,
        target_component="ruthless_pipeline.pattern_genome",
        proposed_change="Test one bounded implementation change.",
        evaluation_version="RAC-EVAL-004",
        acceptance={"metric": {"max_regression": 0.0}},
        falsification={"metric": {"min_regression": 0.01}},
        created_utc="2026-09-18T00:00:00Z",
    )


def _evidence(
    spec: RACImprovementSpec,
    index: int,
    *,
    outcome: str = "PASS",
    replication_id: str = "replication-a",
    verifier_id: str = "verifier-a",
) -> RACEvidenceBundle:
    return RACEvidenceBundle(
        evidence_id=f"RAC-EV-{index:06d}",
        spec_sha256=spec.content_sha256,
        source_revision=REV,
        evaluation_version=spec.evaluation_version,
        experiment_manifest_sha256=SHA,
        firewall_attestation_sha256=SHA,
        artifact_sha256s=(SHA,),
        outcome=outcome,
        producer_id="worker-a",
        independent_verifier_id=verifier_id,
        replication_id=replication_id,
    )


def test_improvement_spec_is_deeply_immutable() -> None:
    spec = _spec()
    before = spec.content_sha256
    with pytest.raises(TypeError):
        spec.acceptance["metric"]["max_regression"] = 9.0
    assert spec.content_sha256 == before


def test_mandatory_forbidden_capabilities_cannot_be_removed() -> None:
    assert "held_out_candidate_selection" in DEFAULT_FORBIDDEN_CAPABILITIES
    with pytest.raises(RACResidualContractError):
        RACImprovementSpec(
            spec_id="RAC-I-000001",
            hypothesis_id="RAC-H-000001",
            baseline_revision=REV,
            target_component="component",
            proposed_change="bounded change",
            evaluation_version="RAC-EVAL-004",
            acceptance={"a": 1},
            falsification={"b": 1},
            created_utc="2026-09-18T00:00:00Z",
            forbidden_capabilities=("automatic_scientific_promotion",),
        )


def test_fail_is_retained_and_rejects_improvement() -> None:
    spec = _spec()
    failed = _evidence(spec, 1, outcome="FAIL")
    decision = evaluate_improvement(
        spec, [failed], decision_id="RAC-D-000001"
    )
    assert decision.status == "REJECTED"
    assert decision.evidence_sha256s == (failed.content_sha256,)


def test_promotable_requires_replication_and_independent_verifiers() -> None:
    spec = _spec()
    first = _evidence(
        spec, 1, replication_id="replication-a", verifier_id="verifier-a"
    )
    same_replication = _evidence(
        spec, 2, replication_id="replication-a", verifier_id="verifier-a"
    )
    decision = evaluate_improvement(
        spec, [first, same_replication], decision_id="RAC-D-000002"
    )
    assert decision.status == "INCONCLUSIVE"

    second = _evidence(
        spec, 3, replication_id="replication-b", verifier_id="verifier-b"
    )
    decision = evaluate_improvement(
        spec, [first, second], decision_id="RAC-D-000003"
    )
    assert decision.status == "PROMOTABLE"


def test_promotable_is_still_advisory_and_human_gated() -> None:
    spec = _spec()
    first = _evidence(
        spec, 1, replication_id="replication-a", verifier_id="verifier-a"
    )
    second = _evidence(
        spec, 2, replication_id="replication-b", verifier_id="verifier-b"
    )
    decision = evaluate_improvement(
        spec, [first, second], decision_id="RAC-D-000004"
    )
    assert decision.human_gate_required is True
    assert decision.automation_may_promote is False

    candidate = build_residual_candidate(spec, [first, second], decision)
    assert candidate["authority"] == {
        "advisory_only": True,
        "human_gate_required": True,
        "automatic_promotion_forbidden": True,
    }


def test_evaluation_version_drift_is_refused() -> None:
    spec = _spec()
    drifted = RACEvidenceBundle(
        evidence_id="RAC-EV-000010",
        spec_sha256=spec.content_sha256,
        source_revision=REV,
        evaluation_version="RAC-EVAL-005",
        experiment_manifest_sha256=SHA,
        firewall_attestation_sha256=SHA,
        artifact_sha256s=(SHA,),
        outcome="PASS",
        producer_id="worker-a",
        independent_verifier_id="verifier-a",
        replication_id="replication-a",
    )
    with pytest.raises(RACResidualContractError):
        evaluate_improvement(
            spec, [drifted], decision_id="RAC-D-000005"
        )


def test_producer_cannot_self_verify() -> None:
    spec = _spec()
    with pytest.raises(RACResidualContractError):
        RACEvidenceBundle(
            evidence_id="RAC-EV-000011",
            spec_sha256=spec.content_sha256,
            source_revision=REV,
            evaluation_version=spec.evaluation_version,
            experiment_manifest_sha256=SHA,
            firewall_attestation_sha256=SHA,
            artifact_sha256s=(SHA,),
            outcome="PASS",
            producer_id="worker-a",
            independent_verifier_id="worker-a",
            replication_id="replication-a",
        )


def test_candidate_rejects_decision_evidence_mismatch() -> None:
    spec = _spec()
    evidence = _evidence(spec, 12)
    decision = RACImprovementDecision(
        decision_id="RAC-D-000006",
        spec_sha256=spec.content_sha256,
        evidence_sha256s=(),
        status="INCONCLUSIVE",
        reason="insufficient evidence",
    )
    with pytest.raises(RACResidualContractError):
        build_residual_candidate(spec, [evidence], decision)

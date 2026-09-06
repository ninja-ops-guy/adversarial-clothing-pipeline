import pytest

from ruthless_pipeline.certification.evidence import (
    BenchmarkObservation,
    EvidenceRecord,
    EvidenceType,
    ObservationStatus,
    eligible_values,
    require_evidence_for_state,
    validate_transition,
)
from ruthless_pipeline.certification.manifest import EvidenceState


SHA256 = "a" * 64


def record(
    state: EvidenceState,
    evidence_type: EvidenceType,
) -> EvidenceRecord:
    model_metadata = {}
    if evidence_type == EvidenceType.DIGITAL:
        model_metadata = {
            "models": ["fixture-model"],
            "preprocessing": {"resize": 640},
            "thresholds": {"confidence": 0.5},
        }
    return EvidenceRecord(
        rac_state=state,
        evidence_type=evidence_type,
        source="pytest",
        fixture_type="digital_fixture",
        created_at="2026-09-06T17:44:00-04:00",
        code_commit="deadbeef",
        configuration={"seed": 42},
        artifact_hashes={"pattern.png": SHA256},
        model_metadata=model_metadata,
    )


def test_adjacent_forward_transition_is_allowed() -> None:
    validate_transition(EvidenceState.DESIGN, EvidenceState.SURROGATE)
    validate_transition(EvidenceState.DIGITAL_HELDOUT, EvidenceState.PHYSICAL)


def test_skipped_and_reverse_transitions_fail_closed() -> None:
    with pytest.raises(ValueError, match="illegal RAC transition"):
        validate_transition(EvidenceState.DESIGN, EvidenceState.DIGITAL_HELDOUT)
    with pytest.raises(ValueError, match="illegal RAC transition"):
        validate_transition(EvidenceState.PHYSICAL, EvidenceState.DIGITAL_HELDOUT)


def test_digital_evidence_cannot_claim_physical_state() -> None:
    evidence = record(EvidenceState.PHYSICAL, EvidenceType.DIGITAL)
    with pytest.raises(ValueError, match="requires evidence_type=physical"):
        evidence.validate()


def test_physical_evidence_cannot_claim_manufacturing_state() -> None:
    evidence = record(EvidenceState.GOLDEN_SAMPLE, EvidenceType.PHYSICAL)
    with pytest.raises(ValueError, match="requires evidence_type=manufacturing"):
        evidence.validate()


def test_malformed_sha256_is_rejected() -> None:
    evidence = EvidenceRecord(
        rac_state=EvidenceState.DESIGN,
        evidence_type=EvidenceType.DIGITAL,
        source="pytest",
        fixture_type="digital_fixture",
        created_at="2026-09-06T17:44:00-04:00",
        code_commit="deadbeef",
        configuration={},
        artifact_hashes={"pattern.png": "not-a-hash"},
    )
    with pytest.raises(ValueError, match="invalid SHA-256"):
        evidence.validate()


def test_invalid_observations_are_excluded_from_aggregates() -> None:
    observations = [
        BenchmarkObservation(0.8, ObservationStatus.VALID),
        BenchmarkObservation(
            1.0,
            ObservationStatus.INVALID,
            invalid_reason="control_not_detected",
        ),
        BenchmarkObservation(0.2, ObservationStatus.EXCLUDED),
    ]
    assert eligible_values(observations) == [0.8]


def test_invalid_observation_requires_reason() -> None:
    observation = BenchmarkObservation(1.0, ObservationStatus.INVALID)
    with pytest.raises(ValueError, match="invalid_reason"):
        observation.validate()


def test_physical_state_requires_physical_evidence() -> None:
    digital = record(EvidenceState.DIGITAL_HELDOUT, EvidenceType.DIGITAL)
    with pytest.raises(ValueError, match="requires physical evidence"):
        require_evidence_for_state(EvidenceState.PHYSICAL, [digital])


def test_manufacturing_state_requires_physical_and_manufacturing_evidence() -> None:
    manufacturing = record(
        EvidenceState.GOLDEN_SAMPLE,
        EvidenceType.MANUFACTURING,
    )
    with pytest.raises(ValueError, match="requires prior physical evidence"):
        require_evidence_for_state(EvidenceState.GOLDEN_SAMPLE, [manufacturing])

    physical = record(EvidenceState.PHYSICAL, EvidenceType.PHYSICAL)
    require_evidence_for_state(
        EvidenceState.GOLDEN_SAMPLE,
        [physical, manufacturing],
    )


def test_nonfinite_benchmark_observations_are_rejected() -> None:
    observation = BenchmarkObservation(float("nan"), ObservationStatus.VALID)
    with pytest.raises(ValueError, match="must be finite"):
        observation.validate()

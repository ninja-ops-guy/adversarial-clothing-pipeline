"""NR-01 evaluation-exposure and feature-provenance tests.

Acceptance fixtures:
(i)   a cohort whose evaluation output influenced later candidate selection
      can never receive an INDEPENDENT_CONFIRMATION label for that same cohort;
(ii)  a feature computed from prohibited outcome labels fails provenance review;
(iii) identity disjointness and calibration isolation are necessary-but-distinct
      checks (each fails closed on its own axis while the other passes).
"""

from hashlib import sha256
import json

import pytest

from ruthless_pipeline.governance.evaluation_exposure import (
    ConfirmationLabel,
    CohortOutputClass,
    EvaluationExposureError,
    EvaluationExposureLedger,
    ExposureEvent,
    FeatureProvenance,
    FeatureSource,
    FeatureSourceRole,
    issue_independent_confirmation_label,
    review_feature_provenance,
)
from ruthless_pipeline.governance.seal import seal_cohort
from ruthless_pipeline.governance.sentinel import (
    CalibrationState,
    EvaluationPipeline,
    PreprocessingMode,
    SentinelGovernanceError,
    create_sentinel,
    validate_blind_sentinel_evaluation,
)

H_A = "a" * 64
H_B = "b" * 64
H_C = "c" * 64
H_D = "d" * 64
H_E = "e" * 64

COHORT_SEL = "RAC-COHORT-SELECT01"  # cohort used for discovery/selection
COHORT_FRESH = "RAC-COHORT-FRESH01"  # untouched confirmation cohort


def _event(
    event_id: str,
    cohort_id: str,
    output_class: CohortOutputClass,
    *,
    influenced: bool = True,
    output_hash: str = H_A,
) -> ExposureEvent:
    return ExposureEvent(
        event_id=event_id,
        cohort_id=cohort_id,
        output_class=output_class,
        output_hash=output_hash,
        decision_id="select_surrogate_candidate:D2-0004",
        decision_influenced=influenced,
    )


# ---------------------------------------------------------------------------
# Fixture (i): exposure before selection blocks independent confirmation
# ---------------------------------------------------------------------------

def test_selection_influenced_cohort_cannot_be_labeled_independent_confirmation():
    ledger = EvaluationExposureLedger()
    ledger.register(
        _event("RAC-GOV-EVT-EXP001", COHORT_SEL, CohortOutputClass.SURROGATE_EVALUATION)
    )
    with pytest.raises(EvaluationExposureError, match="influenced selection"):
        issue_independent_confirmation_label(
            cohort_id=COHORT_SEL, basis_evidence_hash=H_B, ledger=ledger
        )


def test_dashboard_feedback_influence_also_blocks_confirmation_label():
    ledger = EvaluationExposureLedger()
    ledger.register(
        _event("RAC-GOV-EVT-EXP002", COHORT_SEL, CohortOutputClass.DASHBOARD_FEEDBACK)
    )
    with pytest.raises(EvaluationExposureError):
        issue_independent_confirmation_label(
            cohort_id=COHORT_SEL, basis_evidence_hash=H_B, ledger=ledger
        )


def test_outcome_derived_covariate_influence_blocks_confirmation_label():
    ledger = EvaluationExposureLedger()
    ledger.register(
        _event(
            "RAC-GOV-EVT-EXP003", COHORT_SEL, CohortOutputClass.OUTCOME_DERIVED_COVARIATE
        )
    )
    with pytest.raises(EvaluationExposureError):
        issue_independent_confirmation_label(
            cohort_id=COHORT_SEL, basis_evidence_hash=H_B, ledger=ledger
        )


def test_unexposed_cohort_receives_label_bound_to_ledger_hash():
    ledger = EvaluationExposureLedger()
    ledger.register(
        _event("RAC-GOV-EVT-EXP004", COHORT_SEL, CohortOutputClass.SURROGATE_EVALUATION)
    )
    label = issue_independent_confirmation_label(
        cohort_id=COHORT_FRESH, basis_evidence_hash=H_B, ledger=ledger
    )
    assert isinstance(label, ConfirmationLabel)
    assert label.label == "INDEPENDENT_CONFIRMATION"
    assert label.ledger_hash == ledger.ledger_hash()


def test_non_influencing_availability_does_not_block_confirmation():
    # An output that was merely *available* but recorded as NOT consumed by the
    # decision does not taint the cohort; the ledger records both facts.
    ledger = EvaluationExposureLedger()
    ledger.register(
        _event(
            "RAC-GOV-EVT-EXP005",
            COHORT_FRESH,
            CohortOutputClass.DASHBOARD_FEEDBACK,
            influenced=False,
        )
    )
    label = issue_independent_confirmation_label(
        cohort_id=COHORT_FRESH, basis_evidence_hash=H_B, ledger=ledger
    )
    assert label.cohort_id == COHORT_FRESH


def test_heldout_evaluation_influencing_selection_fails_at_event_validation():
    event = _event(
        "RAC-GOV-EVT-EXP006", COHORT_SEL, CohortOutputClass.HELDOUT_EVALUATION
    )
    with pytest.raises(EvaluationExposureError, match="held-out evaluation"):
        event.validate()


def test_exposure_ledger_is_append_only_and_hash_stable():
    ledger = EvaluationExposureLedger()
    event = _event("RAC-GOV-EVT-EXP007", COHORT_SEL, CohortOutputClass.SURROGATE_EVALUATION)
    ledger.register(event)
    with pytest.raises(EvaluationExposureError, match="duplicate"):
        ledger.register(event)
    assert ledger.ledger_hash() == ledger.ledger_hash()
    other = EvaluationExposureLedger()
    other.register(event)
    assert other.ledger_hash() == ledger.ledger_hash()


def test_unknown_confirmation_label_fails_closed():
    label = ConfirmationLabel(
        cohort_id=COHORT_FRESH,
        label="SORT_OF_CONFIRMED",
        basis_evidence_hash=H_B,
        ledger_hash=H_C,
    )
    with pytest.raises(EvaluationExposureError, match="unknown confirmation label"):
        label.validate()


# ---------------------------------------------------------------------------
# Fixture (ii): outcome-label-derived features fail provenance review
# ---------------------------------------------------------------------------

def test_feature_from_outcome_labels_fails_provenance_review():
    feature = FeatureProvenance(
        feature_id="outcome_leakage_score",
        feature_hash=H_D,
        sources=(
            FeatureSource(
                artifact_id="artifacts/outcomes/wave1.json",
                sha256=H_A,
                role=FeatureSourceRole.OUTCOME_LABEL,
                consumed_outcome_labels=True,
            ),
        ),
    )
    with pytest.raises(EvaluationExposureError, match="provenance review failed"):
        review_feature_provenance(feature)


def test_feature_with_clean_role_but_outcome_consumption_flag_fails():
    feature = FeatureProvenance(
        feature_id="sneaky_covariate",
        feature_hash=H_D,
        sources=(
            FeatureSource(
                artifact_id="artifacts/cal/state.json",
                sha256=H_A,
                role=FeatureSourceRole.CALIBRATION_STATE,
                consumed_outcome_labels=True,
            ),
        ),
    )
    with pytest.raises(EvaluationExposureError, match="outcome labels"):
        review_feature_provenance(feature)


def test_transitively_derived_feature_fails_closed_in_v1():
    feature = FeatureProvenance(
        feature_id="derived_covariate",
        feature_hash=H_D,
        sources=(
            FeatureSource(
                artifact_id="artifacts/features/parent.json",
                sha256=H_A,
                role=FeatureSourceRole.DERIVED_FEATURE,
            ),
        ),
    )
    with pytest.raises(EvaluationExposureError, match="not"):
        review_feature_provenance(feature)


def test_clean_feature_passes_review_and_is_hash_pinned():
    feature = FeatureProvenance(
        feature_id="palette_entropy",
        feature_hash=H_D,
        synthetic=True,
        sources=(
            FeatureSource(
                artifact_id="artifacts/raw/capture.png",
                sha256=H_A,
                role=FeatureSourceRole.RAW_MEASUREMENT,
            ),
            FeatureSource(
                artifact_id="design_profiles/profile.json",
                sha256=H_B,
                role=FeatureSourceRole.DESIGN_METADATA,
            ),
        ),
    )
    review_feature_provenance(feature)
    payload = feature.to_dict()
    assert payload["schema_version"] == "rac-feature-provenance/1.0"
    assert payload["synthetic"] is True
    assert feature.provenance_hash() == sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def test_sourceless_feature_fails_closed():
    feature = FeatureProvenance(feature_id="orphan", feature_hash=H_D, sources=())
    with pytest.raises(EvaluationExposureError, match=">=1 source"):
        feature.validate()


# ---------------------------------------------------------------------------
# Fixture (iii): identity disjointness and calibration isolation are
# necessary-but-distinct (existing sentinel machinery; regression pin)
# ---------------------------------------------------------------------------

def _sentinel():
    data = b"source"
    manifest = {
        "cohort_id": "RAC-COHORT-SOURCE02",
        "experiment_id": "RAC-EXP-SOURCE02",
        "constraint_id": "RAC-CS-SRC00001",
        "code_commit": "a" * 40,
        "seed": 17,
        "diagnostic_threshold_hash": H_B,
        "specimen_ids": ["S1", "S2", "S3"],
        "artifacts": {"source.bin": sha256(data).hexdigest()},
    }
    seal = seal_cohort(manifest, {"source.bin": data})
    sentinel = create_sentinel(
        sentinel_id="RAC-SENT-WAVE0002",
        source_wave_id="WAVE2",
        source_seal=seal,
        cohort_manifest=manifest,
        specimen_ids=["S1"],
        selection_seed=7,
        selection_policy_hash=H_C,
    )
    pipeline = EvaluationPipeline(
        pipeline_id="RAC-PIPE-PIPE002",
        software_version="1.0.0",
        code_hash=H_A,
        detector_hash=H_B,
        preprocessing_hash=H_C,
        random_seed=11,
        preprocessing_mode=PreprocessingMode.CALIBRATED,
        calibration_id="RAC-CAL-CAL0002",
        calibration_state_hash=H_D,
    )
    return sentinel, pipeline


def test_identity_disjointness_alone_is_not_sufficient_outcome_label_consumption_fails():
    """Calibration members disjoint from the sentinel do NOT rescue a state
    that consumed outcome labels: isolation is a distinct, necessary axis."""
    sentinel, pipeline = _sentinel()
    contaminated_but_disjoint = CalibrationState(
        "RAC-CAL-CAL0002", ("C9", "C10"), H_D, H_E, 22, outcome_labels_consumed=True
    )
    with pytest.raises(SentinelGovernanceError, match="outcome labels"):
        validate_blind_sentinel_evaluation(sentinel, pipeline, calibration=contaminated_but_disjoint)


def test_calibration_isolation_alone_is_not_sufficient_identity_overlap_fails():
    """A clean (no outcome labels) calibration state that overlaps sentinel
    membership still fails: disjointness is a distinct, necessary axis."""
    sentinel, pipeline = _sentinel()
    overlapping_but_clean = CalibrationState("RAC-CAL-CAL0002", ("S1", "C2"), H_D, H_E, 22)
    with pytest.raises(SentinelGovernanceError, match="overlaps"):
        validate_blind_sentinel_evaluation(sentinel, pipeline, calibration=overlapping_but_clean)


def test_both_axes_satisfied_passes():
    sentinel, pipeline = _sentinel()
    clean_disjoint = CalibrationState("RAC-CAL-CAL0002", ("C1", "C2"), H_D, H_E, 22)
    validate_blind_sentinel_evaluation(sentinel, pipeline, calibration=clean_disjoint)

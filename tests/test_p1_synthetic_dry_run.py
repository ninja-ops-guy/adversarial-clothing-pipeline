from scripts.p1_synthetic_dry_run import build_synthetic_trials

from ruthless_pipeline.certification.trial_statistics import (
    invalid_condition_report,
    paired_trial_statistics,
)


def test_synthetic_p1_dry_run_is_explicitly_non_evidence():
    trials = build_synthetic_trials()
    assert trials
    assert all(t.metadata["evidence_class"] == "synthetic_pipeline_validation_only" for t in trials)
    stats = paired_trial_statistics(trials, bootstrap_resamples=200, bootstrap_seed=7)
    invalid = invalid_condition_report(trials)
    assert stats.valid_trials + invalid.invalid_trials == len(trials)
    assert 0 <= stats.candidate_detection_rate <= 1

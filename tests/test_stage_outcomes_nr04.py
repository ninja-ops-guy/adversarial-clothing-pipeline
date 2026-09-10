"""NR-04 acceptance fixtures — stage outcomes and denominator integrity.

Synthetic fixtures only (synthetic-labeled; no held-out access, no
D2-0004/D2-0005 modification, no synthetic->measured promotion). Every
fixture asserts the fail-closed contract of
``ruthless_pipeline.ctm.stage_outcomes``:

- one upstream failure cannot be counted as two independent successes;
- a skipped stage cannot receive a fabricated numeric result;
- a missing input to recognition is NOT a measured recognition score;
- multi-model summaries state whether specimen/cohort/conditions were shared;
- confidence changes and discrete task outcomes stay in separate fields.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.ctm.stage_outcomes import (
    StageOutcome,
    StageOutcomeError,
    StageOutcomeSet,
    multi_model_summary,
)

EVIDENCE_LABEL = "synthetic-fixture-nr04"  # synthetic-labeled, never measured


def _outcome(stage, **kw) -> StageOutcome:
    return StageOutcome(stage=stage, **kw)


def _set(outcomes) -> StageOutcomeSet:
    return StageOutcomeSet(
        set_id="fixture-set", evidence_label=EVIDENCE_LABEL, outcomes=tuple(outcomes)
    )


# ---------------------------------------------------------------------------
# Well-formed sets pass and are hash-pinned / schema-versioned.
# ---------------------------------------------------------------------------


def test_valid_outcome_set_passes_and_validates_against_schema():
    s = _set(
        [
            _outcome(
                "person_detection",
                outcome_kind="direct_measurement",
                measured_value=0.87,
                discrete_outcome="success",
                confidence_delta=-0.12,
            ),
            _outcome(
                "face_recognition",
                outcome_kind="upstream_dependent",
                upstream_stages=("person_detection", "face_detection"),
                discrete_outcome="inconclusive",
            ),
            _outcome("face_detection", outcome_kind="direct_measurement",
                     discrete_outcome="success"),
            _outcome("reid_tracking", outcome_kind="not_evaluated",
                     note="skipped: not part of this fixture protocol"),
        ]
    )
    s.validate_against_schema()
    assert len(s.outcomes_sha256()) == 64
    # round-trip through dict form is lossless
    again = StageOutcomeSet.from_dict(s.to_dict())
    assert again.outcomes_sha256() == s.outcomes_sha256()


# ---------------------------------------------------------------------------
# (c) A skipped stage cannot receive a fabricated numeric result.
# ---------------------------------------------------------------------------


def test_skipped_stage_with_fabricated_number_fails_closed():
    with pytest.raises(StageOutcomeError, match="not_evaluated"):
        _outcome(
            "reid_tracking",
            outcome_kind="not_evaluated",
            measured_value=0.5,  # fabricated number on a skipped stage
        )
    with pytest.raises(StageOutcomeError, match="not_evaluated"):
        _outcome(
            "reid_tracking",
            outcome_kind="not_evaluated",
            discrete_outcome="success",
        )
    with pytest.raises(StageOutcomeError, match="not_evaluated"):
        _outcome(
            "reid_tracking",
            outcome_kind="not_evaluated",
            confidence_delta=0.01,
        )


# ---------------------------------------------------------------------------
# (b) One upstream failure cannot be counted as two independent successes.
# ---------------------------------------------------------------------------


def test_upstream_failure_counted_as_two_successes_fails_closed():
    detection = _outcome(
        "person_detection", outcome_kind="direct_measurement",
        discrete_outcome="failure", measured_value=0.0,
    )
    downstream = [
        _outcome(
            stage,
            outcome_kind="upstream_dependent",
            upstream_stages=("person_detection",),
            discrete_outcome="success",  # fabricated independent success
        )
        for stage in ("face_detection", "face_recognition")
    ]
    with pytest.raises(StageOutcomeError, match="upstream failure"):
        _set([detection, *downstream])


def test_single_downstream_success_over_failed_upstream_also_refused():
    with pytest.raises(StageOutcomeError, match="upstream failure"):
        _set(
            [
                _outcome("person_detection", outcome_kind="direct_measurement",
                         discrete_outcome="failure"),
                _outcome("reid_tracking", outcome_kind="upstream_dependent",
                         upstream_stages=("person_detection",),
                         discrete_outcome="success"),
            ]
        )


# ---------------------------------------------------------------------------
# (a) Missing input to recognition is NOT a measured recognition score.
# ---------------------------------------------------------------------------


def test_missing_input_is_not_a_measured_score_fails_closed():
    detection = _outcome(
        "person_detection", outcome_kind="not_evaluated",
        note="fixture: detector stage skipped",
    )
    recognition = _outcome(
        "face_recognition",
        outcome_kind="upstream_dependent",
        upstream_stages=("person_detection",),
        measured_value=0.93,  # fabricated: no input ever existed
    )
    with pytest.raises(StageOutcomeError, match="missing input"):
        _set([detection, recognition])


def test_upstream_dependent_outcome_must_name_its_inputs():
    with pytest.raises(StageOutcomeError, match="upstream_stages"):
        _outcome("face_recognition", outcome_kind="upstream_dependent")
    with pytest.raises(StageOutcomeError, match="direct_measurement"):
        _outcome(
            "person_detection",
            outcome_kind="direct_measurement",
            upstream_stages=("face_detection",),
        )


def test_dangling_upstream_reference_fails_closed():
    with pytest.raises(StageOutcomeError, match="no outcome record"):
        _set(
            [
                _outcome("face_recognition", outcome_kind="upstream_dependent",
                         upstream_stages=("face_detection",),
                         discrete_outcome="inconclusive"),
            ]
        )


# ---------------------------------------------------------------------------
# (e) Confidence changes and discrete task outcomes keep separate fields.
# ---------------------------------------------------------------------------


def test_confidence_delta_and_discrete_outcome_are_separate_fields():
    o = _outcome(
        "person_detection",
        outcome_kind="direct_measurement",
        discrete_outcome="failure",   # task outcome: detector missed
        confidence_delta=0.35,        # confidence change: separate field
        measured_value=0.0,
    )
    d = o.to_dict()
    assert d["discrete_outcome"] == "failure"
    assert d["confidence_delta"] == 0.35
    assert "confidence" not in d["discrete_outcome"]
    # non-finite deltas are refused, never coerced
    with pytest.raises(StageOutcomeError):
        _outcome(
            "person_detection", outcome_kind="direct_measurement",
            confidence_delta=float("nan"),
        )


# ---------------------------------------------------------------------------
# (d) Multi-model summaries identify shared specimen/cohort/conditions.
# ---------------------------------------------------------------------------


def _record(model_id, specimen, cohort, conditions, outcome=0.5):
    return {
        "model_id": model_id,
        "specimen_id": specimen,
        "cohort_id": cohort,
        "condition_ids": list(conditions),
        "outcome": outcome,
    }


def test_shared_specimen_summary_is_labeled():
    summary = multi_model_summary(
        [
            _record("m-a", "spec-1", "cohort-x", ["c1", "c2"]),
            _record("m-b", "spec-1", "cohort-x", ["c2", "c3"]),
        ]
    )
    assert summary["specimen_shared"] is True
    assert summary["cohort_shared"] is True
    assert summary["conditions_shared"] is False
    assert summary["n_shared_conditions"] == 1
    assert summary["shared_condition_ids"] == ["c2"]


def test_unlabeled_multi_model_summary_fails_closed():
    # missing specimen_id: an unlabeled summary is refused outright
    bad = _record("m-b", "spec-1", "cohort-x", ["c1"])
    del bad["specimen_id"]
    with pytest.raises(StageOutcomeError, match="context field"):
        multi_model_summary([_record("m-a", "spec-1", "cohort-x", ["c1"]), bad])


def test_distinct_specimen_and_cohort_flagged_not_shared():
    summary = multi_model_summary(
        [
            _record("m-a", "spec-1", "cohort-x", ["c1"]),
            _record("m-b", "spec-2", "cohort-y", ["c1"]),
        ]
    )
    assert summary["specimen_shared"] is False
    assert summary["cohort_shared"] is False
    assert summary["conditions_shared"] is True

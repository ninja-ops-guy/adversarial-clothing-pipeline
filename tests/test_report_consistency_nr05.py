"""NR-05 acceptance fixtures — reports derived from one evidence snapshot.

Synthetic fixtures only (synthetic-labeled; no held-out access, no
D2-0004/D2-0005 modification, no synthetic->measured promotion). Every
fixture asserts the fail-closed contract of
``ruthless_pipeline.certification.report_consistency``:

- inconsistent fraction/percentage pairs fail a report check;
- differing aggregation methods require explicit labels;
- selected-best results retain selection history (median does not erase
  selection bias);
- external observations never enter internal totals;
- tables/narrative/counts derive from one versioned evidence view that
  displays numerator, denominator, eligibility rules, cohort, specimen,
  measurement medium, metric definition, and source version, with
  evaluations / participants / runs / retained observations counted in
  separate fields.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.report_consistency import (
    CHECKED_REPORT_SCHEMA_VERSION,
    COUNT_FIELDS,
    EvidenceView,
    ReportConsistencyError,
    check_report_consistency,
    require_report_consistent,
)


def _view(**over) -> EvidenceView:
    payload = {
        "schema_version": "rac-evidence-view/1.0",
        "view_id": "fixture-view-1",
        "source_version": "synthetic-fixture-nr05",  # synthetic-labeled
        "eligibility_rules": "fixture: control garment detected",
        "cohort_id": "fixture-cohort",
        "specimen_id": "fixture-specimen",
        "measurement_medium": "fixture-medium",
        "metric_definition": "fixture: candidate detection rate",
        "evidence_label": "synthetic-fixture-nr05",
        "counts": {
            "n_evaluations": 2,
            "n_independent_participants": 1,
            "n_experimental_runs": 3,
            "n_retained_observations": 108,
        },
    }
    payload.update(over)
    return EvidenceView.from_dict(payload)


def _block(view, rows, **kw):
    block = {
        "block_id": kw.pop("block_id", "b1"),
        "block_type": kw.pop("block_type", "table"),
        "evidence_view_sha256": view.content_sha256(),
        "rows": rows,
    }
    block.update(kw)
    return block


def _report(view, blocks):
    return {
        "schema_version": CHECKED_REPORT_SCHEMA_VERSION,
        "evidence_view_sha256": view.content_sha256(),
        "blocks": blocks,
    }


# ---------------------------------------------------------------------------
# A well-formed report over one snapshot passes; the view validates against
# its schema and carries all display fields.
# ---------------------------------------------------------------------------


def test_consistent_report_passes():
    view = _view()
    view.validate_against_schema()
    rows = [
        {"condition_id": "c1", "numerator": 40, "denominator": 50,
         "fraction": 0.8, "percent": 80.0, "evidence_class": "internal_fixture"},
        {"condition_id": "c2", "numerator": 9, "denominator": 10,
         "fraction": 0.9, "percent": 90.0, "evidence_class": "internal_fixture"},
    ]
    report = _report(
        view,
        [
            _block(view, rows, block_id="tbl", block_type="table"),
            _block(view, [], block_id="narr", block_type="narrative"),
            _block(view, [], block_id="cnt", block_type="counts"),
        ],
    )
    assert check_report_consistency(report, view) == []
    require_report_consistent(report, view)


# ---------------------------------------------------------------------------
# (a) tables/narrative/counts must come from the same versioned view.
# ---------------------------------------------------------------------------


def test_mixed_evidence_snapshots_fail_closed():
    view = _view()
    other = _view(view_id="fixture-view-2")
    report = _report(view, [_block(view, []), _block(other, [], block_id="b2")])
    violations = check_report_consistency(report, view)
    assert any("evidence-view hash" in v for v in violations)


def test_report_pin_mismatch_fails_closed():
    view = _view()
    report = _report(view, [_block(view, [])])
    report["evidence_view_sha256"] = "0" * 64
    with pytest.raises(ReportConsistencyError, match="one"):
        require_report_consistent(report, view)


# ---------------------------------------------------------------------------
# Acceptance: inconsistent fraction/percentage pairs fail a report check.
# ---------------------------------------------------------------------------


def test_inconsistent_fraction_percentage_pair_fails():
    view = _view()
    rows = [{"fraction": 0.8, "percent": 75.0}]  # 80% != 75%
    violations = check_report_consistency(_report(view, [_block(view, rows)]), view)
    assert any("inconsistent fraction/percentage" in v for v in violations)


def test_fraction_must_match_numerator_denominator():
    view = _view()
    rows = [{"numerator": 40, "denominator": 50, "fraction": 0.7}]
    violations = check_report_consistency(_report(view, [_block(view, rows)]), view)
    assert any("numerator/denominator" in v for v in violations)
    # denominator zero with a fraction shown is refused
    rows = [{"numerator": 0, "denominator": 0, "fraction": 0.0}]
    violations = check_report_consistency(_report(view, [_block(view, rows)]), view)
    assert any("denominator" in v for v in violations)


# ---------------------------------------------------------------------------
# Acceptance: differing aggregation methods require explicit labels;
# selected-best results retain selection history; median does not erase
# selection bias.
# ---------------------------------------------------------------------------


def test_unlabeled_aggregation_fails_closed():
    view = _view()
    rows = [{"aggregates_n": 3, "value": 0.5}]  # no aggregation_method
    violations = check_report_consistency(_report(view, [_block(view, rows)]), view)
    assert any("aggregation_method" in v for v in violations)
    # with an explicit label the same row passes
    rows = [{"aggregates_n": 3, "value": 0.5, "aggregation_method": "median"}]
    assert check_report_consistency(_report(view, [_block(view, rows)]), view) == []


def test_selected_best_requires_selection_history():
    view = _view()
    rows = [{"selection": "best", "value": 0.9, "aggregation_method": "max"}]
    violations = check_report_consistency(_report(view, [_block(view, rows)]), view)
    assert any("selection_history" in v for v in violations)
    # a median aggregation still does not erase the selection-bias record
    rows = [
        {
            "selection": "best",
            "value": 0.9,
            "aggregation_method": "median",
            "selection_history": [
                {"round": 1, "selected": "cand-a", "fixture": True}
            ],
        }
    ]
    assert check_report_consistency(_report(view, [_block(view, rows)]), view) == []


# ---------------------------------------------------------------------------
# Acceptance: external observations never enter internal totals.
# ---------------------------------------------------------------------------


def test_external_observations_never_enter_internal_totals():
    view = _view()
    rows = [
        {"value": 10, "evidence_class": "internal_fixture"},
        {"value": 5, "evidence_class": "external_physical_observation"},
    ]
    # undeclared exclusion -> refused
    block = _block(view, rows, totals={"value": 10})
    violations = check_report_consistency(_report(view, [block]), view)
    assert any("external_observations_excluded" in v for v in violations)
    # declared but total silently includes the external rows -> refused
    block = _block(
        view, rows, totals={"value": 15}, external_observations_excluded=True
    )
    violations = check_report_consistency(_report(view, [block]), view)
    assert any("internal" in v for v in violations)
    # declared and correctly excluded -> passes
    block = _block(
        view, rows, totals={"value": 10}, external_observations_excluded=True
    )
    assert check_report_consistency(_report(view, [block]), view) == []


# ---------------------------------------------------------------------------
# (c) evaluations / participants / runs / retained observations are separate
# fields; merging or omitting them is refused.
# ---------------------------------------------------------------------------


def test_count_fields_are_separate_and_required():
    view = _view()
    assert set(view.counts) == set(COUNT_FIELDS)
    assert view.counts["n_evaluations"] != view.counts["n_retained_observations"]
    with pytest.raises(ReportConsistencyError, match="separately"):
        _view(counts={"n_evaluations": 2})  # merged/omitted counts refused
    with pytest.raises(ReportConsistencyError, match="non-negative"):
        _view(
            counts={
                "n_evaluations": 2,
                "n_independent_participants": 1,
                "n_experimental_runs": -1,
                "n_retained_observations": 108,
            }
        )


def test_view_display_fields_required():
    with pytest.raises(ReportConsistencyError, match="measurement_medium"):
        _view(measurement_medium="")
    with pytest.raises(ReportConsistencyError, match="metric_definition"):
        _view(metric_definition="")
    with pytest.raises(ReportConsistencyError, match="source_version"):
        _view(source_version="")

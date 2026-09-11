"""SW-13 tests: simulation <-> measurement discrepancy layer (synthetic only)."""
from __future__ import annotations

import dataclasses

import pytest

from ruthless_pipeline.future_evidence.discrepancy import (
    SCHEMA_VERSION,
    DiscrepancyComparison,
    DiscrepancyRegistry,
)
from ruthless_pipeline.future_evidence.errors import (
    LeakageError,
    MeasuredFlagAbsentError,
    PromotionImpossibleError,
    SchemaFrozenError,
)
from tests.future_evidence.fixtures import h


def make_comparison(**kw) -> DiscrepancyComparison:
    base = dict(
        schema_version=SCHEMA_VERSION,
        simulator_id="SIM-SYNTH",
        simulator_version="0.1-synthetic",
        simulator_content_sha256=h("sim::0.1"),
        metric_name="detection_score",
        predicted_distribution=(0.5, 0.6, 0.7),
        measured_distribution=None,
        uncertainty={"std": 0.01},
        calibration_set_ref="RAC-CAL-SYNTH-1",
        evaluation_set_ref="RAC-EVAL-SYNTH-1",
    )
    base.update(kw)
    return DiscrepancyComparison(**base)


def test_operates_before_measured_data():
    rec = DiscrepancyRegistry().seal(make_comparison())
    assert rec["measured_distribution"] is None
    assert rec["residual"] is None
    assert rec["evidence_class"] == "synthetic_pipeline_validation_only"


def test_residual_computed_only_with_measured():
    comp = make_comparison(
        measured_distribution=(0.55, 0.65, 0.75),
        evidence_class="measured_physical_capture",
    )
    rec = DiscrepancyRegistry().seal(comp)
    assert rec["residual"] == pytest.approx([0.05, 0.05, 0.05])


def test_residual_never_fabricated_on_mismatch():
    comp = make_comparison(
        measured_distribution=(0.5, 0.5), evidence_class="measured_physical_capture"
    )
    with pytest.raises(MeasuredFlagAbsentError):
        DiscrepancyRegistry().seal(comp)


def test_synthetic_comparison_cannot_promote():
    reg = DiscrepancyRegistry()
    rec = reg.seal(make_comparison())
    with pytest.raises(PromotionImpossibleError):
        reg.promote_to_physical_evidence(rec["comparison_id"])


def test_synthetic_cannot_carry_measured_class():
    comp = make_comparison(evidence_class="measured_physical_capture")
    with pytest.raises(PromotionImpossibleError):
        DiscrepancyRegistry().seal(comp)


def test_same_set_both_roles_leakage():
    comp = make_comparison(
        calibration_set_ref="RAC-SET-X", evaluation_set_ref="RAC-SET-X"
    )
    with pytest.raises(LeakageError):
        DiscrepancyRegistry().seal(comp)


def test_cross_comparison_leakage_rejected():
    reg = DiscrepancyRegistry()
    reg.seal(make_comparison())
    comp2 = make_comparison(
        calibration_set_ref="RAC-EVAL-SYNTH-1",  # was evaluation in sealed comp
        evaluation_set_ref="RAC-CAL-SYNTH-9",
    )
    with pytest.raises(LeakageError):
        reg.seal(comp2)


def test_simulator_version_immutable_once_sealed():
    reg = DiscrepancyRegistry()
    reg.seal(make_comparison())
    tampered = make_comparison(
        simulator_content_sha256=h("sim::tampered"),
        metric_name="other_metric",
    )
    with pytest.raises(SchemaFrozenError):
        reg.seal(tampered)


def test_double_seal_rejected():
    reg = DiscrepancyRegistry()
    comp = make_comparison()
    reg.seal(comp)
    with pytest.raises(SchemaFrozenError):
        reg.seal(comp)


def test_sealed_output_deterministic():
    a = DiscrepancyRegistry().seal(make_comparison())
    b = DiscrepancyRegistry().seal(make_comparison())
    assert a == b
    assert a["comparison_id"].startswith("RAC-DISC-")

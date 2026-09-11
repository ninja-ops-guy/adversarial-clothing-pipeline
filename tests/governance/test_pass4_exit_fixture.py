from __future__ import annotations

from hashlib import sha256

from ruthless_pipeline.governance.bridge import ConstraintBridgeCohort
from ruthless_pipeline.governance.ledger import GovernanceLedger
from ruthless_pipeline.governance.overlap import (
    CountEstimate,
    DetailedRegimeDecision,
    RegimeDecisionPolicy,
)
from ruthless_pipeline.governance.pass4_exit import (
    MaterialStratumRegistry,
    run_pass4_exit_fixture,
)
from ruthless_pipeline.governance.seal import seal_cohort


def _source():
    artifact = b"sealed-source-fixture"
    manifest = {
        "cohort_id": "RAC-COHORT-WAVEA001",
        "experiment_id": "RAC-EXP-PASS4EXIT001",
        "constraint_id": "RAC-CS-CSA001",
        "code_commit": "a" * 40,
        "seed": 7,
        "diagnostic_threshold_hash": "d" * 64,
        "specimen_ids": ["old-0", "old-1", "old-2", "old-3"],
        "artifacts": {"fixture.bin": sha256(artifact).hexdigest()},
    }
    return manifest, seal_cohort(manifest, {"fixture.bin": artifact})


def _run(new_samples=None):
    manifest, seal = _source()
    old_samples = (
        {"x": 0, "stratum": "A"},
        {"x": 1, "stratum": "A"},
        {"x": 1, "stratum": "B"},
        {"x": 2, "stratum": "B"},
    )
    if new_samples is None:
        new_samples = (
            {"x": 1, "stratum": "A"},
            {"x": 2, "stratum": "A"},
            {"x": 2, "stratum": "B"},
            {"x": 3, "stratum": "B"},
        )
    ledger = GovernanceLedger()
    record = run_pass4_exit_fixture(
        source_wave_id="WAVE-A",
        source_seal=seal,
        source_manifest=manifest,
        sentinel_id="RAC-SENT-WAVEA001",
        sentinel_specimen_ids=("old-1", "old-2"),
        sentinel_selection_seed=11,
        sentinel_selection_policy_hash="e" * 64,
        bridge=ConstraintBridgeCohort(
            bridge_id="RAC-BRIDGE-CSAB001",
            old_constraint_id="RAC-CS-CSA001",
            new_constraint_id="RAC-CS-CSB001",
            specimen_ids=("bridge-1", "bridge-2"),
            sampling_manifest_id="RAC-SAMP-BRIDGE001",
            source_policy="uniform-common-support-v1",
        ),
        bridge_specimens={
            "bridge-1": {"x": 1, "stratum": "A"},
            "bridge-2": {"x": 2, "stratum": "B"},
        },
        new_cohort_id="RAC-COHORT-WAVEB001",
        old_samples=old_samples,
        new_samples=new_samples,
        old_feasible=lambda row: row["x"] <= 2,
        new_feasible=lambda row: row["x"] >= 1,
        stratum_of=lambda row: row["stratum"],
        old_policy_strata=tuple(row["stratum"] for row in old_samples),
        new_policy_strata=tuple(row["stratum"] for row in new_samples),
        old_count=CountEstimate(3, 3, 3, "exact-fixture"),
        new_count=CountEstimate(3, 3, 3, "exact-fixture"),
        intersection_count=CountEstimate(2, 2, 2, "exact-fixture"),
        material_registry=MaterialStratumRegistry("material-strata-v1", ("A", "B")),
        overlap_id="RAC-OVERLAP-CSAB001",
        decision_policy=RegimeDecisionPolicy(0.0, 0.0),
        bootstrap_seed=19,
        bootstrap_replicates=100,
        ledger=ledger,
        decision_event_id="RAC-GOV-EVT-PASS4EXIT001",
        actor="pass4-exit-fixture",
    )
    return record, ledger


def test_pass4_exit_fixture_invokes_both_overlap_paths_and_logs_uncertainty():
    record, ledger = _run()
    assert record.decision is DetailedRegimeDecision.COMPARABLE_WITH_BRIDGE
    assert record.projected_count_overlap.method.startswith("projected_count:")
    assert record.bidirectional_overlap.support_overlap.method.startswith("bidirectional_monte_carlo")
    assert record.material_registry_hash
    assert len(ledger.events) == 1

    payload = ledger.events[0].payload
    assert payload["material_registry"]["registry_hash"] == record.material_registry_hash
    for key in ("projected_count_overlap",):
        assert {"estimate", "lower", "upper", "confidence"} <= set(payload[key])
    for key in ("old_to_new", "new_to_old", "support_overlap"):
        assert {"estimate", "lower", "upper", "confidence"} <= set(payload["bidirectional_overlap"][key])


def test_pass4_exit_record_roundtrip_surface_retains_intervals_and_binding():
    record, _ = _run()
    payload = record.to_dict()
    assert payload["material_registry_version"] == "material-strata-v1"
    assert payload["overlap_analysis"]["left_constraint_id"] == "RAC-CS-CSA001"
    assert payload["overlap_analysis"]["right_constraint_id"] == "RAC-CS-CSB001"
    assert payload["projected_count_overlap"]["lower"] <= payload["projected_count_overlap"]["estimate"]
    assert payload["projected_count_overlap"]["estimate"] <= payload["projected_count_overlap"]["upper"]


def test_pass4_exit_fixture_emits_regime_reset_when_material_stratum_missing():
    new_samples = (
        {"x": 1, "stratum": "A"},
        {"x": 2, "stratum": "A"},
        {"x": 3, "stratum": "A"},
        {"x": 2, "stratum": "A"},
    )
    record, ledger = _run(new_samples)
    assert record.decision is DetailedRegimeDecision.REGIME_RESET
    assert ledger.events[0].payload["decision"] == "REGIME_RESET"

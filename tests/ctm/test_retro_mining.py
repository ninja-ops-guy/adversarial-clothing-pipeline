"""Tests for SPEC-7 retro-mining preregistration and sealed gate (lane D)."""
from __future__ import annotations

import pytest

from ruthless_pipeline.ctm.retro_mining import (
    DECISION_STATES,
    PREDICTOR_FAMILIES,
    RETRO_DECISION_SCHEMA_VERSION,
    RETRO_PREREG_SCHEMA_VERSION,
    FamilyResult,
    RetroMiningError,
    RetroPreregistration,
    require_reject_legal,
    seal_decision,
    verify_decision,
)

ALL4 = ("harmonic_energy_curve", "description_length", "group_risk", "persistence_summary")


def _prereg(**overrides):
    kwargs = dict(
        created_utc="2026-04-01",
        minimum_useful_effect=0.2,
        minimum_analyzable_cohort=5,
        min_power=0.8,
        max_heterogeneity=0.5,
        multiplicity_correction="holm",
        missing_data_policy="stratum_specific",
        predictor_families=ALL4,
    )
    kwargs.update(overrides)
    return RetroPreregistration(**kwargs)


def _result(family, **overrides):
    kwargs = dict(
        family=family,
        cohort_size=10,
        achieved_power=0.9,
        heterogeneity=0.2,
        incremental_signal=False,
        min_effect_excluded=True,
    )
    kwargs.update(overrides)
    return FamilyResult(**kwargs)


def _all_results(**per_family_overrides):
    return [_result(f, **per_family_overrides.get(f, {})) for f in ALL4]


# -- preregistration ------------------------------------------------------------

def test_prereg_valid_and_deterministic():
    p = _prereg()
    p.validate_against_schema()
    assert p.preregistration_id == _prereg().preregistration_id
    assert len(p.preregistration_sha256()) == 64


def test_prereg_missing_min_effect_fails():
    with pytest.raises(RetroMiningError):
        _prereg(minimum_useful_effect=0.0)


def test_prereg_missing_power_fails():
    with pytest.raises(RetroMiningError):
        _prereg(min_power=0.0)


def test_prereg_bad_multiplicity_fails():
    with pytest.raises(RetroMiningError):
        _prereg(multiplicity_correction="none")


def test_prereg_unknown_family_fails():
    with pytest.raises(RetroMiningError):
        _prereg(predictor_families=("harmonic_energy_curve", "secret_sauce"))


# -- decision: CONTINUE -----------------------------------------------------------

def test_continue_on_any_incremental_signal():
    results = _all_results(group_risk={"incremental_signal": True, "min_effect_excluded": False})
    artifact = seal_decision(_prereg(), results)
    assert artifact["decision"] == "CONTINUE"
    assert artifact["claim_state"] == "EXPLORATORY"
    assert artifact["physical_efficacy_claimed"] is False
    verify_decision(artifact)


# -- decision: REJECT -------------------------------------------------------------

def test_reject_only_when_all_families_legally_rejected():
    artifact = seal_decision(_prereg(), _all_results())
    assert artifact["decision"] == "REJECT_HYPOTHESIS_FAMILY"
    assert all(d == "legally_rejected" for d in artifact["family_dispositions"].values())
    verify_decision(artifact)


def test_reject_deterministic_hash():
    a = seal_decision(_prereg(), _all_results())
    b = seal_decision(_prereg(), _all_results())
    assert a["report_sha256"] == b["report_sha256"]
    assert a["decision_id"] == b["decision_id"]


# -- decision: RESCOPE (rejection blocked) -----------------------------------------

@pytest.mark.parametrize("override", [
    {"cohort_size": 3},          # insufficient cohort
    {"achieved_power": 0.5},     # underpowered
    {"heterogeneity": 0.9},      # too heterogeneous
    {"min_effect_excluded": False},  # effect not excluded
])
def test_rescope_when_rejection_conditions_unmet(override):
    results = _all_results(description_length=override)
    artifact = seal_decision(_prereg(), results)
    assert artifact["decision"] == "RESCOPE"
    verify_decision(artifact)


def test_null_pooled_result_is_not_falsification():
    # A fully null outcome across an underpowered, heterogeneous cohort is
    # RESCOPE, never rejection.
    results = _all_results(**{f: {"achieved_power": 0.3, "heterogeneity": 0.8,
                                  "min_effect_excluded": False} for f in ALL4})
    artifact = seal_decision(_prereg(), results)
    assert artifact["decision"] == "RESCOPE"


def test_decision_states_exactly_three():
    assert DECISION_STATES == frozenset({"CONTINUE", "RESCOPE", "REJECT_HYPOTHESIS_FAMILY"})


# -- legality gate ------------------------------------------------------------------

def test_require_reject_legal_blocks_each_unmet_condition():
    prereg = _prereg()
    require_reject_legal(prereg, _result("group_risk"))  # all met: passes
    for override in ({"cohort_size": 1}, {"achieved_power": 0.1},
                     {"heterogeneity": 1.0}, {"min_effect_excluded": False}):
        with pytest.raises(RetroMiningError):
            require_reject_legal(prereg, _result("group_risk", **override))


def test_signal_below_minimum_cohort_refused():
    results = _all_results(group_risk={"incremental_signal": True, "cohort_size": 2})
    with pytest.raises(RetroMiningError):
        seal_decision(_prereg(), results)


def test_missing_family_result_refused():
    with pytest.raises(RetroMiningError):
        seal_decision(_prereg(), [_result("group_risk")])


def test_unpreregistered_family_refused():
    results = _all_results()
    prereg = _prereg(predictor_families=("group_risk",))
    with pytest.raises(RetroMiningError):
        seal_decision(prereg, results)


def test_duplicate_family_refused():
    with pytest.raises(RetroMiningError):
        seal_decision(_prereg(predictor_families=("group_risk",)),
                      [_result("group_risk"), _result("group_risk")])


# -- verification traps ---------------------------------------------------------------

def test_tampered_decision_refused():
    artifact = seal_decision(_prereg(), _all_results())
    artifact["decision"] = "RESCOPE"  # tamper after sealing
    with pytest.raises(RetroMiningError):
        verify_decision(artifact)


def test_impossible_reject_artifact_refused():
    artifact = seal_decision(_prereg(), _all_results(
        description_length={"min_effect_excluded": False}))
    assert artifact["decision"] == "RESCOPE"
    # forge a rejection without re-deriving the hash
    artifact["decision"] = "REJECT_HYPOTHESIS_FAMILY"
    with pytest.raises(RetroMiningError):
        verify_decision(artifact)


def test_version_strings():
    assert RETRO_PREREG_SCHEMA_VERSION == "rac-ctm-retro-prereg/1.0"
    assert RETRO_DECISION_SCHEMA_VERSION == "rac-ctm-retro-decision/1.0"
    assert PREDICTOR_FAMILIES == frozenset(ALL4)

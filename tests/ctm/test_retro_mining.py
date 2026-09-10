"""Tests for SPEC-7 retro-mining preregistration and sealed gate."""
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
from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

ALL4 = (
    "harmonic_energy_curve",
    "description_length",
    "group_risk",
    "persistence_summary",
)


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
        channel_metadata_adequate=True,
        provenance_adequate=True,
        metadata_gaps=(),
    )
    kwargs.update(overrides)
    return FamilyResult(**kwargs)


def _all_results(**per_family_overrides):
    return [_result(f, **per_family_overrides.get(f, {})) for f in ALL4]


def test_prereg_valid_and_deterministic():
    p = _prereg()
    p.validate_against_schema()
    assert p.preregistration_id == _prereg().preregistration_id
    assert len(p.preregistration_sha256()) == 64


def test_prereg_invalid_fields_fail_closed():
    with pytest.raises(RetroMiningError):
        _prereg(minimum_useful_effect=0.0)
    with pytest.raises(RetroMiningError):
        _prereg(min_power=0.0)
    with pytest.raises(RetroMiningError):
        _prereg(multiplicity_correction="none")
    with pytest.raises(RetroMiningError):
        _prereg(predictor_families=("harmonic_energy_curve", "secret_sauce"))


def test_continue_on_any_valid_incremental_signal():
    results = _all_results(
        group_risk={"incremental_signal": True, "min_effect_excluded": False}
    )
    artifact = seal_decision(_prereg(), results)
    assert artifact["decision"] == "CONTINUE"
    assert artifact["claim_state"] == "EXPLORATORY"
    assert artifact["physical_efficacy_claimed"] is False
    verify_decision(artifact)


def test_reject_only_when_all_families_legally_rejected():
    artifact = seal_decision(_prereg(), _all_results())
    assert artifact["decision"] == "REJECT_HYPOTHESIS_FAMILY"
    assert all(
        d == "legally_rejected"
        for d in artifact["family_dispositions"].values()
    )
    verify_decision(artifact)


def test_reject_deterministic_hash():
    a = seal_decision(_prereg(), _all_results())
    b = seal_decision(_prereg(), _all_results())
    assert a["report_sha256"] == b["report_sha256"]
    assert a["decision_id"] == b["decision_id"]


@pytest.mark.parametrize("override", [
    {"cohort_size": 3},
    {"achieved_power": 0.5},
    {"heterogeneity": 0.9},
    {"min_effect_excluded": False},
    {"channel_metadata_adequate": False, "metadata_gaps": ("camera",)},
    {"provenance_adequate": False, "metadata_gaps": ("source_capture",)},
])
def test_rescope_when_rejection_conditions_unmet(override):
    results = _all_results(description_length=override)
    artifact = seal_decision(_prereg(), results)
    assert artifact["decision"] == "RESCOPE"
    verify_decision(artifact)


def test_missing_channel_metadata_blocks_continue_too():
    results = _all_results(
        group_risk={
            "incremental_signal": True,
            "min_effect_excluded": False,
            "channel_metadata_adequate": False,
            "metadata_gaps": ("camera", "isp"),
        }
    )
    artifact = seal_decision(_prereg(), results)
    assert artifact["decision"] == "RESCOPE"
    assert artifact["family_dispositions"]["group_risk"] == "metadata_inadequate"


def test_null_pooled_result_is_not_falsification():
    results = _all_results(**{
        f: {
            "achieved_power": 0.3,
            "heterogeneity": 0.8,
            "min_effect_excluded": False,
        }
        for f in ALL4
    })
    assert seal_decision(_prereg(), results)["decision"] == "RESCOPE"


def test_decision_states_exactly_three():
    assert DECISION_STATES == frozenset({
        "CONTINUE", "RESCOPE", "REJECT_HYPOTHESIS_FAMILY"
    })


def test_require_reject_legal_blocks_each_unmet_condition():
    prereg = _prereg()
    require_reject_legal(prereg, _result("group_risk"))
    overrides = (
        {"cohort_size": 1},
        {"achieved_power": 0.1},
        {"heterogeneity": 1.0},
        {"min_effect_excluded": False},
        {"channel_metadata_adequate": False, "metadata_gaps": ("camera",)},
        {"provenance_adequate": False, "metadata_gaps": ("source",)},
    )
    for override in overrides:
        with pytest.raises(RetroMiningError):
            require_reject_legal(prereg, _result("group_risk", **override))


def test_validity_flags_are_required_on_deserialization():
    payload = _result("group_risk").to_dict()
    payload.pop("channel_metadata_adequate")
    with pytest.raises(RetroMiningError, match="missing required fields"):
        FamilyResult.from_dict(payload)


def test_metadata_gaps_cannot_coexist_with_full_adequacy():
    with pytest.raises(RetroMiningError):
        _result("group_risk", metadata_gaps=("camera",))


def test_signal_below_minimum_cohort_refused():
    results = _all_results(
        group_risk={"incremental_signal": True, "cohort_size": 2}
    )
    with pytest.raises(RetroMiningError):
        seal_decision(_prereg(), results)


def test_missing_unpreregistered_and_duplicate_families_refused():
    with pytest.raises(RetroMiningError):
        seal_decision(_prereg(), [_result("group_risk")])

    with pytest.raises(RetroMiningError):
        seal_decision(
            _prereg(predictor_families=("group_risk",)),
            _all_results(),
        )

    with pytest.raises(RetroMiningError):
        seal_decision(
            _prereg(predictor_families=("group_risk",)),
            [_result("group_risk"), _result("group_risk")],
        )


def test_tampered_decision_refused():
    artifact = seal_decision(_prereg(), _all_results())
    artifact["decision"] = "RESCOPE"
    with pytest.raises(RetroMiningError):
        verify_decision(artifact)


def test_recomputed_hash_cannot_legalize_forged_rejection():
    artifact = seal_decision(
        _prereg(),
        _all_results(
            description_length={
                "channel_metadata_adequate": False,
                "metadata_gaps": ("camera",),
            }
        ),
    )
    assert artifact["decision"] == "RESCOPE"

    artifact["decision"] = "REJECT_HYPOTHESIS_FAMILY"
    artifact["family_dispositions"]["description_length"] = "legally_rejected"
    body = {
        k: v for k, v in artifact.items()
        if k not in ("report_sha256", "decision_id")
    }
    artifact["report_sha256"] = sha256_bytes(canonical_json(body))
    artifact["decision_id"] = (
        "RAC-CTM-RETRO-DECISION-" + artifact["report_sha256"][:16]
    )
    with pytest.raises(RetroMiningError, match="does not fully re-derive"):
        verify_decision(artifact)


def test_embedded_preregistration_is_hash_bound():
    artifact = seal_decision(_prereg(), _all_results())
    artifact["preregistration"]["min_power"] = 0.1
    body = {
        k: v for k, v in artifact.items()
        if k not in ("report_sha256", "decision_id")
    }
    artifact["report_sha256"] = sha256_bytes(canonical_json(body))
    artifact["decision_id"] = (
        "RAC-CTM-RETRO-DECISION-" + artifact["report_sha256"][:16]
    )
    with pytest.raises(RetroMiningError, match="preregistration_sha256"):
        verify_decision(artifact)


def test_version_strings():
    assert RETRO_PREREG_SCHEMA_VERSION == "rac-ctm-retro-prereg/1.0"
    assert RETRO_DECISION_SCHEMA_VERSION == "rac-ctm-retro-decision/1.1"
    assert PREDICTOR_FAMILIES == frozenset(ALL4)

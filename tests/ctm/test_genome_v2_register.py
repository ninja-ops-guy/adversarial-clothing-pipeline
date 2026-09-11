"""Tests for SPEC-8/14 Genome v2 candidate register (lane E, register only)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ruthless_pipeline.ctm.genome_v2_register import (
    CANDIDATE_FAMILIES,
    ENTRY_STATUSES,
    GENOME_V2_REGISTER_SCHEMA_VERSION,
    GenomeV2Candidate,
    GenomeV2RegisterError,
    apply_spec7_gate,
    build_default_candidates,
    promote_candidate,
    require_promotion_legal,
    seal_register,
    verify_register,
)
from ruthless_pipeline.ctm.retro_mining import (
    FamilyResult,
    RetroPreregistration,
    seal_decision,
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


def _reject_all_decision():
    """A verified REJECT_HYPOTHESIS_FAMILY decision over all four families."""
    prereg = _prereg()
    return seal_decision(prereg, [_result(f) for f in ALL4])


def _continue_decision():
    """A verified CONTINUE decision in which no family is legally rejected
    (every family shows incremental signal)."""
    results = [_result(f, incremental_signal=True) for f in ALL4]
    return seal_decision(_prereg(), results)


def _register():
    return seal_register(build_default_candidates())


def _entry(register, family):
    return next(e for e in register["entries"] if e["family"] == family)


# -- default register content -------------------------------------------------------

def test_default_register_has_exactly_eight_candidates():
    register = _register()
    assert len(register["entries"]) == 8
    assert {e["family"] for e in register["entries"]} == CANDIDATE_FAMILIES


def test_default_register_deterministic_and_verifies():
    a, b = _register(), _register()
    assert a == b
    assert a["register_id"].startswith("RAC-CTM-GV2-REGISTER-")
    assert a["schema_version"] == GENOME_V2_REGISTER_SCHEMA_VERSION
    assert a["genome_v1_frozen"] is True
    verify_register(a)


def test_committed_register_file_re_derives_exactly():
    path = (
        Path(__file__).resolve().parents[2]
        / "ctm_registry" / "genome_v2" / "candidate_register_v1.json"
    )
    on_disk = json.loads(path.read_text())
    assert on_disk == _register()
    verify_register(on_disk)


def test_every_entry_carries_required_fields_and_spec7_dependence():
    for entry in _register()["entries"]:
        assert entry["feature_definition"]
        assert entry["computability_cost"]
        assert entry["spec7_dependence"]
        claim = entry["invariance_claim"]
        assert isinstance(claim["deformation_group"], bool)
        assert isinstance(claim["coarsening_operator"], bool)
        assert claim["statement"]
        assert entry["status"] == "registered"
        assert entry["candidate_id"].startswith("RAC-CTM-GV2-")


def test_spec8_bound_entries_reference_spec7_families():
    register = _register()
    bound = {
        "persistence_landscape_norms": "persistence_summary",
        "harmonic_order_energy_curves": "harmonic_energy_curve",
        "description_length_proxies": "description_length",
    }
    for family, ref in bound.items():
        assert _entry(register, family)["spec7_family_ref"] == ref


def test_spec14_entries_carry_source_and_measured_effect():
    register = _register()
    for family in (
        "region_placement_descriptors",
        "symmetry_enforcement_deltas",
        "landmark_region_density_targeting",
        "template_margin_geometry",
    ):
        entry = _entry(register, family)
        assert entry["source_paper"]
        assert entry["measured_effect"]


def test_symmetry_candidate_records_gap_effect_size():
    entry = _entry(_register(), "symmetry_enforcement_deltas")
    assert "65.4%" in entry["measured_effect"]
    assert "80.7%" in entry["measured_effect"]


# -- entry validation ------------------------------------------------------------

def test_unknown_family_refused():
    with pytest.raises(GenomeV2RegisterError):
        GenomeV2Candidate(
            family="magic_feature",
            feature_definition="x",
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": True,
                "statement": "s",
            },
            computability_cost="low",
            spec7_family_ref=None,
            spec7_dependence="d",
        )


def test_unpreregistered_spec7_family_ref_refused():
    with pytest.raises(GenomeV2RegisterError):
        GenomeV2Candidate(
            family="self_similarity_criticality",
            feature_definition="x",
            invariance_claim={
                "deformation_group": True,
                "coarsening_operator": True,
                "statement": "s",
            },
            computability_cost="low",
            spec7_family_ref="posthoc_family",
            spec7_dependence="d",
        )


def test_invariance_claim_requires_booleans_and_statement():
    with pytest.raises(GenomeV2RegisterError):
        GenomeV2Candidate(
            family="self_similarity_criticality",
            feature_definition="x",
            invariance_claim={"deformation_group": "yes", "coarsening_operator": True, "statement": "s"},
            computability_cost="low",
            spec7_family_ref=None,
            spec7_dependence="d",
        )


def test_duplicate_family_register_refused():
    c = build_default_candidates()
    with pytest.raises(GenomeV2RegisterError):
        seal_register([c[0], c[0]])


def test_empty_register_refused():
    with pytest.raises(GenomeV2RegisterError):
        seal_register([])


def test_status_enum_exact():
    assert ENTRY_STATUSES == frozenset({"registered", "v2_candidate", "dropped"})


# -- tamper traps -----------------------------------------------------------------

def test_tampered_register_hash_refused():
    artifact = _register()
    artifact["entries"][0]["computability_cost"] = "free!"
    with pytest.raises(GenomeV2RegisterError):
        verify_register(artifact)


def test_tampered_candidate_id_refused():
    artifact = _register()
    entry = artifact["entries"][0]
    entry["status"] = "v2_candidate"  # body change without id re-derivation
    artifact_body = {
        k: v for k, v in artifact.items()
        if k not in ("register_sha256", "register_id")
    }
    from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
    artifact["register_sha256"] = sha256_bytes(canonical_json(artifact_body))
    artifact["register_id"] = "RAC-CTM-GV2-REGISTER-" + artifact["register_sha256"][:16]
    with pytest.raises(GenomeV2RegisterError):
        verify_register(artifact)


# -- SPEC-7 kill-gate coupling -----------------------------------------------------

def test_gate_drops_legally_rejected_families():
    gated = apply_spec7_gate(_register(), _reject_all_decision())
    verify_register(gated)
    dropped = {
        "persistence_landscape_norms",
        "harmonic_order_energy_curves",
        "description_length_proxies",
    }
    for entry in gated["entries"]:
        if entry["family"] in dropped:
            assert entry["status"] == "dropped"
        else:
            assert entry["status"] == "registered"


def test_gate_with_continue_decision_drops_nothing():
    gated = apply_spec7_gate(_register(), _continue_decision())
    assert all(e["status"] == "registered" for e in gated["entries"])


def test_gate_refuses_forged_decision():
    forged = _reject_all_decision()
    forged["family_dispositions"]["group_risk"] = "incremental_signal"
    with pytest.raises(Exception):
        apply_spec7_gate(_register(), forged)


def test_rejected_family_can_never_be_promoted():
    register = _register()
    gated = apply_spec7_gate(register, _reject_all_decision())
    with pytest.raises(GenomeV2RegisterError):
        promote_candidate(
            gated, "harmonic_order_energy_curves", _reject_all_decision()
        )


def test_promotion_requires_decision_and_registered_status():
    register = _register()
    promoted = promote_candidate(
        register, "self_similarity_criticality", _continue_decision()
    )
    verify_register(promoted)
    assert (
        _entry(promoted, "self_similarity_criticality")["status"]
        == "v2_candidate"
    )
    # already promoted: cannot be promoted again
    with pytest.raises(GenomeV2RegisterError):
        promote_candidate(
            promoted, "self_similarity_criticality", _continue_decision()
        )


def test_promotion_of_unknown_family_refused():
    with pytest.raises(GenomeV2RegisterError):
        promote_candidate(_register(), "magic_feature", _continue_decision())


def test_require_promotion_legal_refuses_rejected_family_directly():
    register = _register()
    entry = _entry(register, "description_length_proxies")
    with pytest.raises(GenomeV2RegisterError):
        require_promotion_legal(entry, _reject_all_decision())
    # same entry, non-rejecting decision: legal
    require_promotion_legal(entry, _continue_decision())


def test_promoted_family_bound_to_surviving_spec7_family():
    register = _register()
    # harmonic family shows signal -> CONTINUE; bound candidate promotable
    promoted = promote_candidate(
        register, "harmonic_order_energy_curves", _continue_decision()
    )
    assert (
        _entry(promoted, "harmonic_order_energy_curves")["status"]
        == "v2_candidate"
    )


# -- Genome v1 frozen-surface guard -------------------------------------------------

def test_register_module_does_not_touch_genome_v1():
    """The register is a side artifact: sealing, gating, and promotion must
    not modify any file under ruthless_pipeline/pattern_genome/."""
    genome_dir = Path(__file__).resolve().parents[2] / "ruthless_pipeline" / "pattern_genome"
    before = {
        p: p.read_bytes()
        for p in sorted(genome_dir.rglob("*.py"))
    }
    register = _register()
    gated = apply_spec7_gate(register, _reject_all_decision())
    promote_candidate(gated, "self_similarity_criticality", _continue_decision())
    after = {
        p: p.read_bytes()
        for p in sorted(genome_dir.rglob("*.py"))
    }
    assert before == after

"""Tests for the frozen P1 pairing/randomization contract and schedule."""

from __future__ import annotations

import json
from pathlib import Path

from ruthless_pipeline.certification import p1_pairing_schedule as ps

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestGrid:
    def test_grid_cell_count(self):
        # 3 distances x 3 yaw x 1 pitch x 1 lighting x 2 poses = 18 cells.
        assert len(ps.grid_cells()) == 18

    def test_trial_ids_cover_144_exactly_once(self):
        ids = ps.trial_ids()
        assert len(ids) == 144
        assert ids[0] == "RAC-P1-T-0001"
        assert ids[-1] == "RAC-P1-T-0144"
        assert len(set(ids)) == 144


class TestDeterminism:
    def test_derivation_is_byte_identical(self):
        assert ps.derive_schedule() == ps.derive_schedule()
        assert ps.schedule_sha256(ps.derive_schedule()) == ps.schedule_sha256(ps.derive_schedule())

    def test_seed_changes_schedule(self):
        assert ps.derive_schedule("other-seed") != ps.derive_schedule()

    def test_schedule_shape(self):
        schedule = ps.derive_schedule()
        assert len(schedule) == 144
        positions = [e["execution_position"] for e in schedule]
        assert positions == list(range(1, 145))
        for entry in schedule:
            assert entry["arms"] in (["control", "candidate"], ["candidate", "control"])
            assert entry["first_arm"] == entry["arms"][0]
            assert 1 <= entry["repetition"] <= 8

    def test_first_arm_balanced(self):
        schedule = ps.derive_schedule()
        counts = {arm: sum(1 for e in schedule if e["first_arm"] == arm) for arm in ("control", "candidate")}
        assert counts["control"] == counts["candidate"] == 72


class TestFrozenArtifacts:
    def test_contract_matches_derivation(self):
        contract = json.loads((REPO_ROOT / "physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json").read_text())
        regenerated = ps.contract_payload()
        assert contract["schedule_sha256"] == regenerated["schedule_sha256"]
        assert contract["seed"] == ps.CONTRACT_SEED
        assert contract["physical_efficacy_claimed"] is False

    def test_frozen_schedule_matches_derivation(self):
        frozen = json.loads((REPO_ROOT / "physical/p1/P1_CAPTURE_SCHEDULE.json").read_text())
        assert frozen["schedule_sha256"] == ps.schedule_sha256(ps.derive_schedule())
        assert frozen["planned_valid_trials"] == 144
        assert frozen["contract_id"] == ps.CONTRACT_ID
        assert frozen["seed"] == ps.CONTRACT_SEED

    def test_grid_matches_stopping_rule(self):
        stopping = json.loads((REPO_ROOT / "physical/p1/STOPPING_RULE.json").read_text())
        contract = json.loads((REPO_ROOT / "physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json").read_text())
        assert contract["grid"]["planned_valid_trials"] == stopping["max_valid_trials"] == 144

    def test_no_random_module_used(self):
        source = (REPO_ROOT / "ruthless_pipeline/certification/p1_pairing_schedule.py").read_text()
        assert "import random" not in source
        assert "time" not in source.split("def ")[0].replace("from __future__", "")

from __future__ import annotations

from hashlib import sha256

import pytest

from ruthless_pipeline.governance.constraints import (
    ConstraintImpact,
    ConstraintSet,
    MigrationOutcome,
    classify_migration,
)
from ruthless_pipeline.governance.seal import SealError, seal_cohort, verify_seal
from ruthless_pipeline.ctm.intake import CTMIntakeError, accept_governed_cohort


def _h(ch: str) -> str:
    return ch * 64


def _manifest(data: bytes = b"specimen"):
    digest = sha256(data).hexdigest()
    return {
        "cohort_id": "RAC-COH-ABCDEF12",
        "experiment_id": "RAC-EXP-ABCDEF12",
        "constraint_id": "RAC-CST-ABCDEF12",
        "code_commit": "a" * 40,
        "seed": 7,
        "diagnostic_threshold_hash": _h("b"),
        "specimen_ids": ["S1"],
        "artifacts": {"specimen.bin": digest},
    }, {"specimen.bin": data}


def test_definition_change_forces_new_regime():
    old = ConstraintSet("RAC-CST-ABCDEF12", None, _h("a"), _h("b"), _h("c"), "v1", "1.0.0", ConstraintImpact.NONE)
    new = ConstraintSet("RAC-CST-ABCDEF13", old.constraint_id, _h("d"), _h("e"), _h("f"), "v2", "1.0.1", ConstraintImpact.DEFINITION_CHANGE)
    assert classify_migration(old, new) is MigrationOutcome.NEW_REGIME


def test_patch_version_does_not_override_population_change():
    old = ConstraintSet("RAC-CST-ABCDEF12", None, _h("a"), _h("b"), _h("c"), "v1", "1.0.0", ConstraintImpact.NONE)
    new = ConstraintSet("RAC-CST-ABCDEF13", old.constraint_id, _h("a"), _h("d"), _h("e"), "v1", "1.0.1", ConstraintImpact.POPULATION_CHANGE)
    assert classify_migration(old, new) is MigrationOutcome.BRIDGE_REQUIRED
    assert classify_migration(old, new, historical_population_changed=True) is MigrationOutcome.COHORT_INVALIDATION


def test_none_impact_cannot_hide_semantic_change():
    old = ConstraintSet("RAC-CST-ABCDEF12", None, _h("a"), _h("b"), _h("c"), "v1", "1.0.0", ConstraintImpact.NONE)
    new = ConstraintSet("RAC-CST-ABCDEF13", old.constraint_id, _h("d"), _h("b"), _h("c"), "v1", "1.0.1", ConstraintImpact.NONE)
    with pytest.raises(ValueError):
        classify_migration(old, new)


def test_deterministic_seal_and_ctm_acceptance():
    manifest, artifacts = _manifest()
    first = seal_cohort(manifest, artifacts)
    second = seal_cohort(manifest, artifacts)
    assert first == second
    verify_seal(first, manifest, artifacts)
    assert accept_governed_cohort(first, manifest, artifacts) == first


def test_unsealed_and_mutated_cohorts_fail_closed():
    manifest, artifacts = _manifest()
    seal = seal_cohort(manifest, artifacts)
    with pytest.raises(CTMIntakeError):
        accept_governed_cohort(None, manifest, artifacts)
    with pytest.raises(CTMIntakeError):
        accept_governed_cohort(seal, manifest, {"specimen.bin": b"mutated"})


def test_seal_requires_seed_unique_specimens_and_exact_artifact_hashes():
    manifest, artifacts = _manifest()
    no_seed = dict(manifest)
    no_seed.pop("seed")
    with pytest.raises(SealError):
        seal_cohort(no_seed, artifacts)
    duplicate = dict(manifest)
    duplicate["specimen_ids"] = ["S1", "S1"]
    with pytest.raises(SealError):
        seal_cohort(duplicate, artifacts)
    with pytest.raises(SealError):
        seal_cohort(manifest, {"specimen.bin": b"wrong"})

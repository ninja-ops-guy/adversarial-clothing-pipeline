from __future__ import annotations

import pytest

from ruthless_pipeline.governance.constraints import ConstraintImpact, ConstraintSet, TolerancePolicy
from ruthless_pipeline.governance.validators import GovernanceValidationError, validate_manifest


def _h(char: str) -> str:
    return char * 64


def test_semantic_validator_accepts_adopted_constraint_record() -> None:
    record = ConstraintSet(
        constraint_id="RAC-CS-PASS2-VALIDATOR",
        parent_id=None,
        semantic_hash=_h("a"),
        rules_hash=_h("b"),
        encoder_hash=_h("c"),
        projection_version="RAC-PG-1.0",
        software_version="1.0.0",
        impact=ConstraintImpact.NONE,
        encoder_version="0.4.2",
    )
    assert validate_manifest(
        "constraint_set",
        {"schema_version": "1.0", **record.to_dict()},
    )


def test_semantic_validator_rejects_legacy_prefix_in_adopted_field() -> None:
    manifest = {
        "schema_version": "1.0",
        "constraint_set_id": "RAC-CST-PASS2-VALIDATOR",
        "parent_constraint_set_id": None,
        "software_version": "1.0.0",
        "semantic_hash": _h("a"),
        "rules_hash": _h("b"),
        "encoder_version": "0.4.2",
        "encoder_hash": _h("c"),
        "scientific_projection_version": "RAC-PG-1.0",
        "scientific_impact": "NONE",
    }
    with pytest.raises(GovernanceValidationError, match="canonical RAC-CS"):
        validate_manifest("constraint_set", manifest)


def test_semantic_validator_accepts_preregistered_tolerance_policy() -> None:
    policy = TolerancePolicy(
        constraint_family="NULL-SPECTRAL-MATCHED",
        created_at="2026-09-10T00:00:00Z",
        max_population_displacement=0.05,
        max_cohort_change_fraction=0.05,
        registered_before_outcomes=True,
    )
    assert validate_manifest("tolerance_policy", policy.to_dict())

    bad = policy.to_dict()
    bad["registered_before_outcomes"] = False
    with pytest.raises(GovernanceValidationError, match="must be true"):
        validate_manifest("tolerance_policy", bad)

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from ruthless_pipeline.governance.constraints import (
    FROZEN_D2_ARTIFACT_IDS,
    ConstraintImpact,
    ConstraintRegistryError,
    ConstraintSet,
    ConstraintSetRegistry,
    EstimandImpact,
    FrozenArtifactMutationError,
    MigrationImpactAnalysis,
    MigrationOutcome,
    TolerancePolicy,
    assess_migration,
    assert_frozen_d2_artifacts_unchanged,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "ruthless_pipeline" / "governance" / "schemas"


def _h(char: str) -> str:
    return char * 64


def _constraint(
    suffix: str,
    *,
    parent: str | None = None,
    impact: ConstraintImpact = ConstraintImpact.NONE,
    semantic_hash: str = _h("a"),
    rules_hash: str = _h("b"),
    encoder_hash: str = _h("c"),
    projection_version: str = "RAC-PG-1.0",
    software_version: str = "1.0.0",
    encoder_version: str = "0.4.2",
) -> ConstraintSet:
    return ConstraintSet(
        constraint_id=f"RAC-CS-{suffix}",
        parent_id=parent,
        semantic_hash=semantic_hash,
        rules_hash=rules_hash,
        encoder_hash=encoder_hash,
        projection_version=projection_version,
        software_version=software_version,
        impact=impact,
        encoder_version=encoder_version,
    )


def _policy(
    *,
    family: str = "NULL-SPECTRAL-MATCHED",
    population_max: float = 0.05,
    cohort_max: float = 0.05,
) -> TolerancePolicy:
    return TolerancePolicy(
        constraint_family=family,
        created_at="2026-09-10T00:00:00Z",
        max_population_displacement=population_max,
        max_cohort_change_fraction=cohort_max,
        registered_before_outcomes=True,
    )


def _analysis(
    *,
    family: str = "NULL-SPECTRAL-MATCHED",
    population: float = 0.0,
    changed: int = 0,
    total: int = 100,
    estimand: EstimandImpact = EstimandImpact.UNCHANGED,
) -> MigrationImpactAnalysis:
    return MigrationImpactAnalysis(
        constraint_family=family,
        population_displacement=population,
        cohort_changed_count=changed,
        cohort_total_count=total,
        estimand_impact=estimand,
    )


def test_constraint_registry_is_append_only_and_parent_first() -> None:
    registry = ConstraintSetRegistry()
    root = _constraint("PASS2-001")
    child = _constraint(
        "PASS2-002",
        parent=root.constraint_id,
        impact=ConstraintImpact.SEMANTIC_CORRECTION,
        encoder_hash=_h("d"),
        software_version="1.0.1",
    )

    with pytest.raises(ConstraintRegistryError, match="parent constraint set"):
        registry.add(child)

    registry.add(root)
    registry.add(child)
    assert registry.get("RAC-CST-PASS2-001") is root
    assert registry.children(root.constraint_id) == (child,)

    alias_duplicate = ConstraintSet(
        constraint_id="RAC-CST-PASS2-001",
        parent_id=None,
        semantic_hash=root.semantic_hash,
        rules_hash=root.rules_hash,
        encoder_hash=root.encoder_hash,
        projection_version=root.projection_version,
        software_version=root.software_version,
        impact=root.impact,
        encoder_version=root.encoder_version,
    )
    with pytest.raises(ConstraintRegistryError, match="already registered"):
        registry.add(alias_duplicate)

    assert json.loads(registry.to_json())["constraint_sets"] == [
        root.to_dict(),
        child.to_dict(),
    ]


def test_prospective_registry_requires_encoder_version() -> None:
    legacy_shape = ConstraintSet(
        "RAC-CS-PASS2-LEGACY",
        None,
        _h("a"),
        _h("b"),
        _h("c"),
        "RAC-PG-1.0",
        "1.0.0",
        ConstraintImpact.NONE,
    )
    legacy_shape.validate()  # read compatibility remains available
    with pytest.raises(ValueError, match="require encoder_version"):
        ConstraintSetRegistry().add(legacy_shape)


def test_canonical_constraint_record_matches_adopted_schema() -> None:
    record = _constraint("PASS2-SCHEMA")
    manifest = {"schema_version": "1.0", **record.to_dict()}
    schema = json.loads((SCHEMA_DIR / "constraint_set.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(manifest)
    assert manifest["constraint_set_id"] == "RAC-CS-PASS2-SCHEMA"
    assert manifest["scientific_impact"] == "NONE"
    assert manifest["encoder_version"] == "0.4.2"


def test_tolerance_policy_is_preregistered_hash_bound_and_schema_valid() -> None:
    policy = _policy()
    policy.validate()
    assert len(policy.sha256) == 64
    assert policy.sha256 == _policy().sha256
    schema = json.loads((SCHEMA_DIR / "tolerance_policy.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(policy.to_dict())

    with pytest.raises(ValueError, match="preregistered before outcome"):
        TolerancePolicy(
            constraint_family="NULL-SPECTRAL-MATCHED",
            created_at="2026-09-10T00:00:00Z",
            max_population_displacement=0.05,
            max_cohort_change_fraction=0.05,
            registered_before_outcomes=False,
        ).validate()


def test_semantic_correction_uses_explicit_three_axis_impact() -> None:
    old = _constraint("PASS2-010")
    new = _constraint(
        "PASS2-011",
        parent=old.constraint_id,
        impact=ConstraintImpact.SEMANTIC_CORRECTION,
        encoder_hash=_h("d"),
        software_version="1.0.1",
    )
    policy = _policy()

    minor = assess_migration(
        old,
        new,
        analysis=_analysis(population=0.02, changed=0),
        tolerance_policy=policy,
    )
    assert minor.outcome is MigrationOutcome.MINOR_CORRECTION
    assert minor.population_displacement == pytest.approx(0.02)
    assert minor.cohort_change_fraction == pytest.approx(0.0)
    assert minor.estimand_impact is EstimandImpact.UNCHANGED
    assert minor.tolerance_policy_sha256 == policy.sha256

    bridge = assess_migration(
        old,
        new,
        analysis=_analysis(population=0.08, changed=0),
        tolerance_policy=policy,
    )
    assert bridge.outcome is MigrationOutcome.BRIDGE_REQUIRED

    invalidated = assess_migration(
        old,
        new,
        analysis=_analysis(population=0.02, changed=6),
        tolerance_policy=policy,
    )
    assert invalidated.outcome is MigrationOutcome.COHORT_INVALIDATION


def test_population_change_is_not_hidden_by_patch_version() -> None:
    old = _constraint("PASS2-020")
    new = _constraint(
        "PASS2-021",
        parent=old.constraint_id,
        impact=ConstraintImpact.POPULATION_CHANGE,
        rules_hash=_h("d"),
        software_version="1.0.1",
    )
    decision = assess_migration(
        old,
        new,
        analysis=_analysis(population=0.01),
        tolerance_policy=_policy(population_max=0.50),
    )
    assert decision.outcome is MigrationOutcome.BRIDGE_REQUIRED


def test_definition_or_estimand_change_forces_new_regime_despite_tolerance() -> None:
    old = _constraint("PASS2-030")
    definition_change = _constraint(
        "PASS2-031",
        parent=old.constraint_id,
        impact=ConstraintImpact.DEFINITION_CHANGE,
        semantic_hash=_h("d"),
        projection_version="RAC-PG-2.0",
    )
    permissive = _policy(population_max=1.0, cohort_max=1.0)
    assert assess_migration(
        old,
        definition_change,
        analysis=_analysis(population=0.0),
        tolerance_policy=permissive,
    ).outcome is MigrationOutcome.NEW_REGIME

    correction = _constraint(
        "PASS2-032",
        parent=old.constraint_id,
        impact=ConstraintImpact.SEMANTIC_CORRECTION,
        encoder_hash=_h("e"),
    )
    assert assess_migration(
        old,
        correction,
        analysis=_analysis(estimand=EstimandImpact.CHANGED),
        tolerance_policy=permissive,
    ).outcome is MigrationOutcome.NEW_REGIME


def test_none_impact_cannot_hide_measured_scientific_change() -> None:
    old = _constraint("PASS2-040")
    new = _constraint(
        "PASS2-041",
        parent=old.constraint_id,
        impact=ConstraintImpact.NONE,
        software_version="1.0.1",
        encoder_hash=_h("d"),
    )
    assert assess_migration(
        old,
        new,
        analysis=_analysis(),
        tolerance_policy=_policy(),
    ).outcome is MigrationOutcome.NO_IMPACT

    with pytest.raises(ValueError, match="measured population/cohort"):
        assess_migration(
            old,
            new,
            analysis=_analysis(population=0.001),
            tolerance_policy=_policy(),
        )


def test_tolerance_policy_family_must_match_analysis() -> None:
    old = _constraint("PASS2-050")
    new = _constraint(
        "PASS2-051",
        parent=old.constraint_id,
        impact=ConstraintImpact.SEMANTIC_CORRECTION,
        encoder_hash=_h("d"),
    )
    with pytest.raises(ValueError, match="same constraint family"):
        assess_migration(
            old,
            new,
            analysis=_analysis(family="NULL-COLOR-MATCHED"),
            tolerance_policy=_policy(family="NULL-SPECTRAL-MATCHED"),
        )


def test_frozen_d2_guard_requires_complete_unchanged_snapshots() -> None:
    before = {artifact_id: _h("a") for artifact_id in FROZEN_D2_ARTIFACT_IDS}
    after = dict(before)
    assert_frozen_d2_artifacts_unchanged(before, after)

    changed = dict(after)
    changed["RAC-PER-D2-0004"] = _h("b")
    with pytest.raises(FrozenArtifactMutationError, match="D2-0004"):
        assert_frozen_d2_artifacts_unchanged(before, changed)

    missing = dict(after)
    missing.pop("RAC-PER-D2-0005-PREREGISTRATION")
    with pytest.raises(FrozenArtifactMutationError, match="missing protected"):
        assert_frozen_d2_artifacts_unchanged(before, missing)

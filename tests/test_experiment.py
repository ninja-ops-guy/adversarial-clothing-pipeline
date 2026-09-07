"""Tests for the experiment artifact schema and registry."""

from __future__ import annotations

import pytest

from ruthless_pipeline.certification.experiment import (
    EVIDENCE_LABELS,
    ExperimentArtifact,
    ExperimentRegistry,
    StageRef,
)

H1 = "a" * 64
H2 = "b" * 64
H3 = "c" * 64
H4 = "d" * 64


def _stages() -> list[StageRef]:
    return [
        StageRef(stage="candidate", artifact_id="CAND-001", sha256=H1),
        StageRef(stage="generation", artifact_id="GEN-001", sha256=H2),
        StageRef(stage="sku", artifact_id="SKU-001", sha256=H3),
    ]


def _artifact(**overrides) -> ExperimentArtifact:
    kwargs = dict(
        experiment_id="RAC-EXP-2026-001",
        hypothesis_id="HYP-001",
        generation_id="GEN-001",
        created_utc="2026-01-01T00:00:00Z",
        stages=_stages(),
        evidence_label="internally_measured",
        validity_flags={"d2_heldout_clean": True},
    )
    kwargs.update(overrides)
    return ExperimentArtifact(**kwargs)


def test_valid_construction():
    artifact = _artifact()
    artifact.validate()
    assert artifact.experiment_id == "RAC-EXP-2026-001"
    assert len(artifact.lineage_hash) == 64


def test_experiment_id_format_rejected():
    with pytest.raises(ValueError):
        _artifact(experiment_id="EXP-2026-001").validate()
    with pytest.raises(ValueError):
        _artifact(experiment_id="RAC-EXP-26-001").validate()


def test_lineage_hash_stable_for_same_input():
    assert _artifact().lineage_hash == _artifact().lineage_hash


def test_lineage_hash_changes_on_field_change():
    stages = _stages()
    stages[2] = StageRef(stage="sku", artifact_id="SKU-002", sha256=H3)
    assert _artifact().lineage_hash != _artifact(stages=stages).lineage_hash


def test_bad_hash_rejected():
    with pytest.raises(ValueError):
        StageRef(stage="candidate", artifact_id="C", sha256="xyz").validate()
    with pytest.raises(ValueError):
        StageRef(stage="candidate", artifact_id="C", sha256="a" * 63).validate()


def test_missing_required_stage_rejected():
    with pytest.raises(ValueError):
        _artifact(stages=[StageRef("candidate", "C", H1)]).validate()


def test_stage_ordering_violation_rejected():
    stages = [
        StageRef(stage="generation", artifact_id="GEN-001", sha256=H2),
        StageRef(stage="candidate", artifact_id="CAND-001", sha256=H1),
    ]
    with pytest.raises(ValueError):
        _artifact(stages=stages).validate()


def test_absent_intermediate_stages_allowed():
    stages = [
        StageRef(stage="candidate", artifact_id="CAND-001", sha256=H1),
        StageRef(stage="generation", artifact_id="GEN-001", sha256=H2),
        StageRef(stage="certificate", artifact_id="CERT-001", sha256=H4),
    ]
    _artifact(stages=stages).validate()


def test_evidence_label_validation():
    with pytest.raises(ValueError):
        _artifact(evidence_label="not_a_label").validate()
    for label in EVIDENCE_LABELS:
        _artifact(evidence_label=label).validate()


def test_registry_rejects_duplicate_experiment_id():
    registry = ExperimentRegistry()
    registry.add(_artifact())
    with pytest.raises(ValueError):
        registry.add(_artifact())


def test_registry_rejects_duplicate_lineage():
    registry = ExperimentRegistry()
    registry.add(_artifact())
    with pytest.raises(ValueError):
        registry.add(_artifact(experiment_id="RAC-EXP-2026-002"))


def test_reverse_lookup_by_stage():
    registry = ExperimentRegistry()
    registry.add(_artifact())
    stages = _stages()
    stages[2] = StageRef(stage="sku", artifact_id="SKU-002", sha256=H3)
    registry.add(_artifact(experiment_id="RAC-EXP-2026-002", stages=stages))
    hits = registry.find_by_stage("sku", "SKU-001")
    assert [a.experiment_id for a in hits] == ["RAC-EXP-2026-001"]
    assert len(registry.find_by_stage("candidate", "CAND-001")) == 2
    assert registry.find_by_stage("sku", "SKU-999") == []
    with pytest.raises(KeyError):
        registry.get("RAC-EXP-2026-999")


def test_json_round_trip():
    registry = ExperimentRegistry()
    registry.add(_artifact())
    stages = _stages()
    stages[0] = StageRef(
        stage="candidate", artifact_id="CAND-002", sha256=H4, uri="s3://x"
    )
    registry.add(_artifact(experiment_id="RAC-EXP-2026-002", stages=stages))
    restored = ExperimentRegistry.from_json(registry.to_json())
    assert len(restored) == 2
    assert restored.get("RAC-EXP-2026-001").to_dict() == registry.get(
        "RAC-EXP-2026-001"
    ).to_dict()
    assert (
        restored.get("RAC-EXP-2026-001").lineage_hash
        == registry.get("RAC-EXP-2026-001").lineage_hash
    )
    restored.validate()

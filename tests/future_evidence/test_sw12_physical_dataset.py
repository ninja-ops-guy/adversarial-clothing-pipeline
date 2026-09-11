"""SW-12 tests: physical dataset contract + validator (synthetic fixtures only)."""
from __future__ import annotations

import dataclasses

import pytest

from ruthless_pipeline.future_evidence.errors import (
    DuplicateTrialIdError,
    InconsistentIdentityError,
    LeakageError,
    MeasuredFlagAbsentError,
    MissingMetadataError,
    PairingError,
    PromotionImpossibleError,
    UnboundProvenanceError,
)
from ruthless_pipeline.future_evidence.physical_dataset import (
    PhysicalDatasetValidator,
    observation_id,
)
from tests.future_evidence.fixtures import h, make_observation, synthetic_pair


def test_valid_synthetic_pair_passes():
    summary = PhysicalDatasetValidator().validate_dataset(synthetic_pair())
    assert summary["contains_measured"] is False
    assert summary["evidence_class"] == "synthetic_pipeline_validation_only"
    assert summary["n_observations"] == 2


def test_observation_id_content_addressed():
    rec = make_observation("T001", "candidate", "T002", "spec-T001").to_record()
    assert rec["observation_id"].startswith("RAC-PHYDS-")
    assert len(rec["observation_id"]) == len("RAC-PHYDS-") + 16
    assert rec["observation_id"] == observation_id(
        {k: v for k, v in rec.items() if k != "observation_id"}
    )


def test_measured_flag_absent_refused():
    obs = dataclasses.replace(
        make_observation("T001", "candidate", "T002", "spec-T001"), measured=None
    )
    with pytest.raises(MeasuredFlagAbsentError):
        PhysicalDatasetValidator().validate_observation(obs)


def test_duplicate_trial_ids_rejected():
    obs = synthetic_pair()
    obs.append(make_observation("T001", "candidate", "T002", "spec-T001"))
    with pytest.raises(DuplicateTrialIdError):
        PhysicalDatasetValidator().validate_dataset(obs)


def test_unbound_provenance_rejected():
    obs = dataclasses.replace(
        make_observation("T001", "candidate", "T002", "spec-T001"),
        provenance_ref="not-a-hash",
    )
    with pytest.raises(UnboundProvenanceError):
        PhysicalDatasetValidator().validate_observation(obs)


def test_missing_metadata_rejected():
    obs = dataclasses.replace(
        make_observation("T001", "candidate", "T002", "spec-T001"), camera={}
    )
    with pytest.raises(MissingMetadataError):
        PhysicalDatasetValidator().validate_observation(obs)


def test_dangling_pairing_rejected():
    obs = synthetic_pair()
    obs[0] = dataclasses.replace(obs[0], paired_trial_id="T999")
    with pytest.raises(PairingError):
        PhysicalDatasetValidator().validate_dataset(obs)


def test_same_arm_pairing_rejected():
    obs = synthetic_pair()
    obs[1] = dataclasses.replace(obs[1], arm="candidate")
    with pytest.raises(PairingError):
        PhysicalDatasetValidator().validate_dataset(obs)


def test_same_specimen_both_arms_leakage():
    spec = h("specimen::shared")
    meta = {"garment": "shared", "synthetic": True}
    obs = [
        dataclasses.replace(
            make_observation("T001", "candidate", "T002", "s1"),
            specimen_sha256=spec,
            specimen=dict(meta),
        ),
        dataclasses.replace(
            make_observation("T002", "control", "T001", "s2"),
            specimen_sha256=spec,
            specimen=dict(meta),
        ),
    ]
    with pytest.raises(LeakageError):
        PhysicalDatasetValidator().validate_dataset(obs)


def test_calibration_evaluation_leakage_rejected():
    spec = h("specimen::shared-role")
    meta = {"garment": "shared-role", "synthetic": True}
    obs = synthetic_pair()
    obs.append(
        dataclasses.replace(
            make_observation("T003", "candidate", "T004", "s3"),
            specimen_sha256=spec,
            specimen=dict(meta),
            evaluation_role="calibration",
        )
    )
    obs.append(
        dataclasses.replace(
            make_observation("T004", "control", "T003", "s4"),
            evaluation_role="evaluation",
        )
    )
    obs.append(
        dataclasses.replace(
            make_observation("T005", "candidate", "T006", "s5"),
            specimen_sha256=spec,
            specimen=dict(meta),
            evaluation_role="evaluation",
        )
    )
    obs.append(make_observation("T006", "control", "T005", "s6"))
    with pytest.raises(LeakageError):
        PhysicalDatasetValidator().validate_dataset(obs)


def test_specimen_identity_conflict_rejected():
    spec = h("specimen::dup")
    obs = synthetic_pair()
    obs[0] = dataclasses.replace(obs[0], specimen_sha256=spec)
    obs.append(
        dataclasses.replace(
            make_observation("T003", "candidate", "T004", "s3"),
            specimen_sha256=spec,
            specimen={"garment": "DIFFERENT", "synthetic": True},
        )
    )
    obs.append(make_observation("T004", "control", "T003", "s4"))
    with pytest.raises(InconsistentIdentityError):
        PhysicalDatasetValidator().validate_dataset(obs)


def test_synthetic_cannot_claim_measured():
    obs = dataclasses.replace(
        make_observation("T001", "candidate", "T002", "spec-T001"),
        measured=True,
        evidence_class="synthetic_pipeline_validation_only",
    )
    with pytest.raises(PromotionImpossibleError):
        PhysicalDatasetValidator().validate_observation(obs)


def test_frozen_once_released_enforced():
    obs = dataclasses.replace(
        make_observation("T001", "candidate", "T002", "spec-T001"),
        frozen_once_released=False,
    )
    with pytest.raises(MissingMetadataError):
        PhysicalDatasetValidator().validate_observation(obs)


def test_wrong_schema_version_refused():
    obs = dataclasses.replace(
        make_observation("T001", "candidate", "T002", "spec-T001"),
        schema_version="rac-physical-dataset/0.9",
    )
    with pytest.raises(ValueError):
        PhysicalDatasetValidator().validate_observation(obs)

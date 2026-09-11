"""Freeze-integrity and state-machine tests for the RAC-PER-D2-0007 preregistration.

Guards (all fail-closed; nothing here arms, runs, or executes anything):

1. ``docs/PREREGISTRATION_D2-0007.md`` and ``generations/RAC-PER-D2-0007.json``
   recompute byte-for-byte against the sha256 values pinned at freeze — any
   post-freeze mutation of either artifact breaks this test.
2. ``RAC-PER-D2-0007-PREREGISTRATION`` is registered in
   ``FROZEN_D2_ARTIFACT_IDS`` and the migration guard rejects mutation of the
   D2-0007 snapshot (and rejects a missing snapshot).
3. The generation record carries the preregistered skeleton semantics:
   ``lock_status: PREREGISTERED``, ``armed: false``,
   ``lock_inference_performed: false``, ``heldout_feedback_allowed: false``,
   and the frozen motif-screening stopping rule values.
4. ``experiment_state_machine.state_for_lock_status`` reads the record as
   ``State.PREREGISTERED`` and can never read it as ARMED.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ruthless_pipeline.certification.experiment_state_machine import (
    State,
    state_for_lock_status,
)
from ruthless_pipeline.governance.constraints import (
    FROZEN_D2_ARTIFACT_IDS,
    FrozenArtifactMutationError,
    assert_frozen_d2_artifacts_unchanged,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PREREG_PATH = REPO_ROOT / "docs" / "PREREGISTRATION_D2-0007.md"
GENERATION_PATH = REPO_ROOT / "generations" / "RAC-PER-D2-0007.json"

D2007_ARTIFACT_ID = "RAC-PER-D2-0007-PREREGISTRATION"

#: sha256 pinned at preregistration freeze; any post-freeze edit breaks these.
PREREG_SHA256 = "38b955d5b60e3428cce84a8c6b849fbcb61b153a4b3fb3a3040aa730d6e1564f"
GENERATION_SHA256 = "3efd0ddd6ca00c9a9f4ee15ef233eac2d8733cf235ef669927dc8665d072efef"

#: Frozen stopping-rule values (machine-checkable mirror of the preregistration).
EXPECTED_STOPPING_RULE = {
    "compositions_per_generator": 8,
    "seeds": [20270110, 20270111, 20270112],
    "max_candidates_admitted_to_optimization": 4,
}

EXPECTED_GENERATORS = [
    "HyperfaceLikeGenerator",
    "DazzleSurgicalLinesGenerator",
    "KeyFeatureBlackoutGenerator",
    "SaliencyEyeAttackGenerator",
    "AdversarialPatchGenerator",
    "SwappedLandmarksGenerator",
    "LandmarkNoiseGenerator",
    "FeatureCollageGenerator",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# 1. Frozen artifacts recompute byte-for-byte (mutation rejection by hash)
# --------------------------------------------------------------------------

def test_preregistration_document_matches_frozen_hash() -> None:
    assert PREREG_PATH.is_file()
    assert _sha256(PREREG_PATH) == PREREG_SHA256, (
        "docs/PREREGISTRATION_D2-0007.md was mutated after freeze; "
        "changes require a hash-committed amendment"
    )


def test_generation_record_matches_frozen_hash() -> None:
    assert GENERATION_PATH.is_file()
    assert _sha256(GENERATION_PATH) == GENERATION_SHA256, (
        "generations/RAC-PER-D2-0007.json was mutated after freeze; "
        "changes require a hash-committed amendment"
    )


def test_preregistration_declares_not_armed() -> None:
    text = PREREG_PATH.read_text(encoding="utf-8")
    assert "NOT_ARMED" in text
    assert "hypothesis screening" in text  # screening is never evidence promotion


# --------------------------------------------------------------------------
# 2. Frozen-artifact registry membership and mutation rejection
# --------------------------------------------------------------------------

def test_d2007_artifact_registered_in_frozen_ids() -> None:
    assert D2007_ARTIFACT_ID in FROZEN_D2_ARTIFACT_IDS
    # Prior protected ids are untouched.
    assert "RAC-PER-D2-0003" in FROZEN_D2_ARTIFACT_IDS
    assert "RAC-PER-D2-0004" in FROZEN_D2_ARTIFACT_IDS
    assert "RAC-PER-D2-0005-PREREGISTRATION" in FROZEN_D2_ARTIFACT_IDS


def test_frozen_guard_rejects_d2007_mutation() -> None:
    digest = hashlib.sha256(b"snapshot").hexdigest()
    before = {artifact_id: digest for artifact_id in FROZEN_D2_ARTIFACT_IDS}
    after = dict(before)
    assert_frozen_d2_artifacts_unchanged(before, after)

    tampered = dict(after)
    tampered[D2007_ARTIFACT_ID] = hashlib.sha256(b"tampered").hexdigest()
    with pytest.raises(FrozenArtifactMutationError, match="D2-0007"):
        assert_frozen_d2_artifacts_unchanged(before, tampered)

    missing = dict(after)
    missing.pop(D2007_ARTIFACT_ID)
    with pytest.raises(FrozenArtifactMutationError, match="missing protected"):
        assert_frozen_d2_artifacts_unchanged(before, missing)


# --------------------------------------------------------------------------
# 3. Generation record skeleton semantics and frozen stopping rule
# --------------------------------------------------------------------------

def _record() -> dict:
    return json.loads(GENERATION_PATH.read_text())


def test_generation_record_is_unarmed_preregistered_skeleton() -> None:
    record = _record()
    assert record["schema_version"] == "1.0"
    assert record["generation_id"] == "RAC-PER-D2-0007"
    assert record["status"] == "PREREGISTERED"
    assert record["lock_status"] == "PREREGISTERED"
    assert record["armed"] is False
    assert record["lock_inference_performed"] is False
    assert record["lock_source_commit"] is None
    assert record["heldout_feedback_allowed"] is False
    assert record["heldout_model_set"] == "PERSON-HO-v3"
    assert record["surrogate_model_set"] == "PERSON-SUR-v3"
    assert record["preregistration"] == "docs/PREREGISTRATION_D2-0007.md"
    assert record["trigger_revision"] == 4  # unchanged: committing cannot fire CI


def test_frozen_stopping_rule_values() -> None:
    rule = _record()["motif_screening"]["stopping_rule"]
    assert rule["compositions_per_generator"] == EXPECTED_STOPPING_RULE["compositions_per_generator"]
    assert rule["seeds"] == EXPECTED_STOPPING_RULE["seeds"]
    assert (
        rule["max_candidates_admitted_to_optimization"]
        == EXPECTED_STOPPING_RULE["max_candidates_admitted_to_optimization"]
    )
    assert rule["optional_stopping"] is False


def test_screening_generator_set_matches_repo_inventory() -> None:
    from ruthless_pipeline.patterns import P0_GENERATORS

    repo_generators = [cls.__name__ for cls in P0_GENERATORS]
    assert _record()["motif_screening"]["generator_set"] == repo_generators
    assert repo_generators == EXPECTED_GENERATORS


def test_anchor_vocabulary_and_provenance_classes_declared() -> None:
    anchors = _record()["anchor_abstraction"]
    assert anchors["capability_vocabulary"] == [
        "torso_region",
        "shoulder_axis",
        "silhouette_mask",
        "panel_region",
        "bounding_region",
    ]
    assert anchors["provenance_classes"] == ["template_derived", "model_derived"]
    assert anchors["provider_schema"] == "schemas/d2007_anchor_provider_v1.schema.json"


# --------------------------------------------------------------------------
# 4. State machine reads the record as PREREGISTERED, never ARMED
# --------------------------------------------------------------------------

def test_state_machine_reads_d2007_as_preregistered() -> None:
    assert state_for_lock_status(_record()) is State.PREREGISTERED


def test_state_machine_rejects_armed_claim_on_unarmed_record() -> None:
    from ruthless_pipeline.certification.experiment_state_machine import (
        StateMachineError,
    )

    forged = _record()
    forged["lock_status"] = "ARMED"  # armed stays false: must fail closed
    with pytest.raises(StateMachineError):
        state_for_lock_status(forged)

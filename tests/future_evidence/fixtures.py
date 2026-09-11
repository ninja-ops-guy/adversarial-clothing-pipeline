"""Synthetic fixtures for future-evidence tests.

EVERY fixture here is synthetic and explicitly tagged
``synthetic_pipeline_validation_only``. Nothing is measured data.
Deterministic: hashes derived from sha256 of stable strings; no wall-clock.
"""
from __future__ import annotations

import hashlib

from ruthless_pipeline.future_evidence.physical_dataset import (
    SCHEMA_VERSION,
    SYNTHETIC_EVIDENCE_CLASS,
    PhysicalObservation,
)


def h(tag: str) -> str:
    return hashlib.sha256(f"synthetic::{tag}".encode("utf-8")).hexdigest()


def make_observation(
    trial_id: str,
    arm: str,
    paired_trial_id: str,
    specimen_tag: str,
    *,
    measured: bool = False,
    evaluation_role: str = "evaluation",
) -> PhysicalObservation:
    """Build one explicitly-synthetic observation fixture."""
    return PhysicalObservation(
        schema_version=SCHEMA_VERSION,
        dataset_id="RAC-SYNTH-DS-001",
        dataset_version="0.0-synthetic",
        trial_id=trial_id,
        arm=arm,
        paired_trial_id=paired_trial_id,
        capture_condition="synthetic-fixed-condition",
        camera={"model": "SYNTHETIC-CAM", "synthetic": True},
        environment={"lab": "SYNTHETIC", "synthetic": True},
        specimen={"garment": specimen_tag, "synthetic": True},
        calibration_refs=(h(f"cal::{specimen_tag}"),),
        observation_medium="image_composite",
        invalidity_reason=None,
        evaluation_role=evaluation_role,
        measured=measured,
        evidence_class=SYNTHETIC_EVIDENCE_CLASS,
        specimen_sha256=h(f"specimen::{specimen_tag}"),
        provenance_ref=h(f"provenance::{trial_id}"),
        outcome_ref=None,
    )


def synthetic_pair(
    a: str = "T001", b: str = "T002", role: str = "evaluation"
) -> list:
    return [
        make_observation(a, "candidate", b, f"spec-{a}", evaluation_role=role),
        make_observation(b, "control", a, f"spec-{b}", evaluation_role=role),
    ]

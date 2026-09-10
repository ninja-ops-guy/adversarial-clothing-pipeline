"""Schema-level checks for Pass 4 governed artifacts."""

from hashlib import sha256
import json
from pathlib import Path

import jsonschema

from ruthless_pipeline.governance.bridge import ConstraintBridgeCohort
from ruthless_pipeline.governance.seal import seal_cohort
from ruthless_pipeline.governance.sentinel import (
    CalibrationState,
    EvaluationPipeline,
    PipelineBridgePlan,
    PreprocessingMode,
    create_sentinel,
)

SCHEMAS = Path(__file__).resolve().parents[2] / "ruthless_pipeline" / "governance" / "schemas"
H1, H2, H3, H4 = "a" * 64, "b" * 64, "c" * 64, "d" * 64


def validate(name: str, payload: dict) -> None:
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(payload, schema)


def sentinel_payload():
    data = b"source"
    manifest = {
        "cohort_id": "RAC-COH-SOURCE01",
        "experiment_id": "RAC-EXP-SOURCE01",
        "constraint_id": "RAC-CST-OLD0001",
        "code_commit": "a" * 40,
        "seed": 17,
        "diagnostic_threshold_hash": H2,
        "specimen_ids": ["S1", "S2"],
        "artifacts": {"source.bin": sha256(data).hexdigest()},
    }
    seal = seal_cohort(manifest, {"source.bin": data})
    return create_sentinel(
        sentinel_id="RAC-SEN-WAVE001",
        source_wave_id="WAVE-N",
        source_seal=seal,
        cohort_manifest=manifest,
        specimen_ids=("S1",),
        selection_seed=7,
        selection_policy_hash=H3,
    ).to_dict()


def test_sentinel_schema_accepts_canonical_payload():
    validate("sentinel_cohort.schema.json", sentinel_payload())


def test_calibration_schema_accepts_only_blind_state():
    payload = CalibrationState("RAC-CAL-CAL0001", ("C1", "C2"), H4, H1, 22).to_dict()
    validate("calibration_state.schema.json", payload)


def test_evaluation_pipeline_schema_accepts_frozen_initialization():
    payload = EvaluationPipeline(
        "RAC-PIP-PIPE001", "1.0.0", H1, H2, H3, 11, PreprocessingMode.STATELESS
    ).to_dict()
    validate("evaluation_pipeline.schema.json", payload)


def test_pipeline_bridge_schema_accepts_paired_bridge():
    payload = PipelineBridgePlan(
        "RAC-BRG-PIPE001", "RAC-SEN-WAVE001", "RAC-PIP-PIPE001", "RAC-PIP-PIPE002"
    ).to_dict()
    validate("pipeline_bridge.schema.json", payload)


def test_constraint_bridge_schema_accepts_common_support_manifest():
    payload = ConstraintBridgeCohort(
        "RAC-BRG-CST0001", "RAC-CST-OLD0001", "RAC-CST-NEW0001",
        ("S1", "S2"), "RAC-SMP-BRIDGE1", "intersection/v1"
    ).to_dict()
    validate("constraint_bridge.schema.json", payload)

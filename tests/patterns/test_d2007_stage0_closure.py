from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLOSURE = ROOT / "evidence" / "d2-0007" / "stage0-landmark-free-smoke-closure.json"

SURROGATES = {
    "yolov8n",
    "fasterrcnn_mobilenet_v3_320",
    "detr_resnet50",
    "ssdlite320_mobilenet_v3",
    "retinanet_resnet50_fpn_v2",
    "fcos_resnet50_fpn",
}


def _record() -> dict:
    return json.loads(CLOSURE.read_text(encoding="utf-8"))


def test_stage0_closure_is_pass_and_surrogate_only() -> None:
    record = _record()
    receipt = record["receipt"]
    assert record["generation_id"] == "RAC-PER-D2-0007"
    assert record["decision"] == "PASS"
    assert receipt["status"] == "PASS"
    assert receipt["landmark_free"] is True
    assert receipt["surrogate_only"] is True
    assert receipt["heldout_access"] is False
    assert receipt["model_set_id"] == "PERSON-SUR-v3"
    assert set(receipt["per_surrogate_detection_rates"]) == SURROGATES
    assert receipt["invalid_condition_fraction"] <= 0.10


def test_stage0_closure_did_not_advance_scientific_state() -> None:
    receipt = _record()["receipt"]
    assert receipt["screening_opened"] is False
    assert receipt["optimization_opened"] is False
    assert receipt["candidate_freeze_created"] is False
    assert receipt["alpha_002_promoted"] is False


def test_stage0_nested_receipt_hash_recomputes() -> None:
    receipt = dict(_record()["receipt"])
    expected = receipt.pop("telemetry_sha256")
    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(encoded).hexdigest() == expected


def test_stage0_closure_is_bound_to_successful_workflow_artifact() -> None:
    record = _record()
    artifact = record["workflow_artifact"]
    assert record["source_commit"] == "59143b127a7a6570036e9ce18e3f1058ec2e4309"
    assert record["workflow_run_id"] == 34561027145
    assert artifact["artifact_id"] == 10184338219
    assert artifact["digest"].startswith("sha256:")
    assert len(artifact["digest"].split(":", 1)[1]) == 64

import json
from pathlib import Path

import pytest
import torch

from scripts.analyze_capture_session import (
    FrameRecord,
    analyze_stills,
    derive_pair_outcome,
    load_contract,
)


class FakeEvaluator:
    name = "fake"

    def score(self, images: torch.Tensor) -> torch.Tensor:
        return images.mean(dim=(1, 2, 3))


def test_contract_rejects_identity_mode():
    session = {"analysis_contract": {
        "models": ["fake"], "thresholds": {"fake": 0.5},
        "preprocessing": {}, "identity_mode": "closed_set"
    }}
    with pytest.raises(ValueError, match="identity matching"):
        load_contract(session)


def test_contract_requires_threshold_per_model():
    session = {"analysis_contract": {
        "models": ["fake"], "thresholds": {}, "preprocessing": {}, "identity_mode": "disabled"
    }}
    with pytest.raises(ValueError, match="missing frozen threshold"):
        load_contract(session)


def test_fake_still_analysis_is_deterministic():
    records = [
        (FrameRecord("control", "c1", "control/c1.jpg", None, "cond"), torch.ones(3, 8, 8)),
        (FrameRecord("candidate", "p1", "candidate/p1.jpg", None, "cond"), torch.zeros(3, 8, 8)),
    ]
    rows, summaries = analyze_stills(records, [FakeEvaluator()], {"fake": 0.5})
    assert rows[0]["detected"] is True
    assert rows[1]["detected"] is False
    assert summaries["fake"]["control"]["detection_rate"] == 1.0
    assert summaries["fake"]["candidate"]["detection_rate"] == 0.0


def test_pair_outcome_invalidates_control_undetected():
    rows = [
        {"model_id": "a", "arm": "control", "detected": False},
        {"model_id": "a", "arm": "candidate", "detected": False},
        {"model_id": "b", "arm": "control", "detected": True},
        {"model_id": "b", "arm": "candidate", "detected": False},
    ]
    out = derive_pair_outcome(rows, ["a", "b"])
    assert out["model_outcomes"]["a"]["valid"] is False
    assert out["model_outcomes"]["a"]["invalid_reason"] == "control_not_detected"
    assert out["candidate_detected_rate_valid_models"] == 0.0

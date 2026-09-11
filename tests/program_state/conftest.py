"""Shared synthetic-repo builder for program-state tests.

Everything here is synthetic and labelled for pipeline validation only; no
real experiment record, no held-out access, no measured evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GEN_D2_0005 = {
    "schema_version": "1.0",
    "generation_id": "RAC-PER-D2-0005",
    "status": "PREREGISTERED",
    "lock_status": "PREREGISTERED",
    "armed": False,
    "heldout_feedback_allowed": False,
    "lock_inference_performed": False,
}

GEN_D2_0007 = {
    "schema_version": "1.0",
    "generation_id": "RAC-PER-D2-0007",
    "status": "PREREGISTERED",
    "lock_status": "PREREGISTERED",
    "armed": False,
    "heldout_feedback_allowed": False,
    "lock_inference_performed": False,
}

D2_STATUS = {
    "candidate_id": "RAC-PER-D2-0004",
    "decision": "FAIL",
    "evidence_state": "RAC-D0",
    "bundle_verified": True,
    "heldout": {
        "baseline_detection_rate": 1.0,
        "candidate_detection_rate": 1.0,
        "mean_delta": -0.0987,
        "n": 36,
        "valid_n": 36,
    },
}

D2_0005_FREEZE = {"arming": {"armed": False, "attestation": "synthetic"}}


def make_repo(tmp_path: Path) -> Path:
    """Minimal synthetic repo with the canonical sources the compiler reads."""
    (tmp_path / "generations").mkdir(parents=True)
    (tmp_path / "generations" / "RAC-PER-D2-0005.json").write_text(
        json.dumps(GEN_D2_0005, indent=2, sort_keys=True)
    )
    (tmp_path / "generations" / "RAC-PER-D2-0007.json").write_text(
        json.dumps(GEN_D2_0007, indent=2, sort_keys=True)
    )
    (tmp_path / "d2-latest-status.json").write_text(
        json.dumps(D2_STATUS, indent=2, sort_keys=True)
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "D2-0005_FREEZE_CANDIDATE.json").write_text(
        json.dumps(D2_0005_FREEZE, indent=2, sort_keys=True)
    )
    return tmp_path

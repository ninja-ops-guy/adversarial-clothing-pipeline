from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .canonical import FORMAT_ID, sha256_hex

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class FrozenPrediction:
    condition_id: str
    evaluator_id: str
    endpoint_id: str
    predicted_delta: float
    effect_boundary: float
    equivalence_margin: float

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.condition_id, self.evaluator_id, self.endpoint_id)


def _require_sha256(value: Any, field: str) -> str:
    text = str(value)
    if not _SHA256_RE.fullmatch(text):
        raise ValueError(f"{field} must be a lowercase 64-hex SHA-256")
    return text


def validate_prediction_freeze(document: dict[str, Any]) -> dict[tuple[str, str, str], FrozenPrediction]:
    if document.get("schema") != "rac.prc-prediction-freeze.v1":
        raise ValueError("unsupported prediction freeze schema")
    if not document.get("prediction_freeze_id"):
        raise ValueError("prediction freeze requires prediction_freeze_id")
    if not document.get("candidate"):
        raise ValueError("prediction freeze requires candidate identity")
    _require_sha256(document.get("candidate_artifact_sha256"), "candidate_artifact_sha256")
    if document.get("physical_outcomes_accessed") is not False:
        raise ValueError("prediction freeze must assert physical_outcomes_accessed=false")
    evidence_hashes = document.get("digital_evidence_sha256")
    if not isinstance(evidence_hashes, list) or not evidence_hashes:
        raise ValueError("prediction freeze requires at least one digital_evidence_sha256")
    for idx, digest in enumerate(evidence_hashes):
        _require_sha256(digest, f"digital_evidence_sha256[{idx}]")

    predictions: dict[tuple[str, str, str], FrozenPrediction] = {}
    for raw in document.get("predictions") or []:
        pred = FrozenPrediction(
            condition_id=str(raw["condition_id"]),
            evaluator_id=str(raw["evaluator_id"]),
            endpoint_id=str(raw["endpoint_id"]),
            predicted_delta=float(raw["predicted_delta"]),
            effect_boundary=float(raw["effect_boundary"]),
            equivalence_margin=float(raw["equivalence_margin"]),
        )
        if pred.equivalence_margin < 0:
            raise ValueError("equivalence_margin must be nonnegative")
        if pred.key in predictions:
            raise ValueError(f"duplicate frozen prediction key: {pred.key}")
        predictions[pred.key] = pred
    if not predictions:
        raise ValueError("prediction freeze contains no predictions")
    return predictions


def freeze_receipt(document: dict[str, Any]) -> dict[str, Any]:
    validate_prediction_freeze(document)
    return {
        "schema": "rac.prc-prediction-freeze-receipt.v1",
        "canonical_format": FORMAT_ID,
        "prediction_freeze_id": document["prediction_freeze_id"],
        "prediction_freeze_sha256": sha256_hex(document),
        "candidate": document["candidate"],
        "candidate_artifact_sha256": document["candidate_artifact_sha256"],
        "digital_evidence_sha256": list(document["digital_evidence_sha256"]),
        "physical_outcomes_accessed": False,
    }

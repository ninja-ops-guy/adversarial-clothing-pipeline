from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from .authority import AuthoritySnapshot
from .canonical import sha256_hex
from .receipts import refusal_receipt


@dataclass
class P1AdmissionLedger:
    observations: list[dict[str, Any]] = field(default_factory=list)
    refusals: list[dict[str, Any]] = field(default_factory=list)


class PRCP1Adapter:
    """Read-only adapter from the existing paired P1 trial format into PRC observations.

    P1 already defines one trial as one matched control/candidate pair. PRC does
    not invent a second pair identifier and does not rewrite the P1 record.
    """

    def __init__(self, authority: AuthoritySnapshot):
        self.authority = authority
        self.ledger = P1AdmissionLedger()
        self._seen: set[tuple[str, str, str]] = set()

    def _reject(self, record: dict[str, Any], reason: str, detail: str | None = None) -> str:
        self.ledger.refusals.append(refusal_receipt(reason, record, detail=detail))
        return reason

    def ingest_trial(
        self, trial: dict[str, Any], *, session_id: str, source_document_sha256: str | None = None
    ) -> str:
        trial_id = trial.get("trial_id")
        if not isinstance(trial_id, str) or trial_id not in self.authority.trials:
            return self._reject(trial, "UNKNOWN_TRIAL")

        expected = self.authority.trials[trial_id]
        if trial.get("condition_id") != expected["cell_id"]:
            return self._reject(trial, "CONDITION_MISMATCH", f"expected {expected['cell_id']}")

        geometry = trial.get("geometry") or {}
        geometry_checks = {
            "distance_m": expected["distance_m"],
            "yaw_deg": expected["yaw_deg"],
            "pitch_deg": expected["pitch_deg"],
            "pose": expected["pose"],
        }
        for name, expected_value in geometry_checks.items():
            if geometry.get(name) != expected_value:
                return self._reject(trial, "GEOMETRY_MISMATCH", f"{name}: expected {expected_value!r}")

        validity = trial.get("validity") or {}
        decision = trial.get("conservative_trial_decision") or {}
        if not isinstance(decision.get("control_detected"), bool) or not isinstance(decision.get("candidate_detected"), bool):
            return self._reject(trial, "INVALID_ENDPOINT", "conservative trial decisions must be booleans")
        expected_valid = bool(decision["control_detected"])
        if validity.get("valid") is not expected_valid:
            return self._reject(trial, "VALIDITY_MISMATCH")

        detector_outputs = trial.get("detector_outputs") or []
        for output in detector_outputs:
            model_id = output.get("model")
            if not isinstance(model_id, str) or not model_id:
                return self._reject(trial, "INVALID_ENDPOINT", "detector output missing model id")
            if not isinstance(output.get("control_detected"), bool) or not isinstance(output.get("candidate_detected"), bool):
                return self._reject(trial, "INVALID_ENDPOINT", f"{model_id}: detected fields must be booleans")

        source_hash = sha256_hex(trial)
        base = {
            "schema": "rac.prc-physical-observation.v1",
            "session_id": session_id,
            "trial_id": trial_id,
            "condition_id": expected["cell_id"],
            "repetition": expected["repetition"],
            "first_arm": expected["first_arm"],
            "source_record_sha256": source_hash,
            "source_document_sha256": source_document_sha256,
            "authority": {
                "contract_id": self.authority.contract_id,
                "derived_schedule_sha256": self.authority.schedule_sha256,
                "schedule_file_sha256": self.authority.schedule_file_sha256,
                "pairing_contract_file_sha256": self.authority.pairing_contract_file_sha256,
                "readiness_freeze_file_sha256": self.authority.readiness_freeze_file_sha256,
            },
        }

        pending = [
            {
                **base,
                "evaluator_id": "P1-CONSERVATIVE-ENSEMBLE",
                "endpoint_id": "PERSON_DETECTION_DECISION",
                "control_detected": decision["control_detected"],
                "candidate_detected": decision["candidate_detected"],
                "valid": expected_valid,
                "invalid_reason": validity.get("invalid_reason"),
            }
        ]
        for output in detector_outputs:
            pending.append(
                {
                    **base,
                    "evaluator_id": output["model"],
                    "endpoint_id": "PERSON_DETECTION_DECISION",
                    "control_detected": output["control_detected"],
                    "candidate_detected": output["candidate_detected"],
                    "control_score": output.get("control_score"),
                    "candidate_score": output.get("candidate_score"),
                    "threshold": output.get("threshold"),
                    "valid": expected_valid,
                    "invalid_reason": validity.get("invalid_reason"),
                }
            )

        keys = [
            (str(obs["trial_id"]), str(obs["evaluator_id"]), str(obs["endpoint_id"]))
            for obs in pending
        ]
        if len(keys) != len(set(keys)):
            return self._reject(trial, "DUPLICATE", "duplicate evaluator/endpoint inside trial record")
        if any(key in self._seen for key in keys):
            return self._reject(trial, "DUPLICATE", "trial/evaluator/endpoint already admitted")

        # Commit the complete trial atomically only after every endpoint validates.
        self._seen.update(keys)
        self.ledger.observations.extend(pending)
        return "ADMITTED"

    def ingest_document(
        self, document: dict[str, Any], *, source_document_sha256: str | None = None
    ) -> P1AdmissionLedger:
        session_id = document.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            self._reject(document, "INVALID_SESSION", "session_id is required")
            return self.ledger
        for trial in document.get("trials") or []:
            self.ingest_trial(
                trial, session_id=session_id, source_document_sha256=source_document_sha256
            )
        return self.ledger

    def ingest_path(self, path: str | Path) -> P1AdmissionLedger:
        source = Path(path)
        payload = source.read_bytes()
        document = json.loads(payload.decode("utf-8"))
        return self.ingest_document(
            document, source_document_sha256=hashlib.sha256(payload).hexdigest()
        )

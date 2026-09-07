from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PassCriteria:
    min_baseline_detection_rate: float = 0.90
    max_candidate_detection_rate: float = 0.50
    min_relative_reduction: float = 0.25
    max_invalid_condition_fraction: float = 0.10
    confidence_level: float = 0.95


@dataclass(frozen=True)
class CertificationProtocol:
    protocol_id: str
    version: str
    task: str
    surrogate_model_set: str
    heldout_model_set: str
    transforms: dict[str, list[Any]]
    criteria: PassCriteria
    physical_required_for: tuple[str, ...] = ("RAC-P1", "RAC-P2", "RAC-M1", "RAC-M2")
    preregistered: bool = True
    notes: str = ""
    generation_id: str = ""

    def validate(self) -> None:
        if not self.protocol_id.startswith("RAC-"):
            raise ValueError("protocol_id must start with RAC-")
        if self.surrogate_model_set == self.heldout_model_set:
            raise ValueError("surrogate and held-out model sets must differ")
        if not self.preregistered:
            raise ValueError("certification protocol must be preregistered")
        c = self.criteria
        for value in (
            c.min_baseline_detection_rate,
            c.max_candidate_detection_rate,
            c.min_relative_reduction,
            c.max_invalid_condition_fraction,
            c.confidence_level,
        ):
            if not 0 <= value <= 1:
                raise ValueError("criteria values must be within [0,1]")


def load_protocol(path: str | Path) -> CertificationProtocol:
    payload = json.loads(Path(path).read_text())
    payload["criteria"] = PassCriteria(**payload["criteria"])
    payload["physical_required_for"] = tuple(payload.get("physical_required_for", ()))
    protocol = CertificationProtocol(**payload)
    protocol.validate()
    return protocol

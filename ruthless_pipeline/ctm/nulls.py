"""Matched-property null contracts for CTM controlled-effect claims."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MatchedNullType(str, Enum):
    COLOR = "NULL-COLOR-MATCHED"
    SPECTRAL = "NULL-SPECTRAL-MATCHED"
    TOPOLOGY = "NULL-TOPOLOGY-MATCHED"


@dataclass(frozen=True)
class MatchedNullDesign:
    null_id: str
    null_type: MatchedNullType
    candidate_sha256: str
    null_sha256: str
    manipulated_feature: str
    matched_properties: tuple[str, ...]
    tolerance_contract_sha256: str
    design_commit: str

    def validate(self) -> None:
        if not self.null_id:
            raise ValueError("null_id is required")
        for name, value in (
            ("candidate_sha256", self.candidate_sha256),
            ("null_sha256", self.null_sha256),
            ("tolerance_contract_sha256", self.tolerance_contract_sha256),
        ):
            if len(value) != 64:
                raise ValueError(f"{name} must be 64 hex characters")
            try:
                int(value, 16)
            except ValueError as exc:
                raise ValueError(f"{name} must be hexadecimal") from exc
        if self.candidate_sha256 == self.null_sha256:
            raise ValueError("matched null must not be byte-identical to candidate")
        if not self.manipulated_feature:
            raise ValueError("manipulated_feature is required")
        if not self.matched_properties:
            raise ValueError("matched_properties must not be empty")
        if self.manipulated_feature in self.matched_properties:
            raise ValueError("manipulated_feature cannot also be declared matched")
        if not self.design_commit:
            raise ValueError("design_commit is required")

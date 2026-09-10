"""Stable typed identifiers for prospective RAC governance objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class IdKind(str, Enum):
    EXPERIMENT = "EXP"
    EVENT = "EVT"
    COHORT = "COH"
    SAMPLING = "SMP"
    CONSTRAINT = "CST"
    OVERLAP = "OVR"
    DIAGNOSTIC = "DGN"


_ID_RE = re.compile(r"^RAC-(EXP|EVT|COH|SMP|CST|OVR|DGN)-([A-Z0-9][A-Z0-9._-]{2,63})$")


@dataclass(frozen=True, order=True)
class GovernanceId:
    kind: IdKind
    value: str

    def __post_init__(self) -> None:
        raw = f"RAC-{self.kind.value}-{self.value}"
        if not _ID_RE.fullmatch(raw):
            raise ValueError(f"invalid governance id: {raw!r}")

    def __str__(self) -> str:
        return f"RAC-{self.kind.value}-{self.value}"

    @classmethod
    def parse(cls, raw: str) -> "GovernanceId":
        match = _ID_RE.fullmatch(raw)
        if not match:
            raise ValueError(f"invalid governance id: {raw!r}")
        return cls(IdKind(match.group(1)), match.group(2))

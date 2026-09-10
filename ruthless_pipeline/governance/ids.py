"""Stable typed identifiers for prospective RAC governance objects.

Governance v1 adopted long, descriptive prefixes (for example
``RAC-GOV-EVT-*`` and ``RAC-COHORT-*``).  Early prototype code used shorter
aliases such as ``RAC-EVT-*`` and ``RAC-COH-*``.  New objects should use the
canonical prefixes while the parser remains read-compatible with the legacy
aliases so prototype fixtures and already-written development records do not
need to be rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class IdKind(str, Enum):
    EXPERIMENT = "EXP"
    EVENT = "GOV-EVT"
    COHORT = "COHORT"
    SAMPLING = "SAMP"
    CONSTRAINT = "CS"
    SENTINEL = "SENT"
    BRIDGE = "BRIDGE"
    CALIBRATION = "CAL"
    PIPELINE = "PIPE"
    OVERLAP = "OVERLAP"
    DIAGNOSTIC = "DIAG"


# Backward-compatible aliases from the pre-adoption prototype.  They are
# accepted on input only; direct construction uses IdKind.value (canonical).
_LEGACY_PREFIXES: dict[str, IdKind] = {
    "EVT": IdKind.EVENT,
    "COH": IdKind.COHORT,
    "SMP": IdKind.SAMPLING,
    "CST": IdKind.CONSTRAINT,
    "OVR": IdKind.OVERLAP,
    "DGN": IdKind.DIAGNOSTIC,
}
_CANONICAL_PREFIXES: dict[str, IdKind] = {kind.value: kind for kind in IdKind}
_PREFIX_TO_KIND: dict[str, IdKind] = {**_LEGACY_PREFIXES, **_CANONICAL_PREFIXES}
_PREFIX_PATTERN = "|".join(
    re.escape(prefix) for prefix in sorted(_PREFIX_TO_KIND, key=len, reverse=True)
)
_ID_RE = re.compile(
    rf"^RAC-({_PREFIX_PATTERN})-([A-Z0-9][A-Z0-9._-]{{2,63}})$"
)


@dataclass(frozen=True, order=True)
class GovernanceId:
    kind: IdKind
    value: str
    prefix: str | None = None

    def __post_init__(self) -> None:
        prefix = self.prefix or self.kind.value
        if _PREFIX_TO_KIND.get(prefix) is not self.kind:
            raise ValueError(
                f"prefix {prefix!r} is not valid for governance kind {self.kind.name}"
            )
        raw = f"RAC-{prefix}-{self.value}"
        if not _ID_RE.fullmatch(raw):
            raise ValueError(f"invalid governance id: {raw!r}")
        object.__setattr__(self, "prefix", prefix)

    def __str__(self) -> str:
        return f"RAC-{self.prefix}-{self.value}"

    @property
    def canonical(self) -> str:
        """Canonical Governance-v1 spelling, independent of parsed alias."""
        return f"RAC-{self.kind.value}-{self.value}"

    @property
    def is_legacy_alias(self) -> bool:
        return self.prefix != self.kind.value

    @classmethod
    def parse(cls, raw: str) -> "GovernanceId":
        if not isinstance(raw, str):
            raise ValueError(f"invalid governance id: {raw!r}")
        match = _ID_RE.fullmatch(raw)
        if not match:
            raise ValueError(f"invalid governance id: {raw!r}")
        prefix, value = match.groups()
        return cls(_PREFIX_TO_KIND[prefix], value, prefix=prefix)

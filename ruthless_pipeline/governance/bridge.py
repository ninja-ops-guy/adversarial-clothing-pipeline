"""Constraint-bridge cohort validation for Governance Pass 4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .ids import GovernanceId, IdKind


class BridgeGovernanceError(RuntimeError):
    pass


def _require_kind(raw: str, kind: IdKind, field: str) -> None:
    parsed = GovernanceId.parse(raw)
    if parsed.kind is not kind:
        raise BridgeGovernanceError(f"{field} must be RAC-{kind.value}-...")


@dataclass(frozen=True)
class ConstraintBridgeCohort:
    """A cohort whose every specimen lies in old/new common support."""

    bridge_id: str
    old_constraint_id: str
    new_constraint_id: str
    specimen_ids: tuple[str, ...]
    sampling_manifest_id: str
    source_policy: str

    def validate(self) -> None:
        _require_kind(self.bridge_id, IdKind.BRIDGE, "bridge_id")
        _require_kind(self.old_constraint_id, IdKind.CONSTRAINT, "old_constraint_id")
        _require_kind(self.new_constraint_id, IdKind.CONSTRAINT, "new_constraint_id")
        _require_kind(self.sampling_manifest_id, IdKind.SAMPLING, "sampling_manifest_id")
        if self.old_constraint_id == self.new_constraint_id:
            raise BridgeGovernanceError("constraint bridge requires distinct old/new constraint ids")
        if not self.specimen_ids or len(self.specimen_ids) != len(set(self.specimen_ids)):
            raise BridgeGovernanceError("bridge specimen_ids must be non-empty and unique")
        if not self.source_policy:
            raise BridgeGovernanceError("source_policy is required")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema_version": "1.0",
            "bridge_id": self.bridge_id,
            "old_constraint_id": self.old_constraint_id,
            "new_constraint_id": self.new_constraint_id,
            "specimen_ids": list(self.specimen_ids),
            "sampling_manifest_id": self.sampling_manifest_id,
            "source_policy": self.source_policy,
        }


def validate_common_support(
    bridge: ConstraintBridgeCohort,
    specimens: Mapping[str, Any],
    *,
    old_feasible: Callable[[Any], bool],
    new_feasible: Callable[[Any], bool],
) -> None:
    """Verify that every bridge specimen satisfies both constraint regimes."""

    bridge.validate()
    missing = [sid for sid in bridge.specimen_ids if sid not in specimens]
    if missing:
        raise BridgeGovernanceError(f"bridge specimens missing from fixture/store: {missing}")
    outside: list[str] = []
    for specimen_id in bridge.specimen_ids:
        specimen = specimens[specimen_id]
        if not old_feasible(specimen) or not new_feasible(specimen):
            outside.append(specimen_id)
    if outside:
        raise BridgeGovernanceError(
            "bridge specimens must lie in F(old) ∩ F(new): " + ", ".join(outside)
        )

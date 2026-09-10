"""Constraint-bridge cohort validation for Governance Pass 4 hardening."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .ids import GovernanceId, IdKind


class ConstraintBridgeError(RuntimeError):
    pass


def _require_kind(raw: str, kind: IdKind, field: str) -> None:
    parsed = GovernanceId.parse(raw)
    if parsed.kind is not kind:
        raise ConstraintBridgeError(f"{field} must be RAC-{kind.value}-...")


@dataclass(frozen=True)
class ConstraintBridgeCohort:
    """Bridge cohort whose specimens must lie in F(old) ∩ F(new)."""

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
            raise ConstraintBridgeError("constraint bridge requires distinct old/new constraint ids")
        if not self.specimen_ids or len(self.specimen_ids) != len(set(self.specimen_ids)):
            raise ConstraintBridgeError("bridge specimen_ids must be non-empty and unique")
        if not self.source_policy:
            raise ConstraintBridgeError("source_policy is required")

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
    bridge.validate()
    missing = [sid for sid in bridge.specimen_ids if sid not in specimens]
    if missing:
        raise ConstraintBridgeError(f"bridge specimens missing from fixture/store: {missing}")
    outside = [
        sid for sid in bridge.specimen_ids
        if not old_feasible(specimens[sid]) or not new_feasible(specimens[sid])
    ]
    if outside:
        raise ConstraintBridgeError(
            "bridge specimens must lie in F(old) ∩ F(new): " + ", ".join(outside)
        )

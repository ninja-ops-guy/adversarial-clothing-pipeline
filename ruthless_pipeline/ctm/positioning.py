"""SPEC-18 — Impact-axis declaration with corpus-pinned comparison snapshot.

Lesson L16: success axes are orthogonal (scientific impact, demonstrated
physical effectiveness, public availability, policy impact) and only one of
them is CTM's. The manuscript positioning block declares the paper's primary
success axis — default ``measurement_infrastructure`` (historical analogues:
NIST FRVT, RobustBench) — and the axes it explicitly does NOT claim. The
strongest comparison on each axis is resolved from the pinned living-corpus
snapshot rather than handwritten, so framing claims cannot go stale.

Hard rules (fail closed with :class:`PositioningError`):

- The exporter REFUSES if the positioning block is absent, if
  ``comparison_snapshot_ref`` is not a lowercase 64-hex sha256, or if the
  snapshot cannot be verified against the living-corpus registry
  (:func:`serialize_positioning` calls :func:`corpus.verify_snapshot`).
- The primary axis must not also appear in ``disclaimed_axes``.
- Narrative prose that implies competition on a disclaimed axis is refused
  unless the positioning block carries an explicit amendment naming that
  axis (:func:`check_narrative` / :func:`require_narrative_conformant`).

This module is additive; it does not mutate any manuscript template.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .corpus import CorpusSnapshot, verify_snapshot
from .errors import CTMBridgeError

POSITIONING_SCHEMA_VERSION = "rac-ctm-positioning/1.0"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "ctm_positioning_v1.schema.json"
)

#: The four orthogonal success axes (L16).
IMPACT_AXES = frozenset({
    "measurement_infrastructure",
    "attack_superiority",
    "policy_impact",
    "consumer_usability",
})

#: CTM's default primary axis (L16: the program competes on none of the
#: other axes directly; its axis is measurement infrastructure).
DEFAULT_PRIMARY_AXIS = "measurement_infrastructure"

_SHA256_LEN = 64

#: Phrases that imply competition on each axis. Mechanical, conservative.
_AXIS_COMPETITION_PHRASES = {
    "attack_superiority": (
        "state-of-the-art attack",
        "strongest attack",
        "best attack",
        "outperforms existing attacks",
        "superior attack",
        "attack superiority",
    ),
    "policy_impact": (
        "policy impact",
        "municipal ban",
        "corporate discontinuation",
        "regulatory impact",
    ),
    "consumer_usability": (
        "consumer app",
        "desktop app",
        "easy to use",
        "consumer usability",
        "downloads",
    ),
    "measurement_infrastructure": (),  # primary axis; never disclaimed-competition
}


class PositioningError(CTMBridgeError):
    """Positioning-block contract violated (SPEC-18). Fail closed."""


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


class Positioning:
    """Manuscript positioning block pinned to a verified corpus snapshot."""

    __slots__ = ("primary_axis", "disclaimed_axes", "comparison_snapshot_ref", "amendments", "schema_version")

    def __init__(
        self,
        *,
        primary_axis: str = DEFAULT_PRIMARY_AXIS,
        disclaimed_axes: Iterable[str] = (
            "attack_superiority",
            "policy_impact",
            "consumer_usability",
        ),
        comparison_snapshot_ref: str,
        amendments: Iterable[str] = (),
        schema_version: str = POSITIONING_SCHEMA_VERSION,
    ) -> None:
        self.primary_axis = primary_axis
        self.disclaimed_axes = tuple(disclaimed_axes)
        self.comparison_snapshot_ref = comparison_snapshot_ref
        self.amendments = tuple(amendments)
        self.schema_version = schema_version
        self._validate()

    def _validate(self) -> None:
        if self.schema_version != POSITIONING_SCHEMA_VERSION:
            raise PositioningError(
                f"unsupported positioning schema_version: {self.schema_version!r}"
            )
        if self.primary_axis not in IMPACT_AXES:
            raise PositioningError(
                f"unknown primary_axis {self.primary_axis!r}; allowed: {sorted(IMPACT_AXES)}"
            )
        for axis in self.disclaimed_axes:
            if axis not in IMPACT_AXES:
                raise PositioningError(
                    f"unknown disclaimed axis {axis!r}; allowed: {sorted(IMPACT_AXES)}"
                )
        if self.primary_axis in self.disclaimed_axes:
            raise PositioningError(
                f"primary_axis {self.primary_axis!r} cannot also be disclaimed"
            )
        if not _is_sha256(self.comparison_snapshot_ref):
            raise PositioningError(
                "comparison_snapshot_ref must be a lowercase 64-hex sha256 of a "
                "living-corpus snapshot (SPEC-4); framing claims resolve against "
                "a pinned corpus state, never handwritten"
            )
        if isinstance(self.amendments, str):
            raise PositioningError(
                "amendments must be a sequence of strings, not a single string"
            )
        for amendment in self.amendments:
            if not amendment:
                raise PositioningError("amendments must be non-empty strings")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "primary_axis": self.primary_axis,
            "disclaimed_axes": list(self.disclaimed_axes),
            "comparison_snapshot_ref": self.comparison_snapshot_ref,
            "amendments": list(self.amendments),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def positioning_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise PositioningError(
                f"positioning block fails ctm_positioning_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Positioning":
        if not isinstance(payload, dict):
            raise PositioningError("positioning payload must be an object")
        return cls(
            primary_axis=payload.get("primary_axis", ""),
            disclaimed_axes=tuple(payload.get("disclaimed_axes", ())),
            comparison_snapshot_ref=payload.get("comparison_snapshot_ref", ""),
            amendments=tuple(payload.get("amendments", ())),
            schema_version=payload.get("schema_version", ""),
        )


def serialize_positioning(
    positioning: Positioning | None, *, registry_dir: Path | str | None = None
) -> dict[str, Any]:
    """Fail-closed export of the positioning block.

    Refuses if the block is absent or its pinned snapshot cannot be verified
    against the living-corpus registry (unverified/stale snapshot = no
    export). Returns the serialized block plus the resolved comparison set
    (the entries pinned by the verified snapshot) so the manuscript renders
    the comparison set that existed at the declared corpus snapshot.
    """
    if positioning is None:
        raise PositioningError(
            "positioning block is absent: the manuscript exporter fails closed "
            "(SPEC-18)"
        )
    positioning.validate_against_schema()
    snapshot: CorpusSnapshot = verify_snapshot(
        positioning.comparison_snapshot_ref,
        registry_dir=Path(registry_dir) if registry_dir else None,
    )
    return {
        "positioning": positioning.to_dict(),
        "positioning_sha256": positioning.positioning_sha256(),
        "comparison_snapshot_id": snapshot.snapshot_id,
        "comparison_set": [
            {"entry_id": r["entry_id"], "entry_sha256": r["entry_sha256"]}
            for r in snapshot.entries
        ],
    }


def _amended_axes(positioning: Positioning) -> set[str]:
    amended: set[str] = set()
    for amendment in positioning.amendments:
        for axis in IMPACT_AXES:
            if axis in amendment:
                amended.add(axis)
    return amended


def check_narrative(prose: str, positioning: Positioning) -> list[str]:
    """Return narrative violations: prose implying competition on a disclaimed
    axis without an explicit amendment naming that axis."""
    if not isinstance(prose, str) or not prose.strip():
        return ["narrative is empty"]
    violations: list[str] = []
    prose_lower = prose.lower()
    amended = _amended_axes(positioning)
    for axis in positioning.disclaimed_axes:
        if axis in amended:
            continue
        for phrase in _AXIS_COMPETITION_PHRASES.get(axis, ()):
            if phrase in prose_lower:
                violations.append(
                    f"narrative phrase {phrase!r} implies competition on the "
                    f"disclaimed axis {axis!r} without an explicit amendment to "
                    "the positioning block"
                )
    return violations


def require_narrative_conformant(prose: str, positioning: Positioning) -> None:
    """Fail-closed narrative gate for manuscript export."""
    violations = check_narrative(prose, positioning)
    if violations:
        raise PositioningError(
            "manuscript narrative violates the positioning block: "
            + "; ".join(violations)
        )

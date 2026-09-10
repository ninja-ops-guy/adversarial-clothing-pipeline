"""SPEC-10 — Camera/ISP identity as a first-class channel factor (CTM-A
extension → CTM-C registry).

Lessons L10/L12: in essentially every published physical study, camera
hardware is confounded with architecture (Phan et al. CVPR 2021; CAP
NeurIPS 2024). A transfer tensor cell recorded without channel identity is
an unidentifiable mixture. This module makes that confound a recorded,
stratifiable, fail-closed variable instead of a remembered caution.

Hard rules (fail closed with :class:`ChannelSemanticsError`):

- Unknowns are EXPLICIT. Channel fields take the value ``"unknown"`` (or
  ``"inferred"``) rather than being silently omitted; an unknown never
  inherits a CTM channel identity.
- Any physical-tier channel record without camera identity is classified
  ``CHANNEL-C`` (observational) and is ineligible for strong claims:
  :func:`claim_ceiling` never returns a strong ceiling for it, and
  :func:`require_strong_physical_eligible` refuses it.
- Digital channel claims require at least two distinct differentiable
  ISP-proxy variants (Phan/CAP-style) so "camera-specific vs.
  camera-agnostic" is a measurable factor rather than an assumption:
  :func:`require_digital_claim_eligible` refuses a single-variant record.
- Cross-camera replication (>= 2 distinct identified cameras, same channel
  class) is a promotion precondition for the ``PHYSICAL_REPLICATED`` claim
  state: :func:`require_physical_replicated_eligible`.

Additive: this module does not mutate any frozen schema; the serialized
record is governed by ``schemas/ctm_channel_v1.schema.json``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .errors import CTMBridgeError

CHANNEL_SCHEMA_VERSION = "rac-ctm-channel/1.0"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "ctm_channel_v1.schema.json"
)


class ChannelSemanticsError(CTMBridgeError):
    """Camera/ISP channel semantics contract violated (SPEC-10). Fail closed."""


#: Explicit-unknown sentinels (SPEC-10/SPEC-16: known | unknown | inferred).
UNKNOWN = "unknown"
INFERRED = "inferred"
_FIELD_SENTINELS = frozenset({UNKNOWN, INFERRED})

CHANNEL_TIERS = frozenset({"digital", "physical"})

#: Channel evidence classes. CHANNEL-C is the observational floor;
#: CHANNEL-B is an identified single channel; CHANNEL-A is a cross-camera
#: replicated channel.
CHANNEL_CLASSES = frozenset({"CHANNEL-A", "CHANNEL-B", "CHANNEL-C"})

#: Claim states this module can ceiling. Observational is always legal;
#: stronger states are gated by channel identity and replication.
CLAIM_STATES = frozenset({
    "OBSERVATIONAL",
    "DIGITAL_REPLICATED",
    "PHYSICAL_SINGLE_CHANNEL",
    "PHYSICAL_REPLICATED",
})

_STRONG_PHYSICAL_STATES = frozenset({
    "PHYSICAL_SINGLE_CHANNEL",
    "PHYSICAL_REPLICATED",
})

#: Minimum distinct ISP-proxy variants for a digital channel claim (rule b).
MIN_DIGITAL_ISP_PROXY_VARIANTS = 2

#: Minimum distinct identified cameras for PHYSICAL_REPLICATED (rule c).
MIN_CROSS_CAMERA_REPLICATION = 2

_SHA256_LEN = 64


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _check_descriptors(descriptors: dict[str, str], *, block: str) -> None:
    for key, value in sorted(descriptors.items()):
        if not key:
            raise ChannelSemanticsError(f"{block} descriptor keys must be non-empty")
        if not isinstance(value, str) or not value:
            raise ChannelSemanticsError(
                f"{block} descriptor {key!r} must be a non-empty string; use "
                f"{UNKNOWN!r} or {INFERRED!r} to record an explicit unknown"
            )


@dataclass(frozen=True)
class ChannelRecord:
    """Immutable, versioned camera/ISP channel record (SPEC-10).

    Every descriptor field defaults to ``"unknown"`` — unknowns are
    explicit and serialized, never silently absent.
    """

    channel_id: str
    tier: str
    camera_model: str = UNKNOWN
    isp_pipeline_id: str = UNKNOWN
    raw_available: str = UNKNOWN  # "yes" | "no" | "unknown" | "inferred"
    codec_format: str = UNKNOWN
    codec_bitrate_class: str = UNKNOWN
    demosaic: str = UNKNOWN
    denoise: str = UNKNOWN
    tone_map: str = UNKNOWN
    #: Differentiable ISP-proxy references for the digital tier (Phan/CAP).
    isp_proxy_refs: tuple[str, ...] = ()
    schema_version: str = CHANNEL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CHANNEL_SCHEMA_VERSION:
            raise ChannelSemanticsError(
                f"unsupported channel schema_version: {self.schema_version!r}"
            )
        if not self.channel_id:
            raise ChannelSemanticsError("channel_id is required")
        if self.tier not in CHANNEL_TIERS:
            raise ChannelSemanticsError(
                f"unknown channel tier {self.tier!r}; allowed: {sorted(CHANNEL_TIERS)}"
            )
        for name in (
            "camera_model", "isp_pipeline_id", "codec_format",
            "codec_bitrate_class", "demosaic", "denoise", "tone_map",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ChannelSemanticsError(
                    f"channel field {name!r} must be a non-empty string; use "
                    f"{UNKNOWN!r} for an explicit unknown (fail closed)"
                )
        if self.raw_available not in frozenset({"yes", "no"}) | _FIELD_SENTINELS:
            raise ChannelSemanticsError(
                f"raw_available must be 'yes' | 'no' | 'unknown' | 'inferred'; "
                f"got {self.raw_available!r}"
            )
        for ref in self.isp_proxy_refs:
            if not isinstance(ref, str) or not ref:
                raise ChannelSemanticsError(
                    "isp_proxy_refs entries must be non-empty strings"
                )
        if len(set(self.isp_proxy_refs)) != len(self.isp_proxy_refs):
            raise ChannelSemanticsError(
                "isp_proxy_refs must be distinct (duplicate proxy variants do "
                "not count toward the two-variant minimum)"
            )
        if self.tier == "digital" and not self.isp_proxy_refs:
            raise ChannelSemanticsError(
                "digital-tier channel records must carry at least one "
                "differentiable_isp_proxy_ref (SPEC-10: the digital tier "
                "models the ISP explicitly; two distinct variants are required "
                "before any digital channel claim)"
            )

    # -- derived properties --------------------------------------------------

    @property
    def camera_identified(self) -> bool:
        """True only when BOTH camera identity fields are explicitly known."""
        return (
            self.camera_model not in _FIELD_SENTINELS
            and self.isp_pipeline_id not in _FIELD_SENTINELS
        )

    @property
    def channel_class(self) -> str:
        """Derived channel evidence class. Never user-asserted.

        Physical tier without camera identity -> CHANNEL-C (observational).
        Digital tier with >= 2 distinct ISP-proxy variants -> CHANNEL-B
        (camera-agnostic measurable); a single digital proxy is CHANNEL-C
        until the second variant exists. Cross-camera replication upgrades
        to CHANNEL-A only via :func:`derive_replicated_channel_class`.
        """
        if self.tier == "physical":
            return "CHANNEL-B" if self.camera_identified else "CHANNEL-C"
        # digital
        if len(self.isp_proxy_refs) >= MIN_DIGITAL_ISP_PROXY_VARIANTS:
            return "CHANNEL-B"
        return "CHANNEL-C"

    # -- canonical serialization ---------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "channel_id": self.channel_id,
            "tier": self.tier,
            "camera_model": self.camera_model,
            "isp_pipeline_id": self.isp_pipeline_id,
            "raw_available": self.raw_available,
            "codec": {
                "format": self.codec_format,
                "bitrate_class": self.codec_bitrate_class,
            },
            "isp_descriptors": {
                "demosaic": self.demosaic,
                "denoise": self.denoise,
                "tone_map": self.tone_map,
            },
            "isp_proxy_refs": sorted(self.isp_proxy_refs),
            "camera_identified": self.camera_identified,
            "channel_class": self.channel_class,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def channel_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise ChannelSemanticsError(
                f"channel record fails ctm_channel_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChannelRecord":
        """Parse a serialized record, REFUSING any user-asserted derived
        field (``camera_identified``/``channel_class``) that disagrees with
        the derivation."""
        if not isinstance(payload, dict):
            raise ChannelSemanticsError("channel payload must be an object")
        codec = payload.get("codec", {}) or {}
        isp = payload.get("isp_descriptors", {}) or {}
        record = cls(
            channel_id=payload.get("channel_id", ""),
            tier=payload.get("tier", ""),
            camera_model=payload.get("camera_model", UNKNOWN),
            isp_pipeline_id=payload.get("isp_pipeline_id", UNKNOWN),
            raw_available=payload.get("raw_available", UNKNOWN),
            codec_format=codec.get("format", UNKNOWN),
            codec_bitrate_class=codec.get("bitrate_class", UNKNOWN),
            demosaic=isp.get("demosaic", UNKNOWN),
            denoise=isp.get("denoise", UNKNOWN),
            tone_map=isp.get("tone_map", UNKNOWN),
            isp_proxy_refs=tuple(payload.get("isp_proxy_refs", ())),
            schema_version=payload.get("schema_version", ""),
        )
        for derived_name, derived_value in (
            ("camera_identified", record.camera_identified),
            ("channel_class", record.channel_class),
        ):
            asserted = payload.get(derived_name)
            if asserted is not None and asserted != derived_value:
                raise ChannelSemanticsError(
                    f"user-asserted {derived_name} {asserted!r} disagrees with "
                    f"the derived value {derived_value!r}: channel class is "
                    "derived, never user-asserted (fail closed)"
                )
        return record


# ---------------------------------------------------------------------------
# Claim-ceiling derivation and promotion gates
# ---------------------------------------------------------------------------

def claim_ceiling(record: ChannelRecord) -> str:
    """Derive the maximum claim state a single channel record can support.

    - Physical tier without camera identity: OBSERVATIONAL (CHANNEL-C),
      ineligible for strong claims — no matter what else is recorded.
    - Physical tier with camera identity: PHYSICAL_SINGLE_CHANNEL.
    - Digital tier with >= 2 distinct ISP-proxy variants: DIGITAL_REPLICATED.
    - Digital tier below the two-variant minimum: OBSERVATIONAL.
    """
    if record.tier == "physical":
        if not record.camera_identified:
            return "OBSERVATIONAL"
        return "PHYSICAL_SINGLE_CHANNEL"
    if len(record.isp_proxy_refs) >= MIN_DIGITAL_ISP_PROXY_VARIANTS:
        return "DIGITAL_REPLICATED"
    return "OBSERVATIONAL"


def require_digital_claim_eligible(record: ChannelRecord) -> None:
    """Fail-closed gate (rule b): a digital channel claim requires at least
    two distinct differentiable ISP-proxy variants so "camera-specific vs.
    camera-agnostic" is a measurable factor rather than an assumption."""
    if record.tier != "digital":
        raise ChannelSemanticsError(
            f"digital channel claim refused for tier {record.tier!r}: only "
            "digital-tier records support digital channel claims"
        )
    if len(record.isp_proxy_refs) < MIN_DIGITAL_ISP_PROXY_VARIANTS:
        raise ChannelSemanticsError(
            f"digital channel claim refused: {len(record.isp_proxy_refs)} "
            f"distinct ISP-proxy variant(s) recorded, but "
            f"{MIN_DIGITAL_ISP_PROXY_VARIANTS} are required — a single-proxy "
            "result is camera-specific by construction and cannot support a "
            "camera-agnostic digital claim (fail closed)"
        )


def require_strong_physical_eligible(record: ChannelRecord) -> None:
    """Fail-closed gate (rule a): no strong physical claim from a channel
    record without camera identity (auto-classified CHANNEL-C)."""
    if record.tier != "physical":
        raise ChannelSemanticsError(
            f"strong physical claim refused for tier {record.tier!r}"
        )
    if not record.camera_identified:
        raise ChannelSemanticsError(
            "strong physical claim refused: channel record has no camera "
            "identity (camera_model/isp_pipeline_id unknown or inferred) and "
            "is auto-classified CHANNEL-C (observational). Missing camera "
            "identity downgrades/refuses strong physical promotion — it "
            "never silently passes (fail closed)"
        )


def require_physical_replicated_eligible(records: Iterable[ChannelRecord]) -> None:
    """Fail-closed gate (rule c): PHYSICAL_REPLICATED requires cross-camera
    replication — at least two distinct identified cameras across physical
    records."""
    records = list(records)
    if not records:
        raise ChannelSemanticsError(
            "PHYSICAL_REPLICATED refused: no channel records provided"
        )
    for record in records:
        if record.tier != "physical":
            raise ChannelSemanticsError(
                f"PHYSICAL_REPLICATED refused: record {record.channel_id!r} is "
                f"tier {record.tier!r}, not physical"
            )
    identified = {
        (r.camera_model, r.isp_pipeline_id)
        for r in records
        if r.camera_identified
    }
    if len(identified) < MIN_CROSS_CAMERA_REPLICATION:
        raise ChannelSemanticsError(
            f"PHYSICAL_REPLICATED refused: cross-camera replication is a "
            f"promotion precondition; {len(identified)} distinct identified "
            f"camera(s) across {len(records)} record(s), but "
            f"{MIN_CROSS_CAMERA_REPLICATION} are required (fail closed)"
        )


def derive_replicated_channel_class(records: Iterable[ChannelRecord]) -> str:
    """Derived class for a replicated set: CHANNEL-A only when the
    cross-camera replication gate passes; otherwise the weakest member's
    class (never silently upgraded)."""
    records = list(records)
    if not records:
        raise ChannelSemanticsError("cannot classify an empty channel set")
    try:
        require_physical_replicated_eligible(records)
    except ChannelSemanticsError:
        classes = [r.channel_class for r in records]
        return "CHANNEL-B" if classes and all(c != "CHANNEL-C" for c in classes) else "CHANNEL-C"
    return "CHANNEL-A"

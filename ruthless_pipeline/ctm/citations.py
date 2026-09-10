"""SPEC-6 — Citation verification-status field and load-bearing export gate.

Lesson L5 (verification before amplification): a citation whose evidentiary
basis is "abstract only" must be labeled as such, and no framing decision —
and no load-bearing claim — may rest on it. A claim is *load-bearing* on a
citation when the claim would need rewording if the citation were removed;
``load_bearing`` is therefore machine-declared with a stated reason, never
implicit.

Hard rules (fail closed with :class:`CitationVerificationError`):

- ``verification_status`` is exactly one of ``abstract_only``,
  ``full_text_verified``, ``reproduced_internally`` (same enum as the
  living-corpus registry, SPEC-4).
- A ``load_bearing`` citation MUST carry a ``load_bearing_reason`` stating
  why removing it would force rewording.
- Export/serialization of a claim artifact REFUSES any load-bearing citation
  whose status is ``abstract_only`` (:func:`check_claim_export`). Only
  ``full_text_verified`` or ``reproduced_internally`` support load-bearing
  use (L15: foundational papers never load-bear at abstract level).
- Non-load-bearing citations may remain ``abstract_only`` but serialize with
  that status visible — the label travels with the citation.

This module is additive; it does not mutate the existing
``manuscript/exports/citation_evidence_matrix.json`` contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .corpus import VERIFICATION_STATUSES
from .errors import CTMBridgeError

CITATION_SCHEMA_VERSION = "rac-ctm-citation/1.0"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "ctm_citation_v1.schema.json"
)

#: Statuses that may support a load-bearing claim (L15 hard precondition).
LOAD_BEARING_OK = frozenset({"full_text_verified", "reproduced_internally"})


class CitationError(CTMBridgeError):
    """Base class for citation-contract failures (SPEC-6). Fail closed."""


class CitationVerificationError(CitationError):
    """A load-bearing claim rests on an insufficient verification status."""


@dataclass(frozen=True)
class Citation:
    """Immutable citation verification record.

    ``load_bearing`` is a machine-declared relationship between this citation
    and ``claim_id``: True iff the claim would need rewording if this citation
    were removed. The declaration requires a stated reason.
    """

    citation_id: str
    claim_id: str
    target_ref: str
    verification_status: str
    load_bearing: bool = False
    load_bearing_reason: str = ""
    schema_version: str = CITATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CITATION_SCHEMA_VERSION:
            raise CitationError(
                f"unsupported citation schema_version: {self.schema_version!r}"
            )
        for name in ("citation_id", "claim_id", "target_ref"):
            if not getattr(self, name):
                raise CitationError(f"{name} is required")
        if self.verification_status not in VERIFICATION_STATUSES:
            raise CitationError(
                f"unknown verification_status {self.verification_status!r}; "
                f"allowed: {sorted(VERIFICATION_STATUSES)}"
            )
        if self.load_bearing and not self.load_bearing_reason:
            raise CitationError(
                "load_bearing=True requires load_bearing_reason: state why "
                "removing this citation would force the claim to be reworded "
                "(fail closed)"
            )
        if not self.load_bearing and self.load_bearing_reason:
            raise CitationError(
                "load_bearing_reason is set but load_bearing is False: the "
                "load-bearing relationship must be declared, not implied"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "citation_id": self.citation_id,
            "claim_id": self.claim_id,
            "target_ref": self.target_ref,
            "verification_status": self.verification_status,
            "load_bearing": self.load_bearing,
            "load_bearing_reason": self.load_bearing_reason,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def citation_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise CitationError(
                f"citation record fails ctm_citation_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Citation":
        if not isinstance(payload, dict):
            raise CitationError("citation payload must be an object")
        return cls(
            citation_id=payload.get("citation_id", ""),
            claim_id=payload.get("claim_id", ""),
            target_ref=payload.get("target_ref", ""),
            verification_status=payload.get("verification_status", ""),
            load_bearing=bool(payload.get("load_bearing", False)),
            load_bearing_reason=payload.get("load_bearing_reason", ""),
            schema_version=payload.get("schema_version", ""),
        )


def check_claim_export(citations: Iterable[Citation], *, claim_id: str) -> None:
    """Fail-closed export gate for a claim artifact.

    Refuses (raises :class:`CitationVerificationError`) if ANY citation the
    claim is load-bearing on has verification_status ``abstract_only``.
    Non-load-bearing ``abstract_only`` citations pass but keep their label.
    """
    citations = list(citations)
    for cit in citations:
        if cit.claim_id != claim_id:
            raise CitationError(
                f"citation {cit.citation_id!r} declares claim_id {cit.claim_id!r}, "
                f"not the claim being exported {claim_id!r} (fail closed)"
            )
    offenders = [
        cit for cit in citations
        if cit.load_bearing and cit.verification_status not in LOAD_BEARING_OK
    ]
    if offenders:
        detail = "; ".join(
            f"{c.citation_id} -> {c.target_ref} ({c.verification_status})"
            for c in offenders
        )
        raise CitationVerificationError(
            f"export of claim {claim_id!r} refused: load-bearing citations with "
            f"insufficient verification: {detail}. A claim that would need "
            "rewording without a citation may not rest on abstract_only support "
            "(L5: verification before amplification)."
        )


def export_claim_artifact(
    claim_id: str,
    claim_text: str,
    citations: Iterable[Citation],
) -> dict[str, Any]:
    """Serialize a claim artifact with its citations, after the export gate.

    Every citation serializes with its verification_status visible; the
    artifact is canonicalizable and hash-pinnable.
    """
    citations = list(citations)
    for cit in citations:
        cit.validate_against_schema()
    check_claim_export(citations, claim_id=claim_id)
    if not claim_text:
        raise CitationError("claim_text is required")
    return {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "citations": [c.to_dict() for c in citations],
        "citation_matrix_sha256": sha256_bytes(
            canonical_json([c.to_dict() for c in citations])
        ),
    }

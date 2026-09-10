"""Additive observation-medium annotation registry (NR-02 reconciliation).

The frozen contracts (``schemas/physical_transfer_record.schema.json``,
``schemas/evidence_class.schema.json``) carry NO field distinguishing the
physical medium of an observation: an image composite, a display photographed
by a camera, a printed flat material sample, or a worn fabric garment are
indistinguishable at the schema level. This module closes that gap
ADDITIVELY via sidecar annotations:

- Frozen schemas are NOT modified. An annotation is a separate, versioned
  document that references its subject record by id/hash.
- ``observation_medium`` defaults to ``unknown`` and unknown STAYS unknown:
  a missing medium is never silently upgraded to a concrete medium.
- Promotion guard: :func:`assert_worn_fabric_claim_eligible` extends the
  existing ``PromotionRefusedError`` machinery (imported from
  ``certification.physical_capture_rehearsal`` — not forked). Synthetic
  fixture evidence and photographed-display evidence can never promote a
  worn-fabric claim; only ``worn_fabric`` medium with
  ``measured_physical_capture`` evidence class is eligible, and even that
  never sets ``physical_efficacy_claimed`` under current frozen contracts.
- A change in rendering assumptions creates a NEW annotation that supersedes
  the old one via :func:`compare_rendering_assumptions`; the old annotation
  is never rewritten (immutable, sha256-stamped; mirrors the
  ``physical_transfer.production_profiles.ProfileStore`` immutability rule).

Pure stdlib plus the existing promotion-guard error type.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, FrozenSet, Optional

from ruthless_pipeline.certification.physical_capture_rehearsal import (
    PromotionRefusedError,
)

#: Version of THIS additive extension schema (independent of the frozen
#: subject-record schemas, which remain at their frozen versions).
EXT_SCHEMA_VERSION = "1.0"

IMAGE_COMPOSITE = "image_composite"
DISPLAY_PHOTOGRAPHED_BY_CAMERA = "display_photographed_by_camera"
PRINTED_FLAT_MATERIAL = "printed_flat_material"
WORN_FABRIC = "worn_fabric"
UNKNOWN = "unknown"

OBSERVATION_MEDIA: FrozenSet[str] = frozenset(
    {
        IMAGE_COMPOSITE,
        DISPLAY_PHOTOGRAPHED_BY_CAMERA,
        PRINTED_FLAT_MATERIAL,
        WORN_FABRIC,
        UNKNOWN,
    }
)

DESCRIPTIONS: Dict[str, str] = {
    IMAGE_COMPOSITE: (
        "Digitally composited image (artwork rendered onto a template); "
        "no physical substrate was ever observed."
    ),
    DISPLAY_PHOTOGRAPHED_BY_CAMERA: (
        "A camera photograph of a rendered display surface; photons came "
        "from an emissive display, not from a printed/worn material."
    ),
    PRINTED_FLAT_MATERIAL: (
        "A physical print on flat material (e.g. calibration target, flat "
        "fabric swatch); physically printed but not worn garment geometry."
    ),
    WORN_FABRIC: (
        "A physical garment worn by a person/mannequin under capture-rig "
        "geometry; the only medium eligible to support a worn-fabric claim."
    ),
    UNKNOWN: (
        "Medium not recorded. Unknown stays unknown: never promoted, never "
        "silently reclassified."
    ),
}

#: Media that may support a worn-fabric physical claim. Everything else
#: (including ``unknown``) is refused by the promotion guard.
WORN_FABRIC_CLAIM_MEDIA: FrozenSet[str] = frozenset({WORN_FABRIC})

MEASURED_EVIDENCE_CLASS = "measured_physical_capture"


def is_valid(medium: str) -> bool:
    return medium in OBSERVATION_MEDIA


def describe(medium: str) -> str:
    if not is_valid(medium):
        raise KeyError(f"unregistered observation medium: {medium!r}")
    return DESCRIPTIONS[medium]


def normalize_medium(value: Optional[str]) -> str:
    """Missing/None/empty medium normalizes to ``unknown`` (unknown stays
    unknown). A non-empty unregistered value raises KeyError (fail-closed on
    typos) — it is never coerced to ``unknown``."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return UNKNOWN
    if not is_valid(value):
        raise KeyError(f"unregistered observation medium: {value!r}")
    return value


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def build_medium_annotation(
    *,
    subject_ref: str,
    observation_medium: Optional[str] = None,
    basis: str,
    subject_sha256: Optional[str] = None,
    rendering_assumption_ref: Optional[str] = None,
    supersedes_annotation_sha256: Optional[str] = None,
    annotation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build an additive, sha256-stamped observation-medium annotation.

    ``subject_ref`` identifies the annotated artifact (e.g. a physical
    transfer record id, a capture id, a specimen sku). ``basis`` is a
    mandatory free-text justification of the medium assignment (fail-closed
    like ``assumed_documented`` rationale in production_profiles). When
    ``observation_medium`` is omitted the annotation records ``unknown``.
    """
    if not isinstance(subject_ref, str) or not subject_ref.strip():
        raise ValueError("subject_ref is required")
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError("basis is required (medium assignments must be justified)")
    medium = normalize_medium(observation_medium)
    annotation: dict[str, Any] = {
        "ext_schema_version": EXT_SCHEMA_VERSION,
        "annotation_type": "observation_medium",
        "annotation_id": annotation_id or f"oma-{_sha({'s': subject_ref, 'b': basis})[:16]}",
        "subject_ref": subject_ref,
        "observation_medium": medium,
        "basis": basis,
        "additive_only": True,
        "modifies_subject": False,
        "physical_efficacy_claimed": False,
    }
    if subject_sha256 is not None:
        annotation["subject_sha256"] = subject_sha256
    if rendering_assumption_ref is not None:
        annotation["rendering_assumption_ref"] = rendering_assumption_ref
    if supersedes_annotation_sha256 is not None:
        annotation["supersedes_annotation_sha256"] = supersedes_annotation_sha256
    annotation["annotation_sha256"] = _sha(annotation)
    return annotation


def verify_annotation(annotation: dict[str, Any]) -> dict[str, Any]:
    """Verify an annotation's integrity stamp and medium registration."""
    if annotation.get("ext_schema_version") != EXT_SCHEMA_VERSION:
        raise ValueError("unsupported ext_schema_version")
    if annotation.get("annotation_type") != "observation_medium":
        raise ValueError("annotation_type must be 'observation_medium'")
    normalize_medium(annotation.get("observation_medium"))
    stored = annotation.get("annotation_sha256")
    if not stored:
        raise ValueError("annotation missing annotation_sha256")
    body = {k: v for k, v in annotation.items() if k != "annotation_sha256"}
    if _sha(body) != stored:
        raise ValueError("annotation_sha256 mismatch (tampered annotation)")
    return annotation


def assert_worn_fabric_claim_eligible(
    observation_medium: Optional[str],
    evidence_class: Optional[str],
) -> None:
    """Promotion guard: refuse unless the observation is worn fabric AND the
    evidence class is measured physical capture.

    Synthetic fixture evidence, photographed-display evidence, printed flat
    material, and unknown media are all refused. Raises
    ``PromotionRefusedError`` (the existing rehearsal promotion machinery).
    """
    medium = normalize_medium(observation_medium)
    if medium not in WORN_FABRIC_CLAIM_MEDIA:
        raise PromotionRefusedError(
            f"observation_medium {medium!r} cannot promote a worn-fabric claim; "
            f"eligible media: {sorted(WORN_FABRIC_CLAIM_MEDIA)}. Synthetic fixture "
            "evidence and photographed-display evidence never promote."
        )
    if evidence_class != MEASURED_EVIDENCE_CLASS:
        raise PromotionRefusedError(
            f"evidence_class {evidence_class!r} cannot promote a worn-fabric claim; "
            f"requires {MEASURED_EVIDENCE_CLASS!r}"
        )


def compare_rendering_assumptions(
    old_annotation: dict[str, Any],
    new_annotation: dict[str, Any],
) -> dict[str, Any]:
    """Create a VERSIONED comparison when rendering assumptions change.

    The new annotation must explicitly supersede the old one; the old
    annotation is returned untouched (never rewritten). The comparison record
    binds both annotation hashes so the change is auditable.
    """
    verify_annotation(old_annotation)
    verify_annotation(new_annotation)
    old_sha = old_annotation["annotation_sha256"]
    if new_annotation.get("supersedes_annotation_sha256") != old_sha:
        raise ValueError(
            "new annotation must set supersedes_annotation_sha256 to the old "
            "annotation's hash; rendering-assumption changes are append-only"
        )
    if new_annotation.get("subject_ref") != old_annotation.get("subject_ref"):
        raise ValueError("superseding annotation must annotate the same subject_ref")
    comparison: dict[str, Any] = {
        "ext_schema_version": EXT_SCHEMA_VERSION,
        "annotation_type": "rendering_assumption_comparison",
        "subject_ref": old_annotation["subject_ref"],
        "old_annotation_sha256": old_sha,
        "new_annotation_sha256": new_annotation["annotation_sha256"],
        "old_rendering_assumption_ref": old_annotation.get("rendering_assumption_ref"),
        "new_rendering_assumption_ref": new_annotation.get("rendering_assumption_ref"),
        "old_observation_medium": old_annotation["observation_medium"],
        "new_observation_medium": new_annotation["observation_medium"],
        "old_results_rewritten": False,
    }
    comparison["comparison_sha256"] = _sha(comparison)
    return comparison

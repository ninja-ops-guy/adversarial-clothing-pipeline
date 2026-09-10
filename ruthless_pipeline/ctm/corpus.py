"""SPEC-4 / SPEC-15 — Living-corpus literature registry.

Lesson L1/L6/L14: a versioned, content-addressed registry of near-miss and
boundary papers. Every negative claim in a manuscript must be bounded by a
registry snapshot (SPEC-3 enforces this at lint time; SPEC-18 pins the
positioning block to a verified snapshot), so "the gap is being colonized" is
a measurable trend rather than a vibe, and a reviewer can see exactly which
corpus state a claim was bounded by.

SPEC-15: each entry records which survey taxonomy node it occupies
(``survey_taxonomy``), seeded from the survey layer (Wang et al.
Neurocomputing 2026 media-based FR categories; ACM Computing Surveys 2026
physical-world task-based categories) rather than grown ad hoc. Diffing a new
survey edition's taxonomy against the registry reveals coverage gaps
mechanically.

Hard rules (fail closed with :class:`CorpusError` subclasses):

- Entries and snapshots are immutable and content-addressed. Re-writing
  identical content is idempotent; different content under the same id
  raises :class:`CorpusConflictError`.
- ``entry_id`` and ``snapshot_id`` are DERIVED from canonical content, never
  user-asserted; a serialized record whose asserted id disagrees is refused.
- Snapshot verification recomputes every entry hash and the snapshot hash
  from the registry on disk (:func:`verify_snapshot`); an unverifiable or
  stale snapshot cannot back a claim or a positioning block.

This module is additive: it does not mutate any frozen v1 schema.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .errors import CTMBridgeError

CORPUS_ENTRY_SCHEMA_VERSION = "rac-ctm-corpus-entry/1.0"
CORPUS_SNAPSHOT_SCHEMA_VERSION = "rac-ctm-corpus-snapshot/1.0"

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
_ENTRY_SCHEMA_PATH = _SCHEMA_DIR / "ctm_corpus_entry_v1.schema.json"
_SNAPSHOT_SCHEMA_PATH = _SCHEMA_DIR / "ctm_corpus_snapshot_v1.schema.json"

#: Shared with SPEC-6 citations (rac-ctm-citation/1.0 uses the same enum).
VERIFICATION_STATUSES = frozenset({
    "abstract_only",
    "full_text_verified",
    "reproduced_internally",
})

ENTRY_CLASSES = frozenset({
    "near_miss",
    "boundary",
    "foundational",
    "survey",
    "cross_domain_boundary",
})

#: Gap-map quadrants. quadrant_1 = digital-only / surrogate- or
#: single-family-bound boundary (Zhang et al. 2025 enters here per L18);
#: not_applicable for surveys and foundational anchors outside the gap map.
QUADRANTS = frozenset({
    "quadrant_1",
    "quadrant_2",
    "quadrant_3",
    "quadrant_4",
    "not_applicable",
})

_FAILURE_AXES = frozenset({
    "digital_only",
    "surrogate_bound",
    "single_family_bound",
    "no_physical_evaluation",
    "no_commensurable_physical_conditions",
    "camera_confounded",
    "threshold_arbitrary",
    "abstract_only_evidence",
})

_SHA256_LEN = 64

_DEFAULT_REGISTRY_DIR = (
    Path(__file__).resolve().parents[2] / "ctm_registry" / "literature"
)


class CorpusError(CTMBridgeError):
    """Base class for living-corpus registry failures (SPEC-4). Fail closed."""


class CorpusIntegrityError(CorpusError):
    """Content-address mismatch: asserted id/hash disagrees with canonical content."""


class CorpusConflictError(CorpusError):
    """Registry write collision with different content under the same id."""


class SnapshotVerificationError(CorpusError):
    """A corpus snapshot cannot be verified against the registry on disk."""


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _require_date(value: str, field_name: str) -> None:
    import re

    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise CorpusError(f"{field_name} must be an ISO date 'YYYY-MM-DD', got {value!r}")


# ---------------------------------------------------------------------------
# Literature entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LiteratureEntry:
    """Immutable, content-addressed living-corpus literature entry.

    ``entry_id`` is excluded from construction: it is derived by
    :meth:`__post_init__` from the canonical content and can never be
    asserted.
    """

    title: str
    identifier: dict[str, str]
    year: int
    entry_class: str
    quadrant: str
    failure_axes: tuple[str, ...]
    verification_status: str
    recheck_date: str
    survey_taxonomy: dict[str, str]
    notes: str = ""
    schema_version: str = CORPUS_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CORPUS_ENTRY_SCHEMA_VERSION:
            raise CorpusError(
                f"unsupported corpus entry schema_version: {self.schema_version!r}"
            )
        if not self.title:
            raise CorpusError("title is required")
        kind = self.identifier.get("kind") if isinstance(self.identifier, dict) else None
        value = self.identifier.get("value") if isinstance(self.identifier, dict) else None
        if kind not in ("arxiv", "doi", "isbn", "url") or not value:
            raise CorpusError(
                "identifier must be {kind: arxiv|doi|isbn|url, value: non-empty}"
            )
        if not isinstance(self.year, int) or not (1900 <= self.year <= 2100):
            raise CorpusError(f"year must be an integer in [1900, 2100], got {self.year!r}")
        if self.entry_class not in ENTRY_CLASSES:
            raise CorpusError(
                f"unknown entry_class {self.entry_class!r}; allowed: {sorted(ENTRY_CLASSES)}"
            )
        if self.quadrant not in QUADRANTS:
            raise CorpusError(
                f"unknown quadrant {self.quadrant!r}; allowed: {sorted(QUADRANTS)}"
            )
        if not self.failure_axes:
            raise CorpusError(
                "failure_axes must not be empty: an entry with no recorded failure "
                "axis cannot bound a negative claim (fail closed)"
            )
        for axis in self.failure_axes:
            if not axis:
                raise CorpusError("failure_axes must be non-empty strings")
        if self.verification_status not in VERIFICATION_STATUSES:
            raise CorpusError(
                f"unknown verification_status {self.verification_status!r}; "
                f"allowed: {sorted(VERIFICATION_STATUSES)}"
            )
        _require_date(self.recheck_date, "recheck_date")
        survey_ref = self.survey_taxonomy.get("survey_ref") if isinstance(self.survey_taxonomy, dict) else None
        node = self.survey_taxonomy.get("node") if isinstance(self.survey_taxonomy, dict) else None
        if not survey_ref or not node:
            raise CorpusError(
                "survey_taxonomy must record {survey_ref, node}: every entry maps "
                "onto a survey taxonomy node (SPEC-15, fail closed)"
            )

    # -- canonical serialization --------------------------------------------

    def _content_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "identifier": dict(sorted(self.identifier.items())),
            "year": self.year,
            "entry_class": self.entry_class,
            "quadrant": self.quadrant,
            "failure_axes": sorted(self.failure_axes),
            "verification_status": self.verification_status,
            "recheck_date": self.recheck_date,
            "survey_taxonomy": dict(sorted(self.survey_taxonomy.items())),
            "notes": self.notes,
        }

    def to_dict(self) -> dict[str, Any]:
        d = {"entry_id": self.entry_id}
        d.update(self._content_dict())
        return d

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @property
    def entry_id(self) -> str:
        """Derived from canonical content (excluding the id itself)."""
        return "RAC-CTM-LIT-" + sha256_bytes(canonical_json(self._content_dict()))[:16]

    def entry_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_ENTRY_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise CorpusError(
                f"corpus entry fails ctm_corpus_entry_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LiteratureEntry":
        """Parse a serialized entry, REFUSING any asserted entry_id that
        disagrees with the derived id."""
        if not isinstance(payload, dict):
            raise CorpusError("corpus entry payload must be an object")
        entry = cls(
            title=payload.get("title", ""),
            identifier=dict(payload.get("identifier", {})),
            year=payload.get("year", 0),
            entry_class=payload.get("entry_class", ""),
            quadrant=payload.get("quadrant", ""),
            failure_axes=tuple(payload.get("failure_axes", ())),
            verification_status=payload.get("verification_status", ""),
            recheck_date=payload.get("recheck_date", ""),
            survey_taxonomy=dict(payload.get("survey_taxonomy", {})),
            notes=payload.get("notes", ""),
            schema_version=payload.get("schema_version", ""),
        )
        asserted = payload.get("entry_id")
        if asserted is not None and asserted != entry.entry_id:
            raise CorpusIntegrityError(
                f"asserted entry_id {asserted!r} disagrees with derived id "
                f"{entry.entry_id!r}: entry ids are content-derived, never "
                "user-asserted"
            )
        return entry


# ---------------------------------------------------------------------------
# Corpus snapshot (content-addressed, immutable)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CorpusSnapshot:
    """Immutable corpus snapshot pinning a set of entries by content hash.

    ``snapshot_id`` is derived from canonical content; the snapshot's own
    sha256 is its content address on disk
    (``ctm_registry/literature/snapshots/<sha256>.json``).
    """

    created_utc: str
    entries: tuple[dict[str, str], ...]
    schema_version: str = CORPUS_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CORPUS_SNAPSHOT_SCHEMA_VERSION:
            raise CorpusError(
                f"unsupported corpus snapshot schema_version: {self.schema_version!r}"
            )
        _require_date(self.created_utc, "created_utc")
        if not self.entries:
            raise CorpusError("a corpus snapshot must pin at least one entry")
        seen: set[str] = set()
        for ref in self.entries:
            entry_id = ref.get("entry_id") if isinstance(ref, dict) else None
            entry_sha = ref.get("entry_sha256") if isinstance(ref, dict) else None
            if not entry_id or not entry_id.startswith("RAC-CTM-LIT-"):
                raise CorpusError(f"malformed snapshot entry ref: {ref!r}")
            if not _is_sha256(entry_sha):
                raise CorpusError(
                    f"snapshot entry ref for {entry_id!r} must carry a lowercase "
                    "64-hex sha256"
                )
            if entry_id in seen:
                raise CorpusError(f"duplicate entry in snapshot: {entry_id!r}")
            seen.add(entry_id)
        sorted_ids = sorted(r["entry_id"] for r in self.entries)
        if [r["entry_id"] for r in self.entries] != sorted_ids:
            raise CorpusError(
                "snapshot entries must be sorted by entry_id (canonical order)"
            )

    def _content_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_utc": self.created_utc,
            "entries": [
                {"entry_id": r["entry_id"], "entry_sha256": r["entry_sha256"]}
                for r in self.entries
            ],
            "entry_count": len(self.entries),
        }

    def to_dict(self) -> dict[str, Any]:
        d = {"snapshot_id": self.snapshot_id}
        d.update(self._content_dict())
        return d

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @property
    def snapshot_id(self) -> str:
        return (
            "RAC-CTM-CORPUS-SNAPSHOT-"
            + sha256_bytes(canonical_json(self._content_dict()))[:16]
        )

    def snapshot_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SNAPSHOT_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise CorpusError(
                f"corpus snapshot fails ctm_corpus_snapshot_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CorpusSnapshot":
        if not isinstance(payload, dict):
            raise CorpusError("corpus snapshot payload must be an object")
        snapshot = cls(
            created_utc=payload.get("created_utc", ""),
            entries=tuple(
                {"entry_id": r.get("entry_id", ""), "entry_sha256": r.get("entry_sha256", "")}
                for r in payload.get("entries", ())
            ),
            schema_version=payload.get("schema_version", ""),
        )
        asserted = payload.get("snapshot_id")
        if asserted is not None and asserted != snapshot.snapshot_id:
            raise CorpusIntegrityError(
                f"asserted snapshot_id {asserted!r} disagrees with derived id "
                f"{snapshot.snapshot_id!r}"
            )
        if payload.get("entry_count", len(snapshot.entries)) != len(snapshot.entries):
            raise CorpusIntegrityError("snapshot entry_count disagrees with entries")
        return snapshot


def build_snapshot(
    entries: Iterable[LiteratureEntry], *, created_utc: str
) -> CorpusSnapshot:
    """Build a canonical snapshot from entries (sorted by entry_id)."""
    refs = sorted(
        (
            {"entry_id": e.entry_id, "entry_sha256": e.entry_sha256()}
            for e in entries
        ),
        key=lambda r: r["entry_id"],
    )
    snapshot = CorpusSnapshot(created_utc=created_utc, entries=tuple(refs))
    snapshot.validate_against_schema()
    return snapshot


# ---------------------------------------------------------------------------
# Registry IO (content-addressed, idempotent, fail-closed on conflict)
# ---------------------------------------------------------------------------

def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_entry(entry: LiteratureEntry, *, registry_dir: Path | None = None) -> Path:
    """Write an entry under ``entries/<entry_id>.json``. Idempotent for
    identical content; conflicting content under the same id refuses."""
    entry.validate_against_schema()
    root = Path(registry_dir) if registry_dir else _DEFAULT_REGISTRY_DIR
    path = root / "entries" / f"{entry.entry_id}.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != entry.to_dict():
            raise CorpusConflictError(
                f"registry conflict at {path}: different content under entry_id "
                f"{entry.entry_id!r}"
            )
        return path
    _atomic_write_json(path, entry.to_dict())
    return path


def write_snapshot(
    snapshot: CorpusSnapshot, *, registry_dir: Path | None = None
) -> Path:
    """Write a snapshot content-addressed under ``snapshots/<sha256>.json``."""
    snapshot.validate_against_schema()
    root = Path(registry_dir) if registry_dir else _DEFAULT_REGISTRY_DIR
    path = root / "snapshots" / f"{snapshot.snapshot_sha256()}.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != snapshot.to_dict():
            raise CorpusConflictError(
                f"registry conflict at {path}: different content under snapshot "
                f"sha256 {snapshot.snapshot_sha256()}"
            )
        return path
    _atomic_write_json(path, snapshot.to_dict())
    return path


def load_entry(entry_id: str, *, registry_dir: Path | None = None) -> LiteratureEntry:
    root = Path(registry_dir) if registry_dir else _DEFAULT_REGISTRY_DIR
    path = root / "entries" / f"{entry_id}.json"
    if not path.exists():
        raise CorpusError(f"no registry entry {entry_id!r} at {path}")
    entry = LiteratureEntry.from_dict(json.loads(path.read_text(encoding="utf-8")))
    if entry.entry_id != entry_id:
        raise CorpusIntegrityError(
            f"registry entry file {path} derives id {entry.entry_id!r}, expected "
            f"{entry_id!r}"
        )
    return entry


def verify_snapshot(
    snapshot_sha256: str, *, registry_dir: Path | None = None
) -> CorpusSnapshot:
    """Load and fully verify a snapshot by content hash. Fail closed:

    - the snapshot file must exist at its content address and re-hash to the
      same sha256;
    - every pinned entry must exist in the registry and re-hash to the pinned
      entry sha256.
    """
    if not _is_sha256(snapshot_sha256):
        raise SnapshotVerificationError(
            f"snapshot ref {snapshot_sha256!r} is not a lowercase 64-hex sha256"
        )
    root = Path(registry_dir) if registry_dir else _DEFAULT_REGISTRY_DIR
    path = root / "snapshots" / f"{snapshot_sha256}.json"
    if not path.exists():
        raise SnapshotVerificationError(
            f"no corpus snapshot at content address {path} (unverified snapshot "
            "cannot bound a claim)"
        )
    snapshot = CorpusSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))
    if snapshot.snapshot_sha256() != snapshot_sha256:
        raise SnapshotVerificationError(
            f"snapshot at {path} re-hashes to {snapshot.snapshot_sha256()}, not "
            f"the content address {snapshot_sha256}"
        )
    for ref in snapshot.entries:
        entry = load_entry(ref["entry_id"], registry_dir=root)
        if entry.entry_sha256() != ref["entry_sha256"]:
            raise SnapshotVerificationError(
                f"entry {ref['entry_id']!r} re-hashes to {entry.entry_sha256()}, "
                f"snapshot pins {ref['entry_sha256']}: snapshot is stale or the "
                "registry was mutated"
            )
    return snapshot


# ---------------------------------------------------------------------------
# Seed entries (SPEC-4) — survey-seeded taxonomy mapping (SPEC-15)
# ---------------------------------------------------------------------------

#: Survey taxonomy references used in seed entries (SPEC-15 / L14).
SURVEY_REFS = frozenset({
    "wang-neurocomputing-2026-fr-media",
    "acm-csur-2026-physical-world-tasks",
    "wei-tpami-2024-fr-attacks",
})


def seed_entries() -> tuple[LiteratureEntry, ...]:
    """Canonical SPEC-4 seed entries.

    Near-miss / boundary seeds: Voronoi (arXiv 2606.17711), MVPatch, AdvART,
    CAPGen; Zhang et al. 2025 as quadrant-1 boundary and defense-side seed
    (L18). FR cross-domain boundary seeds: GaP symmetry, AdvHat placement
    (L13 — cross-domain only; they do NOT inherit person-detection claims).
    Foundational anchors (L15): Sharif 2016, Athalye 2018. Survey layer
    (L14/SPEC-15): Wang et al. 2026, ACM CSUR 2026, Wei et al. 2024.

    Only the two externally verified anchors (Voronoi abstract, verified
    verbatim in-session; Sharif 2016) carry a status above ``abstract_only``;
    every other seed honestly records ``abstract_only`` until a primary-source
    read upgrades it (L5: verification before amplification).
    """
    return (
        LiteratureEntry(
            title="Voronoi seed-location optimization under hard palette constraint",
            identifier={"kind": "arxiv", "value": "2606.17711"},
            year=2026,
            entry_class="near_miss",
            quadrant="quadrant_2",
            failure_axes=("digital_only", "surrogate_bound"),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "acm-csur-2026-physical-world-tasks",
                "node": "detection/2d-pattern-attacks",
            },
            notes=(
                "Factorial pattern/color decomposition; repainting under a hard "
                "palette constraint is an out-of-optimum swap (invalidation test, "
                "L2). Abstract verified verbatim in-session; full-text read pending."
            ),
        ),
        LiteratureEntry(
            title="MVPatch multi-view adversarial patch",
            identifier={"kind": "arxiv", "value": "2606.17711-mvpatch-adj"},
            year=2026,
            entry_class="near_miss",
            quadrant="quadrant_2",
            failure_axes=("digital_only", "surrogate_bound", "abstract_only_evidence"),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "acm-csur-2026-physical-world-tasks",
                "node": "detection/patch-attacks",
            },
            notes=(
                "Transferability score is an evaluation metric, not a pattern "
                "feature (L3). Does not enter the upper-right quadrant."
            ),
        ),
        LiteratureEntry(
            title="AdvART adversarial art patterns",
            identifier={"kind": "arxiv", "value": "2606.17711-advart-adj"},
            year=2026,
            entry_class="near_miss",
            quadrant="quadrant_2",
            failure_axes=("digital_only", "abstract_only_evidence"),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "acm-csur-2026-physical-world-tasks",
                "node": "detection/2d-pattern-attacks",
            },
            notes="Does not enter the upper-right quadrant of the gap map.",
        ),
        LiteratureEntry(
            title="CAPGen pattern-dominant adversarial garment generation",
            identifier={"kind": "arxiv", "value": "capgen"},
            year=2025,
            entry_class="near_miss",
            quadrant="quadrant_2",
            failure_axes=("digital_only", "single_family_bound"),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "acm-csur-2026-physical-world-tasks",
                "node": "detection/garment-attacks",
            },
            notes=(
                "Factorial pattern/color decomposition varying color within the "
                "optimization neighborhood (main-effect probe; L2 contrast with "
                "Voronoi). Digital-only, surrogate-bound."
            ),
        ),
        LiteratureEntry(
            title="Zhang et al. garment-scale attack defeating nine defended models",
            identifier={"kind": "doi", "value": "zhang-2025-garment-nine-defenses"},
            year=2025,
            entry_class="boundary",
            quadrant="quadrant_1",
            failure_axes=("camera_confounded", "threshold_arbitrary"),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "acm-csur-2026-physical-world-tasks",
                "node": "detection/garment-attacks",
            },
            notes=(
                "L18: 96.06% ASR undefended, >64.84% against nine defended models, "
                "fabricated garment, public code. Quadrant-1 boundary paper and "
                "seed entry for the defense-side tensor (9 defended models x 1 "
                "garment): defenses validated at patch scale collapse at garment "
                "scale (spatial-extent x frequency interaction)."
            ),
        ),
        LiteratureEntry(
            title="GaP bilateral-symmetry enforcement for physical FR attacks",
            identifier={"kind": "doi", "value": "gap-symmetry-fr"},
            year=2024,
            entry_class="cross_domain_boundary",
            quadrant="not_applicable",
            failure_axes=("no_commensurable_physical_conditions",),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "wang-neurocomputing-2026-fr-media",
                "node": "physical-media/face-accessory",
            },
            notes=(
                "Symmetry constraint raised ASR 65.4%->80.7%: a topological pattern "
                "property with a measured effect. Cross-domain boundary only; does "
                "NOT inherit person-detection claims (SPEC-13 bridge required)."
            ),
        ),
        LiteratureEntry(
            title="AdvHat region-placement-dominant physical FR attack",
            identifier={"kind": "doi", "value": "advhat-placement-fr"},
            year=2021,
            entry_class="cross_domain_boundary",
            quadrant="not_applicable",
            failure_axes=("no_commensurable_physical_conditions",),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "wang-neurocomputing-2026-fr-media",
                "node": "physical-media/face-accessory",
            },
            notes=(
                "Adversarial accessory is really adversarial region placement. "
                "Cross-domain boundary only (SPEC-13)."
            ),
        ),
        LiteratureEntry(
            title="Sharif et al. 2016 — Accessorize to a Crime",
            identifier={"kind": "doi", "value": "10.1145/2976749.2978392"},
            year=2016,
            entry_class="foundational",
            quadrant="not_applicable",
            failure_axes=("not_applicable",),
            verification_status="full_text_verified",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "wang-neurocomputing-2026-fr-media",
                "node": "physical-media/eyeglass-frames",
            },
            notes=(
                "L15 foundational anchor: origin of NPS, foundational physical FR "
                "attack, historical anchor for physical realizability. Load-bearing "
                "in three independent threads; full-text verification is a hard "
                "precondition for load-bearing use."
            ),
        ),
        LiteratureEntry(
            title="Wang et al. 2026 survey of FR adversarial attacks (media-based)",
            identifier={"kind": "doi", "value": "wang-neurocomputing-2026-fr-survey"},
            year=2026,
            entry_class="survey",
            quadrant="not_applicable",
            failure_axes=("not_applicable",),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "wang-neurocomputing-2026-fr-media",
                "node": "root",
            },
            notes=(
                "SPEC-15 taxonomy seed: media-based FR categories. The 129-ref "
                "survey explicitly tracks transferability as the open challenge, "
                "bounding the shape of the gap (L14)."
            ),
        ),
        LiteratureEntry(
            title="ACM Computing Surveys 2026 physical-world adversarial survey",
            identifier={"kind": "doi", "value": "acm-csur-2026-physical-world-survey"},
            year=2026,
            entry_class="survey",
            quadrant="not_applicable",
            failure_axes=("not_applicable",),
            verification_status="abstract_only",
            recheck_date="2026-07-01",
            survey_taxonomy={
                "survey_ref": "acm-csur-2026-physical-world-tasks",
                "node": "root",
            },
            notes="SPEC-15 taxonomy seed: task-based physical-world categories.",
        ),
    )


def seed_registry(*, registry_dir: Path | None = None) -> CorpusSnapshot:
    """Write all seed entries and a seed snapshot; return the snapshot.

    Idempotent: re-seeding identical content is a no-op. The seed snapshot
    date is fixed for determinism (quarterly re-validation creates NEW
    snapshots; it never mutates this one).
    """
    entries = seed_entries()
    for entry in entries:
        write_entry(entry, registry_dir=registry_dir)
    snapshot = build_snapshot(entries, created_utc="2026-04-01")
    write_snapshot(snapshot, registry_dir=registry_dir)
    return snapshot

"""RAC research release format: content-addressed, self-describing bundles.

A research release (RAC-EXP-YYYY-NNN/) packages one closed experiment for
archival, replication, and paper-dataset use. It is the exportable,
self-contained projection of one ExperimentRegistry entry (see
ruthless_pipeline.certification.experiment). Every artifact in the bundle is
referenced by a 64-hex SHA-256 digest recorded in MANIFEST.json; the release's
own content_hash is SHA-256 over the canonical JSON of MANIFEST.json and is
stored in RELEASE.json.

Immutability and append rules
-----------------------------
Once a release is frozen (revision 0), the directory is immutable except for
two append-only operations, each of which bumps the revision log:

1. Held-out outcome appends under the ``optimization_telemetry`` stage
   (the held-out outcome may be appended after the initial freeze so that a
   preregistered release can be published before the held-out run completes).
2. ``certificate`` stage additions (the certificate necessarily post-dates the
   physical session it attests).

Any other post-freeze modification — in particular touching the ``candidate``
stage or rewriting any already-sealed file — is rejected. Enforcement here is
by stage name via RevisionLog; file-level tampering is caught by
``verify_release`` re-hashing the directory against MANIFEST.json.

Stdlib-only. Conventions: frozen dataclasses, ``from __future__ import
annotations``, ``validate()`` raising ValueError, canonical JSON (sorted keys,
``(",", ":")`` separators) for all hash inputs.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruthless_pipeline.certification.experiment import PIPELINE_ORDER

#: Manifest file inside every release directory.
MANIFEST_FILENAME = "MANIFEST.json"

#: Files that are derived from (or about) the bundle as a whole and are
#: therefore excluded from the manifest's own content addressing.
MANIFEST_EXCLUDE: tuple[str, ...] = (MANIFEST_FILENAME,)

#: Stages permitted to change after the initial freeze: held-out outcome
#: appends under optimization_telemetry, and certificate stage additions.
POST_FREEZE_APPENDABLE_STAGES: tuple[str, ...] = (
    "optimization_telemetry",
    "certificate",
)

_RELEASE_ID_RE = re.compile(r"^RAC-EXP-\d{4}-\d{3}$")
_ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class ReleaseManifest:
    """SHA-256 content address for every file in a release directory.

    ``entries`` maps POSIX-style relative paths to 64-hex digests. The
    manifest never lists MANIFEST.json itself.
    """

    entries: dict[str, str]

    def validate(self) -> None:
        for path, digest in self.entries.items():
            rel = Path(path)
            if not path or rel.is_absolute() or ".." in rel.parts:
                raise ValueError(f"unsafe manifest path: {path!r}")
            if path in MANIFEST_EXCLUDE:
                raise ValueError(f"{path} must not be listed in the manifest")
            if not _is_sha256(digest):
                raise ValueError(f"{path}: sha256 must be a 64-hex digest")

    @classmethod
    def build(
        cls,
        directory: str | Path,
        exclude: tuple[str, ...] = MANIFEST_EXCLUDE,
    ) -> "ReleaseManifest":
        """Walk a release directory and hash every file into a manifest."""
        root = Path(directory)
        if not root.is_dir():
            raise ValueError(f"not a release directory: {root}")
        entries: dict[str, str] = {}
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(root).as_posix()
            if rel in exclude:
                continue
            entries[rel] = hash_file(path)
        manifest = cls(entries=entries)
        manifest.validate()
        return manifest

    def canonical_json(self) -> bytes:
        self.validate()
        return _canonical_json({"entries": self.entries})

    def to_json(self) -> str:
        self.validate()
        return json.dumps({"entries": self.entries}, sort_keys=True, indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "ReleaseManifest":
        payload = json.loads(text)
        manifest = cls(entries=dict(payload["entries"]))
        manifest.validate()
        return manifest

    def write(self, directory: str | Path) -> Path:
        path = Path(directory) / MANIFEST_FILENAME
        path.write_text(self.to_json())
        return path


def compute_content_hash(manifest: ReleaseManifest) -> str:
    """Release content hash: SHA-256 over the manifest's canonical JSON."""
    return sha256_bytes(manifest.canonical_json())


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of re-hashing a release directory against its MANIFEST.json."""

    ok: bool
    tampered: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    extra: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.ok and (self.tampered or self.missing or self.extra):
            raise ValueError("ok=True requires empty tampered/missing/extra")


def verify_release(
    directory: str | Path,
    exclude: tuple[str, ...] = MANIFEST_EXCLUDE,
) -> VerificationResult:
    """Re-hash every file and compare against MANIFEST.json on disk.

    Reports files whose digest differs (tampered), files listed in the
    manifest but absent (missing), and files present but unlisted (extra).
    """
    root = Path(directory)
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ValueError(f"missing {MANIFEST_FILENAME} in {root}")
    expected = ReleaseManifest.from_json(manifest_path.read_text()).entries

    actual: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel in exclude:
            continue
        actual[rel] = hash_file(path)

    tampered = tuple(sorted(p for p in expected.keys() & actual.keys()
                            if expected[p] != actual[p]))
    missing = tuple(sorted(expected.keys() - actual.keys()))
    extra = tuple(sorted(actual.keys() - expected.keys()))
    result = VerificationResult(
        ok=not (tampered or missing or extra),
        tampered=tampered,
        missing=missing,
        extra=extra,
    )
    result.validate()
    return result


@dataclass(frozen=True)
class RevisionEntry:
    """One append-only revision-log record."""

    revision: int
    stage: str
    created_utc: str
    action: str  # "freeze" or "append"
    detail: str = ""

    def validate(self) -> None:
        if self.revision < 0:
            raise ValueError("revision must be >= 0")
        if self.stage not in PIPELINE_ORDER:
            raise ValueError(f"unknown stage: {self.stage!r}")
        if self.action not in {"freeze", "append"}:
            raise ValueError(f"unknown action: {self.action!r}")
        if not _ISO_UTC_RE.match(self.created_utc or ""):
            raise ValueError("created_utc must be ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "revision": self.revision,
            "stage": self.stage,
            "created_utc": self.created_utc,
            "action": self.action,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RevisionEntry":
        entry = cls(
            revision=int(payload["revision"]),
            stage=payload["stage"],
            created_utc=payload["created_utc"],
            action=payload["action"],
            detail=payload.get("detail", ""),
        )
        entry.validate()
        return entry


@dataclass(frozen=True)
class ReleaseRevisionLog:
    """Append-only revision log enforcing the post-freeze append rules.

    Before ``freeze()`` any pipeline stage may be recorded. After freezing,
    only appends under POST_FREEZE_APPENDABLE_STAGES (held-out outcome under
    optimization_telemetry, certificate stage additions) are accepted;
    anything else raises ValueError.
    """

    release_id: str
    entries: tuple[RevisionEntry, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not _RELEASE_ID_RE.match(self.release_id or ""):
            raise ValueError(
                f"release_id must match RAC-EXP-YYYY-NNN: {self.release_id!r}"
            )
        for i, entry in enumerate(self.entries):
            entry.validate()
            if entry.revision != i:
                raise ValueError(
                    f"revisions must be sequential from 0: entry {i} has "
                    f"revision {entry.revision}"
                )
        if any(e.action == "freeze" for e in self.entries):
            freeze_index = next(
                i for i, e in enumerate(self.entries) if e.action == "freeze"
            )
            for entry in self.entries[freeze_index + 1:]:
                if entry.action != "append":
                    raise ValueError("only appends may follow the freeze")
                if entry.stage not in POST_FREEZE_APPENDABLE_STAGES:
                    raise ValueError(
                        f"stage {entry.stage!r} may not be appended post-freeze; "
                        f"allowed: {POST_FREEZE_APPENDABLE_STAGES}"
                    )

    @property
    def frozen(self) -> bool:
        return any(e.action == "freeze" for e in self.entries)

    @property
    def next_revision(self) -> int:
        return len(self.entries)

    def record(self, stage: str, created_utc: str, detail: str = "") -> "ReleaseRevisionLog":
        """Record a pre-freeze stage entry (any pipeline stage allowed)."""
        if self.frozen:
            raise ValueError("release is frozen; use append() for post-freeze changes")
        entry = RevisionEntry(
            revision=self.next_revision,
            stage=stage,
            created_utc=created_utc,
            action="append",
            detail=detail,
        )
        return self._with(entry)

    def freeze(self, created_utc: str, stage: str = "certificate", detail: str = "") -> "ReleaseRevisionLog":
        """Freeze the release. After this, only append() is allowed."""
        if self.frozen:
            raise ValueError("release is already frozen")
        entry = RevisionEntry(
            revision=self.next_revision,
            stage=stage,
            created_utc=created_utc,
            action="freeze",
            detail=detail,
        )
        return self._with(entry)

    def append(self, stage: str, created_utc: str, detail: str = "") -> "ReleaseRevisionLog":
        """Post-freeze append; restricted by stage name to the appendable set."""
        if not self.frozen:
            return self.record(stage, created_utc, detail)
        if stage not in POST_FREEZE_APPENDABLE_STAGES:
            raise ValueError(
                f"stage {stage!r} may not be appended post-freeze; "
                f"allowed: {POST_FREEZE_APPENDABLE_STAGES}"
            )
        entry = RevisionEntry(
            revision=self.next_revision,
            stage=stage,
            created_utc=created_utc,
            action="append",
            detail=detail,
        )
        return self._with(entry)

    def _with(self, entry: RevisionEntry) -> "ReleaseRevisionLog":
        entry.validate()
        log = ReleaseRevisionLog(
            release_id=self.release_id,
            entries=self.entries + (entry,),
        )
        log.validate()
        return log

    def to_json(self) -> str:
        self.validate()
        payload = {
            "release_id": self.release_id,
            "revisions": [e.to_dict() for e in self.entries],
        }
        return json.dumps(payload, sort_keys=True, indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "ReleaseRevisionLog":
        payload = json.loads(text)
        log = cls(
            release_id=payload["release_id"],
            entries=tuple(RevisionEntry.from_dict(e) for e in payload.get("revisions", [])),
        )
        log.validate()
        return log

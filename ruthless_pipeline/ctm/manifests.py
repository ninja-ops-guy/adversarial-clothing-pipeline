"""CTM experiment manifests: a new protocol version on existing machinery.

A CTM experiment is expressed as a :class:`CTMExperimentManifest` payload
with its own ``schema_version`` (``rac-ctm-experiment/1.0``) plus a hash-locked
on-disk record, and its lifecycle is driven through the existing
``ruthless_pipeline.certification.experiment_state_machine`` module, which is
imported and WRAPPED here, never edited.

Hard governance rules enforced at build/transition time (fail closed):

- Evidence tiers are ``SYNTHETIC`` or ``DIGITAL`` only. Physical tiers are
  refused with :class:`PhysicalTierBlockedError`: physical work is
  post-Barrier-CTM-2 and user-action gated.
- ``physical_efficacy_claimed`` is hard ``False``; ``True`` raises immediately.
- Locked manifests are immutable: any byte drift is detected by
  :func:`verify_lock` (fail closed with :class:`LockMismatchError`), and
  re-locking with different content raises :class:`ManifestLockedError`.
- CTM experiments NEVER arm in this wave. Arming is a governance authority,
  not a library call: :meth:`CTMExperimentAdapter.arm` and
  :meth:`CTMExperimentAdapter.execute` raise :class:`ArbitrationError`.

Everything here is synthetic-only (``synthetic_pipeline_validation_only``).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from ruthless_pipeline.certification.experiment_state_machine import (
    EVIDENCE_CLASS,
    ExperimentStateMachine,
    GuardEvidence,
    State,
    replay_journal,
    verify_journal,
)

from .contracts import CTMClaim

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CTM_MANIFEST_SCHEMA_VERSION = "rac-ctm-experiment/1.0"

EXPERIMENT_ID_RE = re.compile(r"^CTM-E-[0-9]{6}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

MANIFEST_FILENAME = "manifest.json"
LOCK_FILENAME = "manifest.lock"
JOURNAL_FILENAME = "journal.json"
CLAIM_FILENAME = "claim.json"

#: Evidence tiers legal for CTM experiments in this wave (digital-only).
ALLOWED_EVIDENCE_TIERS = frozenset({"SYNTHETIC", "DIGITAL"})

#: Physical tiers: post-Barrier-CTM-2, user-action gated. Refused at build.
PHYSICAL_EVIDENCE_TIERS = frozenset(
    {"PHYSICAL", "PRINT", "HARDWARE", "EXPERIMENTAL_PRINT", "BENCH"}
)

#: Schema path for the frozen CTM-A claim contract (read-only use).
_CLAIM_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "ctm_claim_v1.schema.json"
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class CTMManifestError(Exception):
    """Base class for all CTM manifest refusals (fail closed)."""


class ManifestLockedError(CTMManifestError):
    """A locked manifest was re-locked with different (non-identical) bytes."""


class LockMismatchError(CTMManifestError):
    """On-disk manifest bytes drifted from the pinned lock digest."""


class PhysicalTierBlockedError(CTMManifestError):
    """A physical evidence tier was requested before Barrier-CTM-2."""


class ArbitrationError(CTMManifestError):
    """An arming/execution transition was attempted on a CTM experiment.

    Arming is a governance authority, not a library call: CTM experiments
    never arm in this wave. This refusal is unconditional and documented.
    """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CTMExperimentManifest:
    """Immutable description of a CTM experiment (digital tiers only).

    ``created_utc`` is caller-supplied so that two builds with identical
    inputs produce byte-identical canonical encodings (determinism).
    """

    experiment_id: str
    title: str
    design: dict[str, Any]
    seed: int
    created_utc: str
    target_panel_ref: str | None = None
    channel_refs: tuple[str, ...] = ()
    null_design_ids: tuple[str, ...] = ()
    evidence_tier: str = "SYNTHETIC"
    physical_efficacy_claimed: bool = False
    status: str = "DRAFT"
    schema_version: str = CTM_MANIFEST_SCHEMA_VERSION
    evidence_class: str = EVIDENCE_CLASS

    def __post_init__(self) -> None:
        if self.schema_version != CTM_MANIFEST_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported CTM manifest schema_version: {self.schema_version!r}"
            )
        if not EXPERIMENT_ID_RE.match(self.experiment_id):
            raise ValueError(
                f"experiment_id {self.experiment_id!r} does not match "
                "^CTM-E-[0-9]{6}$"
            )
        if not self.title:
            raise ValueError("title is required")
        if not isinstance(self.design, dict):
            raise ValueError("design must be a dict (DoE plan / genome-cell targets)")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an int")
        if not self.created_utc:
            raise ValueError(
                "created_utc is required and must be caller-supplied (determinism)"
            )
        if self.target_panel_ref is not None and not _is_sha256(self.target_panel_ref):
            raise ValueError("target_panel_ref must be a 64-hex sha256 or None")
        for channel in self.channel_refs:
            if not isinstance(channel, str) or not channel:
                raise ValueError("channel_refs must be non-empty strings")
        for null_id in self.null_design_ids:
            if not isinstance(null_id, str) or not null_id:
                raise ValueError("null_design_ids must be non-empty strings")
        if self.evidence_tier in PHYSICAL_EVIDENCE_TIERS:
            raise PhysicalTierBlockedError(
                f"evidence_tier {self.evidence_tier!r} is physical: physical work "
                "is post-Barrier-CTM-2 and user-action gated; refused at build time"
            )
        if self.evidence_tier not in ALLOWED_EVIDENCE_TIERS:
            raise ValueError(
                f"unknown evidence_tier {self.evidence_tier!r}; allowed: "
                f"{sorted(ALLOWED_EVIDENCE_TIERS)}"
            )
        if self.physical_efficacy_claimed:
            raise ValueError(
                "physical_efficacy_claimed=True is refused: CTM experiments are "
                "digital-tier only and can never claim physical efficacy"
            )
        if self.status != "DRAFT":
            raise ValueError("a new manifest always starts in status DRAFT")

    # -- canonical encoding --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_class": self.evidence_class,
            "experiment_id": self.experiment_id,
            "title": self.title,
            "design": self.design,
            "target_panel_ref": self.target_panel_ref,
            "channel_refs": list(self.channel_refs),
            "null_design_ids": list(self.null_design_ids),
            "seed": self.seed,
            "created_utc": self.created_utc,
            "evidence_tier": self.evidence_tier,
            "physical_efficacy_claimed": self.physical_efficacy_claimed,
            "status": self.status,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.to_dict())

    def manifest_sha256(self) -> str:
        return _sha256_bytes(self.canonical_bytes())

    def to_json_file(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_bytes(self.canonical_bytes() + b"\n")
        return path


# ---------------------------------------------------------------------------
# Manifest lock semantics
# ---------------------------------------------------------------------------

def lock_manifest(
    manifest: CTMExperimentManifest,
    dir: str | Path,
    *,
    locked_utc: str,
) -> dict[str, Any]:
    """Write ``manifest.json`` + ``manifest.lock`` into ``dir`` (idempotent).

    The lock pins the sha256 of the canonical manifest bytes. If the directory
    is already locked:
    - byte-identical content -> no-op (idempotent re-lock);
    - any other content -> :class:`ManifestLockedError` (immutability).

    ``locked_utc`` is caller-supplied for determinism.
    """
    if not locked_utc:
        raise ValueError("locked_utc is required and must be caller-supplied")
    dir = Path(dir)
    dir.mkdir(parents=True, exist_ok=True)
    manifest_path = dir / MANIFEST_FILENAME
    lock_path = dir / LOCK_FILENAME
    blob = manifest.canonical_bytes() + b"\n"

    if lock_path.exists():
        lock = json.loads(lock_path.read_text())
        existing = manifest_path.read_bytes() if manifest_path.exists() else b""
        pinned = lock.get("manifest_sha256")
        if existing == blob and pinned == manifest.manifest_sha256():
            return lock  # idempotent re-lock
        raise ManifestLockedError(
            f"{dir} is already locked (pinned {pinned}); a locked manifest is "
            "immutable and cannot be re-locked with different content"
        )

    manifest_path.write_bytes(blob)
    lock = {
        "schema_version": CTM_MANIFEST_SCHEMA_VERSION,
        "experiment_id": manifest.experiment_id,
        "manifest_sha256": manifest.manifest_sha256(),
        "locked_utc": locked_utc,
    }
    lock_path.write_bytes(_canonical_bytes(lock) + b"\n")
    return lock


def verify_lock(dir: str | Path) -> dict[str, Any]:
    """Fail closed unless ``dir``'s manifest bytes match its lock digest.

    Any byte drift (edited manifest, missing file, malformed lock) raises
    :class:`LockMismatchError`. Returns the parsed lock record on success.
    """
    dir = Path(dir)
    manifest_path = dir / MANIFEST_FILENAME
    lock_path = dir / LOCK_FILENAME
    if not lock_path.is_file():
        raise LockMismatchError(f"no manifest lock at {lock_path} (fail closed)")
    if not manifest_path.is_file():
        raise LockMismatchError(f"locked manifest missing at {manifest_path}")
    try:
        lock = json.loads(lock_path.read_text())
    except json.JSONDecodeError as exc:
        raise LockMismatchError(f"lock file at {lock_path} is not valid JSON") from exc
    pinned = lock.get("manifest_sha256")
    if not _is_sha256(pinned):
        raise LockMismatchError("lock pins no valid sha256 (fail closed)")
    actual = _sha256_bytes(manifest_path.read_bytes().rstrip(b"\n"))
    actual_with_nl = _sha256_bytes(manifest_path.read_bytes())
    if pinned not in (actual, actual_with_nl):
        raise LockMismatchError(
            f"manifest drift detected in {dir}: on-disk sha256 {actual} != "
            f"pinned {pinned}"
        )
    return lock


# ---------------------------------------------------------------------------
# State-machine adapter (wraps, never edits, the experiment state machine)
# ---------------------------------------------------------------------------

class CTMExperimentAdapter:
    """Drive a CTM experiment through the existing lifecycle machine.

    The adapter owns a caller-provided directory (the CTM registry's
    experiments dir belongs to another lane) holding ``manifest.json``,
    ``manifest.lock`` and the sha-chained ``journal.json``. The wrapped
    :class:`ExperimentStateMachine` is reconstructed from the journal on
    construction, so two adapters built from the same directory are in
    identical states (replay determinism).

    CTM experiments NEVER arm: :meth:`arm` and :meth:`execute` raise
    :class:`ArbitrationError` unconditionally. Arming is a governance
    authority decision, not a library call; this wave stops at PREREGISTERED.
    """

    def __init__(self, experiment_label: str, journal_dir: str | Path) -> None:
        if not experiment_label:
            raise ValueError("experiment_label is required")
        self.experiment_label = experiment_label
        self.dir = Path(journal_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.journal_path = self.dir / JOURNAL_FILENAME
        if self.journal_path.exists():
            machine = replay_journal(json.loads(self.journal_path.read_text()))
            if machine.experiment_label != experiment_label:
                raise CTMManifestError(
                    f"journal in {self.dir} belongs to "
                    f"{machine.experiment_label!r}, not {experiment_label!r}"
                )
            machine.journal_path = self.journal_path
            self.machine = machine
        else:
            self.machine = ExperimentStateMachine(
                experiment_label=experiment_label,
                journal_path=self.journal_path,
            )

    @property
    def state(self) -> State:
        return self.machine.state

    def start(self, manifest: CTMExperimentManifest, *, locked_utc: str) -> dict[str, Any]:
        """Write + lock the manifest; the machine stays DRAFT."""
        if self.machine.state is not State.DRAFT:
            raise CTMManifestError(
                f"start() requires DRAFT, machine is {self.machine.state.value}"
            )
        return lock_manifest(manifest, self.dir, locked_utc=locked_utc)

    def preregister(
        self,
        manifest: CTMExperimentManifest,
        prereg_sha256: str,
        created_utc: str,
    ) -> None:
        """DRAFT -> PREREGISTERED, pinning the preregistration document hash.

        The locked manifest is verified first (fail closed on drift), and the
        transition is journaled under the adapter's own directory.
        """
        verify_lock(self.dir)
        on_disk = _sha256_bytes(
            (self.dir / MANIFEST_FILENAME).read_bytes().rstrip(b"\n")
        )
        if on_disk != manifest.manifest_sha256():
            raise CTMManifestError(
                "presented manifest does not match the locked manifest on disk"
            )
        self.machine.transition(
            State.PREREGISTERED,
            created_utc=created_utc,
            evidence=GuardEvidence(preregistration_sha256=prereg_sha256),
            detail=f"CTM manifest {manifest.experiment_id} preregistered "
            f"(manifest_sha256={manifest.manifest_sha256()})",
        )

    def arm(self, *args: Any, **kwargs: Any) -> None:
        """Refused: CTM experiments never arm in this wave.

        Arming is a governance authority decision (post-Barrier-CTM-2,
        user-action gated), not a library call.
        """
        raise ArbitrationError(
            "CTM experiments cannot be armed through this adapter: arming is a "
            "governance authority, not a library call (hard refusal)"
        )

    def execute(self, *args: Any, **kwargs: Any) -> None:
        """Refused: execution requires ARMED, which CTM experiments never reach."""
        raise ArbitrationError(
            "CTM experiments cannot execute: execution requires arming, and "
            "arming is a governance authority, not a library call (hard refusal)"
        )

    def verify(self) -> None:
        """Fail closed unless the journal chain AND the manifest lock verify."""
        if self.journal_path.exists():
            verify_journal(json.loads(self.journal_path.read_text()))
        verify_lock(self.dir)


# ---------------------------------------------------------------------------
# Claim bridge: CTM-A claim -> provenance-walker JSON shape
# ---------------------------------------------------------------------------

def claim_to_payload(claim: CTMClaim) -> dict[str, Any]:
    """Serialise a :class:`CTMClaim` to the canonical firewall-walker shape."""
    claim.validate()
    payload: dict[str, Any] = {
        "schema_version": claim.schema_version,
        "claim_id": claim.claim_id,
        "state": claim.state.value,
        "feature_id": claim.feature_id,
        "outcome_id": claim.outcome_id,
        "source_commit": claim.source_commit,
        "independent_cohort_count": claim.independent_cohort_count,
        "matched_null_design_ids": list(claim.matched_null_design_ids),
        "consumed_artifacts": [
            {
                "artifact_id": artifact.artifact_id,
                "role": artifact.role.value,
                "sha256": artifact.sha256,
                "heldout_access": artifact.heldout_access,
                "heldout_feedback_used": artifact.heldout_feedback_used,
                "selection_influence": artifact.selection_influence,
                "metadata": dict(artifact.metadata),
            }
            for artifact in claim.consumed_artifacts
        ],
    }
    if claim.notes:
        payload["notes"] = list(claim.notes)
    return payload


def build_claim_artifacts(claim: CTMClaim, out_dir: str | Path) -> Path:
    """Write a claim JSON round-trip-validated against ctm_claim_v1 schema.

    The output is in the canonical provenance-walker shape so it can later be
    placed at ``artifacts/ctm/claims/`` by the owning lane; this function only
    writes to the caller-provided ``out_dir`` and never touches ``artifacts/``.
    Returns the written file path.
    """
    payload = claim_to_payload(claim)
    schema = json.loads(_CLAIM_SCHEMA_PATH.read_text())
    jsonschema.validate(payload, schema)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / CLAIM_FILENAME
    path.write_bytes(_canonical_bytes(payload) + b"\n")
    # Round-trip: re-read and re-validate the bytes actually on disk.
    reread = json.loads(path.read_text())
    jsonschema.validate(reread, schema)
    return path

"""Versioned production-profile store.

Profiles are JSON documents capturing vendor-specific print parameters
(gamut box, min feature size, MTF cutoff, dpi, panel geometry, optional
measured calibration reference). Every profile carries provenance:

- ``profile_id``: stable identifier (string).
- ``version``: positive integer, monotonically increasing per profile_id.
- ``vendor``: vendor name.
- ``source``: one of ``vendor_spec`` | ``measured`` | ``assumed_documented``.
  ``assumed_documented`` REQUIRES a non-empty ``rationale`` field explaining
  why the assumption is acceptable; assumed profiles must never be promoted
  to ``measured`` semantics (UA-4 gates measured values).
- ``created``: ISO-8601 date string (UTC).
- ``sha256``: sha256 of the canonical JSON of the profile content
  (everything except the ``sha256`` field itself), hex-encoded.

Unknown or missing version -> ``ProfileVersionError``. Tampered content
(sha mismatch) -> ``ProfileIntegrityError``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

SOURCES = ("vendor_spec", "measured", "assumed_documented")

REQUIRED_FIELDS = ("profile_id", "version", "vendor", "source", "created")


class ProfileError(ValueError):
    """Base class for profile store errors."""


class ProfileValidationError(ProfileError):
    pass


class ProfileVersionError(ProfileError):
    pass


class ProfileIntegrityError(ProfileError):
    pass


def canonical_json(profile: dict) -> str:
    """Canonical JSON of a profile excluding the ``sha256`` field."""
    body = {k: v for k, v in profile.items() if k != "sha256"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def compute_sha256(profile: dict) -> str:
    return hashlib.sha256(canonical_json(profile).encode("utf-8")).hexdigest()


def validate_profile(profile: dict) -> dict:
    """Validate structure/provenance; returns the profile unchanged.

    Does NOT verify the sha (use ``verify_integrity``) so callers can
    validate before stamping.
    """
    if not isinstance(profile, dict):
        raise ProfileValidationError("profile must be a dict")
    for f in REQUIRED_FIELDS:
        if f not in profile:
            raise ProfileValidationError(f"missing required field: {f}")
    if not isinstance(profile["version"], int) or isinstance(
        profile["version"], bool
    ) or profile["version"] < 1:
        raise ProfileVersionError(
            f"version must be a positive integer, got {profile['version']!r}"
        )
    if profile["source"] not in SOURCES:
        raise ProfileValidationError(
            f"source must be one of {SOURCES}, got {profile['source']!r}"
        )
    if profile["source"] == "assumed_documented":
        rationale = profile.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ProfileValidationError(
                "source 'assumed_documented' requires a non-empty 'rationale'"
            )
    return profile


def verify_integrity(profile: dict) -> dict:
    if "sha256" not in profile:
        raise ProfileIntegrityError("profile missing sha256")
    expected = compute_sha256(profile)
    if profile["sha256"] != expected:
        raise ProfileIntegrityError(
            f"sha256 mismatch: stored {profile['sha256']} != computed {expected}"
        )
    return profile


def make_profile(
    profile_id: str,
    version: int,
    vendor: str,
    source: str,
    rationale: str | None = None,
    created: str | None = None,
    **params,
) -> dict:
    """Build a new stamped (validated + sha256) profile dict.

    ``params`` carry the vendor-specific payload (gamut, min_feature_mm,
    dpi, panel geometry, mtf_cutoff_cycles_per_mm, calibration_ref, ...).
    """
    profile = {
        "profile_id": profile_id,
        "version": version,
        "vendor": vendor,
        "source": source,
        "created": created or date.today().isoformat(),
    }
    if rationale is not None:
        profile["rationale"] = rationale
    profile.update(params)
    validate_profile(profile)
    profile["sha256"] = compute_sha256(profile)
    return profile


class ProfileStore:
    """File-backed store: one JSON file per (profile_id, version)."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, profile_id: str, version: int) -> Path:
        return self.root / f"{profile_id}__v{version}.json"

    def save(self, profile: dict) -> Path:
        validate_profile(profile)
        if "sha256" not in profile:
            profile = dict(profile)
            profile["sha256"] = compute_sha256(profile)
        verify_integrity(profile)
        path = self._path(profile["profile_id"], profile["version"])
        if path.exists():
            raise ProfileVersionError(
                f"profile {profile['profile_id']} v{profile['version']} already "
                "exists; versions are immutable, bump the version"
            )
        path.write_text(json.dumps(profile, indent=2, sort_keys=True))
        return path

    def load(self, profile_id: str, version: int | None = None) -> dict:
        """Load a profile. ``version=None`` loads the latest version.

        Unknown profile / version -> ProfileVersionError.
        """
        if version is None:
            versions = self.versions(profile_id)
            if not versions:
                raise ProfileVersionError(f"unknown profile_id: {profile_id!r}")
            version = max(versions)
        path = self._path(profile_id, version)
        if not path.exists():
            raise ProfileVersionError(
                f"unknown version {version} for profile {profile_id!r}"
            )
        profile = json.loads(path.read_text())
        validate_profile(profile)
        verify_integrity(profile)
        return profile

    def versions(self, profile_id: str) -> list[int]:
        out = []
        for p in sorted(self.root.glob(f"{profile_id}__v*.json")):
            try:
                out.append(int(p.stem.split("__v")[1]))
            except (ValueError, IndexError):
                continue
        return sorted(out)

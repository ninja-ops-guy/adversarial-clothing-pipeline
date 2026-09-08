"""Guard against post-hoc modification of the frozen experiment surface.

Recomputes SHA-256 over every file under the frozen surface and compares
against the committed manifest ``benchmarks/frozen_surface_sha256.json``.
The manifest is infrastructure-owned (generated from HEAD bytes); it is not
the legacy ``SHA256SUMS.txt``, which covers only historical top-level files
and is intentionally left untouched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "benchmarks" / "frozen_surface_sha256.json"

FROZEN_DIRS = ("generations", "protocols", "model_manifests", "model_sets", "design_profiles")
FROZEN_FILES = ("benchmarks/model_manifest.json", "benchmarks/runtime_lock.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _current_surface() -> dict[str, str]:
    entries: dict[str, str] = {}
    for rel in FROZEN_FILES:
        entries[rel] = _sha256(ROOT / rel)
    for directory in FROZEN_DIRS:
        base = ROOT / directory
        for path in sorted(base.rglob("*")):
            if path.is_file():
                entries[path.relative_to(ROOT).as_posix()] = _sha256(path)
    return entries


def test_manifest_is_canonical_json() -> None:
    text = MANIFEST_PATH.read_text()
    manifest = json.loads(text)
    assert text == json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def test_frozen_surface_matches_committed_hashes() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    current = _current_surface()
    missing = sorted(set(manifest) - set(current))
    unexpected = sorted(set(current) - set(manifest))
    mismatched = sorted(p for p in set(manifest) & set(current) if manifest[p] != current[p])
    assert not missing, f"frozen files missing from disk: {missing}"
    assert not unexpected, f"unmanifested files in frozen surface: {unexpected}"
    assert not mismatched, f"frozen files modified post-hoc: {mismatched}"

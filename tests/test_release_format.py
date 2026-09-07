"""Tests for the RAC research release format module."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ruthless_pipeline.certification.release_format import (
    MANIFEST_FILENAME,
    ReleaseManifest,
    ReleaseRevisionLog,
    compute_content_hash,
    verify_release,
)

UTC = "2025-01-15T12:00:00Z"
UTC2 = "2025-01-16T12:00:00Z"


def _make_release(root: Path) -> Path:
    """Build a minimal release directory tree."""
    release = root / "RAC-EXP-2025-001"
    (release / "stages" / "candidate").mkdir(parents=True)
    (release / "stages" / "generation").mkdir(parents=True)
    (release / "stages" / "candidate" / "candidate.json").write_text(
        json.dumps({"candidate_id": "cand-1"}) + "\n"
    )
    (release / "stages" / "generation" / "master.png").write_bytes(b"\x89PNGfake")
    (release / "experiment.json").write_text(json.dumps({"experiment_id": "RAC-EXP-2025-001"}) + "\n")
    (release / "REPORT.md").write_text("# Report\n")
    return release


def _seal(release: Path) -> ReleaseManifest:
    manifest = ReleaseManifest.build(release)
    manifest.write(release)
    return manifest


def test_manifest_build_hashes_every_file(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    manifest = ReleaseManifest.build(release)
    assert set(manifest.entries) == {
        "experiment.json",
        "REPORT.md",
        "stages/candidate/candidate.json",
        "stages/generation/master.png",
    }
    assert all(len(d) == 64 for d in manifest.entries.values())


def test_manifest_excludes_itself(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    manifest = _seal(release)
    rebuilt = ReleaseManifest.build(release)
    assert MANIFEST_FILENAME not in rebuilt.entries
    assert rebuilt.entries == manifest.entries


def test_content_hash_determinism(tmp_path: Path) -> None:
    release_a = _make_release(tmp_path / "a")
    release_b = _make_release(tmp_path / "b")
    h1 = compute_content_hash(ReleaseManifest.build(release_a))
    h2 = compute_content_hash(ReleaseManifest.build(release_b))
    assert h1 == h2 and len(h1) == 64
    # Changing file content changes the content hash.
    (release_b / "REPORT.md").write_text("# Different\n")
    assert compute_content_hash(ReleaseManifest.build(release_b)) != h1


def test_manifest_json_round_trip(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    manifest = ReleaseManifest.build(release)
    restored = ReleaseManifest.from_json(manifest.to_json())
    assert restored == manifest
    assert compute_content_hash(restored) == compute_content_hash(manifest)


def test_verify_release_ok(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    _seal(release)
    result = verify_release(release)
    assert result.ok
    assert not (result.tampered or result.missing or result.extra)


def test_verify_detects_tampering(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    _seal(release)
    target = release / "stages" / "generation" / "master.png"
    data = bytearray(target.read_bytes())
    data[0] ^= 0xFF  # flip a byte
    target.write_bytes(bytes(data))
    result = verify_release(release)
    assert not result.ok
    assert result.tampered == ("stages/generation/master.png",)
    assert not result.missing and not result.extra


def test_verify_detects_missing_file(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    _seal(release)
    (release / "stages" / "candidate" / "candidate.json").unlink()
    result = verify_release(release)
    assert not result.ok
    assert result.missing == ("stages/candidate/candidate.json",)


def test_verify_detects_extra_file(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    _seal(release)
    (release / "stages" / "candidate" / "smuggled.bin").write_bytes(b"evil")
    result = verify_release(release)
    assert not result.ok
    assert result.extra == ("stages/candidate/smuggled.bin",)


def test_verify_requires_manifest(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    with pytest.raises(ValueError, match="MANIFEST"):
        verify_release(release)


def test_revision_log_allows_pre_freeze_stages(tmp_path: Path) -> None:
    log = ReleaseRevisionLog(release_id="RAC-EXP-2025-001")
    log = log.record("candidate", UTC).record("generation", UTC)
    log = log.freeze(UTC2)
    assert log.frozen
    assert log.next_revision == 3


def test_revision_log_rejects_candidate_post_freeze(tmp_path: Path) -> None:
    log = ReleaseRevisionLog(release_id="RAC-EXP-2025-001").freeze(UTC)
    with pytest.raises(ValueError, match="post-freeze"):
        log.append("candidate", UTC2)
    with pytest.raises(ValueError, match="post-freeze"):
        log.append("generation", UTC2)


def test_revision_log_allows_outcome_append_and_certificate(tmp_path: Path) -> None:
    log = ReleaseRevisionLog(release_id="RAC-EXP-2025-001").freeze(UTC)
    log = log.append("optimization_telemetry", UTC2, detail="held-out outcome")
    log = log.append("certificate", "2025-01-17T12:00:00Z")
    assert [e.revision for e in log.entries] == [0, 1, 2]
    assert log.entries[-1].stage == "certificate"


def test_revision_log_rejects_double_freeze(tmp_path: Path) -> None:
    log = ReleaseRevisionLog(release_id="RAC-EXP-2025-001").freeze(UTC)
    with pytest.raises(ValueError, match="already frozen"):
        log.freeze(UTC2)


def test_revision_log_rejects_bad_ids_and_stages(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="RAC-EXP"):
        ReleaseRevisionLog(release_id="nope").validate()
    with pytest.raises(ValueError, match="unknown stage"):
        ReleaseRevisionLog(release_id="RAC-EXP-2025-001").record("bogus", UTC)


def test_revision_log_json_round_trip(tmp_path: Path) -> None:
    log = (
        ReleaseRevisionLog(release_id="RAC-EXP-2025-001")
        .record("candidate", UTC)
        .freeze(UTC2)
        .append("optimization_telemetry", "2025-01-17T12:00:00Z")
    )
    restored = ReleaseRevisionLog.from_json(log.to_json())
    assert restored == log
    restored.validate()


def test_revision_log_rejects_sealed_tamper_via_from_json(tmp_path: Path) -> None:
    log = ReleaseRevisionLog(release_id="RAC-EXP-2025-001").freeze(UTC)
    payload = json.loads(log.to_json())
    payload["revisions"].append(
        {"revision": 1, "stage": "candidate", "created_utc": UTC2,
         "action": "append", "detail": ""}
    )
    with pytest.raises(ValueError, match="post-freeze"):
        ReleaseRevisionLog.from_json(json.dumps(payload))


def test_full_round_trip_build_seal_verify_copy(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    manifest = _seal(release)
    content_hash = compute_content_hash(manifest)
    # RELEASE.json references the content hash; adding it post-seal makes it
    # "extra" unless the manifest is rebuilt — so rebuild then re-seal.
    (release / "RELEASE.json").write_text(
        json.dumps({
            "release_id": "RAC-EXP-2025-001",
            "created_utc": UTC,
            "source_commit": "e78f79d" + "0" * 33,
            "content_hash": content_hash,
        }, indent=2, sort_keys=True) + "\n"
    )
    manifest = _seal(release)
    assert verify_release(release).ok
    # Copy the sealed bundle elsewhere; hashes must survive transport.
    clone = tmp_path / "clone" / release.name
    shutil.copytree(release, clone)
    assert verify_release(clone).ok
    assert compute_content_hash(ReleaseManifest.build(clone)) == compute_content_hash(manifest)

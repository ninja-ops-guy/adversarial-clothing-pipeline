"""Tests for SPEC-4/SPEC-15 living-corpus registry (lane C)."""
from __future__ import annotations

import json

import pytest

from ruthless_pipeline.ctm.corpus import (
    CORPUS_ENTRY_SCHEMA_VERSION,
    CORPUS_SNAPSHOT_SCHEMA_VERSION,
    CorpusConflictError,
    CorpusError,
    CorpusIntegrityError,
    LiteratureEntry,
    CorpusSnapshot,
    SnapshotVerificationError,
    build_snapshot,
    load_entry,
    seed_entries,
    seed_registry,
    verify_snapshot,
    write_entry,
    write_snapshot,
)


def _entry(**overrides):
    kwargs = dict(
        title="Test paper",
        identifier={"kind": "arxiv", "value": "0000.00000"},
        year=2025,
        entry_class="near_miss",
        quadrant="quadrant_2",
        failure_axes=("digital_only",),
        verification_status="abstract_only",
        recheck_date="2026-07-01",
        survey_taxonomy={
            "survey_ref": "acm-csur-2026-physical-world-tasks",
            "node": "detection/patch-attacks",
        },
    )
    kwargs.update(overrides)
    return LiteratureEntry(**kwargs)


# -- positive ----------------------------------------------------------------

def test_entry_roundtrip_and_schema_validation():
    entry = _entry()
    entry.validate_against_schema()
    again = LiteratureEntry.from_dict(entry.to_dict())
    assert again == entry
    assert again.entry_id == entry.entry_id
    assert entry.entry_id.startswith("RAC-CTM-LIT-")


def test_entry_id_is_content_derived_and_deterministic():
    assert _entry().entry_id == _entry().entry_id
    assert _entry(title="Other").entry_id != _entry().entry_id


def test_snapshot_roundtrip_schema_and_determinism():
    entries = [_entry(title="B"), _entry(title="A")]
    snap = build_snapshot(entries, created_utc="2026-04-01")
    snap.validate_against_schema()
    ids = [r["entry_id"] for r in snap.entries]
    assert ids == sorted(ids)
    assert CorpusSnapshot.from_dict(snap.to_dict()) == snap
    assert snap.snapshot_sha256() == build_snapshot(
        [_entry(title="A"), _entry(title="B")], created_utc="2026-04-01"
    ).snapshot_sha256()


def test_write_and_verify_snapshot(tmp_path):
    entries = seed_entries()
    for e in entries:
        write_entry(e, registry_dir=tmp_path)
    snap = build_snapshot(entries, created_utc="2026-04-01")
    write_snapshot(snap, registry_dir=tmp_path)
    verified = verify_snapshot(snap.snapshot_sha256(), registry_dir=tmp_path)
    assert verified == snap
    # idempotent re-write
    write_snapshot(snap, registry_dir=tmp_path)
    write_entry(entries[0], registry_dir=tmp_path)


def test_seed_registry_is_idempotent_and_verifiable(tmp_path):
    snap1 = seed_registry(registry_dir=tmp_path)
    snap2 = seed_registry(registry_dir=tmp_path)
    assert snap1.snapshot_sha256() == snap2.snapshot_sha256()
    assert verify_snapshot(snap1.snapshot_sha256(), registry_dir=tmp_path)
    assert len(snap1.entries) == 10


def test_seed_entries_cover_spec4_seeds():
    entries = seed_entries()
    ids = {e.identifier["value"] for e in entries}
    assert "2606.17711" in ids  # Voronoi
    assert any("mvpatch" in v for v in ids)
    assert any("advart" in v for v in ids)
    assert "capgen" in ids
    zhang = [e for e in entries if "zhang" in e.identifier["value"]][0]
    assert zhang.quadrant == "quadrant_1"  # L18 quadrant-1 boundary
    # SPEC-15: every entry maps to a survey taxonomy node
    for e in entries:
        assert e.survey_taxonomy["survey_ref"] and e.survey_taxonomy["node"]
    # SPEC-13: FR boundary papers are cross_domain_boundary, not person-detection
    for e in entries:
        if e.entry_class == "cross_domain_boundary":
            assert e.quadrant == "not_applicable"


def test_shipped_seed_snapshot_verifies_against_repo_registry():
    """The committed ctm_registry/literature seed snapshot verifies."""
    from ruthless_pipeline.ctm.corpus import _DEFAULT_REGISTRY_DIR

    snap = seed_registry(registry_dir=_DEFAULT_REGISTRY_DIR)  # idempotent no-op
    verified = verify_snapshot(snap.snapshot_sha256())
    assert len(verified.entries) == 10


# -- negative / fail-closed ---------------------------------------------------

def test_missing_survey_taxonomy_fails_closed():
    with pytest.raises(CorpusError):
        _entry(survey_taxonomy={"survey_ref": "", "node": ""})


def test_empty_failure_axes_fails_closed():
    with pytest.raises(CorpusError):
        _entry(failure_axes=())


def test_unknown_verification_status_fails_closed():
    with pytest.raises(CorpusError):
        _entry(verification_status="peer_reviewed")


def test_bad_schema_version_fails_closed():
    with pytest.raises(CorpusError):
        _entry(schema_version="rac-ctm-corpus-entry/0.9")


def test_asserted_entry_id_mismatch_refused():
    payload = _entry().to_dict()
    payload["entry_id"] = "RAC-CTM-LIT-0000000000000000"
    with pytest.raises(CorpusIntegrityError):
        LiteratureEntry.from_dict(payload)


def test_registry_conflict_refused(tmp_path):
    entry = _entry()
    write_entry(entry, registry_dir=tmp_path)
    path = tmp_path / "entries" / f"{entry.entry_id}.json"
    payload = json.loads(path.read_text())
    payload["notes"] = "tampered"
    path.write_text(json.dumps(payload))
    with pytest.raises(CorpusConflictError):
        write_entry(entry, registry_dir=tmp_path)


def test_verify_missing_snapshot_fails_closed(tmp_path):
    with pytest.raises(SnapshotVerificationError):
        verify_snapshot("a" * 64, registry_dir=tmp_path)


def test_verify_non_sha256_ref_fails_closed(tmp_path):
    with pytest.raises(SnapshotVerificationError):
        verify_snapshot("not-a-hash", registry_dir=tmp_path)


def test_verify_snapshot_detects_mutated_entry(tmp_path):
    entries = seed_entries()
    for e in entries:
        write_entry(e, registry_dir=tmp_path)
    snap = build_snapshot(entries, created_utc="2026-04-01")
    write_snapshot(snap, registry_dir=tmp_path)
    # mutate one entry file in place (registry tampering)
    ref = snap.entries[0]
    path = tmp_path / "entries" / f"{ref['entry_id']}.json"
    payload = json.loads(path.read_text())
    payload["notes"] = payload.get("notes", "") + " tampered"
    payload.pop("entry_id")  # avoid from_dict id-mismatch; force hash mismatch
    path.write_text(json.dumps(payload))
    with pytest.raises((SnapshotVerificationError, CorpusError)):
        verify_snapshot(snap.snapshot_sha256(), registry_dir=tmp_path)


def test_unsorted_snapshot_entries_refused():
    entries = [_entry(title="B"), _entry(title="A")]
    refs = [
        {"entry_id": e.entry_id, "entry_sha256": e.entry_sha256()}
        for e in entries
    ]
    if refs[0]["entry_id"] < refs[1]["entry_id"]:
        refs = [refs[1], refs[0]]
    with pytest.raises(CorpusError):
        CorpusSnapshot(created_utc="2026-04-01", entries=tuple(refs))


def test_load_entry_missing_fails_closed(tmp_path):
    with pytest.raises(CorpusError):
        load_entry("RAC-CTM-LIT-0000000000000000", registry_dir=tmp_path)


def test_version_strings():
    assert CORPUS_ENTRY_SCHEMA_VERSION == "rac-ctm-corpus-entry/1.0"
    assert CORPUS_SNAPSHOT_SCHEMA_VERSION == "rac-ctm-corpus-snapshot/1.0"

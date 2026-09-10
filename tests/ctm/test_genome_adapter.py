"""End-to-end registration tests for ctm.genome_adapter."""
import json
from pathlib import Path

import pytest

from ruthless_pipeline.ctm.errors import RegistrationError, RegistryConflictError
from ruthless_pipeline.ctm.genome_adapter import (
    list_registered_pattern_ids,
    load_registered_genome,
    register_digital_genome,
)


def _register(checker_bytes, cfg, registry_root):
    return register_digital_genome(
        checker_bytes,
        candidate_label="fixture://checker.png",
        source_commit="0" * 40,
        runtime_lock_sha256="0" * 64,
        config=cfg,
        registry_root=registry_root,
        extracted_utc="2026-01-01T00:00:00Z",
    )


def test_register_writes_expected_files(checker_bytes, cfg, registry_root):
    rec = _register(checker_bytes, cfg, registry_root)
    assert rec.pattern_id.startswith("RAC-CTM-PAT-")
    assert rec.already_present is False
    d = Path(registry_root) / "patterns" / rec.pattern_id
    for name in ("genome.json", "provenance.json", "master.sha256.json"):
        assert (d / name).is_file()
        assert rec.paths[name].endswith(name)


def test_genome_json_is_canonical(checker_bytes, cfg, registry_root):
    rec = _register(checker_bytes, cfg, registry_root)
    raw = (Path(registry_root) / "patterns" / rec.pattern_id / "genome.json").read_bytes()
    assert raw.endswith(b"\n")
    body = raw[:-1]
    parsed = json.loads(body)
    # canonical: sorted keys, no whitespace separators
    assert body == json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert parsed["genome_id"] == rec.genome_id


def test_provenance_and_sidecar_content(checker_bytes, cfg, registry_root):
    rec = _register(checker_bytes, cfg, registry_root)
    d = Path(registry_root) / "patterns" / rec.pattern_id
    prov = json.loads((d / "provenance.json").read_text())
    assert prov["evidence_class"] == "derived_digital_measurement"
    assert prov["candidate_sha256"] == rec.candidate_sha256
    sidecar = json.loads((d / "master.sha256.json").read_text())
    assert sidecar["candidate_sha256"] == rec.candidate_sha256
    assert sidecar["byte_length"] == len(checker_bytes)
    assert sidecar["physical_efficacy_claimed"] is False
    assert sidecar["evidence_class"] == "derived_digital_measurement"


def test_reregister_idempotent_byte_identical(checker_bytes, cfg, registry_root):
    rec1 = _register(checker_bytes, cfg, registry_root)
    d = Path(registry_root) / "patterns" / rec1.pattern_id
    before = {p.name: p.read_bytes() for p in d.iterdir()}
    rec2 = _register(checker_bytes, cfg, registry_root)
    assert rec2.pattern_id == rec1.pattern_id
    assert rec2.already_present is True
    after = {p.name: p.read_bytes() for p in d.iterdir()}
    assert before == after


def test_conflict_on_different_content_same_forced_id(checker_bytes, stripes_bytes, cfg, registry_root):
    rec = _register(checker_bytes, cfg, registry_root)
    d = Path(registry_root) / "patterns" / rec.pattern_id
    # force a collision: same directory, different genome content
    genome_path = d / "genome.json"
    genome_path.write_bytes(b'{"tampered":true}\n')
    with pytest.raises(RegistryConflictError):
        _register(checker_bytes, cfg, registry_root)


def test_sha_mismatch_fails_closed(checker_bytes, cfg, registry_root):
    with pytest.raises(RegistrationError):
        register_digital_genome(
            b"not a png at all",
            candidate_label="fixture://garbage.png",
            source_commit="0" * 40,
            runtime_lock_sha256="0" * 64,
            config=cfg,
            registry_root=registry_root,
        )


def test_empty_input_rejected(cfg, registry_root):
    with pytest.raises(RegistrationError):
        register_digital_genome(
            b"",
            candidate_label="x",
            source_commit="0" * 40,
            runtime_lock_sha256="0" * 64,
            config=cfg,
            registry_root=registry_root,
        )


def test_list_and_load(checker_bytes, stripes_bytes, cfg, registry_root):
    assert list_registered_pattern_ids(registry_root) == []
    r1 = _register(checker_bytes, cfg, registry_root)
    r2 = register_digital_genome(
        stripes_bytes,
        candidate_label="fixture://stripes.png",
        source_commit="0" * 40,
        runtime_lock_sha256="0" * 64,
        config=cfg,
        registry_root=registry_root,
    )
    ids = list_registered_pattern_ids(registry_root)
    assert ids == sorted([r1.pattern_id, r2.pattern_id])
    loaded = load_registered_genome(registry_root, r1.pattern_id)
    assert loaded["genome_id"] == r1.genome_id
    with pytest.raises(RegistrationError):
        load_registered_genome(registry_root, "RAC-CTM-PAT-0000000000000000")

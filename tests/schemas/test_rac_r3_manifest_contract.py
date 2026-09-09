"""Contract tests for schemas/rac_r3_manifest.schema.json."""

from __future__ import annotations

SCHEMA = "rac_r3_manifest.schema.json"

H = "c" * 64
COMMIT = "1f3ab47" + "0" * 33  # 40 hex chars


def _minimal():
    return {
        "source_commit": COMMIT,
        "dependency_lock_sha256": H,
        "model_hashes": {"yolov8n": H},
        "fixture_hashes": {"fixture-0001": H},
        "seed_manifest": {"optimizer": 7},
        "optimizer_config_ref": None,
        "transformation_manifest_ref": None,
        "candidate_sha256": None,
        "analysis_sha256": None,
        "environment_manifest": {
            "python_version": "3.11.9",
            "os": "linux-x86_64",
            "key_packages": {"numpy": "2.1.0"},
        },
        "journal_ref": "registry/experiments.json",
        "release_manifest_ref": "releases/RAC-EXP-2026-001/MANIFEST.json",
    }


def _full():
    m = _minimal()
    m.update(
        {
            "model_hashes": {"yolov8n": H, "detr-resnet-50": H},
            "fixture_hashes": {"fixture-0001": H, "fixture-0002": H},
            "seed_manifest": {"optimizer": 7, "sampler": 11, "evaluator": 13},
            "optimizer_config_ref": "configs/optimizer/RAC-OBJ-0001.json",
            "transformation_manifest_ref": "configs/transformations/RAC-TD-0001.json",
            "candidate_sha256": H,
            "analysis_sha256": H,
        }
    )
    m["environment_manifest"]["key_packages"] = {"numpy": "2.1.0", "torch": "2.4.0"}
    return m


def test_minimal_valid(validate):
    assert validate(SCHEMA, _minimal()) == []


def test_full_valid(validate):
    assert validate(SCHEMA, _full()) == []


def test_all_twelve_fields_required(validate):
    required = {
        "source_commit",
        "dependency_lock_sha256",
        "model_hashes",
        "fixture_hashes",
        "seed_manifest",
        "optimizer_config_ref",
        "transformation_manifest_ref",
        "candidate_sha256",
        "analysis_sha256",
        "environment_manifest",
        "journal_ref",
        "release_manifest_ref",
    }
    assert len(required) == 12
    for field in required:
        m = _minimal()
        del m[field]
        assert validate(SCHEMA, m), f"missing {field} must fail"


def test_bad_source_commit_fails(validate):
    m = _minimal()
    m["source_commit"] = "1f3ab47"  # short sha not allowed
    assert validate(SCHEMA, m)
    m = _minimal()
    m["source_commit"] = "g" * 40
    assert validate(SCHEMA, m)


def test_bad_sha256_pattern_fails(validate):
    m = _minimal()
    m["dependency_lock_sha256"] = "xyz"
    assert validate(SCHEMA, m)
    m = _minimal()
    m["candidate_sha256"] = "C" * 64  # uppercase
    assert validate(SCHEMA, m)


def test_additional_properties_fails(validate):
    m = _minimal()
    m["extra_field"] = True
    assert validate(SCHEMA, m)
    m = _minimal()
    m["environment_manifest"]["gpu"] = "none"
    assert validate(SCHEMA, m)


def test_seed_manifest_values_must_be_ints(validate):
    m = _minimal()
    m["seed_manifest"]["optimizer"] = "seven"
    assert validate(SCHEMA, m)


def test_hash_maps_must_contain_sha256(validate):
    m = _minimal()
    m["model_hashes"]["yolov8n"] = "deadbeef"
    assert validate(SCHEMA, m)


def test_environment_manifest_missing_packages_fails(validate):
    m = _minimal()
    del m["environment_manifest"]["key_packages"]
    assert validate(SCHEMA, m)

"""Tests for the versioned production-profile store."""

import json

import pytest

from ruthless_pipeline.physical_transfer.production_profiles import (
    ProfileIntegrityError,
    ProfileStore,
    ProfileValidationError,
    ProfileVersionError,
    compute_sha256,
    make_profile,
)


def test_make_profile_stamps_sha_and_validates(tmp_path):
    p = make_profile("vendor-a", 1, "vendor-a", "vendor_spec", dpi=150)
    assert p["sha256"] == compute_sha256(p)
    store = ProfileStore(tmp_path)
    store.save(p)
    loaded = store.load("vendor-a", 1)
    assert loaded == p


def test_assumed_documented_requires_rationale():
    with pytest.raises(ProfileValidationError):
        make_profile("v", 1, "v", "assumed_documented")
    p = make_profile(
        "v", 1, "v", "assumed_documented",
        rationale="vendor PDF spec unavailable; values from public product page",
    )
    assert p["source"] == "assumed_documented"


def test_bad_source_and_bad_version_rejected():
    with pytest.raises(ProfileValidationError):
        make_profile("v", 1, "v", "guessed")
    with pytest.raises(ProfileVersionError):
        make_profile("v", 0, "v", "vendor_spec")
    with pytest.raises(ProfileVersionError):
        make_profile("v", "1", "v", "vendor_spec")


def test_unknown_version_and_profile_error(tmp_path):
    store = ProfileStore(tmp_path)
    store.save(make_profile("v", 1, "v", "vendor_spec"))
    with pytest.raises(ProfileVersionError):
        store.load("v", 99)
    with pytest.raises(ProfileVersionError):
        store.load("nope")
    assert store.load("v")["version"] == 1  # latest


def test_versions_are_immutable(tmp_path):
    store = ProfileStore(tmp_path)
    store.save(make_profile("v", 1, "v", "vendor_spec"))
    with pytest.raises(ProfileVersionError):
        store.save(make_profile("v", 1, "v", "vendor_spec"))
    store.save(make_profile("v", 2, "v", "vendor_spec"))
    assert store.versions("v") == [1, 2]
    assert store.load("v")["version"] == 2


def test_tamper_detected_via_sha(tmp_path):
    store = ProfileStore(tmp_path)
    p = make_profile("v", 1, "v", "vendor_spec", dpi=150)
    path = store.save(p)
    tampered = json.loads(path.read_text())
    tampered["dpi"] = 300
    path.write_text(json.dumps(tampered))
    with pytest.raises(ProfileIntegrityError):
        store.load("v", 1)


def test_sha_changes_with_content():
    a = make_profile("v", 1, "v", "vendor_spec", dpi=150)
    b = make_profile("v", 1, "v", "vendor_spec", dpi=151)
    assert a["sha256"] != b["sha256"]

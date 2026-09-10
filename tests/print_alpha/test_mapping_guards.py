"""Positive/negative contract tests for the two print-alpha production guards
(failure-injection matrix items 13 and 14, now implemented).

Guards under test (scripts_print_alpha/validate_manifests.py):
- validate_mapping_pairing: concrete candidate/control collision fails closed;
  literal PENDING_USER_ACTION equality is unresolved, not a collision.
- validate_mapping_source_pin: mapping manifest must pin the exact bytes of
  its source manifest; missing, malformed, or stale pins fail closed.
"""

from __future__ import annotations

import hashlib
import json

import jsonschema
import pytest

from scripts_print_alpha.validate_manifests import (
    PENDING,
    validate_mapping_pairing,
    validate_mapping_source_pin,
)


def _valid_mapping(pin: str = "0" * 64) -> dict:
    return {
        "schema_version": "1.0",
        "manifest_id": "fixture-mapping",
        "evidence_class": "experimental_print_specimen",
        "physical_efficacy_claimed": False,
        "source_manifest_ref": "sku-manifest.json",
        "source_manifest_sha256": pin,
        "placements": [
            {
                "placement": "front",
                "control_file": "control.jpg",
                "candidate_file": "candidate.jpg",
                "panel_geometry_ref": "front",
            }
        ],
    }


class TestPairingGuard:
    def test_distinct_files_pass(self):
        validate_mapping_pairing(_valid_mapping())  # no raise

    def test_pending_equality_is_unresolved_not_collision(self):
        mapping = _valid_mapping()
        mapping["placements"][0]["control_file"] = PENDING
        mapping["placements"][0]["candidate_file"] = PENDING
        validate_mapping_pairing(mapping)  # no raise

    def test_concrete_collision_fails_closed(self):
        mapping = _valid_mapping()
        mapping["placements"][0]["candidate_file"] = "control.jpg"
        with pytest.raises(jsonschema.ValidationError, match="collision"):
            validate_mapping_pairing(mapping)

    def test_pending_vs_concrete_passes(self):
        mapping = _valid_mapping()
        mapping["placements"][0]["candidate_file"] = PENDING
        validate_mapping_pairing(mapping)  # no raise


class TestSourcePinGuard:
    def test_correct_pin_passes(self, tmp_path):
        source = tmp_path / "sku-manifest.json"
        payload = json.dumps({"garments": ["v1"]}).encode()
        source.write_bytes(payload)
        mapping = _valid_mapping(pin=hashlib.sha256(payload).hexdigest())
        validate_mapping_source_pin(mapping, source)  # no raise

    def test_stale_pin_fails_closed(self, tmp_path):
        source = tmp_path / "sku-manifest.json"
        source.write_text(json.dumps({"garments": ["v1"]}))
        mapping = _valid_mapping(pin=hashlib.sha256(b'{"garments": ["v0"]}').hexdigest())
        with pytest.raises(jsonschema.ValidationError, match="stale production mapping"):
            validate_mapping_source_pin(mapping, source)

    def test_missing_pin_fails_closed(self, tmp_path):
        source = tmp_path / "sku-manifest.json"
        source.write_text(json.dumps({"garments": ["v1"]}))
        mapping = _valid_mapping()
        del mapping["source_manifest_sha256"]
        with pytest.raises(jsonschema.ValidationError, match="source_manifest_sha256"):
            validate_mapping_source_pin(mapping, source)

    def test_malformed_pin_fails_closed(self, tmp_path):
        source = tmp_path / "sku-manifest.json"
        source.write_text(json.dumps({"garments": ["v1"]}))
        mapping = _valid_mapping(pin="not-a-sha256")
        with pytest.raises(jsonschema.ValidationError, match="source_manifest_sha256"):
            validate_mapping_source_pin(mapping, source)

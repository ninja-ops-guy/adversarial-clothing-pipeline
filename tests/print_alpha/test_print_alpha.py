"""RAC-PRINT-ALPHA-001 contract tests.

Covers:
- all five manifests exist and the primary manifest validates against the
  FROZEN schemas/print_alpha_manifest.schema.json contract;
- physical_efficacy_claimed is false and evidence_class is
  experimental_print_specimen across every manifest;
- every unresolved vendor field is the literal string PENDING_USER_ACTION
  (fail-closed, never fabricated);
- trial-sheet.csv has exactly 108 data rows and re-export is byte-identical;
- invalid-condition-rules.json parses and covers >= 4 condition classes.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO_ROOT / "print-alpha" / "MANIFESTS"
FROZEN_SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "print_alpha_manifest.schema.json").read_text()
)

MANIFEST_FILES = [
    "print-alpha-manifest.json",
    "artwork-manifest.json",
    "template-manifest.json",
    "mapping-manifest.json",
    "sku-manifest.json",
]

EXPECTED_PATTERN_SHA256 = (
    "b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546"
)


def _load(name: str):
    return json.loads((MANIFEST_DIR / name).read_text())


def _iter_strings(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _iter_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_strings(value)
    elif isinstance(node, str):
        yield node


class TestManifests:
    def test_all_five_manifests_exist(self):
        for name in MANIFEST_FILES:
            assert (MANIFEST_DIR / name).is_file(), name

    def test_primary_manifest_validates_against_frozen_schema(self):
        jsonschema.validate(_load("print-alpha-manifest.json"), FROZEN_SCHEMA)

    def test_supporting_manifests_are_valid_json(self):
        for name in MANIFEST_FILES:
            _load(name)

    @pytest.mark.parametrize("name", MANIFEST_FILES)
    def test_physical_efficacy_claimed_false(self, name):
        data = _load(name)
        assert data.get("physical_efficacy_claimed") is False, name

    @pytest.mark.parametrize("name", MANIFEST_FILES)
    def test_evidence_class(self, name):
        data = _load(name)
        assert data.get("evidence_class") == "experimental_print_specimen", name

    @pytest.mark.parametrize("name", MANIFEST_FILES)
    def test_pending_fields_are_literal(self, name):
        for value in _iter_strings(_load(name)):
            if value.upper().startswith("PENDING"):
                assert value == "PENDING_USER_ACTION", (name, value)

    def test_primary_manifest_pinned_fields(self):
        data = _load("print-alpha-manifest.json")
        assert data["manifest_id"] == "RAC-PRINT-ALPHA-001"
        assert (
            data["candidate_artwork_ref"]["expected_sha256"]
            == EXPECTED_PATTERN_SHA256
        )
        assert data["user_action_refs"] == ["UA-1", "UA-2", "UA-3", "UA-4"]

    def test_vendor_unresolved_fields_pending(self):
        garment = _load("print-alpha-manifest.json")["garment"]
        assert garment["size"] == "PENDING_USER_ACTION"
        assert garment["print_technology"] == "PENDING_USER_ACTION"
        assert garment["printer_vendor"] == "PENDING_USER_ACTION"
        assert garment["manufacturing_batch"] in (None, "PENDING_USER_ACTION")

    def test_validate_manifests_script_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "scripts_print_alpha/validate_manifests.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


class TestTrialSheet:
    CSV_PATH = REPO_ROOT / "print-alpha" / "CAPTURE" / "trial-sheet.csv"

    def test_row_count_108(self):
        with self.CSV_PATH.open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 108

    def test_matched_control_candidate_files(self):
        with self.CSV_PATH.open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            assert row["control_file"] == f"captures/{row['trial_id']}__control.jpg"
            assert row["candidate_file"] == f"captures/{row['trial_id']}__candidate.jpg"
            assert row["wash_state"] == "W0"

    def test_deterministic_reexport_byte_identical(self, tmp_path):
        out = tmp_path / "trial-sheet.csv"
        result = subprocess.run(
            [sys.executable, "scripts_print_alpha/export_trial_sheet.py", str(out)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert out.read_bytes() == self.CSV_PATH.read_bytes()


class TestInvalidConditionRules:
    RULES_PATH = REPO_ROOT / "print-alpha" / "CAPTURE" / "invalid-condition-rules.json"

    def test_parses_and_covers_at_least_four_classes(self):
        rules = json.loads(self.RULES_PATH.read_text())
        classes = {c["class_id"] for c in rules["condition_classes"]}
        assert len(classes) >= 4
        assert {"blur", "exposure", "occlusion", "framing"} <= classes

    def test_stopping_rule_semantics_preserved(self):
        rules = json.loads(self.RULES_PATH.read_text())
        assert rules["physical_efficacy_claimed"] is False
        assert rules["evidence_class"] == "experimental_print_specimen"
        rule_text = rules["semantics"]["invalid_condition_rule"]
        assert "never candidate successes" in rule_text
        assert "invalid_condition_report" in rule_text

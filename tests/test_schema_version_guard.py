"""Tests for the shared schema-version guard and its wired call sites.

Fail-closed contract: a missing, non-string, or mismatched schema_version
must raise SchemaVersionError (a ValueError) with a clear message; only the
exact expected version parses. Covers the incident class of the
print-test-kit 1.3-vs-1.4 mismatch: consumers must never silently parse a
newer/older contract shape.
"""

import json
from pathlib import Path

import pytest

from ruthless_pipeline.certification.schema_version import (
    SchemaVersionError,
    load_versioned_json,
    require_schema_version,
)

import scripts.ingest_capture_inference as ici
from scripts.validate_capture_session import load_session
from scripts import ingest_closed_generation as icg


# --------------------------------------------------------------------------
# Utility unit tests
# --------------------------------------------------------------------------

def test_accepts_exact_version():
    payload = {"schema_version": "1.0", "data": 1}
    assert require_schema_version(payload, "1.0") is payload


@pytest.mark.parametrize("bad", [
    {},                                        # missing
    {"schema_version": None},                  # null
    {"schema_version": 1.0},                   # non-string
    {"schema_version": "2.0"},                 # mismatch (newer)
    {"schema_version": "0.9"},                 # mismatch (older)
    {"schema_version": "1.0.0"},               # near-miss
    {"schema_version": " 1.0"},                # whitespace is significant
    ["not", "a", "dict"],                      # non-mapping
])
def test_rejects_fail_closed(bad):
    with pytest.raises(SchemaVersionError):
        require_schema_version(bad, "1.0", label="unit")


def test_error_message_names_label_expected_and_actual():
    with pytest.raises(SchemaVersionError) as exc:
        require_schema_version({"schema_version": "1.4"}, "1.3", label="print test kit")
    msg = str(exc.value)
    assert "print test kit" in msg and "'1.3'" in msg and "'1.4'" in msg


def test_schema_version_error_is_a_value_error():
    # Existing fail-closed call sites catch ValueError; the guard must fit.
    with pytest.raises(ValueError):
        require_schema_version({}, "1.0")


def test_load_versioned_json_roundtrip(tmp_path: Path):
    path = tmp_path / "contract.json"
    path.write_text(json.dumps({"schema_version": "3.0", "x": 1}))
    assert load_versioned_json(path, "3.0")["x"] == 1
    path.write_text(json.dumps({"schema_version": "4.0"}))
    with pytest.raises(SchemaVersionError, match="unsupported schema_version"):
        load_versioned_json(path, "3.0")
    path.write_text('{"schema_version": "3.0"')  # truncated
    with pytest.raises(ValueError):
        load_versioned_json(path, "3.0")


# --------------------------------------------------------------------------
# Wired call-site integration
# --------------------------------------------------------------------------

def _trial_store_record(prev_sha=None):
    return {
        "schema_version": "1.0",
        "trial": {
            "trial_id": "T1", "condition_id": "C1",
            "control_detected": True, "candidate_detected": False,
            "camera_id": "cam", "distance_m": 3.0, "yaw_deg": 0.0,
            "pitch_deg": 0.0, "pose": "standing", "lighting_id": "L1",
            "wash_state": "W0", "metadata": {},
        },
        "trial_record": {"trial_id": "T1"},
        "evidence_class": "physical_garment_p1",
        "calibration_pass": True,
        "lineage": {"experiment_id": "E1"},
        "prev_record_sha256": prev_sha,
    }


def test_trial_store_rejects_wrong_schema_version(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    record = _trial_store_record()
    record["schema_version"] = "9.9"
    store.write_text(ici.canonical(record).decode() + "\n")
    with pytest.raises(SchemaVersionError, match="trial store line 1"):
        ici.load_trial_store(store)
    record["schema_version"] = "1.0"
    store.write_text(ici.canonical(record).decode() + "\n")
    assert len(ici.load_trial_store(store)) == 1


def test_capture_session_requires_schema_version(tmp_path: Path):
    session = {
        "session_id": "S1", "experiment_id": "E1",
        "evidence_class": "physical_garment_p1", "actor_id": "A1",
        "camera_id": "C1", "captures": {"control": {}, "candidate": {}},
    }
    p = tmp_path / "session.json"
    p.write_text(json.dumps(session))
    with pytest.raises(SchemaVersionError, match="missing schema_version"):
        load_session(p)
    session["schema_version"] = "2.0"
    p.write_text(json.dumps(session))
    with pytest.raises(SchemaVersionError, match="unsupported schema_version"):
        load_session(p)
    session["schema_version"] = "1.0"
    p.write_text(json.dumps(session))
    assert load_session(p)["session_id"] == "S1"


def test_generation_ingest_rejects_unversioned_record():
    with pytest.raises(SchemaVersionError, match="generation record"):
        icg._check_generation_closed(
            {"lock_inference_performed": True, "status": "CLOSED",
             "generation_id": "RAC-PER-D2-9999"},
            Path("generation.json"),
        )
    with pytest.raises(SchemaVersionError):
        icg._check_generation_closed(
            {"schema_version": "1.1", "lock_inference_performed": True,
             "status": "CLOSED", "generation_id": "RAC-PER-D2-9999"},
            Path("generation.json"),
        )

"""Tests for the Research OS dashboard data export (Wave I item 7).

Guards:

1. Schema validation: the export is schema-versioned and fails closed on
   version drift.
2. Determinism: two builds produce byte-identical output (same sha256), and
   the committed ``artifacts/dashboard/experiments.json`` re-derives exactly.
3. The D2-0004 record matches ``d2-latest-status.json`` field-for-field
   (parsed, never transcribed — no drift possible).
4. Every hash field in every record recomputes against its source.
5. Promotion guard: synthetic/draft/planned evidence classes can never
   populate measured fields.
6. D2-0005 is PREREGISTERED, not armed, blocked on the arming packet.
"""

import hashlib
import json
from pathlib import Path

import pytest

from ruthless_pipeline.certification.schema_version import (
    SchemaVersionError,
    require_schema_version,
)
from scripts.export_dashboard_data import (
    DASHBOARD_SCHEMA_ID,
    DASHBOARD_SCHEMA_VERSION,
    D2_STATUS_MEASURED_FIELDS,
    MEASURED_EVIDENCE_CLASSES,
    PromotionGuardError,
    build_dashboard,
    dashboard_sha256,
    measured_fields_for,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_EXPORT = REPO_ROOT / "artifacts" / "dashboard" / "experiments.json"


def _record(payload, experiment_id):
    matches = [r for r in payload["records"] if r["experiment_id"] == experiment_id]
    assert len(matches) == 1
    return matches[0]


def test_schema_validation():
    payload = build_dashboard(REPO_ROOT)
    require_schema_version(payload, DASHBOARD_SCHEMA_VERSION, label="dashboard")
    assert payload["schema_id"] == DASHBOARD_SCHEMA_ID
    with pytest.raises(SchemaVersionError):
        require_schema_version(
            {**payload, "schema_version": "0.1"},
            DASHBOARD_SCHEMA_VERSION,
            label="dashboard",
        )


def test_export_is_deterministic():
    p1 = build_dashboard(REPO_ROOT)
    p2 = build_dashboard(REPO_ROOT)
    assert dashboard_sha256(p1) == dashboard_sha256(p2)
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)


def test_committed_export_rederives_exactly():
    if not COMMITTED_EXPORT.is_file():
        pytest.skip("committed dashboard artifact not present")
    committed = json.loads(COMMITTED_EXPORT.read_text())
    rebuilt = build_dashboard(REPO_ROOT)
    assert dashboard_sha256(rebuilt) == dashboard_sha256(committed)


def test_expected_records_present():
    payload = build_dashboard(REPO_ROOT)
    ids = {r["experiment_id"] for r in payload["records"]}
    assert ids == {
        "RAC-PER-D2-0003",
        "RAC-PER-D2-0004",
        "RAC-PER-D2-0005",
        "RAC-PER-D2-0006",
        "PRODUCTION-ALPHA-P1",
    }


def test_d2004_record_matches_d2_latest_status_exactly():
    payload = build_dashboard(REPO_ROOT)
    record = _record(payload, "RAC-PER-D2-0004")
    status = json.loads((REPO_ROOT / "d2-latest-status.json").read_text())
    assert record["decision"] == status["decision"]
    assert record["source_commit"] == status["source_commit"]
    for field in D2_STATUS_MEASURED_FIELDS:
        if field in status:
            assert record["measured"][field] == status[field], field


def test_every_hash_field_recomputes():
    payload = build_dashboard(REPO_ROOT)
    file_hash_fields = {
        "status_file_sha256": {
            "RAC-PER-D2-0003": "manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json",
            "RAC-PER-D2-0004": "d2-latest-status.json",
        },
        "benchmark_results_sha256": {"RAC-PER-D2-0003": "benchmark-results.json"},
        "log_attested_evidence_sha256": {
            "RAC-PER-D2-0004": "manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json"
        },
        "generation_file_sha256": {"RAC-PER-D2-0005": "generations/RAC-PER-D2-0005.json"},
        "freeze_candidate_sha256": {"RAC-PER-D2-0005": "docs/D2-0005_FREEZE_CANDIDATE.json"},
        "draft_policy_sha256": {"RAC-PER-D2-0006": "docs/PREREGISTRATION_D2-0006_DRAFT.md"},
        "sku_manifest_sha256": {"PRODUCTION-ALPHA-P1": "production_alpha/SKU_MANIFEST.json"},
    }
    for record in payload["records"]:
        for field, by_id in file_hash_fields.items():
            if field not in record["key_hashes"]:
                continue
            rel = by_id[record["experiment_id"]]
            actual = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
            assert record["key_hashes"][field] == actual, (
                record["experiment_id"],
                field,
            )
    # runtime_lock hash recomputes
    lock = REPO_ROOT / payload["runtime_lock"]["path"]
    assert payload["runtime_lock"]["sha256"] == hashlib.sha256(
        lock.read_bytes()
    ).hexdigest()
    # candidate shas match their attested sources (never retyped)
    d4 = _record(payload, "RAC-PER-D2-0004")
    log_doc = json.loads(
        (
            REPO_ROOT
            / "manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json"
        ).read_text()
    )
    assert (
        d4["key_hashes"]["candidate_sha256"]
        == log_doc["step18_measured_benchmark_stdout"]["candidate_sha256"]
    )


def test_promotion_guard_blocks_synthetic_measured_fields():
    called = []

    def loader():
        called.append(True)
        return {"decision": "PASS"}

    for evidence_class in ("synthetic", "draft", "planned", "preregistered_not_executed"):
        with pytest.raises(PromotionGuardError):
            measured_fields_for(evidence_class, loader)
    assert called == [], "loader must never run for non-measured classes"
    assert measured_fields_for("log_attested", loader) == {"decision": "PASS"}
    assert called == [True]


def test_non_measured_records_have_null_measured_block():
    payload = build_dashboard(REPO_ROOT)
    for record in payload["records"]:
        if record["evidence_class"] not in MEASURED_EVIDENCE_CLASSES:
            assert record["measured"] is None, record["experiment_id"]
            assert record["decision"] is None, record["experiment_id"]
        else:
            assert record["measured"] is not None, record["experiment_id"]


def test_d2005_preregistered_not_armed_blocked_on_user():
    payload = build_dashboard(REPO_ROOT)
    record = _record(payload, "RAC-PER-D2-0005")
    assert record["state"] == "PREREGISTERED"
    assert record["armed"] is False
    assert any(
        "arming packet awaiting user" in blocker
        for blocker in record["blockers"]
    )
    assert record["user_actions_required"], "arming actions must be harvested"


def test_production_alpha_harvests_user_actions():
    payload = build_dashboard(REPO_ROOT)
    record = _record(payload, "PRODUCTION-ALPHA-P1")
    actions = " ".join(record["user_actions_required"])
    assert "PENDING-API-FETCH" in actions or "Printful" in actions
    assert record["blockers"]
    assert record["physical_state"] == "no_physical_sample_received"

"""Tests for cumulative P1 trial-store accumulation and physical release export."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from scripts import ingest_capture_inference as ingest
from scripts.export_physical_release import build_release
from ruthless_pipeline.certification import p1_pairing_schedule as ps
from ruthless_pipeline.certification.release_format import (
    ReleaseManifest,
    compute_content_hash,
    verify_release,
)

UTC = "2026-02-01T00:00:00Z"
STOPPING_RULE = Path(__file__).resolve().parent.parent / "physical" / "p1" / "STOPPING_RULE.json"
SCHEDULE = ps.derive_schedule()
SCHEDULE_SHA256 = ps.schedule_sha256(SCHEDULE)


def _schedule_entry(session_id: str) -> dict:
    digits = re.findall(r"\d+", session_id)
    ordinal = int(digits[-1]) if digits else 0
    index = ordinal % len(SCHEDULE)
    return SCHEDULE[index]


def _schedule_binding(entry: dict) -> dict:
    return {
        "contract_id": ps.CONTRACT_ID,
        "schedule_sha256": SCHEDULE_SHA256,
        "trial_id": entry["trial_id"],
        "execution_position": entry["execution_position"],
        "cell_id": entry["cell_id"],
        "repetition": entry["repetition"],
        "first_arm": entry["first_arm"],
        "arms": entry["arms"],
        "distance_m": entry["distance_m"],
        "yaw_deg": entry["yaw_deg"],
        "pitch_deg": entry["pitch_deg"],
        "lighting_variant": entry["lighting_variant"],
        "pose": entry["pose"],
    }


def _session(
    session_id: str,
    *,
    evidence_class: str = "physical_garment_p1",
    calibration_pass: bool = True,
    distance_m: float = 3.0,
) -> dict:
    del distance_m  # physical fixtures use the frozen schedule geometry
    entry = _schedule_entry(session_id)
    return {
        "session_id": session_id,
        "experiment_id": "RAC-EXP-2026-001",
        "hypothesis_id": "RAC-HYP-001",
        "evidence_class": evidence_class,
        "calibration_pass": calibration_pass,
        "sealed": True,
        "trial_id": entry["trial_id"],
        "p1_schedule": _schedule_binding(entry),
        "camera_id": "RAC-CAM-01",
        "distance_m": entry["distance_m"],
        "yaw_deg": entry["yaw_deg"],
        "pitch_deg": entry["pitch_deg"],
        "pose": entry["pose"],
        "lighting_variant": entry["lighting_variant"],
        "lighting_id": "RAC-LIGHT-01",
        "wash_state": "W0",
        "captures": {"still": [f"{session_id}/control.cr3", f"{session_id}/candidate.cr3"]},
        "control": {"artifact_id": "RAC-CTRL-001"},
        "candidate": {"artifact_id": "RAC-CAND-001", "sha256": "c" * 64},
        "generation": {"artifact_id": "RAC-GEN-2026-001", "sha256": "9" * 64},
    }


def _inference(
    session_id: str,
    *,
    control: bool = True,
    candidate: bool = False,
    salt: str = "a",
) -> dict:
    return {
        "session_id": session_id,
        "experiment_id": "RAC-EXP-2026-001",
        "result_sha256": salt if len(salt) == 64 else salt * 64,
        "capture_hash_verification": "PASS",
        "paired_summary": {"model_outcomes": {
            "model-a": {"control_detected": control, "candidate_detected": candidate},
            "model-b": {"control_detected": control, "candidate_detected": False},
        }},
    }


def _run_ingest(
    tmp_path: Path,
    session: dict,
    inference: dict,
    trial_store: Path | None = None,
) -> dict:
    session_path = tmp_path / f"{session['session_id']}-session.json"
    inference_path = tmp_path / f"{session['session_id']}-inference.json"
    session_path.write_text(json.dumps(session))
    inference_path.write_text(json.dumps(inference))
    out_dir = tmp_path / f"out-{session['session_id']}"
    argv = [
        "ingest",
        str(session_path),
        str(inference_path),
        "--stopping-rule",
        str(STOPPING_RULE),
        "--output-dir",
        str(out_dir),
    ]
    if trial_store is not None:
        argv += ["--trial-store", str(trial_store)]
    old = sys.argv
    sys.argv = argv
    try:
        assert ingest.main() == 0
    finally:
        sys.argv = old
    return json.loads((out_dir / "statistics.json").read_text())


def _store_records(store: Path) -> list[dict]:
    return [json.loads(line) for line in store.read_text().splitlines() if line.strip()]


def _make_store(tmp_path: Path, n: int, *, candidate: bool = False) -> Path:
    store = tmp_path / "trial-store.jsonl"
    for i in range(n):
        _run_ingest(
            tmp_path,
            _session(f"S{i:04d}", distance_m=[1.0, 3.0, 5.0][i % 3]),
            _inference(f"S{i:04d}", candidate=candidate, salt=f"{i + 1:064x}"),
            trial_store=store,
        )
    return store


# -- promotion gate ---------------------------------------------------------


def test_promotion_gate_accepts_calibrated_physical_p1() -> None:
    ingest.enforce_promotion_gate(_session("S1"))


def test_promotion_gate_rejects_synthetic() -> None:
    with pytest.raises(ValueError, match="promotion gate"):
        ingest.enforce_promotion_gate(
            _session("S1", evidence_class="synthetic_pipeline_validation_only")
        )


def test_promotion_gate_rejects_paper_prototype() -> None:
    with pytest.raises(ValueError, match="promotion gate"):
        ingest.enforce_promotion_gate(_session("S1", evidence_class="printed_flat_prototype"))


def test_promotion_gate_rejects_failed_calibration() -> None:
    with pytest.raises(ValueError, match="calibration_pass"):
        ingest.enforce_promotion_gate(_session("S1", calibration_pass=False))


def test_cli_store_rejects_synthetic_session(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="promotion gate"):
        _run_ingest(
            tmp_path,
            _session("SYN", evidence_class="synthetic_pipeline_validation_only"),
            _inference("SYN"),
            trial_store=tmp_path / "store.jsonl",
        )
    assert not (tmp_path / "store.jsonl").exists()


def test_cli_store_rejects_paper_prototype_session(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="promotion gate"):
        _run_ingest(
            tmp_path,
            _session("PP", evidence_class="printed_flat_prototype"),
            _inference("PP"),
            trial_store=tmp_path / "store.jsonl",
        )
    assert not (tmp_path / "store.jsonl").exists()


# -- accumulation -----------------------------------------------------------


def test_trial_store_accumulates_and_recomputes(tmp_path: Path) -> None:
    store = tmp_path / "store.jsonl"
    first_session = _session("S1")
    second_session = _session("S2")
    first = _run_ingest(tmp_path, first_session, _inference("S1"), trial_store=store)
    assert first["cumulative_trial_count"] == 1
    second = _run_ingest(tmp_path, second_session, _inference("S2", salt="b"), trial_store=store)
    assert second["cumulative_trial_count"] == 2
    assert second["valid_trial_count"] == 2
    assert second["statistics"]["valid_trials"] == 2
    records = _store_records(store)
    assert [r["trial"]["trial_id"] for r in records] == [first_session["trial_id"], second_session["trial_id"]]


def test_trial_store_counts_invalid_trials_truthfully(tmp_path: Path) -> None:
    store = tmp_path / "store.jsonl"
    _run_ingest(tmp_path, _session("S1"), _inference("S1"), trial_store=store)
    stats = _run_ingest(
        tmp_path, _session("S2"), _inference("S2", control=False, salt="b"), trial_store=store
    )
    assert stats["cumulative_trial_count"] == 2
    assert stats["valid_trial_count"] == 1
    assert stats["statistics"]["valid_trials"] == 1
    assert stats["invalid_conditions"]["invalid_trials"] == 1


def test_trial_store_rejects_duplicate_trial_id(tmp_path: Path) -> None:
    store = tmp_path / "store.jsonl"
    _run_ingest(tmp_path, _session("S1"), _inference("S1"), trial_store=store)
    with pytest.raises(SystemExit, match="duplicate trial_id"):
        _run_ingest(tmp_path, _session("S1"), _inference("S1"), trial_store=store)


def test_trial_store_hash_chain_detects_tampering(tmp_path: Path) -> None:
    store = _make_store(tmp_path, 3)
    lines = store.read_text().splitlines()
    record = json.loads(lines[1])
    record["trial"]["distance_m"] = 99.0
    lines[1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
    store.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="hash-chain break"):
        ingest.load_trial_store(store)


def test_trial_store_rejects_stored_synthetic_record(tmp_path: Path) -> None:
    store = tmp_path / "store.jsonl"
    _run_ingest(tmp_path, _session("S1"), _inference("S1"), trial_store=store)
    record = _store_records(store)[0]
    record["evidence_class"] = "synthetic_pipeline_validation_only"
    store.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    with pytest.raises(ValueError, match="hash-chain break|promotion gate"):
        ingest.load_trial_store(store)


def test_backward_compatible_without_trial_store(tmp_path: Path) -> None:
    stats = _run_ingest(tmp_path, _session("S1"), _inference("S1"))
    assert stats["cumulative_trial_count"] == 1
    assert "trial_store" not in stats
    assert "stored_trial_count" not in stats
    stats = _run_ingest(
        tmp_path,
        _session("SYN", evidence_class="synthetic_pipeline_validation_only", calibration_pass=False),
        _inference("SYN"),
    )
    assert stats["physical_evidence_eligible"] is False


# -- release export ---------------------------------------------------------


def _calibration_profile(tmp_path: Path) -> Path:
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"profile_id": "RAC-PCP-1-001"}) + "\n")
    return path


def test_export_fails_closed_below_minimum_trials(tmp_path: Path) -> None:
    store = _make_store(tmp_path, 3)
    with pytest.raises(ValueError, match="stopping rule"):
        build_release(
            store,
            _calibration_profile(tmp_path),
            "RAC-EXP-2026-001",
            tmp_path / "releases",
            UTC,
            STOPPING_RULE,
        )


def test_export_seals_release_and_verifies(tmp_path: Path) -> None:
    store = _make_store(tmp_path, 93)
    release_dir, manifest = build_release(
        store,
        _calibration_profile(tmp_path),
        "RAC-EXP-2026-001",
        tmp_path / "releases",
        UTC,
        STOPPING_RULE,
    )
    assert release_dir.name == "RAC-EXP-2026-001"
    expected = {
        "trial-records.json", "statistics.json", "invalid-conditions.json",
        "calibration.json", "inference-refs.json", "experiment.json",
        "REPORT.md", "report.json", "RELEASE.json",
    }
    assert set(manifest.entries) == expected
    result = verify_release(release_dir)
    assert result.ok

    stats = json.loads((release_dir / "statistics.json").read_text())
    assert stats["cumulative_trial_count"] == 93
    assert stats["valid_trial_count"] == 93
    assert stats["stopping_decision"]["may_stop"] is True

    release_meta = json.loads((release_dir / "RELEASE.json").read_text())
    assert release_meta["created_utc"] == UTC
    manifest_without_release = ReleaseManifest.build(
        release_dir, exclude=("MANIFEST.json", "RELEASE.json")
    )
    assert release_meta["content_hash"] == compute_content_hash(manifest_without_release)

    experiment = json.loads((release_dir / "experiment.json").read_text())
    assert experiment["evidence_label"] == "internally_measured"
    assert [s["stage"] for s in experiment["stages"]] == [
        "candidate", "generation", "calibration_profile", "physical_session"
    ]

    calibration = json.loads((release_dir / "calibration.json").read_text())
    assert len(calibration["sha256"]) == 64
    inference_refs = json.loads((release_dir / "inference-refs.json").read_text())
    assert len(inference_refs["inference_sha256"]) == 93
    assert all(len(h) == 64 for h in inference_refs["inference_sha256"])
    report_text = (release_dir / "REPORT.md").read_text()
    assert "## Results" in report_text
    assert "RAC-EXP-2026-001" in report_text


def test_export_is_deterministic_given_created_utc(tmp_path: Path) -> None:
    store = _make_store(tmp_path, 93)
    calibration = _calibration_profile(tmp_path)
    dir_a, manifest_a = build_release(
        store, calibration, "RAC-EXP-2026-001", tmp_path / "a", UTC, STOPPING_RULE
    )
    dir_b, manifest_b = build_release(
        store, calibration, "RAC-EXP-2026-001", tmp_path / "b", UTC, STOPPING_RULE
    )
    assert manifest_a.entries == manifest_b.entries
    assert compute_content_hash(manifest_a) == compute_content_hash(manifest_b)
    assert (dir_a / "MANIFEST.json").read_bytes() == (dir_b / "MANIFEST.json").read_bytes()


def test_export_tamper_detection_round_trip(tmp_path: Path) -> None:
    store = _make_store(tmp_path, 93)
    release_dir, _ = build_release(
        store,
        _calibration_profile(tmp_path),
        "RAC-EXP-2026-001",
        tmp_path / "releases",
        UTC,
        STOPPING_RULE,
    )
    (release_dir / "statistics.json").write_text("{}\n")
    result = verify_release(release_dir)
    assert not result.ok
    assert result.tampered == ("statistics.json",)


def test_export_rejects_mismatched_release_id(tmp_path: Path) -> None:
    store = _make_store(tmp_path, 2)
    with pytest.raises(ValueError, match="does not match"):
        build_release(
            store,
            _calibration_profile(tmp_path),
            "RAC-EXP-2026-099",
            tmp_path / "releases",
            UTC,
            STOPPING_RULE,
        )


def test_export_rejects_empty_store(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="empty"):
        build_release(
            tmp_path / "missing.jsonl",
            _calibration_profile(tmp_path),
            "RAC-EXP-2026-001",
            tmp_path / "releases",
            UTC,
            STOPPING_RULE,
        )

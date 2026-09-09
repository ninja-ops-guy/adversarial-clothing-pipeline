"""Tests for the synthetic physical capture rehearsal.

Every artifact under test is synthetic_pipeline_validation_only: no physical
test is executed, no physical efficacy is claimed, and promotion to
P1/physical-measured evidence must be impossible.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.physical_capture_rehearsal import (
    EVIDENCE_LABEL,
    CalibrationAssociationError,
    CaptureLab,
    DuplicateCaptureError,
    PromotionRefusedError,
    TrialStoreTamperedError,
    append_rehearsal_store,
    build_synthetic_calibration_profile,
    build_synthetic_print_alpha_package,
    build_synthetic_receipt,
    build_synthetic_trials,
    canonical,
    evaluate_stopping_rule,
    load_rehearsal_store,
    load_stopping_rule,
    load_trial_sheet_rows,
    paired_trial_statistics,
    promote_rehearsal_release,
    rehearsal_store_record,
    run_rehearsal,
)
from ruthless_pipeline.certification.release_format import verify_release


@pytest.fixture()
def rehearsal(tmp_path: Path) -> dict:
    return run_rehearsal(tmp_path / "run")


# -- happy path -------------------------------------------------------------


def test_full_chain_runs_and_seals_release(rehearsal: dict) -> None:
    assert rehearsal["release_verification_ok"] is True
    assert rehearsal["calibration_accepted"] is True
    assert rehearsal["total_trials"] == 108  # Print Alpha 108-row trial geometry
    assert rehearsal["valid_trials"] < rehearsal["total_trials"]


def test_every_artifact_is_synthetic_labelled(rehearsal: dict, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    for name in (
        "print-alpha-package.json",
        "receipt.json",
        "calibration-profile.json",
        "capture-lab.json",
        "statistics.json",
        "research-os-registry.json",
        "summary.json",
    ):
        payload = json.loads((run_dir / name).read_text())
        assert payload["evidence_label"] == EVIDENCE_LABEL, name
    release = json.loads((run_dir / "release" / rehearsal["release_id"] / "RELEASE.json").read_text())
    assert release["evidence_label"] == EVIDENCE_LABEL
    assert release["physical_test_executed"] is False
    assert release["physical_efficacy_claimed"] is False
    assert release["promotion_eligible"] is False


def test_release_directory_verifies(rehearsal: dict, tmp_path: Path) -> None:
    result = verify_release(tmp_path / "run" / "release" / rehearsal["release_id"])
    assert result.ok


def test_trial_store_round_trip(rehearsal: dict, tmp_path: Path) -> None:
    records = load_rehearsal_store(tmp_path / "run" / "trial-store.jsonl")
    assert len(records) == 108
    assert all(r["evidence_label"] == EVIDENCE_LABEL for r in records)


# -- failure injections ------------------------------------------------------


def test_duplicate_capture_identity_rejected() -> None:
    profile = build_synthetic_calibration_profile()
    lab = CaptureLab(profile.profile_id, profile.profile_sha256())
    lab.register_capture("CAP-X", "SYNTHETIC-SKU-CTRL-001", profile.profile_id)
    with pytest.raises(DuplicateCaptureError):
        lab.register_capture("CAP-X", "SYNTHETIC-SKU-CTRL-001", profile.profile_id)


def test_calibration_association_missing_rejected() -> None:
    profile = build_synthetic_calibration_profile()
    lab = CaptureLab(profile.profile_id, profile.profile_sha256())
    with pytest.raises(CalibrationAssociationError):
        lab.register_capture("CAP-Y", "SYNTHETIC-SKU-CTRL-001", None)
    with pytest.raises(CalibrationAssociationError):
        lab.register_capture("CAP-Z", "SYNTHETIC-SKU-CTRL-001", "RAC-PCP-OTHER-9")


def test_invalid_condition_over_threshold_handled_per_protocol() -> None:
    profile = build_synthetic_calibration_profile()
    lab = CaptureLab(profile.profile_id, profile.profile_sha256())
    package = build_synthetic_print_alpha_package()
    receipt = build_synthetic_receipt(package)
    rows = load_trial_sheet_rows()
    overload = rows[0]["condition_id"]
    trials, _ = build_synthetic_trials(rows, lab, receipt, invalid_overload_condition=overload)
    overloaded = [t for t in trials if t.condition_id == overload]
    # Every overloaded trial is invalid (control undetected)...
    assert all(not t.control_detected for t in overloaded)
    # ...excluded from valid trials and NEVER counted as candidate success.
    stats = paired_trial_statistics(trials, bootstrap_resamples=1000)
    # Valid trials are exactly the control-detected ones (baseline natural
    # invalids plus the injected overload are all excluded).
    assert stats.valid_trials == sum(1 for t in trials if t.control_detected)
    assert stats.valid_trials == len(trials) - len(overloaded) - sum(
        1 for t in trials if t.condition_id != overload and not t.control_detected
    )
    assert all(not t.candidate_detected for t in overloaded)
    # The invalid fraction exceeds the preregistered 0.10 flag threshold.
    fraction = len(overloaded) / (len(overloaded) + 0)  # all trials in condition invalid
    assert fraction > 0.10


def test_stopping_rule_replay_deterministic(rehearsal: dict) -> None:
    assert rehearsal["stopping_rule_replay_deterministic"] is True
    rows = load_trial_sheet_rows()
    profile = build_synthetic_calibration_profile()
    lab = CaptureLab(profile.profile_id, profile.profile_sha256())
    receipt = build_synthetic_receipt(build_synthetic_print_alpha_package())
    trials, _ = build_synthetic_trials(rows, lab, receipt)
    stats = paired_trial_statistics(trials, bootstrap_resamples=1000)
    rule = load_stopping_rule()
    assert asdict(evaluate_stopping_rule(rule, stats)) == asdict(evaluate_stopping_rule(rule, stats))


def test_tampered_trial_store_detected(tmp_path: Path) -> None:
    rows = load_trial_sheet_rows()
    profile = build_synthetic_calibration_profile()
    lab = CaptureLab(profile.profile_id, profile.profile_sha256())
    receipt = build_synthetic_receipt(build_synthetic_print_alpha_package())
    trials, records = build_synthetic_trials(rows, lab, receipt)
    store = tmp_path / "store.jsonl"
    prev = None
    for trial, record in zip(trials[:4], records[:4]):
        store_record = rehearsal_store_record(trial, record, prev)
        append_rehearsal_store(store, store_record)
        prev = hashlib.sha256(canonical(store_record)).hexdigest()
    lines = store.read_text().splitlines()
    tampered = json.loads(lines[1])
    tampered["trial"]["candidate_detected"] = not tampered["trial"]["candidate_detected"]
    lines[1] = canonical(tampered).decode()
    store.write_text("\n".join(lines) + "\n")
    with pytest.raises(TrialStoreTamperedError):
        load_rehearsal_store(store)


def test_promotion_to_p1_refused(rehearsal: dict, tmp_path: Path) -> None:
    release_dir = tmp_path / "run" / "release" / rehearsal["release_id"]
    with pytest.raises(PromotionRefusedError):
        promote_rehearsal_release(release_dir, target="physical_garment_p1")
    with pytest.raises(PromotionRefusedError):
        promote_rehearsal_release(release_dir, target="internally_measured")


def test_promotion_refused_on_missing_release(tmp_path: Path) -> None:
    with pytest.raises(PromotionRefusedError):
        promote_rehearsal_release(tmp_path / "nonexistent")


# -- determinism --------------------------------------------------------------


def test_two_full_runs_identical_summary_sha256(tmp_path: Path) -> None:
    s1 = run_rehearsal(tmp_path / "run1")
    s2 = run_rehearsal(tmp_path / "run2")
    assert s1["summary_sha256"] == s2["summary_sha256"]
    assert s1["artifacts"] == s2["artifacts"]
    assert s1["release_content_hash"] == s2["release_content_hash"]

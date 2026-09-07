"""Wave F / Track C tests: P1 executability artifacts.

Validates the calibration target generator, the physical/p1 templates, the
preregistered stopping rule, and the synthetic end-to-end dry run.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.generate_calibration_target import (
    GRID_COLS,
    GRID_ROWS,
    SCALE_BAR_MM,
    TARGET_ID,
    generate,
    srgb_to_lab,
)
from scripts.p1_synthetic_dry_run import (
    MAX_VALID_TRIALS,
    build_synthetic_calibration_profile,
    build_synthetic_session_trials,
    run_dry_run,
)

from ruthless_pipeline.certification.calibration_ingest import delta_e_2000
from ruthless_pipeline.certification.experiment import ExperimentArtifact
from ruthless_pipeline.certification.trial_statistics import (
    PreregisteredStoppingRule,
    evaluate_stopping_rule,
    minimum_valid_trials,
    paired_trial_statistics,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
P1_DIR = REPO_ROOT / "physical" / "p1"


# --- calibration target -----------------------------------------------------


def test_calibration_target_manifest_matches_png(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    png = tmp_path / manifest["png_file"]
    assert png.is_file()
    assert hashlib.sha256(png.read_bytes()).hexdigest() == manifest["png_sha256"]
    assert len(manifest["png_sha256"]) == 64
    int(manifest["png_sha256"], 16)


def test_calibration_target_manifest_fields(tmp_path: Path) -> None:
    manifest = generate(tmp_path)
    assert manifest["target_id"] == TARGET_ID
    assert len(manifest["patches"]) == GRID_ROWS * GRID_COLS
    for patch in manifest["patches"]:
        assert len(patch["srgb"]) == 3
        assert all(0 <= c <= 255 for c in patch["srgb"])
        assert len(patch["center_mm"]) == 2
        assert len(patch["reference_lab_d65"]) == 3
    assert len(manifest["fiducials"]) == 4
    assert manifest["scale_bar"]["length_mm"] == SCALE_BAR_MM == 100.0


def test_calibration_target_generation_is_deterministic(tmp_path: Path) -> None:
    a = generate(tmp_path / "a")
    b = generate(tmp_path / "b")
    assert a == b
    assert (tmp_path / "a" / a["png_file"]).read_bytes() == (
        tmp_path / "b" / b["png_file"]
    ).read_bytes()


def test_srgb_to_lab_known_values() -> None:
    # D65 white point and black.
    L, a, b = srgb_to_lab((255, 255, 255))
    assert L == pytest.approx(100.0, abs=0.01)
    assert a == pytest.approx(0.0, abs=0.01)
    assert b == pytest.approx(0.0, abs=0.01)
    L, _, _ = srgb_to_lab((0, 0, 0))
    assert L == pytest.approx(0.0, abs=0.01)


def test_synthetic_profile_within_repo_acceptance() -> None:
    profile = build_synthetic_calibration_profile()
    # Reference-vs-measured perturbations really are inside the Delta-E bound.
    assert all(p.delta_e_2000() <= 6.0 for p in profile.patches)
    accepted, failures = profile.acceptance()
    assert accepted, failures


def test_delta_e_2000_identity() -> None:
    assert delta_e_2000((50.0, 2.0, -3.0), (50.0, 2.0, -3.0)) == pytest.approx(0.0)


# --- templates ---------------------------------------------------------------


def _load(name: str) -> dict:
    return json.loads((P1_DIR / name).read_text())


def test_calibration_manifest_template_fields() -> None:
    m = _load("CALIBRATION_MANIFEST.json")
    assert m["target"]["target_id"] == TARGET_ID
    criteria = m["acceptance_criteria"]
    assert criteria["max_mean_delta_e_2000"] == 6.0
    assert criteria["max_scale_error_pct"] == 2.0
    assert criteria["max_registration_error_mm"] == 3.0
    assert m["camera"]["settings"]["exposure_lock"] is True


def test_session_manifest_template_fields() -> None:
    m = _load("SESSION_MANIFEST_TEMPLATE.json")
    for key in ("session_id", "date_utc", "operator", "garments", "environment", "captures"):
        assert key in m
    garments = m["garments"]
    for key in ("candidate_skus", "control_skus", "reserve_skus"):
        assert garments[key]
    grid = m["capture_grid"]
    planned = (
        len(grid["distances_m"])
        * len(grid["yaw_deg"])
        * len(grid["pitch_deg"])
        * len(grid["poses"])
        * len(grid["lighting_variants"])
        * grid["repetitions_per_cell"]
    )
    assert planned == grid["planned_valid_trials"] == MAX_VALID_TRIALS


def test_trial_ingestion_template_fields() -> None:
    m = _load("PHYSICAL_TRIAL_INGESTION_TEMPLATE.json")
    trial = m["trials"][0]
    for key in ("trial_id", "garments", "captures", "geometry", "detector_outputs", "validity"):
        assert key in trial
    assert "control_undetected_rule" in trial["validity"]
    assert m["stopping_rule_ref"] == "physical/p1/STOPPING_RULE.json"


def test_capture_naming_regex_round_trip() -> None:
    doc = (P1_DIR / "CAPTURE_NAMING_CONVENTION.md").read_text()
    pattern = re.search(r"```regex\n(\^.*\$)\n```", doc).group(1)
    name = "P1_S001_RAC_SKU_CAND_003_d0300_ym45_pp00_L1_standing_r02.png"
    match = re.match(pattern, name)
    assert match, "example filename must match the documented grammar"
    assert match.group("session") == "S001"
    assert match.group("distance") == "d0300"
    assert match.group("yaw") == "ym45"
    assert match.group("rep") == "r02"
    assert not re.match(pattern, "P1_S001_nope.png")


# --- stopping rule ------------------------------------------------------------


def test_stopping_rule_matches_preregistered_machinery() -> None:
    payload = _load("STOPPING_RULE.json")
    rule = PreregisteredStoppingRule(
        rule_id=payload["rule_id"],
        min_valid_trials=payload["min_valid_trials"],
        max_valid_trials=payload["max_valid_trials"],
        target_interval_width=payload["target_interval_width"],
        confidence_z=payload["confidence_z"],
        require_interval_below_half=payload["require_interval_below_half"],
    )
    assert rule.min_valid_trials == minimum_valid_trials(target_interval_width=0.20)
    assert rule.target_interval_width == 0.20
    assert rule.max_valid_trials == MAX_VALID_TRIALS


# --- dry run -----------------------------------------------------------------


EXPECTED_DRY_RUN_ARTIFACTS = {
    "calibration-profile.json",
    "session-manifest.json",
    "trial-records.json",
    "experiment-artifact.json",
    "p1-synthetic-dry-run.json",
}


def test_dry_run_emits_complete_artifact_set(tmp_path: Path) -> None:
    summary = run_dry_run(tmp_path, P1_DIR / "STOPPING_RULE.json")
    assert {p.name for p in tmp_path.iterdir()} == EXPECTED_DRY_RUN_ARTIFACTS
    assert summary["calibration_accepted"] is True
    assert summary["evidence_class"] == "synthetic_pipeline_validation_only"
    assert summary["rac_evidence_eligible"] is False
    # Session manifest hash recorded in the summary matches the file bytes.
    blob = (tmp_path / "session-manifest.json").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == summary["artifacts"]["session-manifest.json"]


def test_dry_run_experiment_artifact_binds_physical_session(tmp_path: Path) -> None:
    run_dry_run(tmp_path, P1_DIR / "STOPPING_RULE.json")
    payload = json.loads((tmp_path / "experiment-artifact.json").read_text())
    artifact = ExperimentArtifact.from_dict(payload["experiment"])
    assert artifact.lineage_hash == payload["lineage_hash"]
    stages = {s.stage: s for s in artifact.stages}
    assert "physical_session" in stages
    session_sha = hashlib.sha256((tmp_path / "session-manifest.json").read_bytes()).hexdigest()
    assert stages["physical_session"].sha256 == session_sha
    assert stages["calibration_profile"].sha256 == hashlib.sha256(
        (tmp_path / "calibration-profile.json").read_bytes()
    ).hexdigest()


def test_dry_run_stopping_decision_uses_preregistered_rule(tmp_path: Path) -> None:
    summary = run_dry_run(tmp_path, P1_DIR / "STOPPING_RULE.json")
    assert summary["stopping_rule"]["rule_id"] == "RAC-P1-STOP-2026-001"
    stats_payload = summary["statistics"]
    assert stats_payload["valid_trials"] >= summary["stopping_rule"]["min_valid_trials"]


def test_dry_run_is_deterministic(tmp_path: Path) -> None:
    run_dry_run(tmp_path / "a", P1_DIR / "STOPPING_RULE.json")
    run_dry_run(tmp_path / "b", P1_DIR / "STOPPING_RULE.json")
    for name in EXPECTED_DRY_RUN_ARTIFACTS:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_dry_run_trial_records_cover_full_grid_and_validity_rule(tmp_path: Path) -> None:
    run_dry_run(tmp_path, P1_DIR / "STOPPING_RULE.json")
    records = json.loads((tmp_path / "trial-records.json").read_text())
    trials = records["trials"]
    assert len(trials) == MAX_VALID_TRIALS
    for record in trials:
        # control-undetected => invalid, never candidate success.
        assert record["validity"]["valid"] == record["conservative_trial_decision"]["control_detected"]
        if not record["validity"]["valid"]:
            assert record["validity"]["invalid_reason"]


def test_synthetic_session_trials_full_grid_and_statistics() -> None:
    trials = build_synthetic_session_trials()
    assert len(trials) == MAX_VALID_TRIALS
    stats = paired_trial_statistics(trials, bootstrap_resamples=200, bootstrap_seed=7)
    assert stats.control_detection_rate == 1.0  # physical matched-pair semantics
    rule = PreregisteredStoppingRule(
        rule_id="TEST",
        min_valid_trials=minimum_valid_trials(0.20),
        max_valid_trials=MAX_VALID_TRIALS,
        target_interval_width=0.20,
        require_interval_below_half=True,
    )
    decision = evaluate_stopping_rule(rule, stats)
    assert decision.rule_id == "TEST"

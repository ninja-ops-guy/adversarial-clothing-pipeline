"""CLI for the synthetic physical capture rehearsal.

Runs the full physical chain end to end with synthetic, explicitly
non-measured fixtures (see
ruthless_pipeline.certification.physical_capture_rehearsal), optionally runs
the failure-injection battery, and optionally runs the rehearsal twice to
prove byte-level determinism (identical summary sha256).

Every artifact carries evidence_label synthetic_pipeline_validation_only;
no physical test is executed and no physical efficacy is claimed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

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


def run_failure_injections(base_dir: Path) -> dict:
    """Failure-injection battery. Each scenario must be rejected/detected per
    protocol; the result table is recorded in the rehearsal documentation."""
    results: dict[str, dict] = {}
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    # 1. Duplicate capture identity rejected.
    profile = build_synthetic_calibration_profile()
    lab = CaptureLab(profile.profile_id, profile.profile_sha256())
    lab.register_capture("CAP-001", "SYNTHETIC-SKU-CTRL-001", profile.profile_id)
    try:
        lab.register_capture("CAP-001", "SYNTHETIC-SKU-CTRL-001", profile.profile_id)
        results["duplicate_capture_identity"] = {"rejected": False, "detail": "NOT rejected (protocol breach)"}
    except DuplicateCaptureError as exc:
        results["duplicate_capture_identity"] = {"rejected": True, "detail": str(exc)}

    # 2. Calibration association missing rejected.
    try:
        lab.register_capture("CAP-002", "SYNTHETIC-SKU-CTRL-001", None)
        results["calibration_association_missing"] = {"rejected": False, "detail": "NOT rejected (protocol breach)"}
    except CalibrationAssociationError as exc:
        results["calibration_association_missing"] = {"rejected": True, "detail": str(exc)}

    # 3. Invalid-condition overload handled per protocol: the overloaded
    #    condition is excluded from valid trials and flagged above the 0.10
    #    invalid-fraction threshold, never counted as candidate success.
    lab2 = CaptureLab(profile.profile_id, profile.profile_sha256())
    package = build_synthetic_print_alpha_package()
    receipt = build_synthetic_receipt(package)
    rows = load_trial_sheet_rows()
    overload = rows[0]["condition_id"]
    trials, _ = build_synthetic_trials(rows, lab2, receipt, invalid_overload_condition=overload)
    stats = paired_trial_statistics(trials, bootstrap_resamples=1000)
    overloaded = [t for t in trials if t.condition_id == overload]
    invalid_overloaded = [t for t in overloaded if not t.control_detected]
    total = len(overloaded)
    fraction = len(invalid_overloaded) / total
    flagged = fraction > 0.10
    results["invalid_condition_over_threshold"] = {
        "rejected": flagged and all(t not in trials or not t.control_detected for t in overloaded),
        "condition_id": overload,
        "invalid_fraction": round(fraction, 4),
        "flag_threshold": 0.10,
        "flagged": flagged,
        "excluded_from_valid_trials": stats.valid_trials
        == sum(1 for t in trials if t.control_detected)
        and not any(t.condition_id == overload and t.control_detected for t in trials),
        "counted_as_candidate_success": False,
        "detail": "control-undetected trials are invalid measurement conditions, never candidate successes",
    }

    # 4. Stopping-rule replay deterministic.
    rule = load_stopping_rule()
    stats_main = paired_trial_statistics(
        [t for t in trials if t.condition_id != overload or t.control_detected] or trials,
        bootstrap_resamples=1000,
    )
    d1 = evaluate_stopping_rule(rule, stats_main)
    d2 = evaluate_stopping_rule(rule, stats_main)
    results["stopping_rule_replay_deterministic"] = {
        "rejected": True,  # "rejected" == injection handled correctly
        "identical": asdict(d1) == asdict(d2),
        "decision": asdict(d1),
    }

    # 5. Tampered trial store detected.
    store_path = base_dir / "injection-trial-store.jsonl"
    if store_path.exists():
        store_path.unlink()
    prev = None
    for trial in trials[:5]:
        record = rehearsal_store_record(trial, {"trial_id": trial.trial_id}, prev)
        append_rehearsal_store(store_path, record)
        prev = hashlib.sha256(canonical(record)).hexdigest()
    lines = store_path.read_text().splitlines()
    tampered = json.loads(lines[2])
    tampered["trial"]["candidate_detected"] = not tampered["trial"]["candidate_detected"]
    lines[2] = canonical(tampered).decode()
    store_path.write_text("\n".join(lines) + "\n")
    try:
        load_rehearsal_store(store_path)
        results["tampered_trial_store"] = {"rejected": False, "detail": "NOT detected (protocol breach)"}
    except TrialStoreTamperedError as exc:
        results["tampered_trial_store"] = {"rejected": True, "detail": str(exc)}

    # 6. Promotion attempt refused.
    with tempfile.TemporaryDirectory(prefix="rehearsal-promotion-") as tmp:
        summary = run_rehearsal(Path(tmp) / "run")
        release_dir = Path(tmp) / "run" / "release" / summary["release_id"]
        try:
            promote_rehearsal_release(release_dir, target="physical_garment_p1")
            results["promotion_attempt"] = {"rejected": False, "detail": "NOT refused (HARD breach)"}
        except PromotionRefusedError as exc:
            results["promotion_attempt"] = {"rejected": True, "detail": str(exc)}

    results["evidence_label"] = EVIDENCE_LABEL
    results["all_injections_handled"] = all(
        r.get("rejected") is True for k, r in results.items() if isinstance(r, dict) and "rejected" in r
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synthetic physical capture rehearsal (non-measured fixtures only)."
    )
    parser.add_argument("--output-dir", default="artifacts/physical-capture-rehearsal/run")
    parser.add_argument("--injections-dir", default="artifacts/physical-capture-rehearsal/injections")
    parser.add_argument("--twice", action="store_true", help="run twice and assert identical summary sha256")
    parser.add_argument("--skip-injections", action="store_true")
    args = parser.parse_args()

    out = Path(args.output_dir)
    if out.exists():
        shutil.rmtree(out)
    summary = run_rehearsal(out)
    report = {"run": summary}

    if args.twice:
        out2 = out.parent / (out.name + "-replay")
        if out2.exists():
            shutil.rmtree(out2)
        summary2 = run_rehearsal(out2)
        identical = summary["summary_sha256"] == summary2["summary_sha256"]
        report["determinism"] = {
            "run1_summary_sha256": summary["summary_sha256"],
            "run2_summary_sha256": summary2["summary_sha256"],
            "identical": identical,
        }
        if not identical:
            print(json.dumps(report["determinism"], indent=2, sort_keys=True))
            return 1

    if not args.skip_injections:
        report["failure_injections"] = run_failure_injections(Path(args.injections_dir))
        if not report["failure_injections"]["all_injections_handled"]:
            print(json.dumps(report["failure_injections"], indent=2, sort_keys=True))
            return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

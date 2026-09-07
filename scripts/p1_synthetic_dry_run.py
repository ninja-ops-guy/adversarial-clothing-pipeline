from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from ruthless_pipeline.certification.physical import PhysicalTrial
from ruthless_pipeline.certification.trial_statistics import (
    PreregisteredStoppingRule,
    evaluate_stopping_rule,
    invalid_condition_report,
    paired_trial_statistics,
)


def build_synthetic_trials() -> list[PhysicalTrial]:
    trials: list[PhysicalTrial] = []
    for i in range(36):
        trials.append(
            PhysicalTrial(
                trial_id=f"SYN-{i:03d}",
                condition_id=f"C{i % 6}",
                control_detected=(i % 17 != 0),
                candidate_detected=(i % 4 == 0),
                camera_id="SYNTHETIC-CAMERA",
                distance_m=(1.0, 3.0, 5.0)[i % 3],
                yaw_deg=(-45.0, 0.0, 45.0)[i % 3],
                pitch_deg=0.0,
                pose="synthetic_rotation",
                lighting_id=("L1", "L2")[i % 2],
                metadata={"evidence_class": "synthetic_pipeline_validation_only"},
            )
        )
    return trials


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise the P1 statistical path with synthetic non-evidence data.")
    parser.add_argument("--output", default="artifacts/p1-synthetic-dry-run.json")
    args = parser.parse_args()

    trials = build_synthetic_trials()
    stats = paired_trial_statistics(trials, bootstrap_resamples=1000, bootstrap_seed=20260907)
    invalid = invalid_condition_report(trials)
    rule = PreregisteredStoppingRule(
        rule_id="SYNTHETIC-DRY-RUN-ONLY",
        min_valid_trials=20,
        max_valid_trials=60,
        target_interval_width=0.35,
    )
    decision = evaluate_stopping_rule(rule, stats)

    payload = {
        "schema_version": "1.0",
        "evidence_class": "synthetic_pipeline_validation_only",
        "rac_evidence_eligible": False,
        "warning": "Synthetic pipeline validation. Must never be promoted to RAC-P evidence.",
        "statistics": asdict(stats),
        "invalid_conditions": asdict(invalid),
        "stopping_rule": asdict(rule),
        "stopping_decision": asdict(decision),
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

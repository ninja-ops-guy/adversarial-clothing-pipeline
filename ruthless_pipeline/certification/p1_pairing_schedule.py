"""Deterministic P1 matched-pair pairing and capture-order schedule.

Frozen by ``physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json``. This module is
the single authoritative derivation of:

1. the trial grid (3 distances x 3 yaw x 1 pitch x 1 locked lighting variant
   x 2 poses x 8 repetitions = 144 matched-pair trials, matching
   ``physical/p1/STOPPING_RULE.json`` max_valid_trials),
2. the execution order of grid cells, and
3. the within-trial arm order (which of control/candidate is captured first).

Determinism contract: every ordering is derived from SHA-256 of stable
string identifiers keyed by the frozen contract seed. No ``random`` module
state, no wall-clock, no environment dependence. Re-derivation is
byte-identical on any machine.

Scientific boundary: this schedule is logistics, not evidence. It carries
``evidence_class = "synthetic_pipeline_validation_only"`` semantics until
bound to a real session manifest; it never touches D2-0004, D2-0005,
held-out model sets, or thresholds.
"""

from __future__ import annotations

import hashlib
import json

CONTRACT_SEED = "RAC-P1-PAIRING-SEED-2026-001"
CONTRACT_ID = "RAC-P1-PAIRING-2026-001"
SCHEMA_VERSION = "1.0"

DISTANCES_M = (1.0, 3.0, 5.0)
YAW_DEG = (-45, 0, 45)
PITCH_DEG = (0,)
LIGHTING_VARIANTS = ("session-locked",)
POSES = ("standing", "seated")
REPETITIONS_PER_CELL = 8

EXPECTED_TRIALS = 144
CAPTURES_PER_TRIAL = 2  # one control + one candidate capture per matched pair


def _key(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def grid_cells() -> list[dict]:
    """The 18 grid cells (before repetitions), in canonical (sorted) order."""
    cells = []
    for distance in DISTANCES_M:
        for yaw in YAW_DEG:
            for pitch in PITCH_DEG:
                for lighting in LIGHTING_VARIANTS:
                    for pose in POSES:
                        cells.append(
                            {
                                "cell_id": f"d{distance:g}_y{yaw}_p{pitch}_l-{lighting}_pose-{pose}",
                                "distance_m": distance,
                                "yaw_deg": yaw,
                                "pitch_deg": pitch,
                                "lighting_variant": lighting,
                                "pose": pose,
                            }
                        )
    return cells


def trial_ids() -> list[str]:
    """All 144 trial IDs in canonical order: RAC-P1-T-0001 .. RAC-P1-T-0144."""
    return [f"RAC-P1-T-{i:04d}" for i in range(1, EXPECTED_TRIALS + 1)]


def derive_schedule(seed: str = CONTRACT_SEED) -> list[dict]:
    """Derive the frozen execution schedule.

    Returns 144 entries in execution order. Each entry binds:
    ``trial_id``, the grid cell, the repetition index, the execution
    position, and ``first_arm`` (which arm is captured first in the pair).

    Cell order: cells are sorted by SHA-256(seed | cell_id) — a frozen
    permutation. Within each cell, the 8 repetitions run consecutively;
    ``first_arm`` alternates by SHA-256(seed | cell_id | rep) parity so the
    arm captured first is balanced and unpredictable a priori but perfectly
    reproducible.
    """
    cells = grid_cells()
    cells.sort(key=lambda c: _key(seed, "cell-order", c["cell_id"]))
    schedule: list[dict] = []
    position = 0
    for cell in cells:
        for rep in range(1, REPETITIONS_PER_CELL + 1):
            position += 1
            first_arm = (
                "control"
                if int(_key(seed, "arm-order", cell["cell_id"], rep), 16) % 2 == 0
                else "candidate"
            )
            schedule.append(
                {
                    "execution_position": position,
                    "trial_id": f"RAC-P1-T-{position:04d}",
                    "cell_id": cell["cell_id"],
                    "repetition": rep,
                    "first_arm": first_arm,
                    "arms": ["control", "candidate"]
                    if first_arm == "control"
                    else ["candidate", "control"],
                    **{
                        k: cell[k]
                        for k in (
                            "distance_m",
                            "yaw_deg",
                            "pitch_deg",
                            "lighting_variant",
                            "pose",
                        )
                    },
                }
            )
    return schedule


def schedule_sha256(schedule: list[dict]) -> str:
    payload = json.dumps(schedule, indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def contract_payload() -> dict:
    """The frozen pairing/randomization contract (hash-bound artifact body)."""
    schedule = derive_schedule()
    first_arm_counts = {
        arm: sum(1 for entry in schedule if entry["first_arm"] == arm)
        for arm in ("control", "candidate")
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "seed": CONTRACT_SEED,
        "derivation": "SHA-256 keyed ordering (see ruthless_pipeline/certification/p1_pairing_schedule.py); no random module, no wall clock",
        "grid": {
            "distances_m": list(DISTANCES_M),
            "yaw_deg": list(YAW_DEG),
            "pitch_deg": list(PITCH_DEG),
            "lighting_variants": list(LIGHTING_VARIANTS),
            "poses": list(POSES),
            "repetitions_per_cell": REPETITIONS_PER_CELL,
            "planned_valid_trials": EXPECTED_TRIALS,
            "captures_per_trial": CAPTURES_PER_TRIAL,
        },
        "matched_pair_rule": (
            "Each trial is one matched pair: one control capture and one "
            "candidate capture of the same grid cell, same session, same "
            "variant/size; the pair differs ONLY in the printed artwork. "
            "Control-undetected trials are invalid measurement conditions, "
            "never candidate successes (STOPPING_RULE.json invalid_condition_rule)."
        ),
        "randomization_rule": (
            "Cell execution order is the frozen SHA-256 permutation; "
            "first_arm per repetition is the frozen parity bit. The operator "
            "executes the schedule as recorded in the session manifest; "
            "no on-site re-randomization, no substitution of cells or arms."
        ),
        "reserve_rule": (
            "Reserve garments (PA-HOODIE-CAND-002 / PA-HOODIE-CTRL-002, "
            "fallback tees) replace a failed unit only after receipt-QA "
            "failure is recorded; the pairing checks in "
            "print-alpha/QA/garment-pairing-checklist.md re-run on the "
            "replacement before capture."
        ),
        "balance_check": {
            "first_arm_counts": first_arm_counts,
            "trials": len(schedule),
        },
        "schedule_sha256": schedule_sha256(schedule),
        "stopping_rule_ref": "physical/p1/STOPPING_RULE.json",
        "evidence_class": "synthetic_pipeline_validation_only",
        "physical_efficacy_claimed": False,
    }

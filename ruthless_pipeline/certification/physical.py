from __future__ import annotations

from dataclasses import dataclass, field
import math


@dataclass(frozen=True)
class PhysicalTrial:
    trial_id: str
    condition_id: str
    control_detected: bool
    candidate_detected: bool
    camera_id: str
    distance_m: float
    yaw_deg: float
    pitch_deg: float
    pose: str
    lighting_id: str
    wash_state: str = "W0"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PhysicalSummary:
    total_trials: int
    valid_trials: int
    invalid_trials: int
    control_detection_rate: float
    candidate_detection_rate: float


def summarize_physical_trials(trials: list[PhysicalTrial]) -> PhysicalSummary:
    if not trials:
        raise ValueError("physical certification requires at least one trial")
    trial_ids = [trial.trial_id for trial in trials]
    if any(not trial_id for trial_id in trial_ids):
        raise ValueError("trial_id is required")
    if len(set(trial_ids)) != len(trial_ids):
        raise ValueError("duplicate trial_id")
    for trial in trials:
        values = (trial.distance_m, trial.yaw_deg, trial.pitch_deg)
        if any(not math.isfinite(v) for v in values):
            raise ValueError(f"{trial.trial_id}: physical measurements must be finite")
        if trial.distance_m < 0:
            raise ValueError(f"{trial.trial_id}: distance_m must be nonnegative")
        if not trial.camera_id or not trial.condition_id or not trial.pose or not trial.lighting_id:
            raise ValueError(f"{trial.trial_id}: physical trial metadata is incomplete")
    valid = [trial for trial in trials if trial.control_detected]
    invalid = len(trials) - len(valid)
    if not valid:
        return PhysicalSummary(len(trials), 0, invalid, 0.0, 1.0)
    return PhysicalSummary(
        total_trials=len(trials),
        valid_trials=len(valid),
        invalid_trials=invalid,
        control_detection_rate=sum(t.control_detected for t in valid) / len(valid),
        candidate_detection_rate=sum(t.candidate_detected for t in valid) / len(valid),
    )

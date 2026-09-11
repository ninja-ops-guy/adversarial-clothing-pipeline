"""SW-14: Temporal Evaluation Framework (sequence-oriented, P2-independent).

Sequence-oriented evaluation infrastructure ONLY. Handles synthetic
sequences today; every aggregate carries ``evidence_class``
``synthetic_pipeline_validation_only`` and can never support a physical
claim.

Rules:
- Frames must be strictly ordered: duplicate frame indices or non-monotonic
  timestamps are refused (:class:`TemporalOrderError`).
- A static trial (fewer than 2 frames, or a single timestamp) cannot
  silently masquerade as a sequence (:class:`TemporalOrderError`).
- Every temporal aggregate retains the sequence identity
  (``sequence_id`` is part of the aggregate record and its content hash).
- Deterministic: no wall-clock; timestamps come from the caller.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from ruthless_pipeline.future_evidence.errors import (
    PromotionImpossibleError,
    TemporalOrderError,
)

SCHEMA_VERSION = "rac-temporal-sequence/1.0"
SCHEMA_ID = "https://rac.local/schemas/temporal_sequence_v1.schema.json"
SYNTHETIC_EVIDENCE_CLASS = "synthetic_pipeline_validation_only"


@dataclass(frozen=True)
class Frame:
    """One observation unit in a sequence."""

    frame_index: int
    timestamp: float
    valid: bool
    detected: bool  # target detected/persisting in this frame
    value: float  # observation value for variance metrics
    invalidity_reason: Optional[str] = None


def _validate_sequence(frames: Sequence[Frame]) -> None:
    if len(frames) < 2:
        raise TemporalOrderError(
            "fewer than 2 frames: a static trial cannot masquerade as a sequence"
        )
    indices = [f.frame_index for f in frames]
    if len(set(indices)) != len(indices):
        raise TemporalOrderError("duplicate frame_index in sequence; refused")
    if indices != sorted(indices):
        raise TemporalOrderError("frame indices out of order; refused")
    ts = [f.timestamp for f in frames]
    if any(not math.isfinite(t) for t in ts):
        raise TemporalOrderError("non-finite timestamp; refused")
    if any(b <= a for a, b in zip(ts, ts[1:])):
        raise TemporalOrderError("timestamps not strictly increasing; refused")
    for f in frames:
        if not math.isfinite(f.value):
            raise TemporalOrderError(f"frame {f.frame_index}: non-finite value")
        if not f.valid and f.detected:
            raise TemporalOrderError(
                f"frame {f.frame_index}: invalid frame cannot be detected"
            )
        if not f.valid and f.invalidity_reason is None:
            raise TemporalOrderError(
                f"frame {f.frame_index}: invalid frame requires invalidity_reason"
            )


def _run_lengths(flags: List[bool]) -> List[int]:
    runs: List[int] = []
    cur = 0
    for flag in flags:
        if flag:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return runs


def evaluate_sequence(
    sequence_id: str,
    observation_unit: str,
    frames: Sequence[Frame],
) -> Dict[str, Any]:
    """Compute temporal aggregates for one sequence. Synthetic only.

    Metrics:
    - persistence: fraction of valid frames in which the target persists.
    - reacquisition: number of detected runs after a detected run was lost.
    - time_to_failure: timestamp of the first valid not-detected frame
      following initial detection (None if never failed).
    - run lengths: lengths of consecutive detected runs.
    - within-sequence variance: population variance of valid-frame values.
    """
    _validate_sequence(frames)
    valid = [f for f in frames if f.valid]
    detected_flags = [f.detected for f in valid]
    n_valid = len(valid)
    n_detected = sum(detected_flags)
    persistence = (n_detected / n_valid) if n_valid else 0.0

    runs = _run_lengths(detected_flags)
    reacquisition_count = max(0, len(runs) - 1)

    time_to_failure: Optional[float] = None
    seen_detection = False
    for f in valid:
        if f.detected:
            seen_detection = True
        elif seen_detection:
            time_to_failure = f.timestamp
            break

    values = [f.value for f in valid]
    mean = sum(values) / len(values) if values else 0.0
    variance = (
        sum((v - mean) ** 2 for v in values) / len(values) if values else 0.0
    )

    aggregate: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "sequence_id": sequence_id,
        "observation_unit": observation_unit,
        "n_frames": len(frames),
        "n_valid_frames": n_valid,
        "persistence": persistence,
        "reacquisition_count": reacquisition_count,
        "time_to_failure": time_to_failure,
        "detected_run_lengths": runs,
        "within_sequence_variance": variance,
        "evidence_class": SYNTHETIC_EVIDENCE_CLASS,
    }
    aggregate["aggregate_id"] = (
        "RAC-TAGG-" + sha256_bytes(canonical_json(aggregate))[:16]
    )
    return aggregate


def assert_no_physical_claim(aggregate: Dict[str, Any]) -> None:
    """Hard guard: synthetic temporal aggregates support no physical claim."""
    if aggregate.get("evidence_class") != SYNTHETIC_EVIDENCE_CLASS:
        raise PromotionImpossibleError(
            "temporal aggregates from synthetic sequences can never support a "
            "physical claim"
        )

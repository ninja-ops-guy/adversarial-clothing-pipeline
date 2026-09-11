"""Deterministic seeded property-style fuzz tests over the governed recovery
and state-transition surfaces.

Invariant under test: every corruption class (truncated JSONL, broken
hash-chain links, illegal/ replayed state transitions, replayed trial-store
records, non-P1 promotion attempts) is rejected fail-closed with ValueError,
while valid sequences always pass. Seeded with stdlib random.Random only —
no external fuzzing dependencies.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

import pytest

from ruthless_pipeline.certification.evidence import validate_transition
from ruthless_pipeline.certification.experiment import (
    ExperimentArtifact,
    ExperimentRegistry,
    StageRef,
)
from ruthless_pipeline.certification.manifest import EvidenceState
from ruthless_pipeline.certification.physical import PhysicalTrial
from ruthless_pipeline.certification.schema_version import SchemaVersionError

import scripts.ingest_capture_inference as ici
from scripts.ingest_capture_inference import (
    append_trial_store,
    canonical,
    enforce_promotion_gate,
    load_trial_store,
    trial_store_record,
)

SEEDS = tuple(range(16))

STATE_CHAIN = (
    EvidenceState.DESIGN,
    EvidenceState.SURROGATE,
    EvidenceState.DIGITAL_HELDOUT,
    EvidenceState.PHYSICAL,
    EvidenceState.DURABILITY,
    EvidenceState.GOLDEN_SAMPLE,
    EvidenceState.LOT_CONFORMITY,
)


# --------------------------------------------------------------------------
# RAC state machine
# --------------------------------------------------------------------------

def test_state_machine_full_forward_chain_passes():
    for current, target in zip(STATE_CHAIN, STATE_CHAIN[1:]):
        validate_transition(current, target)


def test_state_machine_all_illegal_pairs_rejected():
    for current in STATE_CHAIN:
        for target in STATE_CHAIN:
            if STATE_CHAIN.index(target) == STATE_CHAIN.index(current) + 1:
                continue
            with pytest.raises(ValueError, match="illegal RAC transition"):
                validate_transition(current, target)


@pytest.mark.parametrize("seed", SEEDS)
def test_state_machine_fuzzed_sequences(seed: int):
    """Random transition sequences: accepted iff they are exactly the forward
    chain prefix; every skip/reverse/repeat must raise."""
    rng = random.Random(seed)
    states = list(STATE_CHAIN)
    for _ in range(50):
        seq = [rng.choice(states) for _ in range(rng.randint(2, 5))]
        try:
            for current, target in zip(seq, seq[1:]):
                validate_transition(current, target)
        except ValueError:
            continue  # rejected, as required for non-chain sequences
        # If nothing raised, every step must have been adjacent-forward.
        for current, target in zip(seq, seq[1:]):
            assert states.index(target) == states.index(current) + 1


def test_state_machine_fuzzed_corruptions_of_valid_chain():
    rng = random.Random(20260214)
    for _ in range(200):
        chain = list(STATE_CHAIN)
        op = rng.choice(("skip", "reverse", "repeat", "shuffle"))
        if op == "skip" and len(chain) > 2:
            # Drop a middle state: dropping the tail would leave a valid
            # prefix, which is legitimately accepted.
            chain.pop(rng.randint(1, len(chain) - 2))
        elif op == "reverse":
            i = rng.randrange(len(chain) - 1)
            chain[i], chain[i + 1] = chain[i + 1], chain[i]
        elif op == "repeat":
            i = rng.randrange(len(chain))
            chain.insert(i, chain[i])
        else:
            rng.shuffle(chain)
            if chain == list(STATE_CHAIN):  # identity shuffle: force a swap
                chain[0], chain[1] = chain[1], chain[0]
        with pytest.raises(ValueError):
            for current, target in zip(chain, chain[1:]):
                validate_transition(current, target)


# --------------------------------------------------------------------------
# Capture-lab trial store append chain
# --------------------------------------------------------------------------

def _session(rng: random.Random, session_id: str) -> dict:
    return {
        "session_id": session_id,
        "experiment_id": "RAC-EXP-2026-900",
        "hypothesis_id": "FUZZ-HYPOTHESIS",
        "evidence_class": "physical_garment_p1",
        "calibration_pass": True,
        "calibration_profile_id": "CAPTURE-CALIBRATION",
        "captures": {"control": {"stills": []}, "candidate": {"stills": []}},
        "control": {"artifact_id": "SKU-CTRL", "sha256": hashlib.sha256(b"ctrl").hexdigest()},
        "candidate": {"artifact_id": "SKU-CAND", "sha256": hashlib.sha256(b"cand").hexdigest()},
        "generation": {"artifact_id": "GEN", "sha256": hashlib.sha256(b"gen").hexdigest()},
        "camera_id": "cam", "lighting_id": "L1",
        "distance_m": 3.0, "yaw_deg": 0.0, "pitch_deg": 0.0,
        "pose": "standing", "wash_state": "W0",
    }


def _write_valid_store(path: Path, rng: random.Random, n: int) -> list[dict]:
    session = _session(rng, "S1")
    inference = {"result_sha256": hashlib.sha256(b"inf").hexdigest()}
    prev_sha = None
    records = []
    for i in range(n):
        trial = PhysicalTrial(
            trial_id=f"T{i:03d}", condition_id=f"C{i:03d}",
            control_detected=True,
            candidate_detected=bool(rng.randint(0, 1)),
            camera_id="cam", distance_m=3.0, yaw_deg=0.0, pitch_deg=0.0,
            pose="standing", lighting_id="L1",
        )
        record = trial_store_record(trial, session, inference, {}, prev_sha)
        append_trial_store(path, record)
        prev_sha = hashlib.sha256(canonical(record)).hexdigest()
        records.append(record)
    return records


@pytest.mark.parametrize("seed", SEEDS)
def test_trial_store_valid_chains_pass(seed: int, tmp_path: Path):
    rng = random.Random(seed)
    store = tmp_path / "store.jsonl"
    records = _write_valid_store(store, rng, rng.randint(1, 6))
    loaded = load_trial_store(store)
    assert [r["trial"]["trial_id"] for r in loaded] == [r["trial"]["trial_id"] for r in records]


@pytest.mark.parametrize("seed", SEEDS)
def test_trial_store_fuzzed_corruptions_rejected(seed: int, tmp_path: Path):
    rng = random.Random(10_000 + seed)
    for case in range(40):
        store = tmp_path / f"store-{case}.jsonl"
        records = _write_valid_store(store, rng, rng.randint(2, 5))
        lines = store.read_text().splitlines()
        op = rng.choice((
            "truncate_midline", "drop_line", "swap_lines", "replay_record",
            "break_link", "synthetic_class", "calibration_false",
            "version_bump", "garbage_line",
        ))
        if op == "truncate_midline":
            cut = rng.randrange(len(lines[-1]) // 2, len(lines[-1]))
            text = "\n".join(lines[:-1] + [lines[-1][:cut]]) + "\n"
        elif op == "drop_line":
            i = rng.randrange(len(lines) - 1)  # keep at least one successor orphaned
            text = "\n".join(lines[:i] + lines[i + 1:]) + "\n"
        elif op == "swap_lines" and len(lines) >= 2:
            i = rng.randrange(len(lines) - 1)
            lines[i], lines[i + 1] = lines[i + 1], lines[i]
            text = "\n".join(lines) + "\n"
        elif op == "replay_record":
            text = "\n".join(lines + [lines[rng.randrange(len(lines))]]) + "\n"
        elif op == "break_link":
            i = rng.randrange(1, len(lines))
            record = json.loads(lines[i])
            record["prev_record_sha256"] = hashlib.sha256(b"forged").hexdigest()
            lines[i] = json.dumps(record, sort_keys=True, separators=(",", ":"))
            text = "\n".join(lines) + "\n"
        elif op == "synthetic_class":
            record = json.loads(lines[-1])
            record["evidence_class"] = "synthetic_pipeline_validation_only"
            lines[-1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
            text = "\n".join(lines) + "\n"
        elif op == "calibration_false":
            record = json.loads(lines[-1])
            record["calibration_pass"] = False
            lines[-1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
            text = "\n".join(lines) + "\n"
        elif op == "version_bump":
            record = json.loads(lines[-1])
            record["schema_version"] = "9.9"
            lines[-1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
            text = "\n".join(lines) + "\n"
        else:  # garbage_line
            text = "\n".join(lines) + "\n" + "not-json{" + "\n"
        store.write_text(text)
        with pytest.raises(ValueError):
            load_trial_store(store)


@pytest.mark.parametrize("seed", SEEDS)
def test_trial_store_truncation_recovery_semantics(seed: int, tmp_path: Path):
    """Byte-truncation recovery: a cut landing exactly after a complete line
    yields the valid prefix; a mid-line cut fails closed. Never a silently
    half-parsed record."""
    rng = random.Random(20_000 + seed)
    store = tmp_path / "store.jsonl"
    _write_valid_store(store, rng, 4)
    blob = store.read_bytes()
    for _ in range(60):
        cut = rng.randrange(1, len(blob))
        truncated = tmp_path / "trunc.jsonl"
        truncated.write_bytes(blob[:cut])
        # Clean prefix: the cut lands on a line boundary (either the byte
        # before the cut is a newline, or the cut splits exactly at a
        # newline, leaving a complete final line). Mid-line cuts must raise.
        clean_prefix = blob[:cut].endswith(b"\n") or blob[cut:cut + 1] == b"\n"
        if clean_prefix:
            loaded = load_trial_store(truncated)
            assert 1 <= len(loaded) <= 4
        else:
            with pytest.raises(ValueError):
                load_trial_store(truncated)


@pytest.mark.parametrize("seed", SEEDS)
def test_promotion_gate_fuzz(seed: int):
    """Only evidence_class == physical_garment_p1 AND calibration_pass is True
    may pass; every other combination (including truthy non-True values and
    the synthetic validation class) is rejected."""
    rng = random.Random(30_000 + seed)
    classes = ["physical_garment_p1", "synthetic_pipeline_validation_only",
               "printed_flat_prototype", "paper_prototype", None, "", 1]
    passes = [True, False, None, 1, "true", 0]
    for _ in range(60):
        session = {"evidence_class": rng.choice(classes),
                   "calibration_pass": rng.choice(passes)}
        if session["evidence_class"] == "physical_garment_p1" and session["calibration_pass"] is True:
            enforce_promotion_gate(session)
        else:
            with pytest.raises(ValueError, match="promotion gate"):
                enforce_promotion_gate(session)


def test_synthetic_records_never_enter_p1_store(tmp_path: Path):
    """Pin the non-promotion invariant at the store boundary: a hash-valid
    chain line carrying the synthetic validation class is still rejected."""
    rng = random.Random(40_000)
    store = tmp_path / "store.jsonl"
    session = _session(rng, "S1")
    session["evidence_class"] = "synthetic_pipeline_validation_only"
    trial = PhysicalTrial(
        trial_id="T0", condition_id="C0", control_detected=True,
        candidate_detected=False, camera_id="cam", distance_m=3.0,
        yaw_deg=0.0, pitch_deg=0.0, pose="standing", lighting_id="L1",
    )
    append_trial_store(store, trial_store_record(trial, session, {"result_sha256": "0" * 64}, {}, None))
    with pytest.raises(ValueError, match="promotion gate"):
        load_trial_store(store)


# --------------------------------------------------------------------------
# Experiment registry replay/duplicate rejection
# --------------------------------------------------------------------------

def _artifact(rng: random.Random, experiment_id: str) -> ExperimentArtifact:
    return ExperimentArtifact(
        experiment_id=experiment_id,
        hypothesis_id="H1",
        generation_id="G1",
        created_utc="2026-01-01T00:00:00Z",
        evidence_label="internally_measured",
        validity_flags={},
        stages=[
            StageRef("candidate", f"cand-{experiment_id}", hashlib.sha256(str(rng.random()).encode()).hexdigest()),
            StageRef("generation", f"gen-{experiment_id}", hashlib.sha256(str(rng.random()).encode()).hexdigest()),
        ],
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_registry_rejects_replays_and_accepts_unique(seed: int):
    rng = random.Random(50_000 + seed)
    registry = ExperimentRegistry()
    ids = [f"RAC-EXP-2026-{i:03d}" for i in range(rng.randint(2, 6))]
    for experiment_id in ids:
        registry.add(_artifact(rng, experiment_id))
    assert len(registry) == len(set(ids))
    for experiment_id in ids:  # replayed registrations must fail closed
        with pytest.raises(ValueError):
            registry.add(_artifact(rng, experiment_id))
    # Registry JSON round-trip preserves membership and still rejects replays.
    restored = ExperimentRegistry.from_json(registry.to_json())
    assert len(restored) == len(registry)
    with pytest.raises(ValueError):
        restored.add(_artifact(rng, ids[0]))


# --------------------------------------------------------------------------
# Physical release export gates
# --------------------------------------------------------------------------

@pytest.mark.parametrize("seed", SEEDS)
def test_release_export_rejects_corrupted_stores(seed: int, tmp_path: Path):
    """scripts/export_physical_release.build_release must fail closed (and
    write nothing) on every fuzzed store corruption, before any release
    directory appears."""
    from scripts.export_physical_release import build_release

    rng = random.Random(60_000 + seed)
    for case in range(12):
        store = tmp_path / f"store-{case}.jsonl"
        _write_valid_store(store, rng, rng.randint(2, 4))
        lines = store.read_text().splitlines()
        op = rng.choice(("truncate_midline", "replay_record", "version_bump",
                         "break_link", "lineage_diverge"))
        if op == "truncate_midline":
            lines[-1] = lines[-1][: rng.randrange(10, len(lines[-1]))]
        elif op == "replay_record":
            lines.append(lines[0])
        elif op == "version_bump":
            record = json.loads(lines[0])
            record["schema_version"] = "2.0"
            lines[0] = json.dumps(record, sort_keys=True, separators=(",", ":"))
        elif op == "break_link":
            record = json.loads(lines[1])
            record["prev_record_sha256"] = None
            lines[1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
        else:  # lineage_diverge: chain stays hash-valid but lineage disagrees
            record = json.loads(lines[-1])
            record["lineage"]["experiment_id"] = f"RAC-EXP-2026-{900 + case}"
            lines[-1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
        store.write_text("\n".join(lines) + "\n")
        out_parent = tmp_path / f"releases-{case}"
        with pytest.raises(ValueError):
            build_release(
                store,
                tmp_path / "calibration.json",
                "RAC-EXP-2026-900",
                out_parent,
                "2026-01-01T00:00:00Z",
                Path("physical/p1/STOPPING_RULE.json"),
                bootstrap_resamples=8,
            )
        assert not out_parent.exists() or not any(out_parent.rglob("*")), op


def test_release_export_rejects_empty_store(tmp_path: Path):
    from scripts.export_physical_release import build_release

    store = tmp_path / "empty.jsonl"
    store.write_text("")
    with pytest.raises(ValueError, match="empty"):
        build_release(
            store,
            tmp_path / "calibration.json",
            "RAC-EXP-2026-900",
            tmp_path / "releases",
            "2026-01-01T00:00:00Z",
            Path("physical/p1/STOPPING_RULE.json"),
            bootstrap_resamples=8,
        )


def test_schema_version_guard_is_fail_closed_subclass():
    assert issubclass(SchemaVersionError, ValueError)

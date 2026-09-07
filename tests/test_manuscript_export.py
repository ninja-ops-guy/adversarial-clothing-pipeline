"""Tests for manuscript_export (Wave F, Track D: Papers 1 and 5 automation).

All fixtures are synthetic and constructed in-test: synthetic experiment
ids/hashes, synthetic telemetry records, synthetic paired-arm outcomes. No
real generation data is touched. Covers: Paper 1 longitudinal CSV row
correctness and deterministic ordering, Paper 5 arm CSV, comparison-JSON
passthrough of the preregistered paired-arm statistics, validation of every
figure scaffold's declared source field paths against the real producer
structures (telemetry contract, failure taxonomy metrics, objective-
telemetry JSON, PairedArmStatistics JSON), empty-registry behavior
(headers/scaffolds only, zero fabricated rows), and canonical serialization
round-trips.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ruthless_pipeline.certification.experiment import (
    ExperimentArtifact,
    ExperimentRegistry,
    StageRef,
)
from ruthless_pipeline.certification.failure_taxonomy import (
    FailureCategory,
    classify_failure,
)
from ruthless_pipeline.certification.manuscript_export import (
    PAPER1_LONGITUDINAL_HEADER,
    PAPER5_ARMS_HEADER,
    Paper5Arm,
    figure_scaffolds,
    paper1_longitudinal_csv,
    paper1_longitudinal_rows,
    paper5_arm_rows,
    paper5_arms_csv,
    paper5_comparison_dict,
    paper5_comparison_json,
    write_figure_scaffolds,
    write_paper1_longitudinal_csv,
    write_paper5_arms_csv,
    write_paper5_comparison_json,
)
from ruthless_pipeline.certification.paired_arm_statistics import (
    paired_arm_statistics,
    to_canonical_json,
)
from ruthless_pipeline.certification.statistics import wilson_interval
from ruthless_pipeline.certification.telemetry_contract import (
    HeldOutOutcome,
    OptimizerConfig,
    PreHeldOutTelemetry,
    TelemetryRecord,
    cross_model_disagreement,
)


def _hex(tag: str) -> str:
    """Deterministic synthetic 64-hex digest derived from a short tag."""
    import hashlib

    return hashlib.sha256(f"synthetic-{tag}".encode()).hexdigest()


def _telemetry(
    gen: str, cand_tag: str, *, verdict: str, with_outcome: bool = True
) -> TelemetryRecord:
    rates = {"sur-a": 0.20, "sur-b": 0.30, "sur-c": 0.40}
    pre = PreHeldOutTelemetry(
        candidate_sha256=_hex(f"candidate-{cand_tag}"),
        generation_id=gen,
        recorded_utc="2026-01-05T00:00:00Z",
        surrogate_mean_detection_rate=0.30,
        surrogate_worst_case_detection_rate=0.40,
        per_surrogate_detection_rates=rates,
        cross_model_disagreement=cross_model_disagreement(rates),
        transformation_sweep_variance=0.01,
        spectral_band_energy={"low": 0.5, "mid": 0.3, "high": 0.2},
        pattern_fidelity=0.9,
        printability=0.8,
        objective_trajectory={"initial": 0.9, "final": 0.3, "best": 0.3, "evaluations": 10},
        coverage_metrics={"coverage_entropy": 0.9},
        optimizer_config=OptimizerConfig(
            optimizer_id="synthetic-opt", seed=1, max_evaluations=10
        ),
    )
    record = TelemetryRecord(pre=pre)
    if with_outcome:
        record = record.append_outcome(
            HeldOutOutcome(
                candidate_sha256=pre.candidate_sha256,
                heldout_detection_rates={"held-x": 0.50, "held-y": 0.70},
                verdict=verdict,
                recorded_utc="2026-02-05T00:00:00Z",
                benchmark_run_id="synthetic-run-1",
            )
        )
    return record


def _registry_with_two() -> tuple[ExperimentRegistry, dict[str, TelemetryRecord]]:
    """Synthetic registry with two closed experiments (reverse-sorted gens)."""
    registry = ExperimentRegistry()
    telemetry = {
        "RAC-EXP-2026-002": _telemetry("RAC-PER-D2-0100", "b", verdict="PASS"),
        "RAC-EXP-2026-001": _telemetry("RAC-PER-D2-0099", "a", verdict="FAIL"),
    }
    for experiment_id, record in telemetry.items():
        artifact = ExperimentArtifact(
            experiment_id=experiment_id,
            hypothesis_id=f"HYP-{experiment_id[-3:]}",
            generation_id=record.pre.generation_id,
            created_utc=f"2026-01-0{experiment_id[-1]}T00:00:00Z",
            evidence_label="internally_measured",
            validity_flags={
                "surrogate_model_set_sha256": _hex(f"surset-{experiment_id}"),
                "heldout_model_set_sha256": _hex(f"heldset-{experiment_id}"),
            },
            stages=[
                StageRef(
                    stage="candidate",
                    artifact_id=f"cand-{experiment_id}",
                    sha256=record.pre.candidate_sha256,
                ),
                StageRef(
                    stage="generation",
                    artifact_id=f"gen-{experiment_id}",
                    sha256=_hex(f"generation-{experiment_id}"),
                    metadata={"protocol": "synthetic-protocol-v0"},
                ),
                StageRef(
                    stage="optimization_telemetry",
                    artifact_id=f"telemetry-{experiment_id}",
                    sha256=record.frozen_sha256(),
                ),
            ],
        )
        registry.add(artifact)
    return registry, telemetry


# ---------------------------------------------------------------------------
# Paper 1 longitudinal CSV.
# ---------------------------------------------------------------------------


def test_paper1_rows_correctness_and_ordering(tmp_path):
    registry, telemetry = _registry_with_two()
    # Synthetic release directory for one experiment (content_hash only).
    release_dir = tmp_path / "RAC-EXP-2026-001"
    release_dir.mkdir()
    content_hash = _hex("release-001")
    (release_dir / "RELEASE.json").write_text(
        json.dumps({"release_id": "RAC-EXP-2026-001", "content_hash": content_hash})
    )
    rows = paper1_longitudinal_rows(
        registry, telemetry=telemetry, releases={"RAC-EXP-2026-001": release_dir}
    )
    assert len(rows) == 2
    # Deterministic ordering: by (generation_id, experiment_id), not insertion.
    assert [r["experiment_id"] for r in rows] == [
        "RAC-EXP-2026-001",
        "RAC-EXP-2026-002",
    ]
    first = rows[0]
    assert first["generation_id"] == "RAC-PER-D2-0099"
    assert first["protocol"] == "synthetic-protocol-v0"
    assert first["surrogate_model_set_sha256"] == _hex("surset-RAC-EXP-2026-001")
    assert first["heldout_model_set_sha256"] == _hex("heldset-RAC-EXP-2026-001")
    assert float(first["surrogate_mean_detection_rate"]) == pytest.approx(0.30)
    # Held-out mean over {"held-x": 0.5, "held-y": 0.7}.
    assert float(first["heldout_mean_detection_rate"]) == pytest.approx(0.60)
    assert first["outcome"] == "fail"
    assert first["failure_classification"] == FailureCategory.UNCLASSIFIED.value
    assert first["release_content_hash"] == content_hash
    assert first["created_utc"] == "2026-01-01T00:00:00Z"
    assert first["outcome_recorded_utc"] == "2026-02-05T00:00:00Z"
    # Second row: PASS verdict, no release dir -> empty content hash.
    assert rows[1]["outcome"] == "pass"
    assert rows[1]["release_content_hash"] == ""


def test_paper1_csv_serialization_and_determinism(tmp_path):
    registry, telemetry = _registry_with_two()
    text = paper1_longitudinal_csv(registry, telemetry=telemetry)
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert list(parsed[0].keys()) == list(PAPER1_LONGITUDINAL_HEADER)
    assert len(parsed) == 2
    # Byte-identical on repeat (deterministic).
    assert text == paper1_longitudinal_csv(registry, telemetry=telemetry)
    out = write_paper1_longitudinal_csv(
        registry, tmp_path / "exports" / "paper1_longitudinal.csv", telemetry=telemetry
    )
    assert out.read_text() == text


def test_paper1_empty_registry_header_only(tmp_path):
    registry = ExperimentRegistry()
    text = paper1_longitudinal_csv(registry)
    lines = text.splitlines()
    assert len(lines) == 1
    assert lines[0] == ",".join(PAPER1_LONGITUDINAL_HEADER)
    # Registry with experiments but NO outcomes attached: still zero rows.
    registry2, telemetry = _registry_with_two()
    open_only = {
        k: TelemetryRecord(pre=v.pre) for k, v in telemetry.items()
    }
    assert paper1_longitudinal_rows(registry2, telemetry=open_only) == []
    assert len(paper1_longitudinal_csv(registry2, telemetry=open_only).splitlines()) == 1


# ---------------------------------------------------------------------------
# Paper 5 arm CSV.
# ---------------------------------------------------------------------------


def _synthetic_arms() -> list[Paper5Arm]:
    outcomes_m = {f"model-x|t0|{i}": (i % 2 == 0) for i in range(10)}
    outcomes_c = {f"model-x|t0|{i}": (i % 4 == 0) for i in range(10)}
    return [
        Paper5Arm(
            arm_id="arm-C",
            objective_name="cvar",
            objective_alpha=0.5,
            winner_candidate_sha256=_hex("winner-c"),
            heldout_outcomes=outcomes_c,
            telemetry_sha256=_hex("telemetry-c"),
        ),
        Paper5Arm(
            arm_id="arm-M",
            objective_name="mean",
            objective_alpha=None,
            winner_candidate_sha256=_hex("winner-m"),
            heldout_outcomes=outcomes_m,
            telemetry_sha256=_hex("telemetry-m"),
        ),
    ]


def test_paper5_arm_rows_and_csv(tmp_path):
    rows = paper5_arm_rows(_synthetic_arms())
    # Sorted by arm_id: arm-C before arm-M.
    assert [r["arm_id"] for r in rows] == ["arm-C", "arm-M"]
    arm_c, arm_m = rows
    assert arm_c["objective_name"] == "cvar"
    assert arm_c["objective_alpha"] == repr(0.5)
    assert arm_m["objective_alpha"] == ""
    assert arm_c["observation_units"] == "10"
    assert arm_c["detected"] == "3"
    lo, hi = wilson_interval(3, 10)
    assert float(arm_c["wilson_lower"]) == pytest.approx(lo)
    assert float(arm_c["wilson_upper"]) == pytest.approx(hi)
    assert float(arm_c["heldout_rate"]) == pytest.approx(0.3)
    assert arm_c["winner_candidate_sha256"] == _hex("winner-c")
    assert arm_c["telemetry_sha256"] == _hex("telemetry-c")
    assert arm_m["detected"] == "5"

    text = paper5_arms_csv(_synthetic_arms())
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert list(parsed[0].keys()) == list(PAPER5_ARMS_HEADER)
    assert len(parsed) == 2
    assert text == paper5_arms_csv(_synthetic_arms())  # deterministic
    out = write_paper5_arms_csv(_synthetic_arms(), tmp_path / "paper5_arms.csv")
    assert out.read_text() == text
    # Empty arms list: header only.
    assert paper5_arms_csv([]).splitlines() == [",".join(PAPER5_ARMS_HEADER)]


def test_paper5_arm_validation_rejects_bad_input():
    with pytest.raises(ValueError):
        paper5_arm_rows(
            [
                Paper5Arm(
                    arm_id="arm-X",
                    objective_name="cvar",
                    objective_alpha=None,  # cvar requires alpha
                    winner_candidate_sha256=_hex("w"),
                    heldout_outcomes={"u": True},
                    telemetry_sha256=_hex("t"),
                )
            ]
        )
    with pytest.raises(ValueError):
        paper5_arm_rows(
            [
                Paper5Arm(
                    arm_id="arm-X",
                    objective_name="mean",
                    objective_alpha=None,
                    winner_candidate_sha256="not-a-hash",
                    heldout_outcomes={"u": True},
                    telemetry_sha256=_hex("t"),
                )
            ]
        )


# ---------------------------------------------------------------------------
# Paper 5 comparison JSON passthrough.
# ---------------------------------------------------------------------------


def _synthetic_stats():
    outcomes = {
        f"model-{m}|transform-{t}|fixture-{f}": ((m + f) % 2 == 0, (m + f) % 3 == 0)
        for m in range(3)
        for t in range(2)
        for f in range(4)
    }
    return paired_arm_statistics(outcomes, bootstrap_resamples=100)


def test_paper5_comparison_json_passthrough(tmp_path):
    stats = _synthetic_stats()
    prereg = _hex("preregistration")
    payload = paper5_comparison_dict(stats, preregistration_sha256=prereg)
    # statistics block is EXACTLY the canonical producer JSON (passthrough).
    assert payload["statistics"] == json.loads(to_canonical_json(stats))
    assert payload["preregistration_sha256"] == prereg
    assert payload["decision_region"]["decision"] == stats.decision
    assert payload["decision_region"]["inconclusive_width_max"] == pytest.approx(0.20)

    text = paper5_comparison_json(stats, preregistration_sha256=prereg)
    assert text.endswith("\n")
    assert json.loads(text) == payload
    # Canonical: sorted keys, compact separators, byte-stable round-trip.
    assert text == paper5_comparison_json(stats, preregistration_sha256=prereg)
    compact = json.dumps(json.loads(text), sort_keys=True, separators=(",", ":")) + "\n"
    assert text == compact
    out = write_paper5_comparison_json(
        stats, tmp_path / "paper5_comparison.json", preregistration_sha256=prereg
    )
    assert out.read_text() == text

    with pytest.raises(ValueError):
        paper5_comparison_dict(stats, preregistration_sha256="bad")


# ---------------------------------------------------------------------------
# Figure scaffolds: structure + declared field paths vs real producers.
# ---------------------------------------------------------------------------


def _resolve_field_path(structure, path: str) -> bool:
    """Resolve a scaffold field path against a nested producer structure.

    Supports "[]" for list elements and "<...>" as a single-key wildcard.
    """
    node = structure
    for part in path.split("."):
        if part.endswith("[]"):
            key = part[:-2]
            if key:
                if not isinstance(node, dict) or key not in node:
                    return False
                node = node[key]
            if not isinstance(node, list) or not node:
                return False
            node = node[0]
        elif part.startswith("<") and part.endswith(">"):
            if not isinstance(node, dict) or not node:
                return False
            node = next(iter(node.values()))
        else:
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
    return True


def _objective_telemetry_sample() -> dict:
    """Build a real objective-telemetry dict via the actual producer."""
    spec = importlib.util.spec_from_file_location(
        "select_surrogate_candidate",
        ROOT / "scripts" / "select_surrogate_candidate.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("select_surrogate_candidate", module)
    spec.loader.exec_module(module)
    from ruthless_pipeline.certification.objectives import ObjectiveSpec

    stage_b = [
        {
            "candidate_id": "cand-a",
            "per_surrogate_detection_rates": {"s0": 0.1, "s1": 0.2, "s2": 0.3},
        },
        {
            "candidate_id": "cand-b",
            "per_surrogate_detection_rates": {"s0": 0.4, "s1": 0.2, "s2": 0.1},
        },
    ]
    return module.build_objective_telemetry(
        stage_b, objective=ObjectiveSpec(name="cvar", alpha=0.5), alpha=0.5
    )


def test_figure_scaffolds_structure_and_canonical(tmp_path):
    scaffolds = figure_scaffolds()
    assert [s["figure_id"] for s in scaffolds] == [
        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8",
    ]
    for scaffold in scaffolds:
        assert scaffold["status"] == "awaiting_data"
        assert scaffold["data"] == []  # empty scaffold, never placeholder data
        assert scaffold["title"]
        assert scaffold["fill_rule"]
        assert scaffold["sources"]
        assert scaffold["paper"] in (1, 5)
    written = write_figure_scaffolds(tmp_path / "manuscript" / "figures")
    assert len(written) == 8
    for path, scaffold in zip(written, scaffolds):
        text = path.read_text()
        assert text.endswith("\n")
        assert json.loads(text) == scaffold
        compact = (
            json.dumps(json.loads(text), sort_keys=True, separators=(",", ":")) + "\n"
        )
        assert text == compact


def test_scaffold_field_paths_match_real_producers():
    scaffolds = {s["figure_id"]: s for s in figure_scaffolds()}

    # Real producer structures.
    record = _telemetry("RAC-PER-D2-0005", "schema", verdict="PASS")
    telemetry_structure = record.to_dict()
    stats_structure = json.loads(to_canonical_json(_synthetic_stats()))
    objective_structure = _objective_telemetry_sample()
    registry, _ = _registry_with_two()
    experiment_structure = json.loads(registry.to_json())["experiments"][0]

    producers = {
        "telemetry": telemetry_structure,
        "paired": stats_structure,
        "objective": objective_structure,
        "experiment": experiment_structure,
    }

    def check(scaffold_id, producer_key):
        scaffold = scaffolds[scaffold_id]
        matched = False
        for source in scaffold["sources"]:
            name = source["producer"]
            if (
                (producer_key == "telemetry" and "telemetry_contract" in name)
                or (producer_key == "paired" and "paired_arm_statistics" in name)
                or (producer_key == "objective" and "build_objective_telemetry" in name)
                or (producer_key == "experiment" and "ExperimentArtifact" in name)
            ):
                matched = True
                for field in source["fields"]:
                    assert _resolve_field_path(
                        producers[producer_key], field
                    ), f"{scaffold_id}: field {field!r} missing from {producer_key} producer"
        assert matched, f"{scaffold_id}: no {producer_key} source declared"

    # F1/F3 consume the telemetry contract; F2 consumes experiment + telemetry.
    check("F1", "telemetry")
    check("F2", "telemetry")
    check("F2", "experiment")
    check("F3", "telemetry")
    # F4's telemetry-declared field also resolves.
    check("F4", "telemetry")
    # F5-F7 consume the real objective-telemetry producer structure.
    check("F5", "objective")
    check("F6", "objective")
    check("F7", "objective")
    # F8 consumes the real PairedArmStatistics canonical JSON structure.
    check("F8", "paired")

    # F4's taxonomy metric key really drives the real failure taxonomy.
    record_f4 = classify_failure(
        {"transformation_rates": {"brightness": 0.1, "blur": 0.6}},
        experiment_id="RAC-EXP-2026-009",
        generation_id="RAC-PER-D2-0005",
    )
    assert record_f4.category is FailureCategory.TRANSFORMATION_FRAGILITY

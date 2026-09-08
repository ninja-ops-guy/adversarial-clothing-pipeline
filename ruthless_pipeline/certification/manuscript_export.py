"""Manuscript automation exports for Papers 1 and 5 (Wave F, Track D).

This module extends the report-compiler family: it projects the append-only
``ExperimentRegistry`` (and frozen research releases per
``docs/RESEARCH_RELEASE_FORMAT.md``) into publication-ready CSV/JSON
artifacts, and declares the deterministic figure-input scaffolds for the
eight predefined manuscript figures.

Hard governance rule: NOTHING here invents results. Every number emitted is
derived from real registry entries, sealed telemetry records
(``telemetry_contract.TelemetryRecord``), sealed release directories, or the
preregistered statistics modules. When no closed experiment exists yet, the
exporters emit header-only CSVs and the figure scaffolds carry
``status: "awaiting_data"`` with an empty ``data`` array — never placeholder
numbers.

An experiment is "closed" for Paper 1 purposes iff a
``TelemetryRecord`` with the held-out ``outcome`` attached is supplied for
its ``experiment_id`` (the outcome is append-only and can only exist after
the generation closes; see telemetry_contract.py). The registry alone never
contains outcomes, so an empty/absent telemetry mapping yields a
header-only longitudinal CSV.

Stdlib-only. Conventions: ``from __future__ import annotations``, frozen
dataclasses, canonical JSON (sort_keys, compact separators, trailing
newline), CSV via the csv module with deterministic row ordering.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .experiment import ExperimentRegistry
from .failure_taxonomy import FailureCategory, classify_failure
from .objectives import ObjectiveSpec
from .paired_arm_statistics import (
    INCONCLUSIVE_WIDTH_MAX,
    PairedArmStatistics,
    to_canonical_json,
)
from .statistics import wilson_interval
from .telemetry_contract import TelemetryRecord

__all__ = [
    "PAPER1_LONGITUDINAL_HEADER",
    "PAPER5_ARMS_HEADER",
    "Paper5Arm",
    "paper1_longitudinal_rows",
    "paper1_longitudinal_csv",
    "write_paper1_longitudinal_csv",
    "paper5_arm_rows",
    "paper5_arms_csv",
    "write_paper5_arms_csv",
    "paper5_comparison_dict",
    "paper5_comparison_json",
    "write_paper5_comparison_json",
    "figure_scaffolds",
    "write_figure_scaffolds",
    "GENERATION_FIELDS",
    "GENERATION_STATUSES",
    "PAPER1_GENERATION_HEADER",
    "SourcedValue",
    "GenerationRecord",
    "load_committed_generation_records",
    "paper1_generation_rows",
    "paper1_generation_csv",
    "paper5_comparison_scaffold",
    "paper5_comparison_scaffold_json",
    "write_manuscript_exports",
    "figure_scaffolds_populated",
    "write_figure_scaffolds_populated",
]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(payload: Any) -> str:
    """Canonical JSON: sort_keys, compact separators, trailing newline."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def _is_sha256(value: str) -> bool:
    return bool(_SHA256_RE.match(value or ""))


def _format_float(value: float) -> str:
    """Deterministic float rendering for CSV cells (repr is stable in py3)."""
    return repr(float(value))


# ---------------------------------------------------------------------------
# Paper 1: longitudinal table over closed generations/experiments.
# ---------------------------------------------------------------------------

#: CSV header for paper1_longitudinal.csv (column order is frozen).
PAPER1_LONGITUDINAL_HEADER: tuple[str, ...] = (
    "experiment_id",
    "generation_id",
    "protocol",
    "surrogate_model_set_sha256",
    "heldout_model_set_sha256",
    "surrogate_mean_detection_rate",
    "heldout_mean_detection_rate",
    "outcome",
    "failure_classification",
    "release_content_hash",
    "created_utc",
    "outcome_recorded_utc",
)


def _stage_metadata(artifact, stage_name: str) -> Mapping[str, Any]:
    for stage in artifact.stages:
        if stage.stage == stage_name:
            return stage.metadata or {}
    return {}


def _release_content_hash(release_dir: Path) -> str:
    """Read content_hash from a frozen release directory's RELEASE.json."""
    payload = json.loads((release_dir / "RELEASE.json").read_text())
    content_hash = payload.get("content_hash", "")
    if not _is_sha256(content_hash):
        raise ValueError(
            f"{release_dir}/RELEASE.json: content_hash must be a 64-hex digest"
        )
    return content_hash


def paper1_longitudinal_rows(
    registry: ExperimentRegistry,
    *,
    telemetry: Mapping[str, TelemetryRecord] | None = None,
    releases: Mapping[str, str | Path] | None = None,
) -> list[dict[str, str]]:
    """One row per CLOSED experiment, sorted by (generation_id, experiment_id).

    ``telemetry`` maps experiment_id -> TelemetryRecord; only records with the
    append-only held-out ``outcome`` attached count as closed. ``releases``
    maps experiment_id -> release directory (per RESEARCH_RELEASE_FORMAT.md);
    when present, the row's ``release_content_hash`` is read from the sealed
    RELEASE.json, otherwise it is the empty string.

    Row fields (matching PAPER1_LONGITUDINAL_HEADER):
    - ``protocol``: the generation stage's ``metadata["protocol"]`` when the
      lineage pins one, else the artifact's evidence label.
    - model-set hashes: ``validity_flags["surrogate_model_set_sha256"]`` /
      ``["heldout_model_set_sha256"]`` when the registry entry carries them,
      else "".
    - ``surrogate_mean_detection_rate``: telemetry
      ``pre.surrogate_mean_detection_rate``.
    - ``heldout_mean_detection_rate``: mean of the sealed
      ``outcome.heldout_detection_rates``.
    - ``outcome``: "inconclusive" when the failure taxonomy classifies the
      metrics as STATISTICAL_INCONCLUSIVE, else the sealed verdict lowercased
      ("pass"/"fail").
    - ``failure_classification``: ``classify_failure`` primary category value,
      computed from the sealed telemetry metrics only.
    """
    telemetry = telemetry or {}
    releases = releases or {}
    # Public serialization already yields experiments sorted by id.
    experiment_ids = [
        entry["experiment_id"] for entry in json.loads(registry.to_json())["experiments"]
    ]
    rows: list[dict[str, str]] = []
    for experiment_id in experiment_ids:
        record = telemetry.get(experiment_id)
        if record is None or record.outcome is None:
            continue  # not closed: contributes no row (never a placeholder)
        record.validate()
        artifact = registry.get(experiment_id)
        pre, outcome = record.pre, record.outcome
        heldout_mean = (
            sum(outcome.heldout_detection_rates[k] for k in sorted(outcome.heldout_detection_rates))
            / len(outcome.heldout_detection_rates)
        )
        metrics = {
            "surrogate_detection_rate": pre.surrogate_mean_detection_rate,
            "heldout_detection_rate": heldout_mean,
            "coverage_entropy": float(pre.coverage_metrics["coverage_entropy"]),
        }
        failure = classify_failure(
            metrics, experiment_id=experiment_id, generation_id=pre.generation_id
        )
        if failure.category is FailureCategory.STATISTICAL_INCONCLUSIVE:
            outcome_label = "inconclusive"
        else:
            outcome_label = outcome.verdict.lower()
        generation_meta = _stage_metadata(artifact, "generation")
        protocol = str(generation_meta.get("protocol", artifact.evidence_label))
        flags = artifact.validity_flags or {}
        release_dir = releases.get(experiment_id)
        content_hash = (
            _release_content_hash(Path(release_dir)) if release_dir is not None else ""
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "generation_id": artifact.generation_id,
                "protocol": protocol,
                "surrogate_model_set_sha256": str(
                    flags.get("surrogate_model_set_sha256", "")
                ),
                "heldout_model_set_sha256": str(
                    flags.get("heldout_model_set_sha256", "")
                ),
                "surrogate_mean_detection_rate": _format_float(
                    pre.surrogate_mean_detection_rate
                ),
                "heldout_mean_detection_rate": _format_float(heldout_mean),
                "outcome": outcome_label,
                "failure_classification": failure.category.value,
                "release_content_hash": content_hash,
                "created_utc": artifact.created_utc,
                "outcome_recorded_utc": outcome.recorded_utc,
            }
        )
    rows.sort(key=lambda row: (row["generation_id"], row["experiment_id"]))
    return rows


def paper1_longitudinal_csv(
    registry: ExperimentRegistry,
    *,
    telemetry: Mapping[str, TelemetryRecord] | None = None,
    releases: Mapping[str, str | Path] | None = None,
) -> str:
    """Serialize the Paper 1 longitudinal table to CSV (header always present).

    With no closed experiments the output is the header line only — zero
    fabricated rows.
    """
    rows = paper1_longitudinal_rows(registry, telemetry=telemetry, releases=releases)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=list(PAPER1_LONGITUDINAL_HEADER), lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def write_paper1_longitudinal_csv(
    registry: ExperimentRegistry,
    path: str | Path,
    *,
    telemetry: Mapping[str, TelemetryRecord] | None = None,
    releases: Mapping[str, str | Path] | None = None,
) -> Path:
    """Write paper1_longitudinal.csv to ``path`` (parent dirs created)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        paper1_longitudinal_csv(registry, telemetry=telemetry, releases=releases)
    )
    return path


# ---------------------------------------------------------------------------
# Paper 5: per-arm table (D2-0005-style arms).
# ---------------------------------------------------------------------------

#: CSV header for paper5_arms.csv (column order is frozen).
PAPER5_ARMS_HEADER: tuple[str, ...] = (
    "arm_id",
    "objective_name",
    "objective_alpha",
    "winner_candidate_sha256",
    "observation_units",
    "detected",
    "heldout_rate",
    "wilson_lower",
    "wilson_upper",
    "telemetry_sha256",
)


@dataclass(frozen=True)
class Paper5Arm:
    """One sealed D2-0005-style arm: objective, winner, held-out outcomes.

    ``heldout_outcomes`` maps the canonical observation-unit key
    ("model_id|transform_id|fixture_index") to whether the arm's winner
    candidate was detected on that unit. These are REAL sealed observations;
    the exporter never fabricates them.
    """

    arm_id: str
    objective_name: str
    objective_alpha: float | None
    winner_candidate_sha256: str
    heldout_outcomes: Mapping[str, Any]
    telemetry_sha256: str

    def validate(self) -> None:
        if not self.arm_id:
            raise ValueError("arm_id is required")
        ObjectiveSpec(name=self.objective_name, alpha=self.objective_alpha).validate()
        if not _is_sha256(self.winner_candidate_sha256):
            raise ValueError("winner_candidate_sha256 must be a 64-hex digest")
        if not _is_sha256(self.telemetry_sha256):
            raise ValueError("telemetry_sha256 must be a 64-hex digest")
        if not self.heldout_outcomes:
            raise ValueError("heldout_outcomes must be non-empty")
        for unit, value in self.heldout_outcomes.items():
            if not isinstance(unit, str) or not unit:
                raise ValueError("observation unit keys must be non-empty strings")
            if not (isinstance(value, bool) or (isinstance(value, int) and value in (0, 1))):
                raise ValueError(
                    f"outcome for unit {unit!r} must be boolean or 0/1; got {value!r}"
                )


def paper5_arm_rows(arms: Sequence[Paper5Arm]) -> list[dict[str, str]]:
    """One row per arm, sorted by arm_id; rates + Wilson intervals computed
    from the sealed per-unit outcomes via certification.statistics."""
    rows: list[dict[str, str]] = []
    for arm in arms:
        arm.validate()
        units = sorted(arm.heldout_outcomes)
        detected = sum(1 for unit in units if bool(arm.heldout_outcomes[unit]))
        total = len(units)
        lo, hi = wilson_interval(detected, total)
        rows.append(
            {
                "arm_id": arm.arm_id,
                "objective_name": arm.objective_name,
                "objective_alpha": (
                    ""
                    if arm.objective_alpha is None
                    else _format_float(arm.objective_alpha)
                ),
                "winner_candidate_sha256": arm.winner_candidate_sha256,
                "observation_units": str(total),
                "detected": str(detected),
                "heldout_rate": _format_float(detected / total),
                "wilson_lower": _format_float(lo),
                "wilson_upper": _format_float(hi),
                "telemetry_sha256": arm.telemetry_sha256,
            }
        )
    rows.sort(key=lambda row: row["arm_id"])
    return rows


def paper5_arms_csv(arms: Sequence[Paper5Arm]) -> str:
    """Serialize the Paper 5 per-arm table to CSV (header always present)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=list(PAPER5_ARMS_HEADER), lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(paper5_arm_rows(arms))
    return buffer.getvalue()


def write_paper5_arms_csv(arms: Sequence[Paper5Arm], path: str | Path) -> Path:
    """Write paper5_arms.csv to ``path`` (parent dirs created)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(paper5_arms_csv(arms))
    return path


# ---------------------------------------------------------------------------
# Paper 5: primary paired-arm comparison JSON.
# ---------------------------------------------------------------------------


def paper5_comparison_dict(
    stats: PairedArmStatistics,
    *,
    preregistration_sha256: str,
) -> dict[str, Any]:
    """Canonical passthrough of the preregistered paired-arm statistics.

    ``statistics`` is exactly the canonical JSON payload produced by
    ``paired_arm_statistics.to_canonical_json`` (no recomputation, no
    rounding). Metadata pins the preregistration hash and the preregistered
    decision region for Delta = R_M - R_C (H1: Delta > 0).
    """
    if not _is_sha256(preregistration_sha256):
        raise ValueError("preregistration_sha256 must be a 64-character hex string")
    return {
        "comparison": "arm_m_minus_arm_c",
        "primary_endpoint": (
            "held-out candidate detection rate; Delta = R_M - R_C; "
            "H1: Delta > 0 (CVaR arm suppresses below the mean arm)"
        ),
        "preregistration_sha256": preregistration_sha256,
        "statistics": json.loads(to_canonical_json(stats)),
        "decision_region": {
            "decision": stats.decision,
            "inconclusive_width_max": INCONCLUSIVE_WIDTH_MAX,
            "rule": (
                "success if risk_difference_interval lower bound > 0; "
                "negative if upper bound < 0; null if the interval includes 0 "
                "within the width budget; inconclusive if interval width "
                "exceeds inconclusive_width_max"
            ),
        },
    }


def paper5_comparison_json(
    stats: PairedArmStatistics,
    *,
    preregistration_sha256: str,
) -> str:
    """Canonical JSON (sort_keys, compact separators, trailing newline)."""
    return _canonical_json(
        paper5_comparison_dict(stats, preregistration_sha256=preregistration_sha256)
    )


def write_paper5_comparison_json(
    stats: PairedArmStatistics,
    path: str | Path,
    *,
    preregistration_sha256: str,
) -> Path:
    """Write paper5_comparison.json to ``path`` (parent dirs created)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        paper5_comparison_json(stats, preregistration_sha256=preregistration_sha256)
    )
    return path


# ---------------------------------------------------------------------------
# Deterministic figure-input scaffolds (F1-F8).
# ---------------------------------------------------------------------------

_TELEMETRY_PRODUCER = "ruthless_pipeline.certification.telemetry_contract.TelemetryRecord"
_TELEMETRY_ARTIFACT = "stages/optimization_telemetry/<telemetry-record>.json (release dir per RESEARCH_RELEASE_FORMAT.md)"
_OBJECTIVE_TELEMETRY_PRODUCER = "scripts.select_surrogate_candidate.build_objective_telemetry"
_OBJECTIVE_TELEMETRY_ARTIFACT = "objective-telemetry JSON emitted by select_surrogate_candidate.py --objective-telemetry"
_PAIRED_STATS_PRODUCER = "ruthless_pipeline.certification.paired_arm_statistics.to_canonical_json"
_FAILURE_TAXONOMY_PRODUCER = "ruthless_pipeline.certification.failure_taxonomy.classify_failure (metrics input)"
_EXPERIMENT_PRODUCER = "ruthless_pipeline.certification.experiment.ExperimentArtifact"

#: Exact fill/population entry point declared by every scaffold source.
_FILL_FUNCTION = "ruthless_pipeline.certification.manuscript_export.write_figure_scaffolds_populated"


def _source(producer: str, artifact: str, fields: list[str], artifact_ids: list[str]) -> dict[str, Any]:
    """One scaffold source declaration: producer, exact artifact ids, fields."""
    return {
        "producer": producer,
        "producer_function": _FILL_FUNCTION,
        "artifact": artifact,
        "artifact_ids": artifact_ids,
        "fields": fields,
    }



def figure_scaffolds() -> list[dict[str, Any]]:
    """The eight predefined manuscript figure-input scaffolds.

    Every scaffold declares its exact data lineage (source artifact + field
    paths into the real producer structures), an empty ``data`` array with
    ``status: "awaiting_data"``, and a ``fill_rule`` describing precisely how
    a future tool populates it from sealed artifacts. No placeholder numbers
    appear anywhere.
    """

    def scaffold(**kwargs) -> dict[str, Any]:
        kwargs.setdefault("status", "awaiting_data")
        kwargs.setdefault("data", [])
        return kwargs

    return [
        scaffold(
            figure_id="F1",
            paper=1,
            title="Surrogate-vs-held-out transfer scatter across closed generations",
            plot_type="scatter",
            axes={
                "x": {
                    "label": "surrogate mean detection rate (frozen pre-held-out)",
                    "field": "pre.surrogate_mean_detection_rate",
                    "scale": "linear [0, 1]",
                },
                "y": {
                    "label": "held-out mean detection rate",
                    "field": "mean of outcome.heldout_detection_rates",
                    "scale": "linear [0, 1]",
                },
                "color": {"label": "outcome", "field": "outcome.verdict"},
            },
            sources=[
                _source(
                    _TELEMETRY_PRODUCER,
                    _TELEMETRY_ARTIFACT,
                    [
                        "pre.candidate_sha256",
                        "pre.surrogate_mean_detection_rate",
                        "outcome.heldout_detection_rates",
                        "outcome.verdict",
                    ],
                    [D2_0003_STATUS_JSON, D2_0003_BENCHMARK_JSON],
                )
            ],
            fill_rule=(
                "For every closed experiment in the ExperimentRegistry, load the "
                "sealed TelemetryRecord referenced by its optimization_telemetry "
                "StageRef (StageRef.sha256 must equal the record's "
                "frozen_sha256()). Emit one point per experiment: x = "
                "pre.surrogate_mean_detection_rate, y = mean of "
                "outcome.heldout_detection_rates (sorted model ids), color by "
                "outcome.verdict. Skip records with outcome == null. The 45-degree "
                "identity line and the x = surrogate / y = held-out quadrant are "
                "drawn by the renderer, not stored."
            ),
        ),
        scaffold(
            figure_id="F2",
            paper=1,
            title="Generation timeline of closed experiments",
            plot_type="timeline",
            axes={
                "x": {
                    "label": "closure date (UTC)",
                    "field": "outcome.recorded_utc",
                    "scale": "time",
                },
                "y": {
                    "label": "held-out mean detection rate",
                    "field": "mean of outcome.heldout_detection_rates",
                    "scale": "linear [0, 1]",
                },
                "series": {"label": "generation", "field": "generation_id"},
            },
            sources=[
                _source(
                    _EXPERIMENT_PRODUCER,
                    "experiment.json (release dir root)",
                    ["experiment_id", "generation_id", "created_utc", "evidence_label"],
                    [D2_0003_STATUS_JSON],
                ),
                _source(
                    _TELEMETRY_PRODUCER,
                    _TELEMETRY_ARTIFACT,
                    ["outcome.heldout_detection_rates", "outcome.recorded_utc"],
                    [D2_0003_STATUS_JSON, D2_0003_BENCHMARK_JSON],
                ),
            ],
            fill_rule=(
                "For every closed experiment, emit one marker at "
                "(outcome.recorded_utc, mean of outcome.heldout_detection_rates) "
                "grouped into series by generation_id from the registry artifact; "
                "markers are annotated with experiment_id and ordered by "
                "outcome.recorded_utc. Experiments without an attached outcome "
                "contribute nothing."
            ),
        ),
        scaffold(
            figure_id="F3",
            paper=1,
            title="Cross-model architecture disagreement per candidate",
            plot_type="bar",
            axes={
                "x": {
                    "label": "candidate (sha256 prefix)",
                    "field": "pre.candidate_sha256",
                    "scale": "categorical",
                },
                "y": {
                    "label": "cross-model disagreement",
                    "field": "pre.cross_model_disagreement",
                    "scale": "linear",
                },
            },
            sources=[
                _source(
                    _TELEMETRY_PRODUCER,
                    _TELEMETRY_ARTIFACT,
                    [
                        "pre.candidate_sha256",
                        "pre.cross_model_disagreement.variance",
                        "pre.cross_model_disagreement.spread",
                        "pre.cross_model_disagreement.max_pairwise_delta",
                    ],
                    [],
                )
            ],
            fill_rule=(
                "For every frozen pre-held-out telemetry record (outcome not "
                "required; the pre-held-out portion is sealed at freeze time), "
                "emit one bar group keyed by pre.candidate_sha256 with bars for "
                "cross_model_disagreement.variance, .spread and "
                ".max_pairwise_delta. Values are copied verbatim from the sealed "
                "record (they are recomputed inside validate() from "
                "per_surrogate_detection_rates, so they cannot drift)."
            ),
        ),
        scaffold(
            figure_id="F4",
            paper=1,
            title="Transformation robustness: per-transform detection rates",
            plot_type="heatmap",
            axes={
                "x": {
                    "label": "transformation (sweep condition id)",
                    "field": "transformation_rates keys",
                    "scale": "categorical",
                },
                "y": {
                    "label": "candidate / generation",
                    "field": "experiment_id",
                    "scale": "categorical",
                },
                "value": {
                    "label": "candidate detection rate",
                    "field": "transformation_rates values",
                    "scale": "linear [0, 1]",
                },
            },
            sources=[
                _source(
                    _FAILURE_TAXONOMY_PRODUCER,
                    "failure-classification metrics bundle per closed experiment",
                    ["transformation_rates"],
                    [],
                ),
                _source(
                    _TELEMETRY_PRODUCER,
                    _TELEMETRY_ARTIFACT,
                    ["pre.transformation_sweep_variance"],
                    [],
                ),
            ],
            fill_rule=(
                "For every closed experiment, take the sealed transformation-sweep "
                "rates mapping {transform_id: detection_rate} that feeds "
                "classify_failure's 'transformation_rates' metric; emit one heatmap "
                "row per experiment with one cell per transform_id (columns sorted "
                "lexicographically). pre.transformation_sweep_variance annotates "
                "each row. Experiments whose sealed bundle lacks "
                "transformation_rates are omitted — cells are never imputed."
            ),
        ),
        scaffold(
            figure_id="F5",
            paper=5,
            title="Objective trajectories: mean / CVaR / worst-model loss per checkpoint",
            plot_type="line",
            axes={
                "x": {
                    "label": "optimization checkpoint (stage-B evaluation index)",
                    "field": "checkpoints[].checkpoint",
                    "scale": "integer",
                },
                "y": {
                    "label": "objective loss (lower is better)",
                    "field": "checkpoints[].losses",
                    "scale": "linear",
                },
                "series": {
                    "label": "loss kind",
                    "field": "checkpoints[].losses.mean | .cvar | .worst_model",
                },
            },
            sources=[
                _source(
                    _OBJECTIVE_TELEMETRY_PRODUCER,
                    _OBJECTIVE_TELEMETRY_ARTIFACT,
                    [
                        "objective.name",
                        "objective.alpha",
                        "checkpoints[].checkpoint",
                        "checkpoints[].candidate_id",
                        "checkpoints[].losses.mean",
                        "checkpoints[].losses.cvar",
                        "checkpoints[].losses.worst_model",
                    ],
                    [],
                )
            ],
            fill_rule=(
                "Load the sealed objective-telemetry JSON for the arm. Emit three "
                "series over checkpoints[].checkpoint: losses.mean, losses.cvar "
                "and losses.worst_model, copying the numbers verbatim in "
                "checkpoint order. The panel title records objective.name and "
                "objective.alpha. One panel per arm; no smoothing or "
                "recomputation."
            ),
        ),
        scaffold(
            figure_id="F6",
            paper=5,
            title="CVaR tail-membership turnover per checkpoint",
            plot_type="event_flow",
            axes={
                "x": {
                    "label": "optimization checkpoint",
                    "field": "checkpoints[].checkpoint",
                    "scale": "integer",
                },
                "y": {
                    "label": "surrogate model id",
                    "field": "checkpoints[].cvar_tail.member_ids",
                    "scale": "categorical",
                },
            },
            sources=[
                _source(
                    _OBJECTIVE_TELEMETRY_PRODUCER,
                    _OBJECTIVE_TELEMETRY_ARTIFACT,
                    [
                        "checkpoints[].checkpoint",
                        "checkpoints[].cvar_tail.alpha",
                        "checkpoints[].cvar_tail.k",
                        "checkpoints[].cvar_tail.member_ids",
                        "checkpoints[].tail_turnover.entered",
                        "checkpoints[].tail_turnover.left",
                    ],
                    [],
                )
            ],
            fill_rule=(
                "Load the sealed objective-telemetry JSON. For each checkpoint, "
                "mark every member of cvar_tail.member_ids as in-tail; annotate "
                "tail_turnover.entered ids with an enter marker and "
                "tail_turnover.left ids with an exit marker. Tail size k and "
                "alpha come from cvar_tail. No turnover is recomputed; the "
                "sealed entered/left lists are authoritative."
            ),
        ),
        scaffold(
            figure_id="F7",
            paper=5,
            title="Mean-vs-CVaR candidate rank changes",
            plot_type="dumbbell",
            axes={
                "x": {
                    "label": "rank (1 = lowest loss)",
                    "field": "checkpoints[].candidate_ranks",
                    "scale": "integer",
                },
                "y": {
                    "label": "candidate id",
                    "field": "checkpoints[].candidate_id",
                    "scale": "categorical",
                },
            },
            sources=[
                _source(
                    _OBJECTIVE_TELEMETRY_PRODUCER,
                    _OBJECTIVE_TELEMETRY_ARTIFACT,
                    [
                        "checkpoints[].checkpoint",
                        "checkpoints[].candidate_id",
                        "checkpoints[].candidate_ranks.<candidate_id>.mean_rank",
                        "checkpoints[].candidate_ranks.<candidate_id>.cvar_rank",
                        "checkpoints[].candidate_ranks.<candidate_id>.rank_delta",
                    ],
                    [],
                )
            ],
            fill_rule=(
                "Load the sealed objective-telemetry JSON and take its FINAL "
                "checkpoint. For every key of candidate_ranks emit one dumbbell "
                "row: left head = mean_rank, right head = cvar_rank, label = "
                "rank_delta (cvar_rank - mean_rank, positive means the candidate "
                "ranks worse under CVaR than under the mean). Rows sorted by "
                "mean_rank, ties by candidate id. Ranks are copied verbatim; "
                "they are never re-derived."
            ),
        ),
        scaffold(
            figure_id="F8",
            paper=5,
            title="Paired-arm outcome: arm rates, CIs, Delta and decision region",
            plot_type="forest",
            axes={
                "x": {
                    "label": "held-out detection rate / risk difference",
                    "field": "risk_difference",
                    "scale": "linear",
                },
                "y": {
                    "label": "estimate",
                    "field": "arm_m | arm_c | delta",
                    "scale": "categorical",
                },
            },
            sources=[
                _source(
                    _PAIRED_STATS_PRODUCER,
                    "paper5_comparison.json (this module) / sealed paired-arm statistics JSON",
                    [
                        "observation_units",
                        "arm_m.rate",
                        "arm_m.interval",
                        "arm_c.rate",
                        "arm_c.interval",
                        "risk_difference",
                        "risk_difference_interval",
                        "interval_width",
                        "decision",
                        "inconclusive_width",
                    ],
                    [],
                )
            ],
            fill_rule=(
                "Load the sealed paired-arm statistics JSON produced by "
                "paired_arm_statistics.to_canonical_json (carried verbatim in "
                "paper5_comparison.json under 'statistics'). Draw point+interval "
                "rows for arm_m.rate/arm_m.interval and arm_c.rate/arm_c.interval "
                "on a [0, 1] rate axis, and risk_difference with "
                "risk_difference_interval on a shared delta axis with a "
                "zero reference line. Shade the preregistered decision regions: "
                "success (interval lower bound > 0), negative (upper bound < 0), "
                "null (includes 0), and mark the comparison inconclusive when "
                "inconclusive_width is true (interval_width > 0.20). The "
                "rendered 'decision' string is copied verbatim."
            ),
        ),
    ]


_FIGURE_SLUGS: dict[str, str] = {
    "F1": "transfer_scatter",
    "F2": "generation_timeline",
    "F3": "architecture_disagreement",
    "F4": "transformation_robustness",
    "F5": "objective_trajectories",
    "F6": "cvar_tail_turnover",
    "F7": "mean_vs_cvar_rank_changes",
    "F8": "paired_arm_outcome",
}


def _figure_slugs() -> dict[str, str]:
    return dict(_FIGURE_SLUGS)


def write_figure_scaffolds(directory: str | Path) -> list[Path]:
    """Write the eight scaffolds as canonical JSON into ``directory``.

    Filenames: ``<figure_id>_<slug>.json`` (e.g. ``F1_transfer_scatter.json``).
    """
    slugs = _figure_slugs()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scaffold in figure_scaffolds():
        path = directory / f"{scaffold['figure_id']}_{slugs[scaffold['figure_id']]}.json"
        path.write_text(_canonical_json(scaffold))
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Overnight stream MS: committed-evidence generation exports (D2-0003/D2-0004).
#
# Governance: every populated datum carries its source artifact (repo-relative
# path) plus the artifact's SHA-256 in adjacent columns/keys. Fields with no
# closed-release evidence stay blank; a "running" generation contributes a
# row with all evidence fields blank. Nothing is invented.
# ---------------------------------------------------------------------------

#: Canonical evidence fields of one generation row, in frozen column order.
GENERATION_FIELDS: tuple[str, ...] = (
    "protocol",
    "surrogate_model_set",
    "heldout_model_set",
    "candidate_sha256",
    "surrogate_detection_rate",
    "heldout_detection_rate",
    "heldout_n",
    "decision",
    "evidence_state",
    "certificate_id",
    "source_commit",
    "recorded_utc",
)

GENERATION_STATUSES: tuple[str, ...] = ("closed", "running")

#: Frozen CSV header for the committed-evidence paper1_longitudinal.csv:
#: id/status (with status provenance), then per field a triple of
#: value/source/sha256 columns.
PAPER1_GENERATION_HEADER: tuple[str, ...] = (
    ("generation_id", "status", "status_source", "status_sha256")
    + tuple(
        column
        for field in GENERATION_FIELDS
        for column in (field, f"{field}_source", f"{field}_sha256")
    )
)

#: Committed evidence files backing the D2-0003 closed-generation row.
D2_0003_STATUS_JSON = "d2-latest-status.json"
D2_0003_BENCHMARK_JSON = "benchmark-results.json"
#: Generation JSON backing the D2-0004 "running" row (read-only).
D2_0004_GENERATION_JSON = "generations/RAC-PER-D2-0004.json"

_PAPER5_COMPARISON_STATUS = "awaiting_d2-0005_closure"


@dataclass(frozen=True)
class SourcedValue:
    """One exported datum with provenance; blank when no evidence exists.

    Invariants: a populated value requires a non-empty ``source`` (release id
    or repo-relative artifact path) and a 64-hex ``sha256`` of that artifact;
    a blank value requires empty source and sha256. There is no third state.
    """

    value: str = ""
    source: str = ""
    sha256: str = ""

    @property
    def populated(self) -> bool:
        return self.value != ""

    def validate(self) -> None:
        if self.populated:
            if not self.source:
                raise ValueError("populated value requires a source artifact id")
            if not _is_sha256(self.sha256):
                raise ValueError("populated value requires the source artifact sha256")
        elif self.source or self.sha256:
            raise ValueError("blank value must have empty source and sha256")


@dataclass(frozen=True)
class GenerationRecord:
    """Evidence for one generation row: status plus sourced fields."""

    generation_id: str
    status: str  # "closed" | "running"
    status_source: SourcedValue = SourcedValue()
    fields: Mapping[str, SourcedValue] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.generation_id:
            raise ValueError("generation_id is required")
        if self.status not in GENERATION_STATUSES:
            raise ValueError(f"status must be one of {GENERATION_STATUSES}")
        self.status_source.validate()
        unknown = sorted(set(self.fields) - set(GENERATION_FIELDS))
        if unknown:
            raise ValueError(f"unknown generation fields: {unknown}")
        populated = 0
        for name, sourced in self.fields.items():
            sourced.validate()
            populated += 1 if sourced.populated else 0
        if self.status == "running" and populated:
            raise ValueError(
                "a running generation must have all evidence fields blank "
                "(no invented results)"
            )
        if self.status == "closed" and not populated:
            raise ValueError("a closed generation must populate its evidence fields")


def _file_sourced(repo_root: Path, rel_path: str, value: Any) -> SourcedValue:
    """Build a SourcedValue pinned to a committed file's actual SHA-256."""
    digest = hashlib.sha256((repo_root / rel_path).read_bytes()).hexdigest()
    return SourcedValue(value=str(value), source=rel_path, sha256=digest)


def load_committed_generation_records(
    repo_root: str | Path,
) -> tuple[GenerationRecord, ...]:
    """Build generation rows from the repo's committed evidence files.

    D2-0003 (closed, retained negative): populated from d2-latest-status.json
    and benchmark-results.json. D2-0004: status "running" (provenance: its
    generation JSON), all evidence fields blank until its release exists.
    """
    repo_root = Path(repo_root)
    status_path = repo_root / D2_0003_STATUS_JSON
    benchmark_path = repo_root / D2_0003_BENCHMARK_JSON
    if not status_path.is_file() or not benchmark_path.is_file():
        raise ValueError("D2-0003 committed evidence files are missing")
    status = json.loads(status_path.read_text())
    benchmark = json.loads(benchmark_path.read_text())

    heldout = status["heldout"]
    surrogate_rate = benchmark["benchmark"]["comparative_summary"]["surrogate"][
        "candidate_detection_rate"
    ]
    d2_0003 = GenerationRecord(
        generation_id=str(status["candidate_id"]),
        status="closed",
        status_source=_file_sourced(
            repo_root, D2_0003_STATUS_JSON, status["evidence_state"]
        ),
        fields={
            "protocol": _file_sourced(
                repo_root,
                D2_0003_STATUS_JSON,
                f"{status['protocol_id']} {status['protocol_version']}",
            ),
            "surrogate_model_set": _file_sourced(
                repo_root, D2_0003_STATUS_JSON, status["surrogate_model_set"]
            ),
            "heldout_model_set": _file_sourced(
                repo_root, D2_0003_STATUS_JSON, status["heldout_model_set"]
            ),
            "candidate_sha256": _file_sourced(
                repo_root, D2_0003_BENCHMARK_JSON, benchmark["candidate"]["sha256"]
            ),
            "surrogate_detection_rate": _file_sourced(
                repo_root, D2_0003_BENCHMARK_JSON, repr(float(surrogate_rate))
            ),
            "heldout_detection_rate": _file_sourced(
                repo_root,
                D2_0003_STATUS_JSON,
                repr(float(heldout["candidate_detection_rate"])),
            ),
            "heldout_n": _file_sourced(repo_root, D2_0003_STATUS_JSON, heldout["n"]),
            "decision": _file_sourced(
                repo_root, D2_0003_STATUS_JSON, status["decision"]
            ),
            "evidence_state": _file_sourced(
                repo_root, D2_0003_STATUS_JSON, status["evidence_state"]
            ),
            "certificate_id": _file_sourced(
                repo_root, D2_0003_STATUS_JSON, status["certificate_id"]
            ),
            "source_commit": _file_sourced(
                repo_root, D2_0003_STATUS_JSON, status["source_commit"]
            ),
            "recorded_utc": _file_sourced(
                repo_root, D2_0003_BENCHMARK_JSON, benchmark["generated_at"]
            ),
        },
    )

    generation_path = repo_root / D2_0004_GENERATION_JSON
    if not generation_path.is_file():
        raise ValueError("D2-0004 generation JSON is missing")
    generation = json.loads(generation_path.read_text())
    d2_0004 = GenerationRecord(
        generation_id=str(generation["generation_id"]),
        status="running",
        status_source=_file_sourced(
            repo_root, D2_0004_GENERATION_JSON, generation["status"]
        ),
        fields={},
    )
    records = (d2_0003, d2_0004)
    for record in records:
        record.validate()
    return records


def paper1_generation_rows(
    records: Sequence[GenerationRecord],
) -> list[dict[str, str]]:
    """One CSV row dict per generation, sorted by generation_id.

    Columns follow PAPER1_GENERATION_HEADER: each populated field carries its
    source artifact id and sha256 in the adjacent ``*_source`` / ``*_sha256``
    columns; blank fields leave all three columns empty.
    """
    rows: list[dict[str, str]] = []
    for record in records:
        record.validate()
        row = {
            "generation_id": record.generation_id,
            "status": record.status,
            "status_source": record.status_source.source,
            "status_sha256": record.status_source.sha256,
        }
        for field_name in GENERATION_FIELDS:
            sourced = record.fields.get(field_name, SourcedValue())
            row[field_name] = sourced.value
            row[f"{field_name}_source"] = sourced.source
            row[f"{field_name}_sha256"] = sourced.sha256
        rows.append(row)
    rows.sort(key=lambda row: row["generation_id"])
    return rows


def paper1_generation_csv(records: Sequence[GenerationRecord]) -> str:
    """Serialize generation rows to CSV (header always present)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=list(PAPER1_GENERATION_HEADER), lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(paper1_generation_rows(records))
    return buffer.getvalue()


# -- Paper 5 awaiting-closure scaffolds -------------------------------------


def paper5_comparison_scaffold() -> dict[str, Any]:
    """paper5_comparison.json schema with every data field null.

    D2-0005 has not closed; the only non-null entries are the status string
    and the preregistered (constant) decision-region documentation. All
    measured/statistical fields are JSON null — never placeholder numbers.
    """
    null_arm = {
        "detected": None,
        "total": None,
        "rate": None,
        "interval": [None, None],
    }
    return {
        "comparison": "arm_m_minus_arm_c",
        "status": _PAPER5_COMPARISON_STATUS,
        "primary_endpoint": (
            "held-out candidate detection rate; Delta = R_M - R_C; "
            "H1: Delta > 0 (CVaR arm suppresses below the mean arm)"
        ),
        "preregistration_sha256": None,
        "statistics": {
            "observation_units": None,
            "arm_m": dict(null_arm),
            "arm_c": dict(null_arm),
            "risk_difference": None,
            "risk_difference_interval": [None, None],
            "interval_width": None,
            "discordant_m_only": None,
            "discordant_c_only": None,
            "decision": None,
            "inconclusive_width": None,
            "z": None,
            "bootstrap_resamples": None,
            "bootstrap_seed": None,
        },
        "decision_region": {
            "decision": None,
            "inconclusive_width_max": INCONCLUSIVE_WIDTH_MAX,
            "rule": (
                "success if risk_difference_interval lower bound > 0; "
                "negative if upper bound < 0; null if the interval includes 0 "
                "within the width budget; inconclusive if interval width "
                "exceeds inconclusive_width_max"
            ),
        },
    }


def paper5_comparison_scaffold_json() -> str:
    """Canonical JSON of the awaiting-closure comparison scaffold."""
    return _canonical_json(paper5_comparison_scaffold())


def write_manuscript_exports(
    repo_root: str | Path,
    out_dir: str | Path,
) -> dict[str, Path]:
    """Emit the deterministic committed-evidence exports into ``out_dir``.

    Writes paper1_longitudinal.csv (committed-evidence generation rows),
    paper5_arms.csv (header only — zero data rows until D2-0005 closes) and
    paper5_comparison.json (all-null scaffold). Byte-identical across runs.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records = load_committed_generation_records(repo_root)
    paths = {
        "paper1_longitudinal.csv": out_dir / "paper1_longitudinal.csv",
        "paper5_arms.csv": out_dir / "paper5_arms.csv",
        "paper5_comparison.json": out_dir / "paper5_comparison.json",
    }
    paths["paper1_longitudinal.csv"].write_text(paper1_generation_csv(records))
    paths["paper5_arms.csv"].write_text(paper5_arms_csv([]))
    paths["paper5_comparison.json"].write_text(paper5_comparison_scaffold_json())
    return paths


# -- Figure population from closed-generation evidence ----------------------


def _closed_figure_point(record: GenerationRecord) -> dict[str, Any]:
    """One deterministic figure datum for a closed generation, with provenance."""
    record.validate()
    fields = record.fields
    artifacts = sorted(
        {sv.source for sv in fields.values() if sv.populated}
        | ({record.status_source.source} if record.status_source.populated else set())
    )
    return {
        "generation_id": record.generation_id,
        "surrogate_detection_rate": float(fields["surrogate_detection_rate"].value),
        "heldout_detection_rate": float(fields["heldout_detection_rate"].value),
        "decision": fields["decision"].value,
        "recorded_utc": fields["recorded_utc"].value,
        "source_artifacts": {path: _artifact_sha(record, path) for path in artifacts},
    }


def _artifact_sha(record: GenerationRecord, path: str) -> str:
    for sv in list(record.fields.values()) + [record.status_source]:
        if sv.source == path:
            return sv.sha256
    raise ValueError(f"no provenance for artifact {path!r}")


def figure_scaffolds_populated(
    records: Sequence[GenerationRecord] = (),
) -> list[dict[str, Any]]:
    """Figure scaffolds with closed-generation data populated deterministically.

    F1 (transfer scatter) and F2 (generation timeline) gain one data point per
    closed generation record; each point carries ``source_artifacts`` mapping
    the committed evidence path to its SHA-256. All other figures keep
    ``status: "awaiting_data"`` with an empty ``data`` array.
    """
    closed = [r for r in records if r.status == "closed"]
    closed.sort(key=lambda r: r.generation_id)
    points = [_closed_figure_point(record) for record in closed]
    scaffolds = []
    for scaffold in figure_scaffolds():
        scaffold = dict(scaffold)
        if scaffold["figure_id"] == "F1" and points:
            scaffold["status"] = "populated"
            scaffold["data"] = [
                {
                    "generation_id": p["generation_id"],
                    "x": p["surrogate_detection_rate"],
                    "y": p["heldout_detection_rate"],
                    "color": p["decision"].lower(),
                    "source_artifacts": p["source_artifacts"],
                }
                for p in points
            ]
        elif scaffold["figure_id"] == "F2" and points:
            scaffold["status"] = "populated"
            scaffold["data"] = [
                {
                    "generation_id": p["generation_id"],
                    "x": p["recorded_utc"],
                    "y": p["heldout_detection_rate"],
                    "series": p["generation_id"],
                    "source_artifacts": p["source_artifacts"],
                }
                for p in points
            ]
        scaffolds.append(scaffold)
    return scaffolds


def write_figure_scaffolds_populated(
    directory: str | Path,
    *,
    repo_root: str | Path,
) -> list[Path]:
    """Write populated figure scaffolds (byte-identical across runs)."""
    records = load_committed_generation_records(repo_root)
    scaffolds = figure_scaffolds_populated(records)
    slugs = _figure_slugs()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scaffold in scaffolds:
        path = directory / f"{scaffold['figure_id']}_{slugs[scaffold['figure_id']]}.json"
        path.write_text(_canonical_json(scaffold))
        written.append(path)
    return written

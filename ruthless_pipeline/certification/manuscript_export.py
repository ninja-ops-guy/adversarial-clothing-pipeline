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
import io
import json
import re
from dataclasses import dataclass
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
                {
                    "producer": _TELEMETRY_PRODUCER,
                    "artifact": _TELEMETRY_ARTIFACT,
                    "fields": [
                        "pre.candidate_sha256",
                        "pre.surrogate_mean_detection_rate",
                        "outcome.heldout_detection_rates",
                        "outcome.verdict",
                    ],
                }
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
                {
                    "producer": _EXPERIMENT_PRODUCER,
                    "artifact": "experiment.json (release dir root)",
                    "fields": ["experiment_id", "generation_id", "created_utc", "evidence_label"],
                },
                {
                    "producer": _TELEMETRY_PRODUCER,
                    "artifact": _TELEMETRY_ARTIFACT,
                    "fields": ["outcome.heldout_detection_rates", "outcome.recorded_utc"],
                },
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
                {
                    "producer": _TELEMETRY_PRODUCER,
                    "artifact": _TELEMETRY_ARTIFACT,
                    "fields": [
                        "pre.candidate_sha256",
                        "pre.cross_model_disagreement.variance",
                        "pre.cross_model_disagreement.spread",
                        "pre.cross_model_disagreement.max_pairwise_delta",
                    ],
                }
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
                {
                    "producer": _FAILURE_TAXONOMY_PRODUCER,
                    "artifact": "failure-classification metrics bundle per closed experiment",
                    "fields": ["transformation_rates"],
                },
                {
                    "producer": _TELEMETRY_PRODUCER,
                    "artifact": _TELEMETRY_ARTIFACT,
                    "fields": ["pre.transformation_sweep_variance"],
                },
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
                {
                    "producer": _OBJECTIVE_TELEMETRY_PRODUCER,
                    "artifact": _OBJECTIVE_TELEMETRY_ARTIFACT,
                    "fields": [
                        "objective.name",
                        "objective.alpha",
                        "checkpoints[].checkpoint",
                        "checkpoints[].candidate_id",
                        "checkpoints[].losses.mean",
                        "checkpoints[].losses.cvar",
                        "checkpoints[].losses.worst_model",
                    ],
                }
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
                {
                    "producer": _OBJECTIVE_TELEMETRY_PRODUCER,
                    "artifact": _OBJECTIVE_TELEMETRY_ARTIFACT,
                    "fields": [
                        "checkpoints[].checkpoint",
                        "checkpoints[].cvar_tail.alpha",
                        "checkpoints[].cvar_tail.k",
                        "checkpoints[].cvar_tail.member_ids",
                        "checkpoints[].tail_turnover.entered",
                        "checkpoints[].tail_turnover.left",
                    ],
                }
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
                {
                    "producer": _OBJECTIVE_TELEMETRY_PRODUCER,
                    "artifact": _OBJECTIVE_TELEMETRY_ARTIFACT,
                    "fields": [
                        "checkpoints[].checkpoint",
                        "checkpoints[].candidate_id",
                        "checkpoints[].candidate_ranks.<candidate_id>.mean_rank",
                        "checkpoints[].candidate_ranks.<candidate_id>.cvar_rank",
                        "checkpoints[].candidate_ranks.<candidate_id>.rank_delta",
                    ],
                }
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
                {
                    "producer": _PAIRED_STATS_PRODUCER,
                    "artifact": "paper5_comparison.json (this module) / sealed paired-arm statistics JSON",
                    "fields": [
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
                }
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


def write_figure_scaffolds(directory: str | Path) -> list[Path]:
    """Write the eight scaffolds as canonical JSON into ``directory``.

    Filenames: ``<figure_id>_<slug>.json`` (e.g. ``F1_transfer_scatter.json``).
    """
    slugs = {
        "F1": "transfer_scatter",
        "F2": "generation_timeline",
        "F3": "architecture_disagreement",
        "F4": "transformation_robustness",
        "F5": "objective_trajectories",
        "F6": "cvar_tail_turnover",
        "F7": "mean_vs_cvar_rank_changes",
        "F8": "paired_arm_outcome",
    }
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scaffold in figure_scaffolds():
        path = directory / f"{scaffold['figure_id']}_{slugs[scaffold['figure_id']]}.json"
        path.write_text(_canonical_json(scaffold))
        written.append(path)
    return written

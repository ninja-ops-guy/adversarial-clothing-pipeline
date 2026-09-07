"""Automated experiment-report compiler for physical certification results.

Consumes an experiment bundle (plain dict) and emits the complete documented
result: per-condition tables, Wilson confidence intervals, invalid-condition
accounting, figure specifications (specs only, no rendering), a Markdown
results section, and manuscript-ready booktabs table rows.

Guardrails mirror the preregistration governance of the pipeline:
- invalid trials (control garment undetected) never count as candidate
  success and are accounted explicitly per condition,
- conditions with invalid fraction > 0.10 are flagged,
- the preregistration hash must be a 64-hex SHA-256 string,
- the experiment id must match RAC-EXP-YYYY-NNN.

Statistics are delegated to certification.trial_statistics.paired_trial_statistics
and certification.statistics.wilson_interval; nothing is reimplemented here.
Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .physical import PhysicalTrial
from .statistics import wilson_interval
from .trial_statistics import (
    PairedTrialStatistics,
    invalid_condition_report,
    paired_trial_statistics,
    split_valid_invalid,
)

INVALID_FRACTION_FLAG = 0.10
EXPERIMENT_ID_RE = re.compile(r"^RAC-EXP-\d{4}-\d{3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_TRIAL_FIELDS = (
    "trial_id",
    "condition_id",
    "control_detected",
    "candidate_detected",
    "camera_id",
    "distance_m",
    "yaw_deg",
    "pitch_deg",
    "pose",
    "lighting_id",
    "wash_state",
    "metadata",
)


@dataclass(frozen=True)
class ConditionResult:
    """Per-condition statistics and accounting."""

    condition_id: str
    valid_trials: int
    invalid_trials: int
    control_rate: float
    candidate_rate: float
    wilson_interval: tuple[float, float]
    risk_difference: float
    notes: tuple[str, ...] = ()

    @property
    def invalid_fraction(self) -> float:
        total = self.valid_trials + self.invalid_trials
        return self.invalid_trials / total if total else 0.0

    @property
    def flagged(self) -> bool:
        return self.invalid_fraction > INVALID_FRACTION_FLAG


@dataclass(frozen=True)
class CompiledReport:
    """Complete documented result for one experiment bundle."""

    experiment_id: str
    hypothesis_id: str
    generation_id: str
    evidence_label: str
    preregistration_sha256: str
    artifact_hashes: tuple[tuple[str, str], ...]
    conditions: tuple[ConditionResult, ...]
    overall: PairedTrialStatistics
    total_trials: int
    valid_trials: int
    invalid_trials: int

    # -- serialisation ---------------------------------------------------

    def summary_dict(self) -> dict:
        """JSON-able summary: ids, prereg hash, rates + CIs, invalid accounting."""
        return {
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "generation_id": self.generation_id,
            "evidence_label": self.evidence_label,
            "preregistration_sha256": self.preregistration_sha256,
            "artifact_hashes": dict(self.artifact_hashes),
            "total_trials": self.total_trials,
            "valid_trials": self.valid_trials,
            "invalid_trials": self.invalid_trials,
            "overall": {
                "control_detection_rate": self.overall.control_detection_rate,
                "candidate_detection_rate": self.overall.candidate_detection_rate,
                "control_wilson_interval": list(self.overall.control_interval),
                "candidate_wilson_interval": list(self.overall.candidate_interval),
                "risk_difference": self.overall.risk_difference,
                "risk_difference_interval": list(self.overall.risk_difference_interval),
                "odds_ratio": self.overall.odds_ratio,
            },
            "conditions": [
                {
                    "condition_id": c.condition_id,
                    "valid_trials": c.valid_trials,
                    "invalid_trials": c.invalid_trials,
                    "invalid_fraction": c.invalid_fraction,
                    "control_rate": c.control_rate,
                    "candidate_rate": c.candidate_rate,
                    "wilson_interval": list(c.wilson_interval),
                    "risk_difference": c.risk_difference,
                    "flagged_invalid_fraction": c.flagged,
                    "notes": list(c.notes),
                }
                for c in self.conditions
            ],
        }

    # -- manuscript outputs ----------------------------------------------

    def markdown(self) -> str:
        """A complete ## Results section with per-condition table and accounting."""
        lines: list[str] = []
        lines.append("## Results")
        lines.append("")
        lines.append(
            f"Experiment {self.experiment_id} (hypothesis {self.hypothesis_id}, "
            f"generation {self.generation_id}; evidence label: {self.evidence_label}) "
            f"was analysed under preregistration "
            f"`{self.preregistration_sha256[:12]}...` (SHA-256). "
            f"Of {self.total_trials} recorded trials, {self.valid_trials} were valid "
            f"(control garment detected) and {self.invalid_trials} were invalid. "
            "Detection rates are reported with 95% Wilson score intervals; "
            "invalid trials never count as candidate success."
        )
        lines.append("")
        lines.append(
            "| Condition | Valid | Invalid | Control rate | Candidate rate | "
            "Candidate 95% Wilson CI | Risk difference |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for c in self.conditions:
            lo, hi = c.wilson_interval
            lines.append(
                f"| {c.condition_id} | {c.valid_trials} | {c.invalid_trials} | "
                f"{c.control_rate:.3f} | {c.candidate_rate:.3f} | "
                f"[{lo:.3f}, {hi:.3f}] | {c.risk_difference:.3f} |"
            )
        o = self.overall
        lines.append(
            f"| **Overall** | {o.valid_trials} | {self.invalid_trials} | "
            f"{o.control_detection_rate:.3f} | {o.candidate_detection_rate:.3f} | "
            f"[{o.candidate_interval[0]:.3f}, {o.candidate_interval[1]:.3f}] | "
            f"{o.risk_difference:.3f} |"
        )
        lines.append("")
        # Invalid-condition accounting paragraph.
        flagged = [c for c in self.conditions if c.flagged]
        lines.append(
            f"Invalid-condition accounting: {self.invalid_trials} of {self.total_trials} "
            "trials were invalid because the control garment was not detected; these "
            "trials were excluded from all rate estimates and never counted as "
            "candidate success."
        )
        if flagged:
            ids = ", ".join(
                f"{c.condition_id} (invalid fraction {c.invalid_fraction:.3f})" for c in flagged
            )
            lines.append(
                f"The following conditions exceeded the preregistered invalid-fraction "
                f"threshold of {INVALID_FRACTION_FLAG:.2f} and are flagged: {ids}. "
                "Results for these conditions should be interpreted with caution."
            )
        else:
            lines.append(
                f"No condition exceeded the preregistered invalid-fraction threshold "
                f"of {INVALID_FRACTION_FLAG:.2f}."
            )
        lines.append("")
        # Limitations paragraph auto-generated from flags.
        limitations: list[str] = []
        if flagged:
            limitations.append(
                "conditions flagged for high invalid fraction may suffer from "
                "systematic measurement conditions not representative of deployment"
            )
        zero_valid = [c.condition_id for c in self.conditions if c.valid_trials == 0]
        if zero_valid:
            limitations.append(
                "conditions with zero valid trials (" + ", ".join(zero_valid) + ") "
                "contribute no rate estimates"
            )
        if self.invalid_trials:
            limitations.append(
                "invalid trials reduce effective sample size and may bias toward "
                "easier measurement conditions"
            )
        if not limitations:
            limitations.append("no condition-level anomalies were detected")
        lines.append(
            "Limitations: " + "; ".join(limitations) + ". All intervals are Wilson "
            "score intervals at 95% confidence; the paired risk-difference interval "
            "uses a deterministic-seed bootstrap fixed by the preregistration."
        )
        lines.append("")
        return "\n".join(lines)

    def latex_rows(self) -> list[str]:
        """Booktabs-style per-condition rows: condition & valid & control% & candidate% & CI \\."""
        rows: list[str] = []
        for c in self.conditions:
            lo, hi = c.wilson_interval
            rows.append(
                f"{c.condition_id} & {c.valid_trials} & "
                f"{100 * c.control_rate:.1f}\\% & {100 * c.candidate_rate:.1f}\\% & "
                f"[{lo:.3f}, {hi:.3f}] \\\\"
            )
        return rows

    def figure_specs(self) -> list[dict]:
        """Figure specifications to be rendered elsewhere (no rendering here)."""
        data_ref = f"{self.experiment_id}/compiled-conditions.json"
        return [
            {
                "figure_id": "fig-rates-by-condition",
                "type": "forest_plot",
                "data_ref": data_ref,
                "x": "candidate_rate",
                "interval": "wilson_interval",
                "group_by": "condition_id",
                "caption": (
                    "Candidate detection rate by condition with 95% Wilson score "
                    "intervals; invalid trials excluded."
                ),
            },
            {
                "figure_id": "fig-invalid-fraction",
                "type": "bar_chart",
                "data_ref": data_ref,
                "x": "condition_id",
                "y": "invalid_fraction",
                "threshold": INVALID_FRACTION_FLAG,
                "caption": (
                    f"Invalid-trial fraction per condition; dashed line at the "
                    f"preregistered flag threshold {INVALID_FRACTION_FLAG:.2f}."
                ),
            },
            {
                "figure_id": "fig-risk-difference",
                "type": "forest_plot",
                "data_ref": data_ref,
                "x": "risk_difference",
                "group_by": "condition_id",
                "caption": (
                    "Paired risk difference (control minus candidate detection "
                    "rate) by condition."
                ),
            },
        ]


def _trial_from_dict(raw: dict) -> PhysicalTrial:
    kwargs = {k: raw[k] for k in _TRIAL_FIELDS if k in raw}
    return PhysicalTrial(**kwargs)


def compile_report(bundle: dict) -> CompiledReport:
    """Compile an experiment bundle into a complete documented report.

    The bundle must contain: experiment_id, hypothesis_id, generation_id,
    trials (list of dicts matching PhysicalTrial fields), conditions metadata,
    evidence_label, preregistration_sha256, artifact_hashes.
    """
    experiment_id = bundle.get("experiment_id", "")
    if not EXPERIMENT_ID_RE.match(experiment_id):
        raise ValueError(f"malformed experiment_id {experiment_id!r}: expected RAC-EXP-YYYY-NNN")
    prereg = bundle.get("preregistration_sha256", "")
    if not SHA256_RE.match(prereg):
        raise ValueError("preregistration_sha256 must be a 64-character hex string")
    raw_trials = bundle.get("trials") or []
    if not raw_trials:
        raise ValueError("experiment bundle contains no trials")

    trials = [_trial_from_dict(raw) for raw in raw_trials]
    valid, invalid = split_valid_invalid(trials)
    accounting = invalid_condition_report(trials)
    overall = paired_trial_statistics(trials)

    condition_ids = sorted({t.condition_id for t in trials})
    conditions: list[ConditionResult] = []
    for cid in condition_ids:
        cid_valid = [t for t in valid if t.condition_id == cid]
        cid_invalid = accounting.invalid_by_condition.get(cid, 0)
        cid_total = accounting.total_by_condition[cid]
        notes: list[str] = []
        if cid_valid:
            stats = paired_trial_statistics(cid_valid)
            candidate_rate = stats.candidate_detection_rate
            candidate_hits = sum(t.candidate_detected for t in cid_valid)
            interval = wilson_interval(candidate_hits, len(cid_valid))
            risk_difference = stats.risk_difference
        else:
            # No valid trials: no rate estimates; the condition still counts
            # toward invalid accounting. Never treat invalid trials as success.
            candidate_rate = 0.0
            interval = (0.0, 1.0)
            risk_difference = 1.0
            notes.append("no valid trials; control garment never detected")
        invalid_fraction = cid_invalid / cid_total
        if invalid_fraction > INVALID_FRACTION_FLAG:
            notes.append(
                f"invalid fraction {invalid_fraction:.3f} exceeds flag threshold "
                f"{INVALID_FRACTION_FLAG:.2f}"
            )
        conditions.append(
            ConditionResult(
                condition_id=cid,
                valid_trials=len(cid_valid),
                invalid_trials=cid_invalid,
                control_rate=1.0 if cid_valid else 0.0,
                candidate_rate=candidate_rate,
                wilson_interval=interval,
                risk_difference=risk_difference,
                notes=tuple(notes),
            )
        )

    artifact_hashes = tuple(sorted((bundle.get("artifact_hashes") or {}).items()))
    return CompiledReport(
        experiment_id=experiment_id,
        hypothesis_id=bundle.get("hypothesis_id", ""),
        generation_id=bundle.get("generation_id", ""),
        evidence_label=bundle.get("evidence_label", ""),
        preregistration_sha256=prereg,
        artifact_hashes=artifact_hashes,
        conditions=tuple(conditions),
        overall=overall,
        total_trials=len(trials),
        valid_trials=len(valid),
        invalid_trials=len(invalid),
    )

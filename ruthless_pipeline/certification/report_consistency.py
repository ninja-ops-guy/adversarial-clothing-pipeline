"""NR-05 — Reports derived from one evidence snapshot (additive, fail-closed).

Basis: RAC evidence-register rules (``docs/RESEARCH_EVIDENCE_REGISTER.md``)
and the report-compilation architecture (``report_compiler.py``,
``manuscript_export.py``). NORECOGNITION review NR-05: tables, narrative
summaries, and counts must be generated from the same *versioned evidence
view*, and the view must display numerator, denominator, eligibility rules,
cohort, specimen, measurement medium, metric definition, and source
version. Evaluations, independent participants, experimental runs, and
retained observations are counted in separate fields — never merged.

Hard rules (fail closed with :class:`ReportConsistencyError`):

- Every block of a checked report (table / narrative / counts) must carry
  the report's ``evidence_view_sha256``, which must equal the supplied
  :class:`EvidenceView` content hash — one snapshot, no mixing.
- Fraction/percentage pairs must agree (``percent == 100 * fraction``);
  numerator/denominator must reproduce the fraction. Any inconsistency
  fails the check.
- A summary row aggregating more than one source row must carry an
  explicit ``aggregation_method`` label. ``selection: "best"`` rows must
  retain ``selection_history``; choosing a ``median`` aggregation does not
  erase that requirement (selection bias is retained, not described away).
- Rows whose ``evidence_class`` is external (``external_*``) never enter
  internal totals; if external rows are present the block must declare
  ``external_observations_excluded: true`` and any declared totals must
  match the sum over internal rows only.

This module adds checks only; it mutates no frozen artifact and promotes
no synthetic evidence to measured.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

EVIDENCE_VIEW_SCHEMA_VERSION = "rac-evidence-view/1.0"
CHECKED_REPORT_SCHEMA_VERSION = "rac-consistency-checked-report/1.0"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "rac_evidence_view_v1.schema.json"
)

#: Separate count fields (NR-05(c)); merging them is refused by schema.
COUNT_FIELDS = (
    "n_evaluations",
    "n_independent_participants",
    "n_experimental_runs",
    "n_retained_observations",
)

#: Block types that must all derive from the one evidence snapshot.
BLOCK_TYPES = frozenset({"table", "narrative", "counts"})

#: Explicit aggregation labels permitted on summary rows.
AGGREGATION_METHODS = frozenset({"mean", "median", "min", "max", "sum"})

#: Tolerance for fraction/percentage and numerator/denominator agreement.
_TOL = 1e-9


class ReportConsistencyError(ValueError):
    """NR-05 report-consistency check failed. Fail closed."""


def _is_external(evidence_class: Any) -> bool:
    return isinstance(evidence_class, str) and (
        evidence_class == "external_physical_observation"
        or evidence_class.startswith("external_")
    )


@dataclass(frozen=True)
class EvidenceView:
    """One versioned evidence view: the single snapshot a report derives from.

    Carries the display fields NR-05(b) requires and the separated count
    fields NR-05(c) requires. Hash-pinned via :meth:`content_sha256`.
    """

    view_id: str
    source_version: str
    eligibility_rules: str
    cohort_id: str
    specimen_id: str
    measurement_medium: str
    metric_definition: str
    evidence_label: str
    counts: Mapping[str, int] = field(default_factory=dict)
    schema_version: str = EVIDENCE_VIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_VIEW_SCHEMA_VERSION:
            raise ReportConsistencyError(
                f"unsupported evidence-view schema_version: {self.schema_version!r}"
            )
        for name in (
            "view_id", "source_version", "eligibility_rules", "cohort_id",
            "specimen_id", "measurement_medium", "metric_definition",
            "evidence_label",
        ):
            if not getattr(self, name):
                raise ReportConsistencyError(f"{name} is required on an evidence view")
        keys = set(self.counts)
        if keys != set(COUNT_FIELDS):
            raise ReportConsistencyError(
                f"counts must contain exactly {sorted(COUNT_FIELDS)}; got "
                f"{sorted(keys)}: evaluations, participants, runs, and "
                "retained observations are counted separately (fail closed)"
            )
        for name, value in self.counts.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ReportConsistencyError(
                    f"count {name} must be a non-negative integer, got {value!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "view_id": self.view_id,
            "source_version": self.source_version,
            "eligibility_rules": self.eligibility_rules,
            "cohort_id": self.cohort_id,
            "specimen_id": self.specimen_id,
            "measurement_medium": self.measurement_medium,
            "metric_definition": self.metric_definition,
            "evidence_label": self.evidence_label,
            "counts": {k: self.counts[k] for k in COUNT_FIELDS},
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def content_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise ReportConsistencyError(
                f"evidence view fails rac_evidence_view_v1 schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidenceView":
        if not isinstance(payload, Mapping):
            raise ReportConsistencyError("evidence view payload must be an object")
        return cls(
            view_id=payload.get("view_id", ""),
            source_version=payload.get("source_version", ""),
            eligibility_rules=payload.get("eligibility_rules", ""),
            cohort_id=payload.get("cohort_id", ""),
            specimen_id=payload.get("specimen_id", ""),
            measurement_medium=payload.get("measurement_medium", ""),
            metric_definition=payload.get("metric_definition", ""),
            evidence_label=payload.get("evidence_label", ""),
            counts=dict(payload.get("counts", {})),
            schema_version=payload.get("schema_version", ""),
        )


def _check_row(row: Mapping[str, Any], *, where: str) -> None:
    if not isinstance(row, Mapping):
        raise ReportConsistencyError(f"{where}: row must be an object")
    # NR-05 acceptance: inconsistent fraction/percentage pairs fail.
    if "fraction" in row and "percent" in row:
        fraction = float(row["fraction"])
        percent = float(row["percent"])
        if not (math.isfinite(fraction) and math.isfinite(percent)):
            raise ReportConsistencyError(f"{where}: non-finite fraction/percent")
        if abs(percent - 100.0 * fraction) > _TOL:
            raise ReportConsistencyError(
                f"{where}: inconsistent fraction/percentage pair "
                f"(fraction={fraction!r}, percent={percent!r})"
            )
    # Numerator/denominator must reproduce the fraction when all are shown.
    if "fraction" in row and "numerator" in row and "denominator" in row:
        numerator = float(row["numerator"])
        denominator = float(row["denominator"])
        if denominator <= 0:
            raise ReportConsistencyError(
                f"{where}: fraction shown with denominator {denominator!r}"
            )
        if abs(float(row["fraction"]) - numerator / denominator) > _TOL:
            raise ReportConsistencyError(
                f"{where}: fraction {row['fraction']!r} does not equal "
                f"numerator/denominator ({numerator!r}/{denominator!r})"
            )
    # NR-05 acceptance: differing aggregation methods require explicit labels.
    aggregates_n = row.get("aggregates_n")
    if aggregates_n is not None:
        if isinstance(aggregates_n, bool) or not isinstance(aggregates_n, int) or aggregates_n < 1:
            raise ReportConsistencyError(f"{where}: aggregates_n must be a positive integer")
        if aggregates_n > 1 and row.get("aggregation_method") not in AGGREGATION_METHODS:
            raise ReportConsistencyError(
                f"{where}: summary row aggregates {aggregates_n} source rows "
                f"without an explicit aggregation_method label "
                f"(allowed: {sorted(AGGREGATION_METHODS)})"
            )
    # NR-05 acceptance: selected-best results retain selection history; a
    # median aggregation improves description but never erases selection bias.
    if row.get("selection") == "best":
        history = row.get("selection_history")
        if not isinstance(history, list) or not history:
            raise ReportConsistencyError(
                f"{where}: selected-best row must retain a non-empty "
                "selection_history (fail closed)"
            )


def check_report_consistency(
    report: Mapping[str, Any], view: EvidenceView
) -> list[str]:
    """Return consistency violations of ``report`` against ``view``.

    Empty list = consistent. See :func:`require_report_consistent` for the
    fail-closed variant.
    """
    violations: list[str] = []
    if not isinstance(report, Mapping):
        return ["report must be an object"]
    view.validate_against_schema()
    expected_pin = view.content_sha256()
    if report.get("schema_version") != CHECKED_REPORT_SCHEMA_VERSION:
        violations.append(
            f"report schema_version must be {CHECKED_REPORT_SCHEMA_VERSION!r}"
        )
    # NR-05(a): one versioned evidence view for the whole report.
    if report.get("evidence_view_sha256") != expected_pin:
        violations.append(
            "report evidence_view_sha256 does not match the supplied evidence "
            "view: tables, narrative, and counts must derive from one "
            "versioned snapshot"
        )
    blocks = report.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        violations.append("report must contain a non-empty 'blocks' list")
        return violations
    for i, block in enumerate(blocks):
        where = f"block[{i}]"
        if not isinstance(block, Mapping):
            violations.append(f"{where}: block must be an object")
            continue
        where = f"block[{i}]({block.get('block_id', '<no-id>')})"
        if block.get("block_type") not in BLOCK_TYPES:
            violations.append(
                f"{where}: block_type must be one of {sorted(BLOCK_TYPES)}"
            )
        if block.get("evidence_view_sha256") != expected_pin:
            violations.append(
                f"{where}: block does not carry the report's evidence-view "
                "hash: mixed evidence snapshots are refused"
            )
        rows = block.get("rows", [])
        if not isinstance(rows, list):
            violations.append(f"{where}: rows must be a list")
            continue
        for j, row in enumerate(rows):
            try:
                _check_row(row, where=f"{where} row[{j}]")
            except ReportConsistencyError as exc:
                violations.append(str(exc))
        # NR-05 acceptance: external observations never enter internal totals.
        external_present = any(
            isinstance(r, Mapping) and _is_external(r.get("evidence_class"))
            for r in rows
        )
        if external_present and block.get("external_observations_excluded") is not True:
            violations.append(
                f"{where}: external-observation rows present but the block "
                "does not declare external_observations_excluded: true"
            )
        totals = block.get("totals")
        if totals is not None:
            if not isinstance(totals, Mapping) or "value" not in totals:
                violations.append(f"{where}: totals must be an object with 'value'")
            else:
                internal_sum = sum(
                    float(r.get("value", 0.0))
                    for r in rows
                    if isinstance(r, Mapping)
                    and not _is_external(r.get("evidence_class"))
                    and isinstance(r.get("value"), (int, float))
                    and not isinstance(r.get("value"), bool)
                )
                if abs(float(totals["value"]) - internal_sum) > _TOL:
                    violations.append(
                        f"{where}: declared total {totals['value']!r} does not "
                        f"equal the internal-row sum {internal_sum!r}: external "
                        "observations never enter internal totals"
                    )
    return violations


def require_report_consistent(
    report: Mapping[str, Any], view: EvidenceView
) -> None:
    """Fail-closed variant of :func:`check_report_consistency`."""
    violations = check_report_consistency(report, view)
    if violations:
        raise ReportConsistencyError(
            "report failed NR-05 consistency checks: " + "; ".join(violations)
        )

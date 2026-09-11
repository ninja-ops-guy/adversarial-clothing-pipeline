"""SW-13: Simulation <-> Measurement Discrepancy Layer.

Neutral prediction/observation comparison contract, additive to the existing
calibration modules (``certification.calibration*``). The framework operates
fully BEFORE any measured data exists: comparisons may carry only the
predicted side. A comparison without a measured counterpart is always
evidence_class ``synthetic_pipeline_validation_only`` and can never be
promoted to physical evidence (:class:`PromotionImpossibleError`).

Rules:
- Residuals are computed ONLY when a measured counterpart is supplied;
  they are never fabricated.
- Calibration-set and evaluation-set roles are disjoint across the same
  metric + simulator identity (:class:`LeakageError`).
- Sealed comparisons are immutable: a simulator version string, once used in
  a sealed comparison, cannot be rebound to different simulator content
  (:class:`SchemaFrozenError`).
- Deterministic: comparison ids are content-addressed via
  ``pattern_genome.canonical``; no wall-clock, no RNG.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from ruthless_pipeline.certification.schema_version import require_schema_version
from ruthless_pipeline.future_evidence.errors import (
    LeakageError,
    MeasuredFlagAbsentError,
    PromotionImpossibleError,
    SchemaFrozenError,
)

SCHEMA_VERSION = "rac-sim-measure-discrepancy/1.0"
SCHEMA_ID = "https://rac.local/schemas/sim_measure_discrepancy_v1.schema.json"

SYNTHETIC_EVIDENCE_CLASS = "synthetic_pipeline_validation_only"
MEASURED_EVIDENCE_CLASS = "measured_physical_capture"

_ID_PREFIX = "RAC-DISC-"


def comparison_id(record: Dict[str, Any]) -> str:
    d = dict(record)
    d.pop("comparison_id", None)
    return _ID_PREFIX + sha256_bytes(canonical_json(d))[:16]


@dataclass(frozen=True)
class DiscrepancyComparison:
    """One neutral prediction/observation comparison.

    ``measured_distribution`` is Optional: None means "not yet supplied".
    ``simulator_content_sha256`` binds the exact simulator build/content so a
    version label can never be silently reused for different code.
    """

    schema_version: str
    simulator_id: str
    simulator_version: str
    simulator_content_sha256: str
    metric_name: str
    predicted_distribution: Tuple[float, ...]
    measured_distribution: Optional[Tuple[float, ...]]
    uncertainty: Optional[Dict[str, float]]
    calibration_set_ref: Optional[str]
    evaluation_set_ref: Optional[str]
    evidence_class: str = SYNTHETIC_EVIDENCE_CLASS

    def to_record(self) -> Dict[str, Any]:
        residual: Optional[List[float]] = None
        if self.measured_distribution is not None:
            if len(self.measured_distribution) != len(self.predicted_distribution):
                raise MeasuredFlagAbsentError(
                    "measured distribution length mismatch; refusing to fabricate a residual"
                )
            residual = [
                m - p
                for p, m in zip(self.predicted_distribution, self.measured_distribution)
            ]
        rec: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "simulator_id": self.simulator_id,
            "simulator_version": self.simulator_version,
            "simulator_content_sha256": self.simulator_content_sha256,
            "metric_name": self.metric_name,
            "predicted_distribution": list(self.predicted_distribution),
            "measured_distribution": (
                list(self.measured_distribution)
                if self.measured_distribution is not None
                else None
            ),
            "residual": residual,
            "uncertainty": dict(self.uncertainty) if self.uncertainty else None,
            "calibration_set_ref": self.calibration_set_ref,
            "evaluation_set_ref": self.evaluation_set_ref,
            "evidence_class": self.evidence_class,
        }
        rec["comparison_id"] = comparison_id(rec)
        return rec


class DiscrepancyRegistry:
    """Registry of sealed comparisons with immutability + leakage guards."""

    def __init__(self) -> None:
        self._sealed: Dict[str, Dict[str, Any]] = {}
        # simulator_version -> simulator_content_sha256 (immutable once sealed)
        self._version_pin: Dict[Tuple[str, str], str] = {}

    def _validate(self, comp: DiscrepancyComparison) -> Dict[str, Any]:
        require_schema_version(
            {"schema_version": comp.schema_version},
            SCHEMA_VERSION,
            label=f"discrepancy comparison {comp.metric_name!r}",
        )
        if comp.measured_distribution is None and (
            comp.evidence_class != SYNTHETIC_EVIDENCE_CLASS
        ):
            raise PromotionImpossibleError(
                "comparison without measured counterpart must remain "
                f"{SYNTHETIC_EVIDENCE_CLASS!r}; promotion impossible"
            )
        if comp.measured_distribution is not None and (
            comp.evidence_class != MEASURED_EVIDENCE_CLASS
        ):
            raise PromotionImpossibleError(
                "comparison with measured counterpart requires evidence_class "
                f"{MEASURED_EVIDENCE_CLASS!r}; synthetic cannot be promoted"
            )
        if (
            comp.calibration_set_ref
            and comp.evaluation_set_ref
            and comp.calibration_set_ref == comp.evaluation_set_ref
        ):
            raise LeakageError(
                "calibration_set_ref == evaluation_set_ref: set leakage rejected"
            )
        return comp.to_record()

    def seal(self, comp: DiscrepancyComparison) -> Dict[str, Any]:
        rec = self._validate(comp)
        cid = rec["comparison_id"]
        if cid in self._sealed:
            raise SchemaFrozenError(f"comparison {cid} already sealed; immutable")
        key = (rec["simulator_id"], rec["simulator_version"])
        pinned = self._version_pin.get(key)
        if pinned is not None and pinned != rec["simulator_content_sha256"]:
            raise SchemaFrozenError(
                f"simulator version {key[0]}@{key[1]} is already sealed against "
                f"content {pinned[:12]}...; versions are immutable once used in a "
                "sealed comparison"
            )
        # Calibration/evaluation leakage across sealed comparisons for the
        # same simulator + metric.
        for other in self._sealed.values():
            if (
                other["simulator_id"] == rec["simulator_id"]
                and other["metric_name"] == rec["metric_name"]
            ):
                for a, b in (
                    ("calibration_set_ref", "evaluation_set_ref"),
                    ("evaluation_set_ref", "calibration_set_ref"),
                ):
                    if rec[a] and rec[a] == other[b]:
                        raise LeakageError(
                            f"set {rec[a]!r} used as {a} here but as {b} in sealed "
                            f"comparison {other['comparison_id']}: leakage rejected"
                        )
        self._version_pin[key] = rec["simulator_content_sha256"]
        self._sealed[cid] = rec
        return rec

    def promote_to_physical_evidence(self, comparison_id_: str) -> None:
        """Always refuses: this layer can never promote synthetic comparisons."""
        raise PromotionImpossibleError(
            f"comparison {comparison_id_!r}: promotion of simulation/measurement "
            "comparisons to physical evidence is impossible from this layer; "
            "only future governance-ratified measured ingestion may reclassify"
        )

    def sealed(self) -> List[Dict[str, Any]]:
        return [self._sealed[k] for k in sorted(self._sealed)]

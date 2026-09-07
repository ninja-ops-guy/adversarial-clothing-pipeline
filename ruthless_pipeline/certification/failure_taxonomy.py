"""Rule-based failure taxonomy for adversarial-pattern experiment analysis.

Classifies failed candidate experiments into research-meaningful categories so
that, across generations, failures accumulate into a longitudinal "failure
atlas" dataset. The classifier is transparent and deterministic: no ML, only
thresholded signals evaluated against module-level audit constants.

Metrics dict keys recognised by classify_failure (all optional; missing keys
mean the corresponding rule cannot fire):

- baseline_detection_rate (float): detection rate of the unmodified control
  garment on the surrogate detector ensemble.
- surrogate_detection_rate (float): detection rate of the candidate on the
  surrogate detector ensemble it was optimised against.
- heldout_detection_rate (float): detection rate of the candidate on fresh,
  held-out detectors never seen during optimisation.
- heldout_same_family (bool): True when the held-out detectors share the
  surrogate architecture family; False for cross-architecture held-out sets.
- transformation_rates (sequence[float] or mapping[str, float]): candidate
  detection rates across the transformation sweep (viewpoint, scale, lighting,
  ...). The spread max-min measures fragility.
- wilson_interval (tuple[float, float]) or wilson_width (float): confidence
  interval for the primary suppression effect.
- effect_direction_consistent (bool): True when the point estimate suppresses
  detection in the intended direction.
- delta_e (float): colour error introduced by manufacturing (CIEDE2000 mean).
- scale_error (float): relative print scale deviation (|actual-nominal|/nominal).
- isp_margin_loss (float): suppression margin lost under camera ISP processing
  (surrogate margin minus post-ISP margin).
- deformation_score_drop (float): drop in suppression score under garment
  deformation (stretch/wrinkle/pose) relative to flat conditions.
- coverage_entropy (float): normalised entropy of the pattern coverage map;
  low entropy means coverage concentrated in too few regions.

Classification rules (evaluated in this fixed priority order; first match wins,
all matches are recorded as signals):

  1. OPTIMIZATION_FAILURE — surrogate_detection_rate >= baseline_detection_rate
     - OPTIMIZATION_TOLERANCE. The optimiser failed to suppress detection even
     on its own surrogate ensemble.
  2. SURROGATE_OVERFIT — surrogate suppressed by at least
     SURROGATE_SUPPRESSION_MIN below baseline, held-out detection rate within
     HELDOUT_HIGH_TOLERANCE of baseline (i.e. high), and heldout_same_family.
  3. CROSS_ARCHITECTURE_TRANSFER_FAILURE — same suppression/high-held-out
     conditions as rule 2 but held-out detectors are a different architecture
     family.
  4. TRANSFORMATION_FRAGILITY — max(transformation_rates) -
     min(transformation_rates) > TRANSFORMATION_SPREAD_MAX.
  5. MANUFACTURING_LOSS — delta_e > DELTA_E_MAX or scale_error >
     SCALE_ERROR_MAX.
  6. CAMERA_ISP_LOSS — isp_margin_loss > ISP_MARGIN_LOSS_MAX.
  7. DEFORMATION_FAILURE — deformation_score_drop > DEFORMATION_DROP_MAX.
  8. COVERAGE_FAILURE — coverage_entropy < COVERAGE_ENTROPY_MIN.
  9. STATISTICAL_INCONCLUSIVE — Wilson interval width > WILSON_WIDTH_MAX with
     effect_direction_consistent True.
 10. UNCLASSIFIED — no rule fired; confidence "low".

Confidence is "high" when exactly one rule fires, "medium" when several fire
(priority resolves the primary category), and "low" for UNCLASSIFIED.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping

# ---------------------------------------------------------------------------
# Auditable thresholds (module-level constants; change deliberately).
# ---------------------------------------------------------------------------

OPTIMIZATION_TOLERANCE = 0.02
SURROGATE_SUPPRESSION_MIN = 0.20
HELDOUT_HIGH_TOLERANCE = 0.10
TRANSFORMATION_SPREAD_MAX = 0.30
WILSON_WIDTH_MAX = 0.20
DELTA_E_MAX = 6.0
SCALE_ERROR_MAX = 0.03
ISP_MARGIN_LOSS_MAX = 0.15
DEFORMATION_DROP_MAX = 0.25
COVERAGE_ENTROPY_MIN = 0.60


class FailureCategory(str, Enum):
    OPTIMIZATION_FAILURE = "optimization_failure"
    SURROGATE_OVERFIT = "surrogate_overfit"
    CROSS_ARCHITECTURE_TRANSFER_FAILURE = "cross_architecture_transfer_failure"
    TRANSFORMATION_FRAGILITY = "transformation_fragility"
    MANUFACTURING_LOSS = "manufacturing_loss"
    CAMERA_ISP_LOSS = "camera_isp_loss"
    DEFORMATION_FAILURE = "deformation_failure"
    COVERAGE_FAILURE = "coverage_failure"
    STATISTICAL_INCONCLUSIVE = "statistical_inconclusive"
    UNCLASSIFIED = "unclassified"


# Fixed priority order; the first fired rule in this list wins.
PRIORITY_ORDER: tuple[FailureCategory, ...] = (
    FailureCategory.OPTIMIZATION_FAILURE,
    FailureCategory.SURROGATE_OVERFIT,
    FailureCategory.CROSS_ARCHITECTURE_TRANSFER_FAILURE,
    FailureCategory.TRANSFORMATION_FRAGILITY,
    FailureCategory.MANUFACTURING_LOSS,
    FailureCategory.CAMERA_ISP_LOSS,
    FailureCategory.DEFORMATION_FAILURE,
    FailureCategory.COVERAGE_FAILURE,
    FailureCategory.STATISTICAL_INCONCLUSIVE,
)


@dataclass(frozen=True)
class FailureSignal:
    name: str
    value: float
    detail: str

    def validate(self) -> None:
        if not self.name:
            raise ValueError("signal name is required")
        if not isinstance(self.value, (int, float)):
            raise ValueError("signal value must be numeric")


@dataclass(frozen=True)
class FailureRecord:
    record_id: str
    experiment_id: str
    generation_id: str
    category: FailureCategory
    signals: tuple[FailureSignal, ...]
    confidence: str  # "high" | "medium" | "low"
    explanation: str
    created_utc: str

    def validate(self) -> None:
        if not self.record_id or not self.experiment_id or not self.generation_id:
            raise ValueError("record_id, experiment_id and generation_id are required")
        if not isinstance(self.category, FailureCategory):
            raise ValueError("category must be a FailureCategory")
        if self.confidence not in {"high", "medium", "low"}:
            raise ValueError("confidence must be high, medium or low")
        if self.category is FailureCategory.UNCLASSIFIED and self.confidence != "low":
            raise ValueError("UNCLASSIFIED records must have low confidence")
        for signal in self.signals:
            signal.validate()

    def canonical_json(self) -> bytes:
        self.validate()
        payload = asdict(self)
        payload["category"] = self.category.value
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    def record_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json()).hexdigest()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _transformation_values(raw: Any) -> list[float]:
    if raw is None:
        return []
    if isinstance(raw, Mapping):
        return [float(v) for v in raw.values()]
    return [float(v) for v in raw]


def _wilson_width(metrics: dict) -> float | None:
    if "wilson_width" in metrics and metrics["wilson_width"] is not None:
        return float(metrics["wilson_width"])
    interval = metrics.get("wilson_interval")
    if interval is not None:
        lo, hi = interval
        return float(hi) - float(lo)
    return None


def classify_failure(
    metrics: dict,
    *,
    experiment_id: str = "",
    generation_id: str = "",
    record_id: str | None = None,
    created_utc: str | None = None,
) -> FailureRecord:
    """Classify a failed experiment from its metric dict.

    See the module docstring for the full rule list, thresholds and priority
    order. Rules that cannot be evaluated (missing metrics) simply do not fire.
    All fired rules contribute FailureSignals; the primary category is the
    highest-priority fired rule.
    """
    fired: list[tuple[FailureCategory, list[FailureSignal], str]] = []

    baseline = metrics.get("baseline_detection_rate")
    surrogate = metrics.get("surrogate_detection_rate")
    heldout = metrics.get("heldout_detection_rate")

    # Rule 1: optimisation failed to suppress even the surrogate ensemble.
    if baseline is not None and surrogate is not None:
        if float(surrogate) >= float(baseline) - OPTIMIZATION_TOLERANCE:
            fired.append((
                FailureCategory.OPTIMIZATION_FAILURE,
                [FailureSignal(
                    "surrogate_detection_rate",
                    float(surrogate),
                    f"surrogate rate {surrogate:.3f} not reduced vs baseline "
                    f"{baseline:.3f} (tolerance {OPTIMIZATION_TOLERANCE})",
                )],
                "candidate failed to suppress detection on its own surrogate ensemble",
            ))

    # Rules 2/3: surrogate suppressed well but held-out detection stayed high.
    if baseline is not None and surrogate is not None and heldout is not None:
        suppressed = float(surrogate) <= float(baseline) - SURROGATE_SUPPRESSION_MIN
        heldout_high = float(heldout) >= float(baseline) - HELDOUT_HIGH_TOLERANCE
        if suppressed and heldout_high:
            same_family = bool(metrics.get("heldout_same_family", False))
            category = (
                FailureCategory.SURROGATE_OVERFIT
                if same_family
                else FailureCategory.CROSS_ARCHITECTURE_TRANSFER_FAILURE
            )
            family_word = "same" if same_family else "different"
            fired.append((
                category,
                [
                    FailureSignal(
                        "surrogate_suppression",
                        float(baseline) - float(surrogate),
                        f"surrogate suppressed by {float(baseline) - float(surrogate):.3f}",
                    ),
                    FailureSignal(
                        "heldout_detection_rate",
                        float(heldout),
                        f"held-out rate {heldout:.3f} high vs baseline {baseline:.3f} "
                        f"({family_word} architecture family)",
                    ),
                ],
                f"surrogate suppression did not transfer to held-out detectors "
                f"of the {family_word} architecture family",
            ))

    # Rule 4: fragility across transformation conditions.
    rates = _transformation_values(metrics.get("transformation_rates"))
    if len(rates) >= 2:
        spread = max(rates) - min(rates)
        if spread > TRANSFORMATION_SPREAD_MAX:
            fired.append((
                FailureCategory.TRANSFORMATION_FRAGILITY,
                [FailureSignal(
                    "transformation_spread",
                    spread,
                    f"detection-rate spread {spread:.3f} across transformation sweep "
                    f"exceeds {TRANSFORMATION_SPREAD_MAX}",
                )],
                "suppression is fragile: performance varies widely across transformations",
            ))

    # Rule 5: manufacturing loss (colour / scale fidelity).
    manufacturing_signals: list[FailureSignal] = []
    delta_e = metrics.get("delta_e")
    if delta_e is not None and float(delta_e) > DELTA_E_MAX:
        manufacturing_signals.append(FailureSignal(
            "delta_e", float(delta_e),
            f"delta_e {float(delta_e):.2f} exceeds {DELTA_E_MAX}",
        ))
    scale_error = metrics.get("scale_error")
    if scale_error is not None and float(scale_error) > SCALE_ERROR_MAX:
        manufacturing_signals.append(FailureSignal(
            "scale_error", float(scale_error),
            f"scale error {float(scale_error):.3f} exceeds {SCALE_ERROR_MAX}",
        ))
    if manufacturing_signals:
        fired.append((
            FailureCategory.MANUFACTURING_LOSS,
            manufacturing_signals,
            "manufacturing process degraded the pattern beyond tolerance",
        ))

    # Rule 6: camera ISP loss.
    isp_loss = metrics.get("isp_margin_loss")
    if isp_loss is not None and float(isp_loss) > ISP_MARGIN_LOSS_MAX:
        fired.append((
            FailureCategory.CAMERA_ISP_LOSS,
            [FailureSignal(
                "isp_margin_loss", float(isp_loss),
                f"ISP margin loss {float(isp_loss):.3f} exceeds {ISP_MARGIN_LOSS_MAX}",
            )],
            "camera ISP pipeline destroyed the suppression margin",
        ))

    # Rule 7: deformation failure.
    deform_drop = metrics.get("deformation_score_drop")
    if deform_drop is not None and float(deform_drop) > DEFORMATION_DROP_MAX:
        fired.append((
            FailureCategory.DEFORMATION_FAILURE,
            [FailureSignal(
                "deformation_score_drop", float(deform_drop),
                f"deformation score drop {float(deform_drop):.3f} exceeds "
                f"{DEFORMATION_DROP_MAX}",
            )],
            "suppression does not survive garment deformation",
        ))

    # Rule 8: coverage failure.
    entropy = metrics.get("coverage_entropy")
    if entropy is not None and float(entropy) < COVERAGE_ENTROPY_MIN:
        fired.append((
            FailureCategory.COVERAGE_FAILURE,
            [FailureSignal(
                "coverage_entropy", float(entropy),
                f"coverage entropy {float(entropy):.3f} below {COVERAGE_ENTROPY_MIN}",
            )],
            "pattern coverage is too concentrated to be robust",
        ))

    # Rule 9: statistically inconclusive despite consistent effect direction.
    width = _wilson_width(metrics)
    if (
        width is not None
        and width > WILSON_WIDTH_MAX
        and bool(metrics.get("effect_direction_consistent", False))
    ):
        fired.append((
            FailureCategory.STATISTICAL_INCONCLUSIVE,
            [FailureSignal(
                "wilson_width", width,
                f"Wilson interval width {width:.3f} exceeds {WILSON_WIDTH_MAX} "
                "with consistent effect direction",
            )],
            "effect direction is consistent but the sample is too small to conclude",
        ))

    if not fired:
        record = FailureRecord(
            record_id=record_id or f"FR-{uuid.uuid4().hex[:12]}",
            experiment_id=experiment_id,
            generation_id=generation_id,
            category=FailureCategory.UNCLASSIFIED,
            signals=(),
            confidence="low",
            explanation="no failure rule fired; metrics do not match any known failure mode",
            created_utc=created_utc or _utcnow_iso(),
        )
        record.validate()
        return record

    fired.sort(key=lambda item: PRIORITY_ORDER.index(item[0]))
    category, _, explanation = fired[0]
    signals = tuple(signal for _, sigs, _ in fired for signal in sigs)
    confidence = "high" if len(fired) == 1 else "medium"
    if len(fired) > 1:
        others = ", ".join(c.value for c, _, in fired[1:])
        explanation = f"{explanation} (also matched: {others})"
    record = FailureRecord(
        record_id=record_id or f"FR-{uuid.uuid4().hex[:12]}",
        experiment_id=experiment_id,
        generation_id=generation_id,
        category=category,
        signals=signals,
        confidence=confidence,
        explanation=explanation,
        created_utc=created_utc or _utcnow_iso(),
    )
    record.validate()
    return record


class FailureAtlas:
    """Append-only collection of FailureRecords forming the failure atlas."""

    def __init__(self, records: Iterable[FailureRecord] = ()) -> None:
        self._records: list[FailureRecord] = []
        for record in records:
            self.add(record)

    def add(self, record: FailureRecord) -> None:
        record.validate()
        self._records.append(record)

    @property
    def records(self) -> tuple[FailureRecord, ...]:
        return tuple(self._records)

    def by_category(self, category: FailureCategory) -> list[FailureRecord]:
        if not isinstance(category, FailureCategory):
            raise ValueError("category must be a FailureCategory")
        return [r for r in self._records if r.category is category]

    def by_generation(self, generation_id: str) -> list[FailureRecord]:
        if not generation_id:
            raise ValueError("generation_id is required")
        return [r for r in self._records if r.generation_id == generation_id]

    def summary(self) -> dict[str, int]:
        counts = {category.value: 0 for category in FailureCategory}
        for record in self._records:
            counts[record.category.value] += 1
        return counts

    def to_json(self) -> str:
        payload: list[dict[str, Any]] = []
        for record in self._records:
            item = asdict(record)
            item["category"] = record.category.value
            payload.append(item)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, data: str) -> "FailureAtlas":
        raw = json.loads(data)
        if not isinstance(raw, list):
            raise ValueError("atlas JSON must be a list of records")
        records = []
        for item in raw:
            signals = tuple(FailureSignal(**s) for s in item.get("signals", ()))
            records.append(FailureRecord(
                record_id=item["record_id"],
                experiment_id=item["experiment_id"],
                generation_id=item["generation_id"],
                category=FailureCategory(item["category"]),
                signals=signals,
                confidence=item["confidence"],
                explanation=item["explanation"],
                created_utc=item["created_utc"],
            ))
        return cls(records)

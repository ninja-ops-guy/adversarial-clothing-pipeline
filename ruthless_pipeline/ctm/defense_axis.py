"""SPEC-17 + SPEC-9 — Defense-intervention tensor axis and defense-dual
heuristic field (additive; no frozen surface is modified).

SPEC-17: the analysis tensor gains an explicit *defense intervention* axis
instead of representing every defended configuration as though it were an
independent base target.  Canonical cell identity::

    pattern x base_target x defense_intervention x channel x condition

Hard rules (fail closed with :class:`DefenseAxisError`):

- a defended variant preserves its ``base_target_ref``; it is NEVER counted
  as an independent architecture for replication (replication counting
  collapses defended variants onto their base target);
- defended-vs-base brittleness deltas require matched base/defended
  observations (same pattern, channel, condition, base target) — otherwise
  the delta is refused unless explicitly labeled unpaired;
- defense records bind identity to ``config_sha256`` so a defense cannot be
  silently reconfigured inside an analysis cell.

SPEC-9: every attack-side invariance principle has a certification dual.
Each heuristic registry entry may carry ``defense_dual`` =
{principle, certification_form, status}.  When an attack-side heuristic is
REJECTED or shows high heterogeneity, the defense dual MUST be evaluated
before the finding is archived — a pattern property that fails to predict
transfer may still succeed as a robustness certificate, and discarding it
untested is a scientific error this module makes mechanically impossible.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import jsonschema

from ..pattern_genome.canonical import canonical_json, sha256_bytes
from .errors import CTMBridgeError

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "ctm_defense_axis_v1.schema.json"
)

DEFENSE_AXIS_SCHEMA_VERSION = "rac-ctm-defense-axis/1.0"

#: SPEC-17 required defense-class enum (exactly the four spec values).
DEFENSE_CLASSES = frozenset({
    "patch_detector",
    "adversarial_training",
    "preprocessing",
    "other",
})

#: SPEC-9 defense-dual evaluation states.
DUAL_STATUSES = frozenset({
    "unevaluated",
    "certified",
    "rejected",
    "not_applicable",
})

#: Sentinel for the undefended slot of the tensor's defense axis.
NO_DEFENSE = "none"

_SHA256_LEN = 64


class DefenseAxisError(CTMBridgeError):
    """Defense-axis / defense-dual contract violated (SPEC-17 / SPEC-9).
    Fail closed."""


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _require_nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DefenseAxisError(f"{name} must be a non-empty string (fail closed)")
    return value


# ---------------------------------------------------------------------------
# SPEC-17 — defense intervention record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DefenseRecord:
    """Immutable, content-hashed defense-intervention record (SPEC-17).

    A defended configuration is a (base_target, defense) pair — never a new
    independent base target.
    """

    base_target_ref: str
    defense_id: str
    defense_class: str
    config_sha256: str
    version: str

    def __post_init__(self) -> None:
        _require_nonempty(self.base_target_ref, "base_target_ref")
        _require_nonempty(self.defense_id, "defense_id")
        _require_nonempty(self.version, "version")
        if self.defense_class not in DEFENSE_CLASSES:
            raise DefenseAxisError(
                f"unknown defense_class {self.defense_class!r}; allowed: "
                f"{sorted(DEFENSE_CLASSES)} (fail closed)"
            )
        if not _is_sha256(self.config_sha256):
            raise DefenseAxisError(
                "config_sha256 must be a lowercase 64-hex sha256: defense "
                "identity binds to an exact configuration hash (fail closed)"
            )

    def _body(self) -> dict[str, Any]:
        return {
            "schema_version": DEFENSE_AXIS_SCHEMA_VERSION,
            "base_target_ref": self.base_target_ref,
            "defense_id": self.defense_id,
            "defense_class": self.defense_class,
            "config_sha256": self.config_sha256,
            "version": self.version,
        }

    @property
    def record_id(self) -> str:
        return "RAC-CTM-DEF-" + sha256_bytes(canonical_json(self._body()))[:16]

    @property
    def defended_target_ref(self) -> str:
        """Panel-execution identity of the defended variant.  The base-target
        prefix is preserved so attribution can never lose the pairing."""
        return f"{self.base_target_ref}::def={self.record_id}"

    def to_dict(self) -> dict[str, Any]:
        body = self._body()
        body["record_id"] = self.record_id
        return body

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DefenseRecord":
        if not isinstance(payload, Mapping):
            raise DefenseAxisError("defense record must be an object")
        record = cls(
            base_target_ref=payload.get("base_target_ref"),
            defense_id=payload.get("defense_id"),
            defense_class=payload.get("defense_class"),
            config_sha256=payload.get("config_sha256"),
            version=payload.get("version"),
        )
        declared = payload.get("record_id")
        if declared is not None and declared != record.record_id:
            raise DefenseAxisError(
                "declared record_id does not re-derive from the record body: "
                "the defense record was tampered with or asserted (fail closed)"
            )
        record.validate_against_schema()
        return record

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise DefenseAxisError(
                f"defense record fails ctm_defense_axis_v1 schema: {exc.message}"
            ) from exc


# ---------------------------------------------------------------------------
# SPEC-17 — canonical tensor cell identity
# ---------------------------------------------------------------------------


def tensor_cell_id(
    *,
    pattern_ref: str,
    base_target_ref: str,
    defense: DefenseRecord | None,
    channel_id: str,
    condition_id: str,
) -> str:
    """Canonical cell identity:
    ``pattern x base_target x defense_intervention x channel x condition``.

    The undefended slot uses the ``NO_DEFENSE`` sentinel; a defended cell
    binds the full defense record id (hence its config hash).
    """
    _require_nonempty(pattern_ref, "pattern_ref")
    _require_nonempty(base_target_ref, "base_target_ref")
    _require_nonempty(channel_id, "channel_id")
    _require_nonempty(condition_id, "condition_id")
    if defense is not None and not isinstance(defense, DefenseRecord):
        raise DefenseAxisError(
            "defense must be a DefenseRecord or None (fail closed)"
        )
    if defense is not None and defense.base_target_ref != base_target_ref:
        raise DefenseAxisError(
            "defense record base_target_ref does not match the cell base "
            "target: a defended cell cannot be re-parented onto another base "
            "target (fail closed)"
        )
    body = {
        "pattern_ref": pattern_ref,
        "base_target_ref": base_target_ref,
        "defense_intervention": defense.record_id if defense else NO_DEFENSE,
        "channel_id": channel_id,
        "condition_id": condition_id,
    }
    return "RAC-CTM-CELL-" + sha256_bytes(canonical_json(body))[:16]


# ---------------------------------------------------------------------------
# SPEC-17 — replication counting: defended != independent architecture
# ---------------------------------------------------------------------------


def collapse_to_base(target: str | DefenseRecord) -> str:
    """Collapse any tensor target identity to its base-target ref."""
    if isinstance(target, DefenseRecord):
        return target.base_target_ref
    if isinstance(target, str) and "::def=" in target:
        return target.split("::def=", 1)[0]
    return _require_nonempty(target, "target")


def independent_replication_count(targets: Iterable[str | DefenseRecord]) -> int:
    """Count independent base architectures for replication purposes.

    Defended variants of the same base target collapse to ONE independent
    target — a defended model is an intervention on a base target, not a new
    architecture (SPEC-17 hard rule).
    """
    bases = {collapse_to_base(t) for t in targets}
    return len(bases)


def require_not_independent_architecture(
    defense: DefenseRecord,
    claimed_independent_count: int,
    prior_independent_count: int,
) -> None:
    """Fail-closed guard: adding a defended variant of an existing base
    target must not increase the independent-architecture count."""
    if not isinstance(defense, DefenseRecord):
        raise DefenseAxisError("defense must be a DefenseRecord (fail closed)")
    if claimed_independent_count > prior_independent_count:
        raise DefenseAxisError(
            f"defended variant {defense.record_id} of base target "
            f"{defense.base_target_ref!r} was counted as an independent "
            "architecture for replication: defended configurations are "
            "interventions on a base target, never independent replication "
            "(fail closed)"
        )


# ---------------------------------------------------------------------------
# SPEC-17 — paired defended-vs-base brittleness deltas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DefenseObservation:
    """One outcome observation in a defense-axis tensor cell.

    ``defense`` is None for the undefended base observation.  ``metrics``
    carries measured quantities such as ``asr`` or ``detection_rate``;
    optionally ``patch_scale_success`` / ``garment_scale_success`` for the
    scale-delta metric.
    """

    pattern_ref: str
    channel_id: str
    condition_id: str
    base_target_ref: str
    defense: DefenseRecord | None
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.pattern_ref, "pattern_ref")
        _require_nonempty(self.channel_id, "channel_id")
        _require_nonempty(self.condition_id, "condition_id")
        _require_nonempty(self.base_target_ref, "base_target_ref")
        if self.defense is not None:
            if not isinstance(self.defense, DefenseRecord):
                raise DefenseAxisError(
                    "defense must be a DefenseRecord or None (fail closed)"
                )
            if self.defense.base_target_ref != self.base_target_ref:
                raise DefenseAxisError(
                    "observation base_target_ref does not match its defense "
                    "record's base_target_ref (fail closed)"
                )
        if not isinstance(self.metrics, Mapping):
            raise DefenseAxisError("metrics must be a mapping (fail closed)")
        for name, value in self.metrics.items():
            if not isinstance(name, str) or not name:
                raise DefenseAxisError("metric names must be non-empty strings")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise DefenseAxisError(
                    f"metric {name!r} must be numeric (fail closed)"
                )


def _check_pairable(
    base: DefenseObservation, defended: DefenseObservation
) -> list[str]:
    mismatches = []
    for attr in ("pattern_ref", "channel_id", "condition_id", "base_target_ref"):
        if getattr(base, attr) != getattr(defended, attr):
            mismatches.append(attr)
    return mismatches


def compute_defended_delta(
    base: DefenseObservation,
    defended: DefenseObservation,
    metric: str,
    *,
    allow_unpaired: bool = False,
) -> dict[str, Any]:
    """Brittleness delta ``defended - base`` for one metric.

    Paired by default: base and defended observations must match on
    pattern, channel, condition, and base target, exactly one of them
    defended.  Unpaired contrasts are refused unless
    ``allow_unpaired=True``, in which case the result is explicitly labeled
    ``paired: False`` so downstream analysis can never mistake it for a
    paired delta.
    """
    if base.defense is not None and defended.defense is not None:
        raise DefenseAxisError(
            "both observations are defended: a brittleness delta contrasts "
            "one defended and one undefended (base) observation (fail closed)"
        )
    if base.defense is None and defended.defense is None:
        raise DefenseAxisError(
            "neither observation is defended: a brittleness delta contrasts "
            "one defended and one undefended (base) observation (fail closed)"
        )
    # orient: base = undefended, defended = defended
    if base.defense is not None:
        base, defended = defended, base
    mismatches = _check_pairable(base, defended)
    paired = not mismatches
    if mismatches and not allow_unpaired:
        raise DefenseAxisError(
            f"base/defended observations mismatch on {mismatches}: paired "
            "brittleness deltas require matched observations; pass "
            "allow_unpaired=True to obtain an explicitly labeled unpaired "
            "contrast (fail closed)"
        )
    for obs, role in ((base, "base"), (defended, "defended")):
        if metric not in obs.metrics:
            raise DefenseAxisError(
                f"metric {metric!r} missing from the {role} observation "
                "(fail closed)"
            )
    return {
        "metric": metric,
        "base_value": float(base.metrics[metric]),
        "defended_value": float(defended.metrics[metric]),
        "delta": float(defended.metrics[metric]) - float(base.metrics[metric]),
        "paired": paired,
        "pairing": "matched" if paired else "unpaired_labeled",
        "base_target_ref": base.base_target_ref,
        "defense_record_id": defended.defense.record_id,
    }


def paired_brittleness_deltas(
    base: DefenseObservation,
    defended: DefenseObservation,
    *,
    allow_unpaired: bool = False,
) -> dict[str, Any]:
    """SPEC-17 defense-specific paired quantities.

    Computes ``delta_asr_defended_vs_base`` and
    ``delta_detection_rate_defended_vs_base`` when present, plus the
    patch-scale vs. garment-scale success delta when both scale metrics are
    present in both observations.
    """
    out: dict[str, Any] = {"deltas": {}}
    canonical = {
        "asr": "delta_asr_defended_vs_base",
        "detection_rate": "delta_detection_rate_defended_vs_base",
    }
    for metric, label in canonical.items():
        if metric in base.metrics and metric in defended.metrics:
            out["deltas"][label] = compute_defended_delta(
                base, defended, metric, allow_unpaired=allow_unpaired
            )
    scale_metrics = ("patch_scale_success", "garment_scale_success")
    if all(
        m in obs.metrics for obs in (base, defended) for m in scale_metrics
    ):
        base_gap = (
            float(base.metrics["patch_scale_success"])
            - float(base.metrics["garment_scale_success"])
        )
        defended_gap = (
            float(defended.metrics["patch_scale_success"])
            - float(defended.metrics["garment_scale_success"])
        )
        mismatches = _check_pairable(
            base if base.defense is None else defended,
            defended if defended.defense is not None else base,
        )
        paired = not mismatches
        if mismatches and not allow_unpaired:
            raise DefenseAxisError(
                f"scale-delta observations mismatch on {mismatches}: paired "
                "scale deltas require matched observations (fail closed)"
            )
        out["deltas"]["patch_vs_garment_scale_gap_shift"] = {
            "metric": "patch_vs_garment_scale_gap",
            "base_value": base_gap,
            "defended_value": defended_gap,
            "delta": defended_gap - base_gap,
            "paired": paired,
            "pairing": "matched" if paired else "unpaired_labeled",
        }
    if not out["deltas"]:
        raise DefenseAxisError(
            "no shared brittleness metrics between the base and defended "
            "observations (fail closed)"
        )
    return out


def heterogeneity_by_defense_class(
    deltas: Iterable[Mapping[str, Any]],
) -> dict[str, list[float]]:
    """Group brittleness deltas by defense class for SPEC-17 heterogeneity
    reporting.  Unpaired-labeled deltas are kept in a separate bucket so
    they can never silently pool with matched pairs."""
    grouped: dict[str, list[float]] = {}
    for d in deltas:
        pairing = d.get("pairing")
        key_prefix = "unpaired::" if pairing == "unpaired_labeled" else ""
        defense_id = d.get("defense_record_id", "")
        grouped.setdefault(key_prefix + defense_id, []).append(float(d["delta"]))
    return grouped


# ---------------------------------------------------------------------------
# SPEC-9 — defense-dual heuristic field
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DefenseDual:
    """SPEC-9 defense-dual tracking field for heuristic registry entries.

    ``{principle, certification_form, status}`` — the certification dual of
    an attack-side invariance principle (e.g. a topological stability bound
    or a worst-case transformation-group guarantee).
    """

    principle: str
    certification_form: str
    status: str = "unevaluated"

    def __post_init__(self) -> None:
        _require_nonempty(self.principle, "principle")
        _require_nonempty(self.certification_form, "certification_form")
        if self.status not in DUAL_STATUSES:
            raise DefenseAxisError(
                f"unknown defense-dual status {self.status!r}; allowed: "
                f"{sorted(DUAL_STATUSES)} (fail closed)"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "principle": self.principle,
            "certification_form": self.certification_form,
            "status": self.status,
        }


def require_dual_evaluated_before_archival(
    attack_outcome: str,
    dual: DefenseDual,
    *,
    heterogeneity: float | None = None,
    high_heterogeneity_threshold: float,
) -> None:
    """SPEC-9 archival gate: when an attack-side heuristic is REJECTED or
    shows high heterogeneity, its defense dual MUST have been evaluated
    (status other than ``unevaluated``) before the finding is archived.

    A property that fails to predict transfer may still succeed as a
    robustness certificate; archiving without evaluating the dual discards
    that finding silently — refused.
    """
    if not isinstance(dual, DefenseDual):
        raise DefenseAxisError("dual must be a DefenseDual (fail closed)")
    if not isinstance(high_heterogeneity_threshold, (int, float)) or isinstance(
        high_heterogeneity_threshold, bool
    ):
        raise DefenseAxisError(
            "high_heterogeneity_threshold must be numeric and explicit "
            "(no silent default) (fail closed)"
        )
    if heterogeneity is not None and (
        not isinstance(heterogeneity, (int, float))
        or isinstance(heterogeneity, bool)
        or not 0.0 <= heterogeneity <= 1.0
    ):
        raise DefenseAxisError(
            "heterogeneity must be in [0, 1] when provided (fail closed)"
        )
    triggered = attack_outcome == "REJECTED" or (
        heterogeneity is not None and heterogeneity >= high_heterogeneity_threshold
    )
    if triggered and dual.status == "unevaluated":
        raise DefenseAxisError(
            f"attack-side outcome {attack_outcome!r}"
            + (
                f" with heterogeneity {heterogeneity} >= "
                f"{high_heterogeneity_threshold}"
                if heterogeneity is not None
                and heterogeneity >= high_heterogeneity_threshold
                else ""
            )
            + " requires the defense dual to be evaluated before archival: "
            "a property that fails to predict transfer may still certify "
            "robustness — discarding it unevaluated is refused (fail closed)"
        )

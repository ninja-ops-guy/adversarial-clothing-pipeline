"""SPEC-7 — Retrospective property-mining protocol (pre-CTM-F gate).

The gate is deliberately conservative. It emits exactly one of CONTINUE,
RESCOPE, or REJECT_HYPOTHESIS_FAMILY. Rejection is legal only when every
preregistered family has adequate cohort size, power, homogeneity, channel
metadata, provenance, and minimum-effect exclusion.

External/corpus observations remain EXPLORATORY and never become controlled
physical-efficacy evidence through this module.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from .errors import CTMBridgeError

RETRO_PREREG_SCHEMA_VERSION = "rac-ctm-retro-prereg/1.0"
RETRO_DECISION_SCHEMA_VERSION = "rac-ctm-retro-decision/1.1"

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
_PREREG_SCHEMA_PATH = _SCHEMA_DIR / "ctm_retro_prereg_v1.schema.json"
_DECISION_SCHEMA_PATH = _SCHEMA_DIR / "ctm_retro_decision_v1_1.schema.json"


class RetroMiningError(CTMBridgeError):
    """SPEC-7 retro-mining contract violated. Fail closed."""


DECISION_STATES = frozenset({
    "CONTINUE", "RESCOPE", "REJECT_HYPOTHESIS_FAMILY"
})

PREDICTOR_FAMILIES = frozenset({
    "harmonic_energy_curve",
    "description_length",
    "group_risk",
    "persistence_summary",
})

MULTIPLICITY_METHODS = frozenset({"holm", "bonferroni", "bh"})
MISSING_DATA_POLICIES = frozenset({"complete_case", "stratum_specific"})

STRATIFICATION_AXES = (
    "target_head_class",
    "channel_class",
    "threshold_regime",
    "cohort",
)

CLAIM_STATE = "EXPLORATORY"

_FAMILY_DISPOSITIONS = frozenset({
    "incremental_signal",
    "legally_rejected",
    "insufficient_cohort",
    "underpowered",
    "heterogeneous",
    "metadata_inadequate",
    "no_signal_not_rejectable",
})


@dataclass(frozen=True)
class RetroPreregistration:
    """Immutable, content-hashed SPEC-7 preregistration."""

    created_utc: str
    minimum_useful_effect: float
    minimum_analyzable_cohort: int
    min_power: float
    max_heterogeneity: float
    multiplicity_correction: str
    missing_data_policy: str
    predictor_families: tuple[str, ...]
    luminance_baseline: str = "luminance_only_description_length"
    schema_version: str = RETRO_PREREG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RETRO_PREREG_SCHEMA_VERSION:
            raise RetroMiningError(
                f"unsupported retro prereg schema_version: {self.schema_version!r}"
            )
        if not self.created_utc:
            raise RetroMiningError("created_utc is required (fail closed)")
        if (
            isinstance(self.minimum_useful_effect, bool)
            or not isinstance(self.minimum_useful_effect, (int, float))
            or self.minimum_useful_effect <= 0
        ):
            raise RetroMiningError(
                "minimum_useful_effect must be > 0 (fail closed)"
            )
        if (
            isinstance(self.minimum_analyzable_cohort, bool)
            or not isinstance(self.minimum_analyzable_cohort, int)
            or self.minimum_analyzable_cohort < 2
        ):
            raise RetroMiningError(
                "minimum_analyzable_cohort must be an integer >= 2 (fail closed)"
            )
        if (
            isinstance(self.min_power, bool)
            or not isinstance(self.min_power, (int, float))
            or not (0.0 < self.min_power <= 1.0)
        ):
            raise RetroMiningError("min_power must be in (0, 1] (fail closed)")
        if (
            isinstance(self.max_heterogeneity, bool)
            or not isinstance(self.max_heterogeneity, (int, float))
            or not (0.0 <= self.max_heterogeneity <= 1.0)
        ):
            raise RetroMiningError(
                "max_heterogeneity must be in [0, 1] (fail closed)"
            )
        if self.multiplicity_correction not in MULTIPLICITY_METHODS:
            raise RetroMiningError(
                f"unknown multiplicity_correction {self.multiplicity_correction!r}; "
                f"allowed: {sorted(MULTIPLICITY_METHODS)} (fail closed)"
            )
        if self.missing_data_policy not in MISSING_DATA_POLICIES:
            raise RetroMiningError(
                f"unknown missing_data_policy {self.missing_data_policy!r}; "
                f"allowed: {sorted(MISSING_DATA_POLICIES)} (fail closed)"
            )
        if not self.predictor_families:
            raise RetroMiningError("predictor_families must not be empty")
        if len(set(self.predictor_families)) != len(self.predictor_families):
            raise RetroMiningError("predictor_families must not contain duplicates")
        for family in self.predictor_families:
            if family not in PREDICTOR_FAMILIES:
                raise RetroMiningError(
                    f"unknown predictor family {family!r}; allowed: "
                    f"{sorted(PREDICTOR_FAMILIES)} (fail closed)"
                )
        if not self.luminance_baseline:
            raise RetroMiningError("luminance_baseline is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_utc": self.created_utc,
            "minimum_useful_effect": self.minimum_useful_effect,
            "minimum_analyzable_cohort": self.minimum_analyzable_cohort,
            "min_power": self.min_power,
            "max_heterogeneity": self.max_heterogeneity,
            "multiplicity_correction": self.multiplicity_correction,
            "missing_data_policy": self.missing_data_policy,
            "predictor_families": sorted(self.predictor_families),
            "luminance_baseline": self.luminance_baseline,
            "stratification_axes": list(STRATIFICATION_AXES),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RetroPreregistration":
        if not isinstance(payload, dict):
            raise RetroMiningError("preregistration payload must be an object")
        axes = payload.get("stratification_axes")
        if axes is not None and tuple(axes) != STRATIFICATION_AXES:
            raise RetroMiningError(
                "preregistration stratification_axes disagree with the frozen "
                "SPEC-7 axes (fail closed)"
            )
        return cls(
            created_utc=payload.get("created_utc", ""),
            minimum_useful_effect=payload.get("minimum_useful_effect", 0),
            minimum_analyzable_cohort=payload.get("minimum_analyzable_cohort", 0),
            min_power=payload.get("min_power", 0),
            max_heterogeneity=payload.get("max_heterogeneity", -1),
            multiplicity_correction=payload.get("multiplicity_correction", ""),
            missing_data_policy=payload.get("missing_data_policy", ""),
            predictor_families=tuple(payload.get("predictor_families", ())),
            luminance_baseline=payload.get("luminance_baseline", ""),
            schema_version=payload.get("schema_version", ""),
        )

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @property
    def preregistration_id(self) -> str:
        return "RAC-CTM-RETRO-PREREG-" + sha256_bytes(self.canonical_bytes())[:16]

    def preregistration_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_PREREG_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise RetroMiningError(
                f"retro preregistration fails ctm_retro_prereg_v1 schema: "
                f"{exc.message}"
            ) from exc


@dataclass(frozen=True)
class FamilyResult:
    """One preregistered predictor-family analysis result.

    Channel/provenance adequacy are explicit booleans. They have no defaults:
    callers cannot omit these validity judgments and still obtain a
    rejection-capable result.
    """

    family: str
    cohort_size: int
    achieved_power: float
    heterogeneity: float
    incremental_signal: bool
    min_effect_excluded: bool
    channel_metadata_adequate: bool
    provenance_adequate: bool
    metadata_gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.family not in PREDICTOR_FAMILIES:
            raise RetroMiningError(
                f"unknown predictor family {self.family!r}; allowed: "
                f"{sorted(PREDICTOR_FAMILIES)} (fail closed)"
            )
        if (
            isinstance(self.cohort_size, bool)
            or not isinstance(self.cohort_size, int)
            or self.cohort_size < 0
        ):
            raise RetroMiningError("cohort_size must be a non-negative integer")
        for name in ("achieved_power", "heterogeneity"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not (0.0 <= value <= 1.0)
            ):
                raise RetroMiningError(f"{name} must be in [0, 1], got {value!r}")
        for name in (
            "incremental_signal",
            "min_effect_excluded",
            "channel_metadata_adequate",
            "provenance_adequate",
        ):
            if not isinstance(getattr(self, name), bool):
                raise RetroMiningError(f"{name} must be boolean (fail closed)")
        if isinstance(self.metadata_gaps, str):
            raise RetroMiningError("metadata_gaps must be a sequence, not a string")
        if any(not isinstance(gap, str) or not gap for gap in self.metadata_gaps):
            raise RetroMiningError("metadata_gaps must contain non-empty strings")
        if len(set(self.metadata_gaps)) != len(self.metadata_gaps):
            raise RetroMiningError("metadata_gaps must not contain duplicates")
        if (
            self.channel_metadata_adequate
            and self.provenance_adequate
            and self.metadata_gaps
        ):
            raise RetroMiningError(
                "metadata_gaps cannot be non-empty when channel/provenance "
                "adequacy are both true"
            )

    @property
    def metadata_adequate(self) -> bool:
        return self.channel_metadata_adequate and self.provenance_adequate

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "cohort_size": self.cohort_size,
            "achieved_power": self.achieved_power,
            "heterogeneity": self.heterogeneity,
            "incremental_signal": self.incremental_signal,
            "min_effect_excluded": self.min_effect_excluded,
            "channel_metadata_adequate": self.channel_metadata_adequate,
            "provenance_adequate": self.provenance_adequate,
            "metadata_gaps": list(self.metadata_gaps),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FamilyResult":
        if not isinstance(payload, dict):
            raise RetroMiningError("family result payload must be an object")
        required = (
            "family",
            "cohort_size",
            "achieved_power",
            "heterogeneity",
            "incremental_signal",
            "min_effect_excluded",
            "channel_metadata_adequate",
            "provenance_adequate",
        )
        missing = [name for name in required if name not in payload]
        if missing:
            raise RetroMiningError(
                f"family result missing required fields {missing} (fail closed)"
            )
        return cls(
            family=payload["family"],
            cohort_size=payload["cohort_size"],
            achieved_power=payload["achieved_power"],
            heterogeneity=payload["heterogeneity"],
            incremental_signal=payload["incremental_signal"],
            min_effect_excluded=payload["min_effect_excluded"],
            channel_metadata_adequate=payload["channel_metadata_adequate"],
            provenance_adequate=payload["provenance_adequate"],
            metadata_gaps=tuple(payload.get("metadata_gaps", ())),
        )


def require_reject_legal(
    prereg: RetroPreregistration, result: FamilyResult
) -> None:
    """Refuse rejection unless every preregistered adequacy condition holds."""
    unmet: list[str] = []
    if result.cohort_size < prereg.minimum_analyzable_cohort:
        unmet.append(
            f"cohort_size {result.cohort_size} < minimum_analyzable_cohort "
            f"{prereg.minimum_analyzable_cohort}"
        )
    if result.achieved_power < prereg.min_power:
        unmet.append(
            f"achieved_power {result.achieved_power} < min_power {prereg.min_power}"
        )
    if result.heterogeneity > prereg.max_heterogeneity:
        unmet.append(
            f"heterogeneity {result.heterogeneity} > max_heterogeneity "
            f"{prereg.max_heterogeneity}"
        )
    if not result.channel_metadata_adequate:
        unmet.append("channel metadata inadequate")
    if not result.provenance_adequate:
        unmet.append("provenance inadequate")
    if not result.min_effect_excluded:
        unmet.append("minimum useful effect not excluded")
    if unmet:
        raise RetroMiningError(
            f"REJECT_HYPOTHESIS_FAMILY is illegal for {result.family!r}: "
            + "; ".join(unmet)
            + " — inadequate comparability/metadata/power is RESCOPE, never "
            "rejection (fail closed)"
        )


def _family_disposition(
    prereg: RetroPreregistration, result: FamilyResult
) -> str:
    if not result.metadata_adequate:
        return "metadata_inadequate"
    if result.incremental_signal:
        if result.cohort_size < prereg.minimum_analyzable_cohort:
            raise RetroMiningError(
                f"family {result.family!r} claims incremental signal below the "
                "minimum analyzable cohort (fail closed)"
            )
        return "incremental_signal"
    if result.cohort_size < prereg.minimum_analyzable_cohort:
        return "insufficient_cohort"
    if result.achieved_power < prereg.min_power:
        return "underpowered"
    if result.heterogeneity > prereg.max_heterogeneity:
        return "heterogeneous"
    if result.min_effect_excluded:
        return "legally_rejected"
    return "no_signal_not_rejectable"


def seal_decision(
    prereg: RetroPreregistration,
    results: Iterable[FamilyResult],
) -> dict[str, Any]:
    """Derive and seal the three-state decision artifact."""
    prereg.validate_against_schema()
    results = list(results)
    by_family = {r.family: r for r in results}
    if len(by_family) != len(results):
        raise RetroMiningError("duplicate FamilyResult for a predictor family")
    missing = [f for f in prereg.predictor_families if f not in by_family]
    if missing:
        raise RetroMiningError(
            f"missing preregistered family results {missing} (fail closed)"
        )
    extra = [f for f in by_family if f not in prereg.predictor_families]
    if extra:
        raise RetroMiningError(
            f"unpreregistered family results {extra} (fail closed)"
        )

    dispositions: dict[str, str] = {}
    for family in sorted(prereg.predictor_families):
        result = by_family[family]
        disposition = _family_disposition(prereg, result)
        if disposition == "legally_rejected":
            require_reject_legal(prereg, result)
        dispositions[family] = disposition

    if any(d == "incremental_signal" for d in dispositions.values()):
        decision = "CONTINUE"
    elif all(d == "legally_rejected" for d in dispositions.values()):
        decision = "REJECT_HYPOTHESIS_FAMILY"
    else:
        decision = "RESCOPE"

    artifact_body = {
        "schema_version": RETRO_DECISION_SCHEMA_VERSION,
        "decision": decision,
        "preregistration_sha256": prereg.preregistration_sha256(),
        "preregistration_id": prereg.preregistration_id,
        "preregistration": prereg.to_dict(),
        "family_dispositions": dispositions,
        "family_results": [by_family[f].to_dict() for f in sorted(by_family)],
        "stratification_axes": list(STRATIFICATION_AXES),
        "claim_state": CLAIM_STATE,
        "physical_efficacy_claimed": False,
    }
    report_sha = sha256_bytes(canonical_json(artifact_body))
    artifact = dict(artifact_body)
    artifact["report_sha256"] = report_sha
    artifact["decision_id"] = "RAC-CTM-RETRO-DECISION-" + report_sha[:16]
    schema = json.loads(_DECISION_SCHEMA_PATH.read_text())
    try:
        jsonschema.validate(artifact, schema)
    except jsonschema.ValidationError as exc:
        raise RetroMiningError(
            f"derived decision artifact fails ctm_retro_decision_v1_1 schema: "
            f"{exc.message}"
        ) from exc
    return artifact


def verify_decision(artifact: dict[str, Any]) -> None:
    """Fully re-derive a sealed decision, not merely its hash.

    v1.1 embeds the preregistration contract so verification can reconstruct
    every family result and re-run the legality/decision logic. A caller
    cannot forge a different decision and make it valid merely by recomputing
    report_sha256.
    """
    if not isinstance(artifact, dict):
        raise RetroMiningError("decision artifact must be an object")
    schema = json.loads(_DECISION_SCHEMA_PATH.read_text())
    try:
        jsonschema.validate(artifact, schema)
    except jsonschema.ValidationError as exc:
        raise RetroMiningError(
            f"decision artifact fails ctm_retro_decision_v1_1 schema: "
            f"{exc.message}"
        ) from exc

    prereg = RetroPreregistration.from_dict(artifact["preregistration"])
    prereg.validate_against_schema()
    if artifact["preregistration_sha256"] != prereg.preregistration_sha256():
        raise RetroMiningError(
            "preregistration_sha256 does not match embedded preregistration "
            "(fail closed)"
        )
    if artifact["preregistration_id"] != prereg.preregistration_id:
        raise RetroMiningError(
            "preregistration_id does not match embedded preregistration "
            "(fail closed)"
        )

    results = [FamilyResult.from_dict(row) for row in artifact["family_results"]]
    expected = seal_decision(prereg, results)
    if artifact != expected:
        raise RetroMiningError(
            "sealed decision does not fully re-derive from the embedded "
            "preregistration and family results (fail closed)"
        )

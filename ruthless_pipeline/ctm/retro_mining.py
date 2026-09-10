"""SPEC-7 — Retrospective property-mining protocol (pre-CTM-F gate).

Lesson L9: a standalone, preregistered analysis module over the living corpus
(SPEC-4) and eligible external-fabrication observations (SPEC-16). It
evaluates the four cheap predictor families against published transfer deltas
and emits a SEALED three-state decision artifact.

Hard rules (fail closed with :class:`RetroMiningError`):

- Exactly three decision states: ``CONTINUE``, ``RESCOPE``,
  ``REJECT_HYPOTHESIS_FAMILY``. No fourth state exists.
- ``REJECT_HYPOTHESIS_FAMILY`` is IMPOSSIBLE unless the preregistered power,
  homogeneity, and minimum-effect conditions are all satisfied for EVERY
  preregistered predictor family. A null pooled regression across
  non-commensurable papers is never falsification: families with
  insufficient cohort size, inadequate power, or excess heterogeneity
  dispositions to RESCOPE, not rejection.
- The preregistration must define: minimum useful effect, minimum analyzable
  cohort, multiplicity correction, missing-data policy, and (via the
  required power/homogeneity/min-effect fields) the exact conditions under
  which rejection is legal. Sealing the preregistration is content-hashed
  and immutable.
- Decisions are DERIVED, never asserted: the only way to obtain a decision
  artifact is :func:`seal_decision`. A user-asserted decision or a tampered
  artifact refuses at verification.
- Claim state is capped at EXPLORATORY/observational by construction;
  corpus-derived digital measurements and external physical observations
  never promote to a controlled physical efficacy claim.

Additive: no frozen schema, Genome v1, or CTM-A contract is mutated.
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
RETRO_DECISION_SCHEMA_VERSION = "rac-ctm-retro-decision/1.0"

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
_PREREG_SCHEMA_PATH = _SCHEMA_DIR / "ctm_retro_prereg_v1.schema.json"
_DECISION_SCHEMA_PATH = _SCHEMA_DIR / "ctm_retro_decision_v1.schema.json"


class RetroMiningError(CTMBridgeError):
    """SPEC-7 retro-mining contract violated. Fail closed."""


#: The sealed three-state decision enum (exactly three; no fourth state).
DECISION_STATES = frozenset({"CONTINUE", "RESCOPE", "REJECT_HYPOTHESIS_FAMILY"})

#: The four cheap preregistered predictor families (SPEC-7(b)).
PREDICTOR_FAMILIES = frozenset({
    "harmonic_energy_curve",
    "description_length",
    "group_risk",
    "persistence_summary",
})

MULTIPLICITY_METHODS = frozenset({"holm", "bonferroni", "bh"})

MISSING_DATA_POLICIES = frozenset({"complete_case", "stratum_specific"})

#: Minimum stratification metadata (SPEC-7: stratify or model heterogeneity).
STRATIFICATION_AXES = (
    "target_head_class",
    "channel_class",
    "threshold_regime",
    "cohort",
)

#: Claim ceiling: secondary/derived evidence, exploratory by construction.
CLAIM_STATE = "EXPLORATORY"

#: Per-family dispositions inside a decision.
_FAMILY_DISPOSITIONS = frozenset({
    "incremental_signal",
    "legally_rejected",
    "insufficient_cohort",
    "underpowered",
    "heterogeneous",
    "no_signal_not_rejectable",
})

_SHA256_LEN = 64


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


# ---------------------------------------------------------------------------
# Preregistration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetroPreregistration:
    """Immutable, content-hashed SPEC-7 preregistration.

    The rejection-legality contract is structural: ``min_power``,
    ``max_heterogeneity``, and ``minimum_useful_effect`` are required fields,
    so the exact conditions under which REJECT_HYPOTHESIS_FAMILY is legal
    are always defined.
    """

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
        if not isinstance(self.minimum_useful_effect, (int, float)) or not (self.minimum_useful_effect > 0):
            raise RetroMiningError(
                "minimum_useful_effect must be > 0: the preregistration must "
                "prespecify the smallest effect worth rejecting for (fail closed)"
            )
        if not isinstance(self.minimum_analyzable_cohort, int) or self.minimum_analyzable_cohort < 2:
            raise RetroMiningError(
                "minimum_analyzable_cohort must be an integer >= 2 (fail closed)"
            )
        if not isinstance(self.min_power, (int, float)) or not (0.0 < self.min_power <= 1.0):
            raise RetroMiningError(
                "min_power must be in (0, 1]: rejection requires adequate power "
                "(fail closed)"
            )
        if not isinstance(self.max_heterogeneity, (int, float)) or not (0.0 <= self.max_heterogeneity <= 1.0):
            raise RetroMiningError(
                "max_heterogeneity must be in [0, 1]: rejection requires "
                "sufficient homogeneity (fail closed)"
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
            raise RetroMiningError(
                "predictor_families must not be empty: the preregistration names "
                "the families under test (fail closed)"
            )
        for family in self.predictor_families:
            if family not in PREDICTOR_FAMILIES:
                raise RetroMiningError(
                    f"unknown predictor family {family!r}; allowed: "
                    f"{sorted(PREDICTOR_FAMILIES)} (fail closed)"
                )
        if len(set(self.predictor_families)) != len(self.predictor_families):
            raise RetroMiningError("predictor_families must not contain duplicates")
        if not self.luminance_baseline:
            raise RetroMiningError(
                "luminance_baseline is required: incremental information is "
                "defined against the luminance-only baseline (fail closed)"
            )

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
                f"retro preregistration fails ctm_retro_prereg_v1 schema: {exc.message}"
            ) from exc


# ---------------------------------------------------------------------------
# Per-family analysis result (input to the gate)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FamilyResult:
    """Preregistered analysis outcome for one predictor family.

    ``incremental_signal`` = reproducible incremental information beyond the
    luminance-only baseline under the preregistered multiplicity correction.
    ``min_effect_excluded`` = the analysis excludes the prespecified minimum
    useful effect for this family.
    """

    family: str
    cohort_size: int
    achieved_power: float
    heterogeneity: float
    incremental_signal: bool
    min_effect_excluded: bool

    def __post_init__(self) -> None:
        if self.family not in PREDICTOR_FAMILIES:
            raise RetroMiningError(
                f"unknown predictor family {self.family!r}; allowed: "
                f"{sorted(PREDICTOR_FAMILIES)} (fail closed)"
            )
        if not isinstance(self.cohort_size, int) or self.cohort_size < 0:
            raise RetroMiningError("cohort_size must be a non-negative integer")
        for name in ("achieved_power", "heterogeneity"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
                raise RetroMiningError(f"{name} must be in [0, 1], got {value!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "cohort_size": self.cohort_size,
            "achieved_power": self.achieved_power,
            "heterogeneity": self.heterogeneity,
            "incremental_signal": self.incremental_signal,
            "min_effect_excluded": self.min_effect_excluded,
        }


def require_reject_legal(prereg: RetroPreregistration, result: FamilyResult) -> None:
    """Fail-closed legality check for rejecting one hypothesis family.

    Rejection is legal ONLY when the preregistered power, homogeneity, and
    minimum-effect conditions are ALL satisfied for an analyzable cohort.
    """
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
    if not result.min_effect_excluded:
        unmet.append(
            "minimum useful effect not excluded by the preregistered analysis"
        )
    if unmet:
        raise RetroMiningError(
            f"REJECT_HYPOTHESIS_FAMILY is illegal for {result.family!r}: "
            + "; ".join(unmet)
            + " — a null result without preregistered power, homogeneity, and "
            "minimum-effect exclusion is RESCOPE, never rejection (fail closed)"
        )


# ---------------------------------------------------------------------------
# Sealed decision artifact
# ---------------------------------------------------------------------------


def _family_disposition(prereg: RetroPreregistration, result: FamilyResult) -> str:
    if result.incremental_signal:
        if result.cohort_size < prereg.minimum_analyzable_cohort:
            raise RetroMiningError(
                f"family {result.family!r} claims incremental signal below the "
                "minimum analyzable cohort: signal claims require an analyzable "
                "cohort (fail closed)"
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
    """Derive and seal the three-state decision artifact. The ONLY way to
    obtain a decision.

    - CONTINUE: >= 1 preregistered family shows incremental signal beyond the
      luminance-only baseline on an analyzable cohort.
    - REJECT_HYPOTHESIS_FAMILY: EVERY preregistered family is legally
      rejected (power + homogeneity + minimum-effect exclusion, verified
      through :func:`require_reject_legal`).
    - RESCOPE: anything else — heterogeneity, missing channel metadata,
      insufficient cohort, or inadequate power prevents rejection.
    """
    prereg.validate_against_schema()
    results = list(results)
    by_family = {r.family: r for r in results}
    if len(by_family) != len(results):
        raise RetroMiningError("duplicate FamilyResult for a predictor family")
    missing = [f for f in prereg.predictor_families if f not in by_family]
    if missing:
        raise RetroMiningError(
            f"missing preregistered family results {missing}: the gate "
            "evaluates exactly the preregistered families (fail closed)"
        )
    extra = [f for f in by_family if f not in prereg.predictor_families]
    if extra:
        raise RetroMiningError(
            f"unpreregistered family results {extra}: post-hoc families cannot "
            "enter the sealed gate (fail closed)"
        )

    dispositions: dict[str, str] = {}
    for family in sorted(prereg.predictor_families):
        result = by_family[family]
        disposition = _family_disposition(prereg, result)
        if disposition == "legally_rejected":
            # mechanical re-verification: rejection is impossible unless the
            # preregistered conditions hold
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
        "family_dispositions": dispositions,
        "family_results": [by_family[f].to_dict() for f in sorted(by_family)],
        "stratification_axes": list(STRATIFICATION_AXES),
        "claim_state": CLAIM_STATE,
        "physical_efficacy_claimed": False,
    }
    artifact = dict(artifact_body)
    artifact["report_sha256"] = sha256_bytes(canonical_json(artifact_body))
    artifact["decision_id"] = "RAC-CTM-RETRO-DECISION-" + artifact["report_sha256"][:16]
    return artifact


def verify_decision(artifact: dict[str, Any]) -> None:
    """Fail-closed verification of a sealed decision artifact: schema,
    derived hash, decision-state enum, and rejection legality."""
    if not isinstance(artifact, dict):
        raise RetroMiningError("decision artifact must be an object")
    schema = json.loads(_DECISION_SCHEMA_PATH.read_text())
    try:
        jsonschema.validate(artifact, schema)
    except jsonschema.ValidationError as exc:
        raise RetroMiningError(
            f"decision artifact fails ctm_retro_decision_v1 schema: {exc.message}"
        ) from exc
    body = {k: v for k, v in artifact.items() if k not in ("report_sha256", "decision_id")}
    if sha256_bytes(canonical_json(body)) != artifact["report_sha256"]:
        raise RetroMiningError(
            "decision artifact report_sha256 does not re-derive: the sealed "
            "report was tampered with or asserted (fail closed)"
        )
    if artifact["decision"] == "REJECT_HYPOTHESIS_FAMILY":
        dispositions = artifact["family_dispositions"]
        if not dispositions or any(d != "legally_rejected" for d in dispositions.values()):
            raise RetroMiningError(
                "REJECT_HYPOTHESIS_FAMILY artifact with a non-rejected family "
                "disposition is structurally impossible and refused (fail closed)"
            )

"""SPEC-16 — External-benchmark adapter: external fabrication-delta cohorts.

Lesson L17: externally captured garment images (e.g. BadPatch/AdvT-shirt-1K)
are NOT equivalent to CTM-controlled physical measurements. This module
ingests an external fabricated-garment dataset as a registered external
cohort with a strict secondary-evidence ceiling.

Hard rules (fail closed with :class:`ExternalCohortError`):

- Every external observation is classified ``external_physical_observation``
  (a SECONDARY evidence class). Its claim ceiling is EXPLORATORY /
  observational unless the source independently satisfies the CTM
  physical-channel requirements of SPEC-10 (an identified, validated
  :class:`~ruthless_pipeline.ctm.channel.ChannelRecord`).
- Promotion of an external observation to CTM-controlled physical efficacy
  evidence is refused unconditionally (:func:`require_secondary_only` and the
  :func:`promote_to_controlled_efficacy` trap).
- Channel completeness fields (camera / isp / codec / resize / lighting /
  geometry) are explicit ``known | unknown | inferred``. An unknown never
  silently inherits a CTM channel identity.
- Fabrication/capture deltas between a digital master genome and the
  observed physical realization route through the existing genome compare
  (:func:`ruthless_pipeline.ctm.compare.compare_genomes`); Genome v1 is
  measured, never modified.
- Digital-master and external-fabricated cohorts are NEVER pooled without an
  explicit cohort term (:func:`build_analysis_pool` fails closed).

Additive: no frozen schema, Genome v1, or CTM-A contract is mutated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .channel import ChannelRecord, require_strong_physical_eligible
from .compare import ComparisonReport, compare_genomes
from .errors import CTMBridgeError

EXTERNAL_OBSERVATION_SCHEMA_VERSION = "rac-ctm-external-observation/1.0"

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "ctm_external_observation_v1.schema.json"
)


class ExternalCohortError(CTMBridgeError):
    """External-cohort contract violated (SPEC-16). Fail closed."""


#: Secondary-evidence class for every external observation (SPEC-16).
EVIDENCE_CLASS = "external_physical_observation"

#: Claim ceiling for external observations without an independent CTM
#: physical-channel qualification.
CLAIM_CEILING_EXPLORATORY = "EXPLORATORY"

#: Explicit channel-completeness values (aligned with SPEC-10 sentinels).
COMPLETENESS_VALUES = frozenset({"known", "unknown", "inferred"})

#: The six channel-completeness fields required on every observation.
CHANNEL_COMPLETENESS_FIELDS = (
    "camera",
    "isp",
    "codec",
    "resize",
    "lighting",
    "geometry",
)

#: Distinguishable cohorts feeding SPEC-7; never silently pooled.
COHORTS = frozenset({"digital_master", "external_fabricated"})

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
# Dataset provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalDatasetProvenance:
    """Registered provenance for an external dataset (SPEC-16 rule 1)."""

    dataset_name: str
    version: str
    source_paper_ref: str
    license: str
    registered_utc: str

    def __post_init__(self) -> None:
        for name in ("dataset_name", "version", "source_paper_ref", "license", "registered_utc"):
            if not getattr(self, name):
                raise ExternalCohortError(
                    f"dataset provenance field {name!r} is required: an external "
                    "dataset without full provenance cannot enter the registry "
                    "(fail closed)"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "version": self.version,
            "source_paper_ref": self.source_paper_ref,
            "license": self.license,
            "registered_utc": self.registered_utc,
        }

    def provenance_sha256(self) -> str:
        return sha256_bytes(canonical_json(self.to_dict()))


#: The canonical AdvT-shirt-1K registration (SPEC-16 seed dataset).
def advtshirt_1k_provenance(*, registered_utc: str = "2026-04-01") -> ExternalDatasetProvenance:
    return ExternalDatasetProvenance(
        dataset_name="AdvT-shirt-1K",
        version="badpatch-advtshirt-1k",
        source_paper_ref="BadPatch/AdvT-shirt-1K source paper (external)",
        license="see-upstream",
        registered_utc=registered_utc,
    )


# ---------------------------------------------------------------------------
# External observation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalObservation:
    """One external fabricated-garment observation (secondary evidence).

    ``genome_measurement_sha256`` pins the Pattern Genome v1 measurement
    extracted from the observed image (extraction happens via the genome
    adapter; Genome v1 itself is never modified).
    """

    artifact_ref: str
    dataset: ExternalDatasetProvenance
    genome_measurement_sha256: str
    channel_completeness: dict[str, str] = field(default_factory=dict)
    schema_version: str = EXTERNAL_OBSERVATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EXTERNAL_OBSERVATION_SCHEMA_VERSION:
            raise ExternalCohortError(
                f"unsupported external observation schema_version: "
                f"{self.schema_version!r}"
            )
        if not self.artifact_ref:
            raise ExternalCohortError("artifact_ref is required (fail closed)")
        if not _is_sha256(self.genome_measurement_sha256):
            raise ExternalCohortError(
                "genome_measurement_sha256 must be a lowercase 64-hex sha256 "
                "pinning the extracted Genome v1 measurement (fail closed)"
            )
        completeness = dict(self.channel_completeness)
        for name in CHANNEL_COMPLETENESS_FIELDS:
            value = completeness.get(name)
            if value is None:
                raise ExternalCohortError(
                    f"channel_completeness.{name} is missing: every channel "
                    "field must be explicitly known | unknown | inferred — an "
                    "absent field is not an unknown, it is a contract violation "
                    "(fail closed)"
                )
            if value not in COMPLETENESS_VALUES:
                raise ExternalCohortError(
                    f"channel_completeness.{name} = {value!r}; allowed: "
                    f"{sorted(COMPLETENESS_VALUES)} (fail closed)"
                )
        extra = set(completeness) - set(CHANNEL_COMPLETENESS_FIELDS)
        if extra:
            raise ExternalCohortError(
                f"unknown channel_completeness fields {sorted(extra)}; allowed: "
                f"{list(CHANNEL_COMPLETENESS_FIELDS)} (fail closed)"
            )
        object.__setattr__(self, "channel_completeness", completeness)

    # -- derived properties ---------------------------------------------------

    @property
    def evidence_class(self) -> str:
        """Always the secondary-evidence class; never user-asserted."""
        return EVIDENCE_CLASS

    @property
    def cohort(self) -> str:
        return "external_fabricated"

    @property
    def channel_fully_known(self) -> bool:
        return all(
            self.channel_completeness[f] == "known"
            for f in CHANNEL_COMPLETENESS_FIELDS
        )

    @property
    def observation_id(self) -> str:
        return "RAC-CTM-EXT-" + sha256_bytes(canonical_json(self._content_dict()))[:16]

    # -- serialization ---------------------------------------------------------

    def _content_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_ref": self.artifact_ref,
            "dataset": self.dataset.to_dict(),
            "genome_measurement_sha256": self.genome_measurement_sha256,
            "channel_completeness": dict(sorted(self.channel_completeness.items())),
            "evidence_class": self.evidence_class,
            "cohort": self.cohort,
        }

    def to_dict(self) -> dict[str, Any]:
        d = {"observation_id": self.observation_id}
        d.update(self._content_dict())
        return d

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    def observation_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def validate_against_schema(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(self.to_dict(), schema)
        except jsonschema.ValidationError as exc:
            raise ExternalCohortError(
                f"external observation fails ctm_external_observation_v1 "
                f"schema: {exc.message}"
            ) from exc

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExternalObservation":
        """Parse a serialized observation, REFUSING an asserted id or an
        asserted primary-evidence class that disagrees with the contract."""
        if not isinstance(payload, dict):
            raise ExternalCohortError("external observation payload must be an object")
        evidence_class = payload.get("evidence_class", EVIDENCE_CLASS)
        if evidence_class != EVIDENCE_CLASS:
            raise ExternalCohortError(
                f"evidence_class {evidence_class!r} refused: external "
                f"observations are always {EVIDENCE_CLASS!r} (secondary "
                "evidence); an external dataset may not present itself as "
                "CTM-controlled physical evidence (fail closed)"
            )
        dataset_payload = payload.get("dataset", {})
        record = cls(
            artifact_ref=payload.get("artifact_ref", ""),
            dataset=ExternalDatasetProvenance(
                dataset_name=dataset_payload.get("dataset_name", ""),
                version=dataset_payload.get("version", ""),
                source_paper_ref=dataset_payload.get("source_paper_ref", ""),
                license=dataset_payload.get("license", ""),
                registered_utc=dataset_payload.get("registered_utc", ""),
            ),
            genome_measurement_sha256=payload.get("genome_measurement_sha256", ""),
            channel_completeness=dict(payload.get("channel_completeness", {})),
            schema_version=payload.get("schema_version", ""),
        )
        asserted = payload.get("observation_id")
        if asserted is not None and asserted != record.observation_id:
            raise ExternalCohortError(
                f"asserted observation_id {asserted!r} disagrees with derived "
                f"id {record.observation_id!r}: ids are content-derived, never "
                "user-asserted (fail closed)"
            )
        return record


# ---------------------------------------------------------------------------
# Claim ceiling and promotion trap
# ---------------------------------------------------------------------------


def claim_ceiling(
    observation: ExternalObservation,
    *,
    ctm_channel: ChannelRecord | None = None,
) -> str:
    """Derive the claim ceiling for an external observation.

    EXPLORATORY/observational by construction. The ceiling rises only when an
    independent SPEC-10 channel record with full camera identity accompanies
    the observation AND passes the strong-physical gate — i.e. the source
    independently satisfies CTM physical-channel requirements.
    """
    if ctm_channel is None:
        return CLAIM_CEILING_EXPLORATORY
    try:
        require_strong_physical_eligible(ctm_channel)
    except Exception:
        return CLAIM_CEILING_EXPLORATORY
    if not observation.channel_fully_known:
        return CLAIM_CEILING_EXPLORATORY
    return "PHYSICAL_SINGLE_CHANNEL"


def require_secondary_only(observation: ExternalObservation) -> None:
    """Attestation helper: external observations are secondary evidence.

    This function exists so call sites must name the rule. It never raises
    for a well-formed observation; the trap below is what refuses promotion.
    """
    if observation.evidence_class != EVIDENCE_CLASS:  # pragma: no cover
        raise ExternalCohortError("evidence class invariant broken")


def promote_to_controlled_efficacy(observation: ExternalObservation) -> None:
    """Promotion trap: ALWAYS refuses. External datasets are secondary
    observations and can never be presented as CTM-controlled physical
    efficacy evidence (SPEC-16; execution-contract hard rule)."""
    raise ExternalCohortError(
        f"promotion refused for {observation.observation_id}: external "
        "physical observations are secondary evidence with claim ceiling "
        "EXPLORATORY/observational and can never be presented as "
        "CTM-controlled physical efficacy evidence (fail closed, unconditional)"
    )


# ---------------------------------------------------------------------------
# Fabrication delta (routes through the existing genome compare)
# ---------------------------------------------------------------------------


def fabrication_delta(
    master_genome: Any,
    observed_genome: Any,
    *,
    observation: ExternalObservation,
) -> dict[str, Any]:
    """External fabrication/capture genome delta between a digital master and
    the observed physical realization (SPEC-16 rule 5).

    Routes through :func:`compare_genomes` — the delta machinery is not
    reimplemented. The result is labeled with the observation's secondary
    evidence class and EXPLORATORY claim state.
    """
    report: ComparisonReport = compare_genomes(
        master_genome, observed_genome, evidence_tier="DIGITAL"
    )
    return {
        "kind": "external_fabrication_delta",
        "observation_id": observation.observation_id,
        "evidence_class": EVIDENCE_CLASS,
        "claim_state": report.claim_state,
        "physical_efficacy_claimed": False,
        "overall_distance": report.overall_distance,
        "identical": report.identical,
        "families": report.to_dict()["families"],
    }


# ---------------------------------------------------------------------------
# Cohort pooling guard
# ---------------------------------------------------------------------------


def build_analysis_pool(
    members: Iterable[tuple[str, Any]],
    *,
    cohort_term_declared: bool = False,
) -> dict[str, Any]:
    """Build an analysis pool from ``(cohort, payload)`` members.

    SPEC-16 rule 6 / spec doc: digital masters and external fabricated
    observations are two distinguishable cohorts feeding SPEC-7; they are
    NEVER pooled without an explicit cohort term. Unknown cohorts fail
    closed.
    """
    members = list(members)
    if not members:
        raise ExternalCohortError("cannot build an empty analysis pool")
    seen: set[str] = set()
    for cohort, _ in members:
        if cohort not in COHORTS:
            raise ExternalCohortError(
                f"unknown cohort {cohort!r}; allowed: {sorted(COHORTS)} "
                "(fail closed)"
            )
        seen.add(cohort)
    if len(seen) > 1 and not cohort_term_declared:
        raise ExternalCohortError(
            f"pool mixes cohorts {sorted(seen)} without an explicit cohort "
            "term: digital masters and external fabricated observations are "
            "never pooled silently (fail closed)"
        )
    return {
        "cohorts": sorted(seen),
        "size": len(members),
        "cohort_term_declared": bool(cohort_term_declared),
        "claim_ceiling": CLAIM_CEILING_EXPLORATORY,
        "physical_efficacy_claimed": False,
    }

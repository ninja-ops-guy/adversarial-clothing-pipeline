"""SW-12: Physical Dataset Contract + Validator (future measured data).

Defines the contract for a FUTURE physical observation dataset and a
fail-closed validator. No measured data exists today; every fixture used
with this module is explicitly tagged ``synthetic_pipeline_validation_only``.

Hard rules:
- The ``measured`` flag CANNOT be inferred or defaulted: an absent flag
  raises :class:`MeasuredFlagAbsentError`.
- Duplicate trial IDs are rejected (:class:`DuplicateTrialIdError`).
- Unbound provenance is rejected (:class:`UnboundProvenanceError`).
- Candidate/control pairing must be complete and one-to-one
  (:class:`PairingError`); the same specimen cannot appear on both arms
  (:class:`LeakageError`).
- The schema version is frozen once released: the contract refuses any
  ``schema_version`` other than :data:`SCHEMA_VERSION` via the shared
  ``certification.schema_version.require_schema_version`` guard, and
  ``frozen_once_released`` is a contract-level constant (``True``) that the
  validator verifies is present and true.

Deterministic, content-addressed: observation ids are
``"RAC-PHYDS-" + sha256(canonical_record)[:16]`` using
``pattern_genome.canonical`` helpers. No wall-clock, no RNG.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes
from ruthless_pipeline.certification.schema_version import require_schema_version
from ruthless_pipeline.future_evidence.errors import (
    DuplicateTrialIdError,
    InconsistentIdentityError,
    LeakageError,
    MeasuredFlagAbsentError,
    MissingMetadataError,
    PairingError,
    PromotionImpossibleError,
    UnboundProvenanceError,
)

SCHEMA_VERSION = "rac-physical-dataset/1.0"
SCHEMA_ID = "https://rac.local/schemas/physical_dataset_contract_v1.schema.json"

#: Once released, this schema version is frozen. This constant is part of the
#: contract and is checked by the validator; it can never flip to False for
#: version 1.0 (a change requires a NEW schema version).
FROZEN_ONCE_RELEASED = True

SYNTHETIC_EVIDENCE_CLASS = "synthetic_pipeline_validation_only"
MEASURED_EVIDENCE_CLASS = "measured_physical_capture"

_ID_PREFIX = "RAC-PHYDS-"

_REQUIRED_METADATA_KEYS = (
    "capture_condition",
    "camera",
    "environment",
    "specimen",
    "calibration_refs",
    "observation_medium",
)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        c in "0123456789abcdef" for c in value
    )


def observation_id(record: Dict[str, Any]) -> str:
    """Content-addressed id: RAC-PHYDS- + sha256(canonical)[:16]."""
    d = dict(record)
    d.pop("observation_id", None)
    return _ID_PREFIX + sha256_bytes(canonical_json(d))[:16]


@dataclass(frozen=True)
class PhysicalObservation:
    """One future physical-dataset observation.

    ``measured`` is Optional[bool] on purpose: None means ABSENT and must be
    refused — the flag can never be inferred or defaulted. Every current
    fixture sets measured=False plus evidence_class
    ``synthetic_pipeline_validation_only``.
    """

    schema_version: str
    dataset_id: str
    dataset_version: str
    trial_id: str
    arm: str  # "candidate" | "control"
    paired_trial_id: str
    capture_condition: str
    camera: Dict[str, Any]
    environment: Dict[str, Any]
    specimen: Dict[str, Any]
    calibration_refs: Tuple[str, ...]
    observation_medium: str
    invalidity_reason: Optional[str]
    evaluation_role: str  # "calibration" | "evaluation"
    measured: Optional[bool]
    evidence_class: str
    specimen_sha256: str
    provenance_ref: str  # content id or 64-hex sha binding origin
    outcome_ref: Optional[str]  # pointer to outcome record (may be unmeasured)
    frozen_once_released: bool = FROZEN_ONCE_RELEASED

    def to_record(self) -> Dict[str, Any]:
        rec: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "trial_id": self.trial_id,
            "arm": self.arm,
            "paired_trial_id": self.paired_trial_id,
            "capture_condition": self.capture_condition,
            "camera": dict(self.camera),
            "environment": dict(self.environment),
            "specimen": dict(self.specimen),
            "calibration_refs": list(self.calibration_refs),
            "observation_medium": self.observation_medium,
            "invalidity_reason": self.invalidity_reason,
            "evaluation_role": self.evaluation_role,
            "measured": self.measured,
            "evidence_class": self.evidence_class,
            "specimen_sha256": self.specimen_sha256,
            "provenance_ref": self.provenance_ref,
            "outcome_ref": self.outcome_ref,
            "frozen_once_released": self.frozen_once_released,
        }
        rec["observation_id"] = observation_id(rec)
        return rec


class PhysicalDatasetValidator:
    """Fail-closed validator for future physical datasets.

    Operates today exclusively on explicitly-synthetic fixtures.
    """

    def validate_observation(self, obs: PhysicalObservation) -> Dict[str, Any]:
        rec = obs.to_record()
        require_schema_version(
            {"schema_version": rec["schema_version"]},
            SCHEMA_VERSION,
            label=f"physical observation {rec['trial_id']!r}",
        )
        if rec["frozen_once_released"] is not True:
            raise MissingMetadataError(
                "physical dataset contract is frozen-once-released; "
                "frozen_once_released must be true"
            )
        if rec["measured"] is None:
            raise MeasuredFlagAbsentError(
                f"observation {rec['trial_id']!r}: measured flag absent; "
                "it cannot be inferred or defaulted"
            )
        if rec["arm"] not in ("candidate", "control"):
            raise PairingError(f"trial {rec['trial_id']!r}: arm must be candidate|control")
        if rec["evaluation_role"] not in ("calibration", "evaluation"):
            raise MissingMetadataError(
                f"trial {rec['trial_id']!r}: evaluation_role must be calibration|evaluation"
            )
        for key in _REQUIRED_METADATA_KEYS:
            value = rec[key]
            if value is None or value == {} or value == [] or value == "":
                raise MissingMetadataError(
                    f"trial {rec['trial_id']!r}: required metadata {key!r} missing/empty"
                )
        if not _is_sha256(rec["specimen_sha256"]):
            raise MissingMetadataError(
                f"trial {rec['trial_id']!r}: specimen_sha256 must be lowercase 64-hex"
            )
        prov = rec["provenance_ref"]
        if not (isinstance(prov, str) and (prov.startswith("RAC-") or _is_sha256(prov))):
            raise UnboundProvenanceError(
                f"trial {rec['trial_id']!r}: provenance_ref must be a RAC- content id "
                "or a 64-hex sha256; unbound provenance is refused"
            )
        if rec["measured"] is False and rec["evidence_class"] != SYNTHETIC_EVIDENCE_CLASS:
            raise PromotionImpossibleError(
                f"trial {rec['trial_id']!r}: non-measured observation must carry "
                f"evidence_class {SYNTHETIC_EVIDENCE_CLASS!r}"
            )
        if rec["measured"] is True:
            if rec["evidence_class"] != MEASURED_EVIDENCE_CLASS:
                raise PromotionImpossibleError(
                    f"trial {rec['trial_id']!r}: measured=True requires evidence_class "
                    f"{MEASURED_EVIDENCE_CLASS!r}; synthetic evidence cannot be promoted"
                )
            if not rec["outcome_ref"]:
                raise MissingMetadataError(
                    f"trial {rec['trial_id']!r}: measured observation requires outcome_ref"
                )
        return rec

    def validate_dataset(
        self, observations: Iterable[PhysicalObservation]
    ) -> Dict[str, Any]:
        """Validate a full dataset: pairing, duplicates, leakage, identities."""
        records = [self.validate_observation(o) for o in observations]
        by_trial: Dict[str, Dict[str, Any]] = {}
        # A specimen may be observed by multiple trials; identity is
        # INCONSISTENT only when the same specimen hash carries conflicting
        # specimen metadata.
        specimen_meta: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            tid = rec["trial_id"]
            if tid in by_trial:
                raise DuplicateTrialIdError(f"duplicate trial_id {tid!r} rejected")
            by_trial[tid] = rec
            spec = rec["specimen_sha256"]
            meta = specimen_meta.setdefault(spec, rec["specimen"])
            if meta != rec["specimen"]:
                raise InconsistentIdentityError(
                    f"specimen {spec[:12]}... carries conflicting metadata across trials"
                )
        # Pairing: complete, one-to-one, opposite arms, mutual.
        seen_pairs: set = set()
        for rec in records:
            tid, pid = rec["trial_id"], rec["paired_trial_id"]
            if tid in seen_pairs:
                continue
            if pid not in by_trial:
                raise PairingError(f"trial {tid!r}: paired_trial_id {pid!r} not in dataset")
            partner = by_trial[pid]
            if partner["paired_trial_id"] != tid:
                raise PairingError(f"pairing {tid!r}<->{pid!r} is not mutual")
            if partner["arm"] == rec["arm"]:
                raise PairingError(f"pairing {tid!r}<->{pid!r}: both arms identical")
            if partner["specimen_sha256"] == rec["specimen_sha256"]:
                raise LeakageError(
                    f"pairing {tid!r}<->{pid!r}: same specimen on both arms (leakage)"
                )
            seen_pairs.add(pid)
        # Calibration/evaluation leakage: no specimen may appear in both roles.
        role_by_specimen: Dict[str, str] = {}
        for rec in records:
            spec, role = rec["specimen_sha256"], rec["evaluation_role"]
            prev = role_by_specimen.setdefault(spec, role)
            if prev != role:
                raise LeakageError(
                    f"specimen {spec[:12]}... appears in both calibration and "
                    "evaluation roles (leakage)"
                )
        return {
            "dataset_ids": sorted({r["dataset_id"] for r in records}),
            "n_observations": len(records),
            "evidence_class": SYNTHETIC_EVIDENCE_CLASS
            if all(r["measured"] is False for r in records)
            else "mixed",
            "contains_measured": any(r["measured"] is True for r in records),
        }


def assert_no_physical_claim(summary: Dict[str, Any]) -> None:
    """Hard guard: refuse any claim promotion from synthetic-only data."""
    if not summary.get("contains_measured"):
        return
    if summary.get("evidence_class") != "mixed":
        raise PromotionImpossibleError(
            "synthetic-only dataset cannot produce a measured/physical claim"
        )

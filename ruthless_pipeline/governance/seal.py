"""Deterministic cohort sealing and verification (Governance Pass 3).

The original ``seal_cohort`` helper remains available for pre-adoption fixtures.
Prospective Governance-v1 cohorts use ``seal_governed_cohort``: a fail-closed
orchestrator that validates both manifests, verifies lineage/artifacts and
threshold provenance, emits optional provenance metadata, and only then moves
the Pass-1 state machine from PREFLIGHT to SEALED.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping, Protocol

import jsonschema

from .constraints import ConstraintRegistryError, ConstraintSetRegistry
from .ids import GovernanceId, IdKind
from .state import ExperimentState, GovernanceStateMachine, StateTransitionError
from .validators import GovernanceValidationError, validate_manifest


class SealError(RuntimeError):
    pass


def _canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Legacy prototype seal (read/test compatibility)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CohortSeal:
    seal_id: str
    cohort_id: str
    experiment_id: str
    constraint_id: str
    code_commit: str
    seed: int
    diagnostic_threshold_hash: str
    manifest_hash: str
    artifact_hashes: dict[str, str]
    seal_hash: str
    state: str = "SEALED"


def _validate_manifest(manifest: Mapping[str, object]) -> None:
    required = {
        "cohort_id", "experiment_id", "constraint_id", "code_commit", "seed",
        "diagnostic_threshold_hash", "specimen_ids", "artifacts",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise SealError(f"missing manifest fields: {', '.join(missing)}")
    if not isinstance(manifest["seed"], int):
        raise SealError("seed must be an integer")
    specimen_ids = manifest["specimen_ids"]
    if not isinstance(specimen_ids, list) or len(specimen_ids) != len(set(specimen_ids)):
        raise SealError("specimen_ids must be a duplicate-free list")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, dict):
        raise SealError("artifacts must map path to sha256")
    threshold_hash = manifest["diagnostic_threshold_hash"]
    if not isinstance(threshold_hash, str) or len(threshold_hash) != 64:
        raise SealError("diagnostic_threshold_hash must be sha256")


def seal_cohort(manifest: Mapping[str, object], artifact_bytes: Mapping[str, bytes]) -> CohortSeal:
    _validate_manifest(manifest)
    expected = manifest["artifacts"]
    assert isinstance(expected, dict)
    if set(expected) != set(artifact_bytes):
        raise SealError("artifact set differs from manifest")
    observed: dict[str, str] = {}
    for path, data in artifact_bytes.items():
        digest = sha256(data).hexdigest()
        observed[path] = digest
        if expected[path] != digest:
            raise SealError(f"artifact hash mismatch: {path}")
    manifest_hash = sha256(_canonical(dict(manifest))).hexdigest()
    body = {
        "cohort_id": manifest["cohort_id"],
        "experiment_id": manifest["experiment_id"],
        "constraint_id": manifest["constraint_id"],
        "code_commit": manifest["code_commit"],
        "seed": manifest["seed"],
        "diagnostic_threshold_hash": manifest["diagnostic_threshold_hash"],
        "manifest_hash": manifest_hash,
        "artifact_hashes": observed,
        "state": "SEALED",
    }
    seal_hash = sha256(_canonical(body)).hexdigest()
    return CohortSeal(seal_id=f"RAC-SEAL-{seal_hash[:16].upper()}", seal_hash=seal_hash, **body)


def verify_seal(seal: CohortSeal, manifest: Mapping[str, object], artifact_bytes: Mapping[str, bytes]) -> None:
    rebuilt = seal_cohort(manifest, artifact_bytes)
    if asdict(rebuilt) != asdict(seal):
        raise SealError("seal does not match current manifest/artifacts")


# ---------------------------------------------------------------------------
# Adopted Governance-v1 seal
# ---------------------------------------------------------------------------

class TimestampAdapter(Protocol):
    """Optional RFC-3161-style adapter interface.

    Implementations may wrap a real RFC 3161 service.  The external timestamp
    token is deliberately excluded from ``seal_hash`` so the scientific seal
    identity remains deterministic for identical complete inputs.
    """

    def timestamp(self, digest: str) -> str:
        ...

    def verify(self, digest: str, token: str) -> bool:
        ...


@dataclass(frozen=True)
class GovernanceCohortSeal:
    seal_id: str
    cohort_id: str
    experiment_id: str
    sampling_id: str
    constraint_set_id: str
    constraint_record_hash: str
    code_commit: str
    code_version: str
    pipeline_id: str
    pipeline_version: str
    calibration_id: str
    calibration_version: str
    seed: int
    sample_count: int
    diagnostic_threshold_hash: str
    sampling_manifest_hash: str
    cohort_manifest_hash: str
    artifact_hashes: dict[str, str]
    seal_hash: str
    git_signature_status: str = "UNAVAILABLE"
    git_signature_ref: str | None = None
    timestamp_token: str | None = None
    state: str = "SEALED"


_SCHEMA_DIR = Path(__file__).with_name("schemas")
_ADOPTED_SAMPLING_FIELDS = {
    "constraint_set_id",
    "sample_count",
    "sampler_version",
}
_ADOPTED_COHORT_FIELDS = {
    "sampling_id",
    "constraint_set_id",
    "code_commit",
    "code_version",
    "pipeline_id",
    "pipeline_version",
    "calibration_id",
    "calibration_version",
    "diagnostic_threshold_hash",
    "artifacts",
}
_GIT_SIGNATURE_STATES = {"VERIFIED", "UNVERIFIED", "UNAVAILABLE"}


def _schema_validate(kind: str, manifest: Mapping[str, object]) -> None:
    schema_path = _SCHEMA_DIR / f"{kind}.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(dict(manifest))
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        raise SealError(f"{kind}: JSON Schema validation failed: {exc}") from exc


def _require_adopted_manifest_fields(
    sampling_manifest: Mapping[str, object],
    cohort_manifest: Mapping[str, object],
) -> None:
    sampling_missing = sorted(_ADOPTED_SAMPLING_FIELDS - set(sampling_manifest))
    cohort_missing = sorted(_ADOPTED_COHORT_FIELDS - set(cohort_manifest))
    if sampling_missing:
        raise SealError(
            "sampling manifest is legacy/incomplete for Governance Pass 3: "
            + ", ".join(sampling_missing)
        )
    if cohort_missing:
        raise SealError(
            "cohort manifest is legacy/incomplete for Governance Pass 3: "
            + ", ".join(cohort_missing)
        )


def _canonical_id(value: object, expected: IdKind, field: str) -> str:
    try:
        parsed = GovernanceId.parse(value)  # type: ignore[arg-type]
    except Exception as exc:
        raise SealError(f"{field}: invalid governance identifier") from exc
    if parsed.kind is not expected or parsed.is_legacy_alias:
        raise SealError(f"{field}: adopted seal requires canonical RAC-{expected.value}-* identity")
    return parsed.canonical


def _registered_ids(values: Iterable[str], kind: IdKind, field: str) -> set[str]:
    return {_canonical_id(value, kind, field) for value in values}


def _validate_git_provenance(status: str, signature_ref: str | None) -> None:
    if status not in _GIT_SIGNATURE_STATES:
        raise SealError(f"unsupported git signature status: {status!r}")
    if status == "VERIFIED" and (not isinstance(signature_ref, str) or not signature_ref.strip()):
        raise SealError("VERIFIED git provenance requires git_signature_ref")


def _prepare_governed_core(
    sampling_manifest: Mapping[str, object],
    cohort_manifest: Mapping[str, object],
    artifact_bytes: Mapping[str, bytes],
    *,
    constraint_registry: ConstraintSetRegistry,
    registered_pipeline_ids: Iterable[str],
    registered_calibration_ids: Iterable[str],
    diagnostic_threshold_bytes: bytes,
    diagnostics_passed: bool,
) -> dict[str, object]:
    # Seal order 1-3: existence, JSON Schema, then semantic validation.
    if not sampling_manifest or not cohort_manifest:
        raise SealError("sampling and cohort manifests are both required")
    _schema_validate("sampling_manifest", sampling_manifest)
    _schema_validate("cohort_manifest", cohort_manifest)
    try:
        validate_manifest("sampling_manifest", dict(sampling_manifest))
        validate_manifest("cohort_manifest", dict(cohort_manifest))
    except GovernanceValidationError as exc:
        raise SealError(f"semantic manifest validation failed: {exc}") from exc
    _require_adopted_manifest_fields(sampling_manifest, cohort_manifest)

    # Seal order 4: referential integrity.
    experiment_id = _canonical_id(
        sampling_manifest["experiment_id"], IdKind.EXPERIMENT, "experiment_id"
    )
    if cohort_manifest["experiment_id"] != experiment_id:
        raise SealError("sampling/cohort experiment_id mismatch")
    sampling_id = _canonical_id(
        sampling_manifest["sampling_id"], IdKind.SAMPLING, "sampling_id"
    )
    if cohort_manifest["sampling_id"] != sampling_id:
        raise SealError("cohort sampling_id does not reference sampling manifest")
    constraint_set_id = _canonical_id(
        sampling_manifest["constraint_set_id"], IdKind.CONSTRAINT, "constraint_set_id"
    )
    if cohort_manifest["constraint_set_id"] != constraint_set_id:
        raise SealError("sampling/cohort constraint_set_id mismatch")
    try:
        constraint_record = constraint_registry.get(constraint_set_id)
    except ConstraintRegistryError as exc:
        raise SealError(f"unregistered constraint set: {constraint_set_id}") from exc

    pipeline_id = _canonical_id(cohort_manifest["pipeline_id"], IdKind.PIPELINE, "pipeline_id")
    calibration_id = _canonical_id(
        cohort_manifest["calibration_id"], IdKind.CALIBRATION, "calibration_id"
    )
    if pipeline_id not in _registered_ids(
        registered_pipeline_ids, IdKind.PIPELINE, "registered_pipeline_id"
    ):
        raise SealError(f"unregistered evaluation pipeline: {pipeline_id}")
    if calibration_id not in _registered_ids(
        registered_calibration_ids, IdKind.CALIBRATION, "registered_calibration_id"
    ):
        raise SealError(f"unregistered calibration state: {calibration_id}")

    sample_count = sampling_manifest["sample_count"]
    specimen_ids = cohort_manifest["specimen_ids"]
    assert isinstance(sample_count, int)
    assert isinstance(specimen_ids, list)
    if sample_count != len(specimen_ids):
        raise SealError(
            f"cohort count mismatch: sampling manifest declares {sample_count}, cohort has {len(specimen_ids)}"
        )

    # Seal order 5: exact artifact/hash verification.
    expected_artifacts = cohort_manifest["artifacts"]
    assert isinstance(expected_artifacts, dict)
    if set(expected_artifacts) != set(artifact_bytes):
        raise SealError("artifact set differs from adopted cohort manifest")
    observed_artifacts: dict[str, str] = {}
    for path in sorted(artifact_bytes):
        digest = sha256(artifact_bytes[path]).hexdigest()
        observed_artifacts[path] = digest
        if expected_artifacts[path] != digest:
            raise SealError(f"artifact hash mismatch: {path}")

    # Seal orders 6-7: immutable threshold binding + diagnostics gate.
    if not isinstance(diagnostic_threshold_bytes, bytes):
        raise SealError("diagnostic_threshold_bytes must be bytes")
    observed_threshold_hash = sha256(diagnostic_threshold_bytes).hexdigest()
    if cohort_manifest["diagnostic_threshold_hash"] != observed_threshold_hash:
        raise SealError("diagnostic threshold changed after cohort manifest generation")
    if diagnostics_passed is not True:
        raise SealError("diagnostics gate refused cohort sealing")

    constraint_record_hash = sha256(_canonical(constraint_record.to_dict())).hexdigest()
    sampling_manifest_hash = sha256(_canonical(dict(sampling_manifest))).hexdigest()
    cohort_manifest_hash = sha256(_canonical(dict(cohort_manifest))).hexdigest()

    return {
        "cohort_id": _canonical_id(cohort_manifest["cohort_id"], IdKind.COHORT, "cohort_id"),
        "experiment_id": experiment_id,
        "sampling_id": sampling_id,
        "constraint_set_id": constraint_set_id,
        "constraint_record_hash": constraint_record_hash,
        "code_commit": cohort_manifest["code_commit"],
        "code_version": cohort_manifest["code_version"],
        "pipeline_id": pipeline_id,
        "pipeline_version": cohort_manifest["pipeline_version"],
        "calibration_id": calibration_id,
        "calibration_version": cohort_manifest["calibration_version"],
        "seed": sampling_manifest["seed"],
        "sample_count": sample_count,
        "diagnostic_threshold_hash": observed_threshold_hash,
        "sampling_manifest_hash": sampling_manifest_hash,
        "cohort_manifest_hash": cohort_manifest_hash,
        "artifact_hashes": observed_artifacts,
        "state": "SEALED",
    }


def _seal_from_core(
    core: Mapping[str, object],
    *,
    git_signature_status: str,
    git_signature_ref: str | None,
    timestamp_token: str | None,
) -> GovernanceCohortSeal:
    deterministic_body = dict(core)
    seal_hash = sha256(_canonical(deterministic_body)).hexdigest()
    return GovernanceCohortSeal(
        seal_id=f"RAC-SEAL-{seal_hash[:16].upper()}",
        seal_hash=seal_hash,
        git_signature_status=git_signature_status,
        git_signature_ref=git_signature_ref,
        timestamp_token=timestamp_token,
        **deterministic_body,
    )


def seal_governed_cohort(
    sampling_manifest: Mapping[str, object],
    cohort_manifest: Mapping[str, object],
    artifact_bytes: Mapping[str, bytes],
    *,
    constraint_registry: ConstraintSetRegistry,
    registered_pipeline_ids: Iterable[str],
    registered_calibration_ids: Iterable[str],
    diagnostic_threshold_bytes: bytes,
    diagnostics_passed: bool,
    state_machine: GovernanceStateMachine,
    seal_event_id: str,
    created_at: str | None = None,
    git_signature_status: str = "UNAVAILABLE",
    git_signature_ref: str | None = None,
    timestamp_adapter: TimestampAdapter | None = None,
) -> GovernanceCohortSeal:
    """Validate, bind, and ledger-seal a prospective Governance-v1 cohort."""
    if not isinstance(state_machine, GovernanceStateMachine):
        raise SealError("state_machine must be a GovernanceStateMachine")
    if state_machine.state is not ExperimentState.PREFLIGHT:
        raise SealError(
            f"seal requires experiment state PREFLIGHT, got {state_machine.state.value}"
        )
    _canonical_id(seal_event_id, IdKind.EVENT, "seal_event_id")
    _validate_git_provenance(git_signature_status, git_signature_ref)

    core = _prepare_governed_core(
        sampling_manifest,
        cohort_manifest,
        artifact_bytes,
        constraint_registry=constraint_registry,
        registered_pipeline_ids=registered_pipeline_ids,
        registered_calibration_ids=registered_calibration_ids,
        diagnostic_threshold_bytes=diagnostic_threshold_bytes,
        diagnostics_passed=diagnostics_passed,
    )
    if state_machine.experiment_id != core["experiment_id"]:
        raise SealError("state machine experiment_id does not match sealed cohort")

    # Seal order 8: provenance/timestamp envelope.  It is not part of the
    # deterministic scientific seal identity.
    provisional = _seal_from_core(
        core,
        git_signature_status=git_signature_status,
        git_signature_ref=git_signature_ref,
        timestamp_token=None,
    )
    timestamp_token: str | None = None
    if timestamp_adapter is not None:
        try:
            timestamp_token = timestamp_adapter.timestamp(provisional.seal_hash)
        except Exception as exc:
            raise SealError(f"timestamp adapter failed: {exc}") from exc
        if not isinstance(timestamp_token, str) or not timestamp_token:
            raise SealError("timestamp adapter returned an empty token")

    seal = _seal_from_core(
        core,
        git_signature_status=git_signature_status,
        git_signature_ref=git_signature_ref,
        timestamp_token=timestamp_token,
    )

    # Seal order 9: append ledger event before mutating state.  Pass-1 state
    # semantics guarantee fail-closed behavior if append/transition fails.
    try:
        state_machine.transition(
            ExperimentState.SEALED,
            event_id=seal_event_id,
            created_at=created_at,
            payload={
                "seal_id": seal.seal_id,
                "seal_hash": seal.seal_hash,
                "cohort_id": seal.cohort_id,
                "sampling_manifest_hash": seal.sampling_manifest_hash,
                "cohort_manifest_hash": seal.cohort_manifest_hash,
            },
        )
    except StateTransitionError as exc:
        raise SealError(f"SEALED transition denied: {exc}") from exc
    return seal


def verify_governed_seal(
    seal: GovernanceCohortSeal,
    sampling_manifest: Mapping[str, object],
    cohort_manifest: Mapping[str, object],
    artifact_bytes: Mapping[str, bytes],
    *,
    constraint_registry: ConstraintSetRegistry,
    registered_pipeline_ids: Iterable[str],
    registered_calibration_ids: Iterable[str],
    diagnostic_threshold_bytes: bytes,
    diagnostics_passed: bool,
    timestamp_adapter: TimestampAdapter | None = None,
) -> None:
    """Independently re-derive a Governance-v1 seal without changing state."""
    if not isinstance(seal, GovernanceCohortSeal) or seal.state != "SEALED":
        raise SealError("invalid Governance-v1 seal object/state")
    _validate_git_provenance(seal.git_signature_status, seal.git_signature_ref)
    core = _prepare_governed_core(
        sampling_manifest,
        cohort_manifest,
        artifact_bytes,
        constraint_registry=constraint_registry,
        registered_pipeline_ids=registered_pipeline_ids,
        registered_calibration_ids=registered_calibration_ids,
        diagnostic_threshold_bytes=diagnostic_threshold_bytes,
        diagnostics_passed=diagnostics_passed,
    )
    rebuilt = _seal_from_core(
        core,
        git_signature_status=seal.git_signature_status,
        git_signature_ref=seal.git_signature_ref,
        timestamp_token=seal.timestamp_token,
    )
    if asdict(rebuilt) != asdict(seal):
        raise SealError("Governance-v1 seal does not match current complete inputs")
    if seal.timestamp_token is not None and timestamp_adapter is not None:
        try:
            timestamp_valid = timestamp_adapter.verify(seal.seal_hash, seal.timestamp_token)
        except Exception as exc:
            raise SealError(f"timestamp verification failed: {exc}") from exc
        if timestamp_valid is not True:
            raise SealError("timestamp token does not verify against seal hash")

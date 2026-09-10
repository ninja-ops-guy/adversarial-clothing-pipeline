"""Governed CTM intake boundary for prospective cohorts."""
from __future__ import annotations

from typing import Iterable, Mapping

from ruthless_pipeline.governance.constraints import ConstraintSetRegistry
from ruthless_pipeline.governance.seal import (
    CohortSeal,
    GovernanceCohortSeal,
    SealError,
    TimestampAdapter,
    verify_governed_seal,
    verify_seal,
)


class CTMIntakeError(RuntimeError):
    pass


def accept_governed_cohort(
    seal: CohortSeal | GovernanceCohortSeal | None,
    manifest: Mapping[str, object],
    artifact_bytes: Mapping[str, bytes],
    *,
    sampling_manifest: Mapping[str, object] | None = None,
    constraint_registry: ConstraintSetRegistry | None = None,
    registered_pipeline_ids: Iterable[str] = (),
    registered_calibration_ids: Iterable[str] = (),
    diagnostic_threshold_bytes: bytes | None = None,
    diagnostics_passed: bool | None = None,
    timestamp_adapter: TimestampAdapter | None = None,
) -> CohortSeal | GovernanceCohortSeal:
    """Law 2: CTM refuses unsealed or unverifiable cohort evidence.

    The original three-argument form remains valid for prototype ``CohortSeal``
    records.  Governance-v1 seals require the complete independent-verification
    context so CTM cannot accept a detached seal object on trust alone.
    """
    if seal is None:
        raise CTMIntakeError("CTM intake denied: cohort is unsealed")
    if seal.state != "SEALED":
        raise CTMIntakeError(f"CTM intake denied: cohort state is {seal.state!r}")

    try:
        if isinstance(seal, GovernanceCohortSeal):
            if sampling_manifest is None:
                raise CTMIntakeError(
                    "CTM intake denied: Governance-v1 seal requires sampling_manifest"
                )
            if constraint_registry is None:
                raise CTMIntakeError(
                    "CTM intake denied: Governance-v1 seal requires constraint_registry"
                )
            if diagnostic_threshold_bytes is None:
                raise CTMIntakeError(
                    "CTM intake denied: Governance-v1 seal requires diagnostic threshold bytes"
                )
            if diagnostics_passed is None:
                raise CTMIntakeError(
                    "CTM intake denied: Governance-v1 seal requires diagnostics result"
                )
            verify_governed_seal(
                seal,
                sampling_manifest,
                manifest,
                artifact_bytes,
                constraint_registry=constraint_registry,
                registered_pipeline_ids=registered_pipeline_ids,
                registered_calibration_ids=registered_calibration_ids,
                diagnostic_threshold_bytes=diagnostic_threshold_bytes,
                diagnostics_passed=diagnostics_passed,
                timestamp_adapter=timestamp_adapter,
            )
        else:
            verify_seal(seal, manifest, artifact_bytes)
    except SealError as exc:
        raise CTMIntakeError(f"CTM intake denied: invalid cohort seal: {exc}") from exc
    return seal

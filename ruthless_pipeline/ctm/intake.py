"""Governed CTM intake boundary for prospective cohorts."""
from __future__ import annotations

from typing import Mapping

from ruthless_pipeline.governance.seal import CohortSeal, SealError, verify_seal


class CTMIntakeError(RuntimeError):
    pass


def accept_governed_cohort(
    seal: CohortSeal | None,
    manifest: Mapping[str, object],
    artifact_bytes: Mapping[str, bytes],
) -> CohortSeal:
    """Law 2: CTM refuses unsealed or unverifiable cohort evidence."""
    if seal is None:
        raise CTMIntakeError("CTM intake denied: cohort is unsealed")
    if seal.state != "SEALED":
        raise CTMIntakeError(f"CTM intake denied: cohort state is {seal.state!r}")
    try:
        verify_seal(seal, manifest, artifact_bytes)
    except SealError as exc:
        raise CTMIntakeError(f"CTM intake denied: invalid cohort seal: {exc}") from exc
    return seal

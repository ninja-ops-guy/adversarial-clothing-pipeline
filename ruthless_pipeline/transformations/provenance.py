"""Per-sample provenance manifest emission and replay.

synthetic_pipeline_validation_only.

Each emitted manifest records (distribution_id, manifest sha256, seed,
sample_index, resolved parameters) so any sample can be replayed exactly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict

from .distribution import (
    Sampler,
    TransformationDistributionSpec,
    canonical_json,
)


@dataclass(frozen=True)
class SampleManifest:
    distribution_id: str
    parameter_manifest_sha256: str
    seed: int
    sample_index: int
    resolved_parameters: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distribution_id": self.distribution_id,
            "parameter_manifest_sha256": self.parameter_manifest_sha256,
            "seed": self.seed,
            "sample_index": self.sample_index,
            "resolved_parameters": self.resolved_parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SampleManifest":
        return cls(
            distribution_id=data["distribution_id"],
            parameter_manifest_sha256=data["parameter_manifest_sha256"],
            seed=int(data["seed"]),
            sample_index=int(data["sample_index"]),
            resolved_parameters=data["resolved_parameters"],
        )

    def sha256(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()


def emit_manifest(spec: TransformationDistributionSpec, sample_index: int) -> SampleManifest:
    """Resolve sample `sample_index` and emit its provenance manifest."""
    sampler = Sampler(spec)
    return SampleManifest(
        distribution_id=spec.distribution_id,
        parameter_manifest_sha256=spec.manifest_sha256,
        seed=spec.seed,
        sample_index=int(sample_index),
        resolved_parameters=sampler.sample(int(sample_index)),
    )


def replay_manifest(spec: TransformationDistributionSpec, manifest: SampleManifest) -> Dict[str, Dict[str, Any]]:
    """Replay a sample from its manifest, verifying provenance fields.

    Fail-closed: raises ValueError if the manifest's distribution_id, manifest
    hash, or seed do not match the given spec, or if the re-resolved
    parameters differ from the recorded ones.
    """
    if manifest.distribution_id != spec.distribution_id:
        raise ValueError("distribution_id mismatch; cannot replay")
    if manifest.parameter_manifest_sha256 != spec.manifest_sha256:
        raise ValueError("parameter manifest hash mismatch; cannot replay")
    if manifest.seed != spec.seed:
        raise ValueError("seed mismatch; cannot replay")
    resolved = Sampler(spec).sample(manifest.sample_index)
    if canonical_json(resolved) != canonical_json(manifest.resolved_parameters):
        raise ValueError("replayed parameters differ from recorded manifest")
    return resolved

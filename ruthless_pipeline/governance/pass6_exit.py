"""Integrated Governance Pass 6 multi-backend exit and seal-binding audit surface."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from typing import Mapping, Sequence, Any

from .constraints import ConstraintSetRegistry
from .sampling import (
    DiagnosticBundle,
    DiagnosticPolicy,
    SamplerBackend,
    SamplerLane,
    SamplingGovernanceError,
    SamplingRequest,
    SamplingResult,
    build_sampling_manifest,
    diagnose,
    require_confirmatory_eligible,
)
from .sampling_diagnostics import exact_distribution_diagnostics
from .seal import GovernanceCohortSeal, seal_governed_cohort
from .state import GovernanceStateMachine


class Pass6ExitError(RuntimeError):
    pass


class LaneCapability(str, Enum):
    BUILTIN_PRODUCTION = "BUILTIN_PRODUCTION"
    EXTERNAL_ADAPTER_PRODUCTION = "EXTERNAL_ADAPTER_PRODUCTION"
    INTERFACE_ONLY = "INTERFACE_ONLY"


@dataclass(frozen=True)
class LaneInventoryEntry:
    lane: SamplerLane
    capability: LaneCapability
    implementation: str

    def validate(self) -> None:
        if not isinstance(self.lane, SamplerLane):
            raise Pass6ExitError("lane inventory requires SamplerLane")
        if not isinstance(self.capability, LaneCapability):
            raise Pass6ExitError("lane inventory requires LaneCapability")
        if not isinstance(self.implementation, str) or not self.implementation.strip():
            raise Pass6ExitError("lane inventory implementation is required")


@dataclass(frozen=True)
class Pass6BackendRun:
    lane: SamplerLane
    result: SamplingResult
    diagnostics: DiagnosticBundle
    sampling_manifest: Mapping[str, Any]
    confirmatory_eligible: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "lane": self.lane.value,
            "result": {
                "achieved_distribution": self.result.achieved_distribution,
                "backend_id": self.result.backend_id,
                "backend_version": self.result.backend_version,
                "sample_count": len(self.result.samples),
            },
            "diagnostics": self.diagnostics.to_dict(),
            "sampling_manifest": dict(self.sampling_manifest),
            "confirmatory_eligible": self.confirmatory_eligible,
        }


@dataclass(frozen=True)
class Pass6ExitRecord:
    inventory: tuple[LaneInventoryEntry, ...]
    runs: tuple[Pass6BackendRun, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "inventory": [
                {
                    "lane": entry.lane.value,
                    "capability": entry.capability.value,
                    "implementation": entry.implementation,
                }
                for entry in self.inventory
            ],
            "runs": [run.to_dict() for run in self.runs],
        }


def diagnostic_policy_bytes(policy: DiagnosticPolicy) -> bytes:
    """Canonical bytes whose sha256 is DiagnosticPolicy.threshold_hash."""
    policy.validate()
    return json.dumps(
        asdict(policy),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def run_pass6_exit_sequence(
    *,
    experiment_id: str,
    request: SamplingRequest,
    backends: Mapping[SamplerLane, SamplerBackend],
    sampling_ids: Mapping[SamplerLane, str],
    inventory: Sequence[LaneInventoryEntry],
    diagnostic_policy: DiagnosticPolicy,
    exact_population: Sequence[Mapping[str, Any]],
    observed_material_strata: Mapping[SamplerLane, Sequence[str]],
    support_coverage: Mapping[SamplerLane, float],
    repeated_seed_instability: Mapping[SamplerLane, float],
    approximate_model_count: float,
    approximate_model_count_interval: tuple[float, float],
    constraint_sensitivity: Mapping[str, float] | None = None,
    constraint_sensitivity_intervals: Mapping[str, tuple[float, float]] | None = None,
) -> Pass6ExitRecord:
    """Run every currently available lane under one common diagnostic policy."""
    request.validate()
    diagnostic_policy.validate()
    entries = tuple(inventory)
    if {entry.lane for entry in entries} != set(SamplerLane):
        raise Pass6ExitError("lane inventory must classify all four adopted sampler lanes")
    if len(entries) != len(SamplerLane):
        raise Pass6ExitError("lane inventory must contain each adopted lane exactly once")
    for entry in entries:
        entry.validate()

    available = {
        entry.lane for entry in entries if entry.capability is not LaneCapability.INTERFACE_ONLY
    }
    if set(backends) != available:
        raise Pass6ExitError("backend set must exactly match lanes classified as available")
    if set(sampling_ids) != available:
        raise Pass6ExitError("sampling IDs must exactly cover available lanes")

    runs: list[Pass6BackendRun] = []
    for lane in sorted(available, key=lambda item: item.value):
        backend = backends[lane]
        if getattr(backend, "lane", None) is not lane:
            raise Pass6ExitError(f"backend lane mismatch for {lane.value}")
        result = backend.sample(request)
        result.validate(request)
        calibration = exact_distribution_diagnostics(request, result, exact_population)
        bundle = diagnose(
            request,
            result,
            policy=diagnostic_policy,
            observed_material_strata=observed_material_strata[lane],
            support_coverage=support_coverage[lane],
            approximate_model_count=approximate_model_count,
            approximate_model_count_interval=approximate_model_count_interval,
            calibration=calibration,
            repeated_seed_instability=repeated_seed_instability[lane],
            external_sampler_test_passed=(
                True if lane is SamplerLane.EXACT else True
            ),
            constraint_sensitivity=constraint_sensitivity,
            constraint_sensitivity_intervals=constraint_sensitivity_intervals,
        )
        try:
            require_confirmatory_eligible(bundle)
            eligible = True
        except SamplingGovernanceError:
            eligible = False
        manifest = build_sampling_manifest(
            sampling_id=sampling_ids[lane],
            experiment_id=experiment_id,
            request=request,
            result=result,
            diagnostic_policy=diagnostic_policy,
        )
        runs.append(Pass6BackendRun(lane, result, bundle, manifest, eligible))

    degraded = [run for run in runs if run.lane is SamplerLane.DEGRADED]
    if degraded and any(run.confirmatory_eligible for run in degraded):
        raise Pass6ExitError("degraded proposal sampler may not become confirmatory eligible")
    return Pass6ExitRecord(entries, tuple(runs))


def seal_pass6_backend_run(
    run: Pass6BackendRun,
    *,
    diagnostic_policy: DiagnosticPolicy,
    cohort_id: str,
    specimen_ids: Sequence[str],
    artifact_bytes: Mapping[str, bytes],
    constraint_registry: ConstraintSetRegistry,
    registered_pipeline_ids: Sequence[str],
    registered_calibration_ids: Sequence[str],
    code_commit: str,
    code_version: str,
    pipeline_id: str,
    pipeline_version: str,
    calibration_id: str,
    calibration_version: str,
    state_machine: GovernanceStateMachine,
    seal_event_id: str,
    created_at: str | None = None,
) -> GovernanceCohortSeal:
    """Bind one eligible Pass-6 run to the adopted Pass-3 cohort seal."""
    require_confirmatory_eligible(run.diagnostics)
    threshold_bytes = diagnostic_policy_bytes(diagnostic_policy)
    manifest_hash = run.sampling_manifest.get("diagnostic_threshold_hash")
    if manifest_hash != diagnostic_policy.threshold_hash:
        raise Pass6ExitError("diagnostic policy changed after sampling manifest generation")
    if len(specimen_ids) != len(run.result.samples):
        raise Pass6ExitError("specimen_ids must align one-to-one with sampled specimens")

    from hashlib import sha256

    cohort_manifest = {
        "schema_version": "1.0",
        "cohort_id": cohort_id,
        "experiment_id": run.sampling_manifest["experiment_id"],
        "sampling_id": run.sampling_manifest["sampling_id"],
        "constraint_set_id": run.sampling_manifest["constraint_set_id"],
        "code_commit": code_commit,
        "code_version": code_version,
        "pipeline_id": pipeline_id,
        "pipeline_version": pipeline_version,
        "calibration_id": calibration_id,
        "calibration_version": calibration_version,
        "diagnostic_threshold_hash": diagnostic_policy.threshold_hash,
        "specimen_ids": list(specimen_ids),
        "artifacts": {path: sha256(data).hexdigest() for path, data in artifact_bytes.items()},
    }
    return seal_governed_cohort(
        run.sampling_manifest,
        cohort_manifest,
        artifact_bytes,
        constraint_registry=constraint_registry,
        registered_pipeline_ids=registered_pipeline_ids,
        registered_calibration_ids=registered_calibration_ids,
        diagnostic_threshold_bytes=threshold_bytes,
        diagnostics_passed=True,
        state_machine=state_machine,
        seal_event_id=seal_event_id,
        created_at=created_at,
    )

"""Experiment artifact schema and registry: the single lineage contract.

An ExperimentArtifact binds the full pipeline lineage of one research claim
into a single machine-readable object: candidate -> generation ->
optimization_telemetry -> calibration_profile -> sku -> physical_session ->
certificate. Each stage is a StageRef pointing at the immutable artifact
produced by that stage (identified by artifact id plus SHA-256 hex digest),
so D2 digital benchmarks, P1 physical trials, manufacturing QA, and paper
datasets all resolve against the same experiment_id instead of becoming
separate data islands. The lineage_hash is computed from the canonical JSON
of the stage list, never stored, so any retroactive edit to the lineage is
detectable. ExperimentRegistry is append-only: it rejects duplicate
experiment_id values and duplicate lineage_hash values (the same lineage
must not be registered twice under different ids), and supports reverse
lookup of every experiment touching a given stage artifact. Stage ordering
follows the declared pipeline order; stages may be absent, but present
stages must appear in pipeline order. Every artifact carries exactly one of
the repo's six evidence labels, matching the preregistration governance.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

# Declared pipeline order. Stages may be absent from an artifact, but the
# stages that are present must appear in this order.
PIPELINE_ORDER: tuple[str, ...] = (
    "candidate",
    "generation",
    "optimization_telemetry",
    "calibration_profile",
    "sku",
    "physical_session",
    "certificate",
)

# Stages that must be present on every experiment artifact.
REQUIRED_STAGES: tuple[str, ...] = ("candidate", "generation")

# The repo's six evidence labels (preregistration governance).
EVIDENCE_LABELS: tuple[str, ...] = (
    "published_observation",
    "external_replication_needed",
    "internally_measured",
    "target",
    "scenario_assumption",
    "speculative_open",
)

_EXPERIMENT_ID_RE = re.compile(r"^RAC-EXP-\d{4}-\d{3}$")


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class StageRef:
    """Reference to the immutable artifact produced by one pipeline stage."""

    stage: str
    artifact_id: str
    sha256: str
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.stage not in PIPELINE_ORDER:
            raise ValueError(f"unknown stage: {self.stage!r}")
        if not self.artifact_id:
            raise ValueError("artifact_id is required")
        if not _is_sha256(self.sha256):
            raise ValueError(f"{self.stage}: sha256 must be a 64-hex digest")

    def canonical_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass(frozen=True)
class ExperimentArtifact:
    """Single machine-readable contract binding a full experiment lineage."""

    experiment_id: str
    hypothesis_id: str
    generation_id: str
    created_utc: str
    stages: tuple[StageRef, ...] | list[StageRef]
    evidence_label: str
    validity_flags: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not _EXPERIMENT_ID_RE.match(self.experiment_id or ""):
            raise ValueError(
                "experiment_id must match RAC-EXP-YYYY-NNN: "
                f"{self.experiment_id!r}"
            )
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id is required")
        if not self.generation_id:
            raise ValueError("generation_id is required")
        if not self.created_utc:
            raise ValueError("created_utc (ISO-8601) is required")
        if self.evidence_label not in EVIDENCE_LABELS:
            raise ValueError(
                f"evidence_label must be one of {EVIDENCE_LABELS}: "
                f"{self.evidence_label!r}"
            )
        if not self.stages:
            raise ValueError("stages must not be empty")
        stage_names = [s.stage for s in self.stages]
        if len(set(stage_names)) != len(stage_names):
            raise ValueError("duplicate stage entries are not allowed")
        for stage in self.stages:
            stage.validate()
        missing = [s for s in REQUIRED_STAGES if s not in stage_names]
        if missing:
            raise ValueError(f"required stages missing: {missing}")
        order_index = [PIPELINE_ORDER.index(name) for name in stage_names]
        if order_index != sorted(order_index):
            raise ValueError(
                "stage ordering must follow the pipeline order: "
                + " < ".join(PIPELINE_ORDER)
            )

    def canonical_json(self) -> bytes:
        self.validate()
        payload = {
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "generation_id": self.generation_id,
            "created_utc": self.created_utc,
            "evidence_label": self.evidence_label,
            "validity_flags": self.validity_flags,
            "stages": [s.canonical_dict() for s in self.stages],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    @property
    def lineage_hash(self) -> str:
        """SHA-256 over the canonical JSON of the stage list (computed)."""
        self.validate()
        stages_payload = [s.canonical_dict() for s in self.stages]
        blob = json.dumps(
            stages_payload, sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(blob).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "generation_id": self.generation_id,
            "created_utc": self.created_utc,
            "evidence_label": self.evidence_label,
            "validity_flags": self.validity_flags,
            "stages": [asdict(s) for s in self.stages],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExperimentArtifact":
        stages = [StageRef(**s) for s in payload["stages"]]
        artifact = cls(
            experiment_id=payload["experiment_id"],
            hypothesis_id=payload["hypothesis_id"],
            generation_id=payload["generation_id"],
            created_utc=payload["created_utc"],
            evidence_label=payload["evidence_label"],
            validity_flags=dict(payload.get("validity_flags", {})),
            stages=stages,
        )
        artifact.validate()
        return artifact


class ExperimentRegistry:
    """Append-only registry of experiment artifacts."""

    def __init__(self) -> None:
        self._by_id: dict[str, ExperimentArtifact] = {}
        self._by_lineage: dict[str, str] = {}
        self._by_stage: dict[tuple[str, str], list[str]] = {}

    def add(self, artifact: ExperimentArtifact) -> None:
        artifact.validate()
        if artifact.experiment_id in self._by_id:
            raise ValueError(
                f"duplicate experiment_id: {artifact.experiment_id}"
            )
        lineage = artifact.lineage_hash
        if lineage in self._by_lineage:
            raise ValueError(
                "duplicate lineage_hash: lineage already registered as "
                f"{self._by_lineage[lineage]}"
            )
        self._by_id[artifact.experiment_id] = artifact
        self._by_lineage[lineage] = artifact.experiment_id
        for stage in artifact.stages:
            key = (stage.stage, stage.artifact_id)
            self._by_stage.setdefault(key, []).append(artifact.experiment_id)

    def get(self, experiment_id: str) -> ExperimentArtifact:
        if experiment_id not in self._by_id:
            raise KeyError(f"unknown experiment_id: {experiment_id}")
        return self._by_id[experiment_id]

    def find_by_stage(self, stage_name: str, artifact_id: str) -> list[ExperimentArtifact]:
        """Reverse lookup: all experiments touching a given stage artifact."""
        if stage_name not in PIPELINE_ORDER:
            raise ValueError(f"unknown stage: {stage_name!r}")
        ids = self._by_stage.get((stage_name, artifact_id), [])
        return [self._by_id[experiment_id] for experiment_id in ids]

    def __len__(self) -> int:
        return len(self._by_id)

    def validate(self) -> None:
        """Re-validate every artifact (hash shapes and stage ordering)."""
        for artifact in self._by_id.values():
            artifact.validate()

    def to_json(self) -> str:
        payload = {
            "experiments": [
                self._by_id[k].to_dict() for k in sorted(self._by_id)
            ]
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "ExperimentRegistry":
        payload = json.loads(text)
        registry = cls()
        for entry in payload.get("experiments", []):
            registry.add(ExperimentArtifact.from_dict(entry))
        return registry

"""Negative Result / Failure Index (SW-08).

An append-only, fail-closed index of negative, null, inconclusive, refused and
invalid experiment outcomes. The index is *generated* from canonical evidence
already in the repository — generation records (``generations/``), experiment
registry records (``registry/experiments.json``), sealed release failure
taxonomy outputs (``releases/*/FAILURE.json``) and retained evidence status
files (``manuscript/evidence/*/d2-latest-status.json``) — never from hand-copied
summaries. Every indexed record carries content-addressed evidence references
(``{path, sha256}``) back to the canonical artifacts it was derived from, so
each query result is traceable.

Structural guarantees:

* Append-only: :class:`NegativeResultIndex` exposes no deletion path. Any
  attempted removal raises :class:`IndexImmutableError`. Deleting or refusing
  to list a negative result through the index is therefore impossible.
* Deterministic: no wall-clock, no randomness. ``created_utc`` values are
  taken from the source evidence; record IDs are content-addressed
  (``RAC-NR-`` + sha256[:16] of the canonical record content).
* Fail-closed: malformed records, unknown outcome kinds, duplicate IDs and
  tampered serializations raise typed errors.

Pure stdlib + the repo canonical helpers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from ruthless_pipeline.certification.failure_taxonomy import FailureCategory
from ruthless_pipeline.pattern_genome.canonical import (
    _to_builtin,
    canonical_json,
    sha256_bytes,
)

SCHEMA_VERSION = "1.0"

INDEX_SCHEMA_ID = "https://rac.local/schemas/rac_negative_outcome_v1.schema.json"


# ---------------------------------------------------------------------------
# Typed errors (fail-closed)
# ---------------------------------------------------------------------------


class NegativeResultIndexError(ValueError):
    """Base error for all negative-result-index contract violations."""


class IndexImmutableError(NegativeResultIndexError):
    """Raised on any attempt to remove or overwrite an indexed record."""


class UnknownOutcomeKindError(NegativeResultIndexError):
    """Raised when an outcome kind is not part of the closed enum."""


class RecordIntegrityError(NegativeResultIndexError):
    """Raised when a serialized record's ID does not match its content."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OutcomeKind(str, Enum):
    """Closed set of indexed outcome kinds."""

    NEGATIVE = "negative"          # valid experiment, hypothesis rejected (FAIL)
    NULL = "null"                  # measured no-effect within a valid contract
    INCONCLUSIVE = "inconclusive"  # valid experiment, statistically unresolved
    REFUSED = "refused"            # pipeline refused to run/certify (fail-closed gate)
    INVALID = "invalid"            # experiment invalid; not a scientific result


_OUTCOME_KINDS = {k.value for k in OutcomeKind}

_FAILURE_CATEGORY_VALUES = {c.value for c in FailureCategory}

_UNCERTAINTY_LEVELS = ("high", "medium", "low")


# Fixed, deterministic lesson text per failure category. These are reusable
# lessons derived from the taxonomy rules themselves (not per-run prose), so
# they are stable across regenerations.
_CATEGORY_LESSONS: dict[str, tuple[str, ...]] = {
    "optimization_failure": (
        "Re-check objective, optimizer budget and surrogate ensemble before "
        "attributing failure to transfer.",
    ),
    "surrogate_overfit": (
        "Increase surrogate diversity and tighten held-out separation; "
        "surrogate suppression alone is not evidence of transfer.",
    ),
    "cross_architecture_transfer_failure": (
        "Treat cross-architecture transfer as the primary open risk; do not "
        "promote surrogate-only results to efficacy claims.",
    ),
    "transformation_fragility": (
        "Optimize and report across the full transformation sweep, not the "
        "best-viewpoint condition.",
    ),
    "manufacturing_loss": (
        "Bind candidates to a manufacturing calibration profile before "
        "physical interpretation.",
    ),
    "camera_isp_loss": (
        "Include ISP simulation in pre-physical screening.",
    ),
    "deformation_failure": (
        "Evaluate under cloth deformation, not only flat renders.",
    ),
    "coverage_failure": (
        "Enforce minimum coverage entropy at generation time.",
    ),
    "statistical_inconclusive": (
        "Pre-register power analysis; widen samples before drawing "
        "conclusions from consistent-but-wide intervals.",
    ),
    "unclassified": (
        "Record richer metrics so future failures classify into a known mode.",
    ),
}


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceRef:
    """Content-addressed pointer to a canonical evidence artifact."""

    path: str
    sha256: str

    def validate(self) -> None:
        if not self.path:
            raise NegativeResultIndexError("evidence ref path is required")
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.sha256)
        ):
            raise NegativeResultIndexError(
                f"evidence ref sha256 must be lowercase 64-hex: {self.path}"
            )


@dataclass(frozen=True)
class NegativeOutcomeRecord:
    """One indexed negative/null/inconclusive/refused/invalid outcome."""

    record_id: str  # "RAC-NR-" + sha256[:16] of canonical content
    outcome_kind: str  # OutcomeKind value
    failure_category: str | None  # FailureCategory value or None
    experiment_id: str
    generation_id: str
    candidate_id: str | None
    generator_family: str | None
    conditions: dict[str, Any]
    evidence_class: str
    evidence_refs: tuple[EvidenceRef, ...]
    root_cause: str | None
    root_cause_established: bool
    uncertainty: str  # "high" | "medium" | "low" (from taxonomy confidence)
    lessons: tuple[str, ...]
    created_utc: str  # taken from source evidence; never wall-clock

    def validate(self) -> None:
        if self.outcome_kind not in _OUTCOME_KINDS:
            raise UnknownOutcomeKindError(
                f"unknown outcome kind: {self.outcome_kind!r}"
            )
        if not self.record_id.startswith("RAC-NR-"):
            raise NegativeResultIndexError("record_id must start with 'RAC-NR-'")
        if not self.experiment_id:
            raise NegativeResultIndexError("experiment_id is required")
        if self.failure_category is not None and (
            self.failure_category not in _FAILURE_CATEGORY_VALUES
        ):
            raise NegativeResultIndexError(
                f"unknown failure category: {self.failure_category!r}"
            )
        if self.uncertainty not in _UNCERTAINTY_LEVELS:
            raise NegativeResultIndexError(
                f"uncertainty must be one of {_UNCERTAINTY_LEVELS}"
            )
        if not self.evidence_class:
            raise NegativeResultIndexError("evidence_class is required")
        if not self.evidence_refs:
            raise NegativeResultIndexError(
                "every indexed outcome must carry at least one evidence ref "
                "(traceability is mandatory)"
            )
        for ref in self.evidence_refs:
            ref.validate()
        if self.root_cause_established and not self.root_cause:
            raise NegativeResultIndexError(
                "root_cause_established requires a root_cause"
            )

    def _content_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("record_id")
        return payload

    def canonical_json(self) -> bytes:
        self.validate()
        return canonical_json(self._content_dict())

    def content_sha256(self) -> str:
        return sha256_bytes(self.canonical_json())

    def expected_record_id(self) -> str:
        return f"RAC-NR-{self.content_sha256()[:16]}"

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return _to_builtin(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NegativeOutcomeRecord":
        refs = tuple(EvidenceRef(**r) for r in data.get("evidence_refs", ()))
        record = cls(
            record_id=data["record_id"],
            outcome_kind=data["outcome_kind"],
            failure_category=data.get("failure_category"),
            experiment_id=data["experiment_id"],
            generation_id=data.get("generation_id", ""),
            candidate_id=data.get("candidate_id"),
            generator_family=data.get("generator_family"),
            conditions=dict(data.get("conditions", {})),
            evidence_class=data["evidence_class"],
            evidence_refs=refs,
            root_cause=data.get("root_cause"),
            root_cause_established=bool(data.get("root_cause_established", False)),
            uncertainty=data["uncertainty"],
            lessons=tuple(data.get("lessons", ())),
            created_utc=data.get("created_utc", ""),
        )
        record.validate()
        if record.record_id != record.expected_record_id():
            raise RecordIntegrityError(
                f"record {record.record_id} does not match its content hash "
                f"({record.expected_record_id()}); refusing to load tampered "
                "negative-result index entry"
            )
        return record


def make_record(
    *,
    outcome_kind: OutcomeKind,
    failure_category: str | None,
    experiment_id: str,
    generation_id: str,
    candidate_id: str | None,
    generator_family: str | None,
    conditions: dict[str, Any],
    evidence_class: str,
    evidence_refs: Iterable[EvidenceRef],
    root_cause: str | None,
    root_cause_established: bool,
    uncertainty: str,
    lessons: Iterable[str],
    created_utc: str,
) -> NegativeOutcomeRecord:
    """Construct a record with its content-addressed ID."""
    record = NegativeOutcomeRecord(
        record_id="RAC-NR-pending",
        outcome_kind=outcome_kind.value,
        failure_category=failure_category,
        experiment_id=experiment_id,
        generation_id=generation_id,
        candidate_id=candidate_id,
        generator_family=generator_family,
        conditions=dict(conditions),
        evidence_class=evidence_class,
        evidence_refs=tuple(evidence_refs),
        root_cause=root_cause,
        root_cause_established=root_cause_established,
        uncertainty=uncertainty,
        lessons=tuple(lessons),
        created_utc=created_utc,
    )
    record.validate()
    return NegativeOutcomeRecord(
        record_id=record.expected_record_id(),
        outcome_kind=record.outcome_kind,
        failure_category=record.failure_category,
        experiment_id=record.experiment_id,
        generation_id=record.generation_id,
        candidate_id=record.candidate_id,
        generator_family=record.generator_family,
        conditions=record.conditions,
        evidence_class=record.evidence_class,
        evidence_refs=record.evidence_refs,
        root_cause=record.root_cause,
        root_cause_established=record.root_cause_established,
        uncertainty=record.uncertainty,
        lessons=record.lessons,
        created_utc=record.created_utc,
    )


# ---------------------------------------------------------------------------
# Index (append-only, fail-closed)
# ---------------------------------------------------------------------------


class NegativeResultIndex:
    """Append-only index of negative/null/inconclusive/refused/invalid outcomes.

    There is deliberately no deletion, replacement or filtering-out path:
    records can only be added. Any removal attempt raises IndexImmutableError.
    """

    def __init__(self, records: Iterable[NegativeOutcomeRecord] = ()) -> None:
        self._records: list[NegativeOutcomeRecord] = []
        self._ids: set[str] = set()
        for record in records:
            self.add(record)

    # -- mutation (append only) --------------------------------------------

    def add(self, record: NegativeOutcomeRecord) -> None:
        record.validate()
        if record.record_id in self._ids:
            raise NegativeResultIndexError(
                f"duplicate record id: {record.record_id}"
            )
        if record.record_id != record.expected_record_id():
            raise RecordIntegrityError(
                f"record id {record.record_id} does not match content hash"
            )
        self._records.append(record)
        self._ids.add(record.record_id)

    def remove(self, *_args: Any, **_kwargs: Any) -> None:
        """Negative results cannot be deleted through the index (append-only)."""
        raise IndexImmutableError(
            "negative results are append-only; deletion is structurally refused"
        )

    # delete/discard aliases all fail closed the same way.
    delete = remove
    discard = remove

    # -- queries ------------------------------------------------------------

    @property
    def records(self) -> tuple[NegativeOutcomeRecord, ...]:
        return tuple(self._records)

    def by_category(self, failure_category: str) -> list[NegativeOutcomeRecord]:
        if failure_category not in _FAILURE_CATEGORY_VALUES:
            raise NegativeResultIndexError(
                f"unknown failure category: {failure_category!r}"
            )
        return [r for r in self._records if r.failure_category == failure_category]

    def by_outcome_kind(self, kind: str) -> list[NegativeOutcomeRecord]:
        if kind not in _OUTCOME_KINDS:
            raise UnknownOutcomeKindError(f"unknown outcome kind: {kind!r}")
        return [r for r in self._records if r.outcome_kind == kind]

    def by_generator_family(self, family: str) -> list[NegativeOutcomeRecord]:
        if not family:
            raise NegativeResultIndexError("generator family is required")
        return [r for r in self._records if r.generator_family == family]

    def by_experiment(self, experiment_id: str) -> list[NegativeOutcomeRecord]:
        if not experiment_id:
            raise NegativeResultIndexError("experiment_id is required")
        return [r for r in self._records if r.experiment_id == experiment_id]

    def by_generation(self, generation_id: str) -> list[NegativeOutcomeRecord]:
        if not generation_id:
            raise NegativeResultIndexError("generation_id is required")
        return [r for r in self._records if r.generation_id == generation_id]

    def summary(self) -> dict[str, int]:
        counts = {kind.value: 0 for kind in OutcomeKind}
        for record in self._records:
            counts[record.outcome_kind] += 1
        return counts

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "schema": INDEX_SCHEMA_ID,
            "records": [r.to_dict() for r in self._records],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict()).decode("utf-8")

    def index_sha256(self) -> str:
        return sha256_bytes(self.to_json().encode("utf-8"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NegativeResultIndex":
        if not isinstance(data, dict) or "records" not in data:
            raise NegativeResultIndexError(
                "index payload must be an object with a 'records' list"
            )
        if data.get("schema_version") != SCHEMA_VERSION:
            raise NegativeResultIndexError(
                f"unsupported index schema_version: {data.get('schema_version')!r}"
            )
        return cls(NegativeOutcomeRecord.from_dict(r) for r in data["records"])

    @classmethod
    def from_json(cls, text: str) -> "NegativeResultIndex":
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Generation from canonical evidence
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _rel(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _ref(repo_root: Path, path: Path) -> EvidenceRef:
    return EvidenceRef(path=_rel(repo_root, path), sha256=_sha256_file(path))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _generation_conditions(generation: dict[str, Any] | None) -> dict[str, Any]:
    if not generation:
        return {}
    conditions: dict[str, Any] = {}
    for key in (
        "protocol",
        "surrogate_model_set",
        "heldout_model_set",
        "status",
        "lock_status",
    ):
        if generation.get(key) is not None:
            conditions[key] = generation[key]
    pool = generation.get("candidate_pool") or {}
    if pool.get("design_profile"):
        conditions["design_profile"] = pool["design_profile"]
    if generation.get("heldout_models"):
        conditions["heldout_models"] = list(generation["heldout_models"])
    return conditions


def _load_generations(repo_root: Path) -> dict[str, dict[str, Any]]:
    generations: dict[str, dict[str, Any]] = {}
    gen_dir = repo_root / "generations"
    if gen_dir.is_dir():
        for path in sorted(gen_dir.glob("*.json")):
            data = _load_json(path)
            gid = data.get("generation_id")
            if gid:
                generations[gid] = data
    return generations


def _records_from_failure_taxonomy(
    repo_root: Path,
    failure_path: Path,
    generations: dict[str, dict[str, Any]],
) -> list[NegativeOutcomeRecord]:
    """Index a sealed release FAILURE.json (failure taxonomy output)."""
    payload = _load_json(failure_path)
    classification = payload.get("classification") or {}
    category = classification.get("category")
    if category not in _FAILURE_CATEGORY_VALUES:
        raise NegativeResultIndexError(
            f"{_rel(repo_root, failure_path)}: unknown failure category {category!r}"
        )
    confidence = classification.get("confidence", "low")
    if confidence not in _UNCERTAINTY_LEVELS:
        raise NegativeResultIndexError(
            f"{_rel(repo_root, failure_path)}: unknown confidence {confidence!r}"
        )
    experiment_id = classification.get("experiment_id") or ""
    generation_id = classification.get("generation_id") or ""
    generation = generations.get(generation_id)

    if category == FailureCategory.STATISTICAL_INCONCLUSIVE.value:
        kind = OutcomeKind.INCONCLUSIVE
    else:
        kind = OutcomeKind.NEGATIVE

    explanation = classification.get("explanation") or payload.get("failure_reason")
    root_cause_established = confidence == "high"
    lessons = _CATEGORY_LESSONS.get(category, ())

    evidence_refs = [_ref(repo_root, failure_path)]
    release_dir = failure_path.parent
    for name in ("experiment.json", "RELEASE.json"):
        sibling = release_dir / name
        if sibling.is_file():
            evidence_refs.append(_ref(repo_root, sibling))
    gen_path = repo_root / "generations" / f"{generation_id}.json"
    if generation_id and gen_path.is_file():
        evidence_refs.append(_ref(repo_root, gen_path))

    conditions = _generation_conditions(generation)
    if payload.get("failure_stage"):
        conditions["failure_stage"] = payload["failure_stage"]
    if classification.get("metrics_provenance"):
        conditions["metrics_provenance"] = classification["metrics_provenance"]
    for signal in classification.get("signals", ()):
        conditions.setdefault("signals", []).append(
            {"name": signal.get("name"), "value": signal.get("value")}
        )

    generator_family = None
    if generation:
        generator_family = (generation.get("candidate_pool") or {}).get(
            "generator_family"
        ) or generation.get("generator_family")

    return [
        make_record(
            outcome_kind=kind,
            failure_category=category,
            experiment_id=experiment_id,
            generation_id=generation_id,
            candidate_id=classification.get("candidate_id"),
            generator_family=generator_family,
            conditions=conditions,
            evidence_class="failure_taxonomy_classification",
            evidence_refs=evidence_refs,
            root_cause=explanation,
            root_cause_established=root_cause_established,
            uncertainty=confidence,
            lessons=lessons,
            created_utc=classification.get("created_utc")
            or payload.get("detected_utc")
            or "",
        )
    ]


def _records_from_status_file(
    repo_root: Path,
    status_path: Path,
    generations: dict[str, dict[str, Any]],
) -> list[NegativeOutcomeRecord]:
    """Index a retained measured status file (e.g. the D2-0003 negative result)."""
    payload = _load_json(status_path)
    decision = payload.get("decision")
    if decision != "FAIL":
        return []
    candidate_id = payload.get("candidate_id") or ""
    generation = generations.get(candidate_id)
    heldout = payload.get("heldout") or {}
    conditions = _generation_conditions(generation)
    for key in ("protocol_id", "protocol_version", "surrogate_model_set",
                "heldout_model_set", "evidence_state"):
        if payload.get(key) is not None:
            conditions.setdefault(key, payload[key])
    if heldout:
        conditions["heldout"] = {
            k: heldout[k]
            for k in ("baseline_detection_rate", "candidate_detection_rate", "n")
            if k in heldout
        }
    root_cause = None
    if heldout.get("candidate_detection_rate") is not None and (
        heldout.get("baseline_detection_rate") is not None
    ):
        if heldout["candidate_detection_rate"] >= heldout["baseline_detection_rate"]:
            root_cause = (
                "held-out candidate detection rate was not suppressed below "
                "baseline (measured negative result)"
            )
    return [
        make_record(
            outcome_kind=OutcomeKind.NEGATIVE,
            failure_category=None,
            experiment_id=candidate_id,
            generation_id=candidate_id,
            candidate_id=candidate_id,
            generator_family=(generation or {}).get("generator_family"),
            conditions=conditions,
            evidence_class=payload.get("evidence_state") or "measured_status",
            evidence_refs=[_ref(repo_root, status_path)],
            root_cause=root_cause,
            root_cause_established=False,
            uncertainty="medium",
            lessons=(
                "Negative held-out generations remain part of the scientific "
                "record and constrain later preregistrations.",
            ),
            created_utc=payload.get("created_utc") or "",
        )
    ]


def _records_from_experiment_registry(
    repo_root: Path,
    registry_path: Path,
    generations: dict[str, dict[str, Any]],
) -> list[NegativeOutcomeRecord]:
    """Index experiments in registry/experiments.json by verdict."""
    payload = _load_json(registry_path)
    experiments = payload.get("experiments")
    if not isinstance(experiments, list):
        raise NegativeResultIndexError(
            f"{_rel(repo_root, registry_path)}: 'experiments' must be a list"
        )
    records: list[NegativeOutcomeRecord] = []
    for entry in experiments:
        flags = entry.get("validity_flags") or {}
        verdict = flags.get("verdict")
        if verdict != "FAIL":
            continue
        experiment_id = entry.get("experiment_id") or ""
        generation_id = entry.get("generation_id") or ""
        generation = generations.get(generation_id)
        taxonomy = flags.get("failure_taxonomy") or {}
        category = taxonomy.get("category")
        if category is not None and category not in _FAILURE_CATEGORY_VALUES:
            raise NegativeResultIndexError(
                f"experiment {experiment_id}: unknown failure category {category!r}"
            )
        conditions = _generation_conditions(generation)
        if flags.get("evidence_state"):
            conditions["evidence_state"] = flags["evidence_state"]
        if flags.get("not_recorded_fields"):
            conditions["not_recorded_fields"] = list(flags["not_recorded_fields"])
        if flags.get("provenance"):
            conditions["provenance"] = flags["provenance"]
        records.append(
            make_record(
                outcome_kind=OutcomeKind.NEGATIVE,
                failure_category=category,
                experiment_id=experiment_id,
                generation_id=generation_id,
                candidate_id=None,
                generator_family=(generation or {}).get("generator_family"),
                conditions=conditions,
                evidence_class=entry.get("evidence_label") or "experiment_registry",
                evidence_refs=[_ref(repo_root, registry_path)],
                root_cause=None,  # root cause lives on the taxonomy-derived record
                root_cause_established=False,
                uncertainty="medium",
                lessons=(
                    "FAIL verdicts under a valid evidence contract are retained "
                    "negative results, not refusals.",
                ),
                created_utc=entry.get("created_utc") or "",
            )
        )
    return records


def build_index(repo_root: str | Path) -> NegativeResultIndex:
    """Generate the index from canonical evidence under ``repo_root``.

    Sources (all read-only; missing sources simply contribute no records):
      - ``releases/*/FAILURE.json`` — failure taxonomy outputs (primary)
      - ``manuscript/evidence/*/d2-latest-status.json`` — retained measured
        negative generations
      - ``registry/experiments.json`` — experiment registry FAIL verdicts
      - ``generations/*.json`` — conditions context for the above

    The build is deterministic: identical canonical evidence yields a
    byte-identical serialized index.
    """
    root = Path(repo_root)
    generations = _load_generations(root)
    index = NegativeResultIndex()

    releases_dir = root / "releases"
    if releases_dir.is_dir():
        for failure_path in sorted(releases_dir.glob("*/FAILURE.json")):
            for record in _records_from_failure_taxonomy(
                root, failure_path, generations
            ):
                index.add(record)

    evidence_dir = root / "manuscript" / "evidence"
    if evidence_dir.is_dir():
        for status_path in sorted(evidence_dir.glob("*/d2-latest-status.json")):
            for record in _records_from_status_file(root, status_path, generations):
                index.add(record)

    registry_path = root / "registry" / "experiments.json"
    if registry_path.is_file():
        for record in _records_from_experiment_registry(
            root, registry_path, generations
        ):
            index.add(record)

    return index

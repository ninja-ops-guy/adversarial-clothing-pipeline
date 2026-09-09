"""Evidence recovery: classify and resume NON-scientific stages only.

This module implements the failure-recovery half of the D2-0004 packaging
incident lesson (see ``experiment_status.py``): when a workflow run dies
AFTER the science is sealed, the sealed scientific evidence must survive
untouched and only the downstream, non-scientific stages (publication,
packaging, report/export, status publication, artifact upload) may be
resumed.

Hard guarantees:

- HARD REFUSAL: any recovery path that would invoke inference, model
  loading, benchmark execution, or candidate generation raises
  :class:`InferenceRefusalError`. Scientific stages (fixture, selection,
  freeze, analysis, seal, and anything named inference/benchmark/
  generation/candidate) are NEVER re-executed by this tool.
- CORRUPT scientific evidence (hash mismatch / missing file on a completed
  scientific stage) fails closed with :class:`ScientificEvidenceError`; the
  tool never "repairs" sealed science.
- The tool never writes to ``generations/`` and never modifies scientific
  fields of any record; journal updates append recovered NON-scientific
  stages only.

Journal contract: the run directory carries a journal following the
``rehearsal_d20005`` pattern (``rehearsal_journal.json``: schema_version
"1.0", ``completed_stages`` an ordered prefix of the stage list,
``artifacts`` mapping stage -> {relpath: sha256}). On classification every
completed stage's artifacts are re-hashed; mismatch => CORRUPT.

Rebuilt downstream artifacts are verified after rebuilding
(``release_format.verify_release`` via the rehearsal helpers) before the
journal is updated, so a failed recovery never marks a stage done.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from . import rehearsal_d20005 as rehearsal
from .release_format import verify_release
from .schema_version import require_schema_version

SCHEMA_VERSION = rehearsal.SCHEMA_VERSION
EVIDENCE_CLASS = rehearsal.EVIDENCE_CLASS

JOURNAL_FILENAME = "rehearsal_journal.json"

#: Stages the tool is allowed to resume: strictly non-scientific downstream
#: work (publication, packaging, report/export, status/upload plumbing).
RECOVERABLE_STAGES: frozenset[str] = frozenset(
    {
        "release",
        "publication",
        "packaging",
        "report",
        "export",
        "status_publication",
        "artifact_upload",
    }
)

#: Tokens that mark a stage as scientific execution. Any unfinished stage
#: matching one of these is refused: resuming it would require inference,
#: model loading, benchmark execution, or candidate generation.
INFERENCE_TOKENS: tuple[str, ...] = (
    "inference",
    "model_load",
    "benchmark",
    "candidate_generation",
    "generation",
    "fixture",
    "selection",
    "freeze",
    "analysis",
    "seal",
)

#: Directories the tool must never write into.
FORBIDDEN_WRITE_PARTS: frozenset[str] = frozenset({"generations", "manuscript"})


class RecoveryError(RuntimeError):
    """Base class for recovery failures."""


class InferenceRefusalError(RecoveryError):
    """Recovery would require inference/model loading/benchmark/candidate
    generation; refused unconditionally."""


class ScientificEvidenceError(RecoveryError):
    """Completed scientific evidence is missing or hash-mismatched; the tool
    fails closed rather than touch sealed science."""


class UnsafeWriteError(RecoveryError):
    """A recovery write would land in a forbidden location."""


class StageStatus(Enum):
    DONE = "DONE"
    INCOMPLETE = "INCOMPLETE"
    CORRUPT = "CORRUPT"


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def assert_safe_write(path: Path) -> None:
    """Refuse to write under generations/ or manuscript/ (fail closed)."""
    parts = Path(path).resolve().parts
    bad = FORBIDDEN_WRITE_PARTS & set(parts)
    if bad:
        raise UnsafeWriteError(
            f"recovery write under {sorted(bad)} is forbidden: {path}"
        )


def stage_is_recoverable(stage: str) -> bool:
    return stage in RECOVERABLE_STAGES


def stage_requires_inference(stage: str) -> bool:
    lowered = stage.lower()
    return stage not in RECOVERABLE_STAGES and any(
        token in lowered for token in INFERENCE_TOKENS
    )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def load_journal(run_dir: Path, journal_name: str = JOURNAL_FILENAME) -> dict:
    path = Path(run_dir) / journal_name
    if not path.is_file():
        raise RecoveryError(f"no recovery journal at {path}")
    payload = json.loads(path.read_text())
    require_schema_version(payload, SCHEMA_VERSION, label=str(path))
    return payload


def classify_run(
    run_dir: Path,
    *,
    stages: tuple[str, ...] = rehearsal.STAGES,
    journal_name: str = JOURNAL_FILENAME,
    journal: dict | None = None,
) -> dict[str, Any]:
    """Classify every stage as DONE / INCOMPLETE / CORRUPT.

    DONE: recorded complete in the journal AND every recorded artifact
    re-hashes. CORRUPT: recorded complete but an artifact is missing or
    hash-mismatched. INCOMPLETE: not recorded (must form a suffix of the
    stage list; a hole in the sequence means the journal itself is corrupt).
    """
    run_dir = Path(run_dir)
    if journal is None:
        journal = load_journal(run_dir, journal_name)
    completed = journal.get("completed_stages", [])
    if len(completed) != len(set(completed)):
        raise RecoveryError("journal lists a stage twice; journal is corrupt")
    if completed != list(stages[: len(completed)]):
        raise RecoveryError(
            "journal stage order violates the pipeline state machine; "
            "journal is corrupt (fail closed)"
        )
    artifacts = journal.get("artifacts", {})
    classification: dict[str, dict[str, Any]] = {}
    for stage in stages:
        if stage not in completed:
            classification[stage] = {
                "status": StageStatus.INCOMPLETE.value,
                "recoverable": stage_is_recoverable(stage),
                "detail": "not recorded in the journal",
            }
            continue
        problems = []
        for rel, expected in sorted(artifacts.get(stage, {}).items()):
            path = run_dir / rel
            if not path.is_file():
                problems.append(f"{rel}: missing")
            elif _sha256_file(path) != expected:
                problems.append(f"{rel}: hash mismatch")
        classification[stage] = {
            "status": StageStatus.CORRUPT.value if problems else StageStatus.DONE.value,
            "recoverable": stage_is_recoverable(stage),
            "detail": "; ".join(problems) if problems else "all artifacts verify",
        }
    return {
        "run_dir": str(run_dir),
        "journal": str(run_dir / journal_name),
        "stages": classification,
        "evidence_class": EVIDENCE_CLASS,
    }


# ---------------------------------------------------------------------------
# Refusal boundary
# ---------------------------------------------------------------------------

def refuse_inference_stage(stage: str) -> None:
    """HARD REFUSAL for any stage whose completion needs scientific compute."""
    if stage_requires_inference(stage):
        raise InferenceRefusalError(
            f"stage {stage!r} is scientific execution (inference / model "
            "loading / benchmark / candidate generation territory); the "
            "evidence recovery tool NEVER resumes scientific stages"
        )


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

def _default_release_rebuilder(run_dir: Path, journal: dict) -> dict[str, str]:
    """Rebuild the publication-style release from VERIFIED scientific artifacts.

    All inputs are the already-sealed, already-verified files of earlier
    stages; nothing scientific is recomputed. The rebuilt release is
    re-verified with release_format.verify_release before the journal update.
    """
    release_dir = run_dir / "release" / rehearsal.RELEASE_ID
    source_names = (
        "fixture-manifest.json",
        "selection-report.json",
        "frozen-telemetry.json",
        "analysis.json",
        "cluster-outcomes.json",
        "sealed-evidence.json",
    )
    files: dict[str, bytes] = {}
    for name in source_names:
        path = run_dir / name
        if not path.is_file():
            raise ScientificEvidenceError(
                f"cannot rebuild release: sealed input {name} is missing"
            )
        files[name] = path.read_bytes()
    created_utc = rehearsal.DEFAULT_CREATED_UTC
    rehearsal.build_release(release_dir, files, created_utc=created_utc)
    result = rehearsal.verify_release_dir(release_dir)
    if not result.ok:
        raise RecoveryError(f"rebuilt release failed verification: {result}")
    return {
        f"release/{rehearsal.RELEASE_ID}/{name}": _sha256_file(release_dir / name)
        for name in sorted(files) + ["MANIFEST.json", "RELEASE.json"]
    }


def _default_export_rebuilder(run_dir: Path, journal: dict) -> dict[str, str]:
    """Rebuild the manuscript-export row into the scratch export dir."""
    outcomes_path = run_dir / "cluster-outcomes.json"
    selection_path = run_dir / "selection-report.json"
    telemetry_path = run_dir / "frozen-telemetry.json"
    for path in (outcomes_path, selection_path, telemetry_path):
        if not path.is_file():
            raise ScientificEvidenceError(
                f"cannot rebuild export: sealed input {path.name} is missing"
            )
    outcomes_payload = json.loads(outcomes_path.read_text())
    cluster_outcomes = {
        cid: {u: (bool(m), bool(c)) for u, (m, c) in members.items()}
        for cid, members in outcomes_payload["cluster_outcomes"].items()
    }
    selection = json.loads(selection_path.read_text())
    frozen = json.loads(telemetry_path.read_text())
    export = rehearsal.export_manuscript_rows(
        run_dir / "export_synthetic",
        cluster_outcomes,
        winner_candidate_sha256=selection["winner_candidate_sha256"],
        telemetry_sha256=frozen["frozen_sha256"],
    )
    return {
        "export_synthetic/paper5_arms_rehearsal_synthetic.csv": export["csv_sha256"],
        "export_synthetic/export-row.json": export["export_sha256"],
    }


DEFAULT_REBUILDERS: dict[str, Callable[[Path, dict], dict[str, str]]] = {
    "release": _default_release_rebuilder,
    "export": _default_export_rebuilder,
}


def recover_run(
    run_dir: Path,
    *,
    stages: tuple[str, ...] = rehearsal.STAGES,
    journal_name: str = JOURNAL_FILENAME,
    rebuilders: dict[str, Callable[[Path, dict], dict[str, str]]] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Classify the run and resume ONLY unfinished non-scientific stages.

    Raises InferenceRefusalError if any unfinished stage would require
    scientific compute, and ScientificEvidenceError if completed scientific
    evidence is corrupt. In dry-run mode nothing is written.
    """
    run_dir = Path(run_dir)
    assert_safe_write(run_dir)
    report = classify_run(run_dir, stages=stages, journal_name=journal_name)
    journal = load_journal(run_dir, journal_name)
    rebuilders = dict(DEFAULT_REBUILDERS if rebuilders is None else rebuilders)

    # Corrupt recoverable stages: roll the journal back to the last intact
    # stage, so the corrupt stage and everything downstream of it is
    # reclassified INCOMPLETE and rebuilt. Scientific stages are never rolled
    # back — a corrupt scientific stage is a hard refusal below.
    completed = list(journal.get("completed_stages", []))
    rollback_at: int | None = None
    dropped_stages: tuple[str, ...] = ()
    for i, stage in enumerate(completed):
        info = report["stages"][stage]
        if info["status"] == StageStatus.CORRUPT.value and info["recoverable"]:
            rollback_at = i
            break
    if rollback_at is not None:
        dropped_stages = tuple(completed[rollback_at:])
        for stage in dropped_stages:
            if not stage_is_recoverable(stage):
                raise ScientificEvidenceError(
                    f"rollback of corrupt stage {completed[rollback_at]!r} would "
                    f"drop scientific stage {stage!r}; refusing to touch sealed "
                    "scientific evidence"
                )
            journal["artifacts"].pop(stage, None)
        journal["completed_stages"] = completed[:rollback_at]
        report = classify_run(
            run_dir, stages=stages, journal_name=journal_name, journal=journal
        )

    actions: list[dict[str, Any]] = []
    recovered: list[str] = []

    for stage in stages:
        info = report["stages"][stage]
        status = info["status"]
        if status == StageStatus.DONE.value:
            continue
        if status == StageStatus.CORRUPT.value and not info["recoverable"]:
            raise ScientificEvidenceError(
                f"stage {stage!r} is recorded complete but its artifacts are "
                f"corrupt ({info['detail']}); refusing to touch sealed "
                "scientific evidence"
            )
        if not info["recoverable"]:
            refuse_inference_stage(stage)  # always raises for scientific stages
            raise RecoveryError(f"stage {stage!r} is not recoverable")
        # recoverable: unfinished (or rolled-back corrupt) downstream stage
        action = {"stage": stage, "prior_status": status}
        if rollback_at is not None and stage in dropped_stages:
            action["journal_rollback"] = True
        actions.append(action)
        if dry_run:
            continue
        rebuilder = rebuilders.get(stage)
        if rebuilder is None:
            raise RecoveryError(
                f"no rebuilder registered for recoverable stage {stage!r}"
            )
        new_artifacts = rebuilder(run_dir, journal)
        for rel in new_artifacts:
            assert_safe_write(run_dir / rel)
        journal["artifacts"].setdefault(stage, {}).update(new_artifacts)
        journal["completed_stages"].append(stage)
        journal_path = run_dir / journal_name
        assert_safe_write(journal_path)
        blob = _canonical(journal) + b"\n"
        tmp = journal_path.with_suffix(".tmp")
        tmp.write_bytes(blob)
        tmp.replace(journal_path)
        recovered.append(stage)

    final = classify_run(run_dir, stages=stages, journal_name=journal_name) if not dry_run else report
    return {
        "run_dir": str(run_dir),
        "dry_run": dry_run,
        "initial": report["stages"],
        "actions": actions,
        "recovered": recovered,
        "final": final["stages"],
        "complete": all(
            info["status"] == StageStatus.DONE.value
            for info in final["stages"].values()
        ),
        "evidence_class": EVIDENCE_CLASS,
    }

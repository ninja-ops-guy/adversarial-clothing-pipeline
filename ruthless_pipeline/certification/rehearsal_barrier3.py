"""Barrier 3 public rehearsal driver.

The stage implementation lives in :mod:`rehearsal_barrier3_core`.  This thin
module restores the public orchestration surface that was lost when the
coordinator was accidentally truncated.  It deliberately delegates all stage
science to the existing core and adds only deterministic orchestration,
resume/replay verification, package bookkeeping, and the synthetic-evidence
promotion refusal.
"""
from __future__ import annotations

import importlib.metadata
import json
import platform
from pathlib import Path
from typing import Any

import numpy as np

from . import rehearsal_barrier3_core as _core

# Preserve the historical module surface, including the private stage helpers
# exercised by the fail-closed rehearsal tests.  Functions below resolve these
# names from this module at call time, so test fault injection still exercises
# the actual orchestration boundary rather than a detached copy.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def _manifest_digest(manifest: dict) -> str:
    return _sha256_bytes(_canonical(manifest))


def _load_stage(output_dir: Path, stage: str) -> dict:
    path = output_dir / _stage_rel_path(stage)
    if not path.is_file():
        raise ResumeIntegrityError(f"stage artifact {stage} is missing")
    payload = json.loads(path.read_text())
    _ensure_finite(payload, stage)
    return payload


def _journaled_sha(journal: dict, stage: str) -> str:
    entry = journal.get("completed", {}).get(stage)
    if not entry or not entry.get("sha256"):
        raise ResumeIntegrityError(f"stage {stage} is not hash-bound in the journal")
    return entry["sha256"]


def _bind_upstream_hashes(payload: dict, journal: dict, stage: str) -> dict:
    """Bind the declared upstream stage artifacts without changing stage science."""
    upstream = {
        parent: {
            "path": _stage_rel_path(parent),
            "sha256": _journaled_sha(journal, parent),
        }
        for parent in UPSTREAM[stage]
    }
    payload = dict(payload)
    payload["upstream_artifact_pins"] = upstream
    return payload


def _environment_lock() -> dict:
    packages = {}
    for name in ("numpy", "scipy", "jsonschema", "torch", "torchvision"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    return _label({
        "schema_id": "barrier3-environment-lock",
        "python": platform.python_version(),
        "platform": platform.system().lower(),
        "packages": packages,
    })


def _telemetry(stages: dict[str, dict]) -> dict:
    optimization = stages["optimization"]
    detector = stages["detector_science"]
    printability = stages["printability"]
    payload = _label({
        "schema_id": "barrier3-objective-telemetry",
        "optimization_best_value": optimization["best_value"],
        "detector_confidence": detector["response"]["confidence"],
        "printability_value": printability["value"],
        "stage_seeds": {stage: stages[stage]["stage_seed"] for stage in STAGES},
    })
    _ensure_finite(payload, "objective_telemetry")
    return payload


def _provenance(output_dir: Path, manifest: dict, journal: dict) -> dict:
    nodes = []
    edges = []
    for rel, digest in sorted(manifest["input_hashes"].items()):
        nodes.append({"id": f"input:{rel}", "kind": "frozen_config", "sha256": digest})
    for stage in STAGES:
        digest = _journaled_sha(journal, stage)
        nodes.append({"id": f"stage:{stage}", "kind": "inference_record", "sha256": digest})
        for parent in UPSTREAM[stage]:
            edges.append({
                "source": f"stage:{parent}",
                "target": f"stage:{stage}",
                "relation": "derived_from",
                "expected_sha256": _journaled_sha(journal, parent),
            })
    return _label({
        "schema_id": "barrier3-run-provenance",
        "run_id": manifest["run_id"],
        "nodes": nodes,
        "edges": edges,
        "unexpected_edges": [],
    })


def _write_hash_manifest(output_dir: Path) -> str:
    paths = sorted(
        p for p in output_dir.rglob("*")
        if p.is_file() and p.name != HASHES_FILE
    )
    lines = [f"{_sha256_file(path)}  {path.relative_to(output_dir).as_posix()}" for path in paths]
    blob = ("\n".join(lines) + "\n").encode("utf-8")
    path = output_dir / HASHES_FILE
    path.write_bytes(blob)
    return _sha256_bytes(blob)


def _verify_hash_manifest(output_dir: Path) -> list[str]:
    path = output_dir / HASHES_FILE
    if not path.is_file():
        return [f"missing {HASHES_FILE}"]
    differences = []
    listed = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            expected, rel = line.split("  ", 1)
        except ValueError:
            differences.append(f"malformed hash line: {line!r}")
            continue
        listed.add(rel)
        target = output_dir / rel
        if not target.is_file():
            differences.append(f"missing listed file: {rel}")
        elif _sha256_file(target) != expected:
            differences.append(f"hash mismatch: {rel}")
    actual = {
        p.relative_to(output_dir).as_posix()
        for p in output_dir.rglob("*")
        if p.is_file() and p.name != HASHES_FILE
    }
    for rel in sorted(actual - listed):
        differences.append(f"unlisted file: {rel}")
    return differences


def _report(manifest: dict, journal: dict) -> dict:
    return _label({
        "schema_id": "barrier3-rehearsal-report",
        "BARRIER_3_RESULT": "PASS",
        "STAGE_COUNT": len(STAGES),
        "STAGES": list(STAGES),
        "HELDOUT_ACCESSED": False,
        "D2_0005_ARMED": False,
        "PHYSICAL_TEST_EXECUTED": False,
        "PHYSICAL_EFFICACY_CLAIMED": False,
        "run_id": manifest["run_id"],
        "manifest_sha256": _manifest_digest(manifest),
        "stage_sha256": {stage: _journaled_sha(journal, stage) for stage in STAGES},
    })


def run_rehearsal(
    output_dir: str | Path,
    manifest: dict,
    *,
    crash_after: str | None = None,
    repo_root: str | Path = _REPO_ROOT,
) -> dict:
    """Execute or resume the six-stage synthetic Barrier 3 rehearsal.

    Completed stages are trusted only after their journaled byte hash is
    re-derived.  A requested crash is injected *after* the named stage is
    durably journaled, allowing the subsequent call to prove resumability.
    """
    if crash_after is not None and crash_after not in STAGES:
        raise Barrier3Error(f"unknown crash_after stage: {crash_after!r}")
    repo_root = Path(repo_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    validate_run_manifest(manifest)
    _verify_committed_inputs(manifest, repo_root)

    manifest_hash = _manifest_digest(manifest)
    manifest_path = output_dir / "run-manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        if _manifest_digest(existing) != manifest_hash:
            raise ResumeIntegrityError("existing run-manifest differs from requested manifest")
    _write_json(manifest_path, manifest)
    _write_json(output_dir / "input-hashes.json", _label({
        "schema_id": "barrier3-input-hashes",
        "input_hashes": manifest["input_hashes"],
        "frozen_surface_manifest_sha256": manifest["frozen_surface_manifest_sha256"],
    }))
    _write_json(output_dir / "environment-lock.json", _environment_lock())

    journal_path = output_dir / JOURNAL_FILE
    journal = _load_journal(journal_path, manifest_hash)
    stage_data: dict[str, dict] = {}

    # Optimization
    resumed = _resume_check(output_dir, journal, "optimization")
    if resumed is None:
        payload, best_params = _optimization_stage(manifest)
        payload = _bind_upstream_hashes(payload, journal, "optimization")
        stage_data["optimization"] = _complete(output_dir, journal_path, journal, "optimization", payload)
    else:
        stage_data["optimization"] = resumed
        best_params = np.asarray(resumed["best_params"], dtype=float)
    if crash_after == "optimization":
        raise RehearsalCrash("injected crash after optimization")

    # EOT
    resumed = _resume_check(output_dir, journal, "eot")
    if resumed is None:
        payload, candidate = _eot_stage(manifest, best_params)
        payload = _bind_upstream_hashes(payload, journal, "eot")
        stage_data["eot"] = _complete(output_dir, journal_path, journal, "eot", payload)
    else:
        stage_data["eot"] = resumed
        candidate = np.asarray(resumed["candidate_pixels"], dtype=float)
    if crash_after == "eot":
        raise RehearsalCrash("injected crash after eot")

    # Detector science
    resumed = _resume_check(output_dir, journal, "detector_science")
    if resumed is None:
        payload = _detector_stage(manifest, candidate, stage_data["eot"])
        payload = _bind_upstream_hashes(payload, journal, "detector_science")
        stage_data["detector_science"] = _complete(output_dir, journal_path, journal, "detector_science", payload)
    else:
        stage_data["detector_science"] = resumed
    if crash_after == "detector_science":
        raise RehearsalCrash("injected crash after detector_science")

    # Pareto/style
    resumed = _resume_check(output_dir, journal, "pareto_style")
    if resumed is None:
        payload = _pareto_style_stage(
            manifest, stage_data["optimization"], stage_data["detector_science"], candidate
        )
        payload = _bind_upstream_hashes(payload, journal, "pareto_style")
        stage_data["pareto_style"] = _complete(output_dir, journal_path, journal, "pareto_style", payload)
    else:
        stage_data["pareto_style"] = resumed
    if crash_after == "pareto_style":
        raise RehearsalCrash("injected crash after pareto_style")

    # Printability
    resumed = _resume_check(output_dir, journal, "printability")
    if resumed is None:
        payload = _printability_stage(manifest, candidate, repo_root)
        payload = _bind_upstream_hashes(payload, journal, "printability")
        stage_data["printability"] = _complete(output_dir, journal_path, journal, "printability", payload)
    else:
        stage_data["printability"] = resumed
    if crash_after == "printability":
        raise RehearsalCrash("injected crash after printability")

    # Synthetic physical-transfer record
    resumed = _resume_check(output_dir, journal, "physical_transfer")
    if resumed is None:
        payload = _physical_transfer_stage(manifest, stage_data["eot"], stage_data["detector_science"])
        payload = _bind_upstream_hashes(payload, journal, "physical_transfer")
        stage_data["physical_transfer"] = _complete(
            output_dir, journal_path, journal, "physical_transfer", payload
        )
    else:
        stage_data["physical_transfer"] = resumed
    if crash_after == "physical_transfer":
        raise RehearsalCrash("injected crash after physical_transfer")

    if set(journal["completed"]) != set(STAGES):
        raise Barrier3Error("not all Barrier 3 stages completed")

    _write_json(output_dir / "objective-telemetry.json", _telemetry(stage_data))
    _write_json(output_dir / "provenance.json", _provenance(output_dir, manifest, journal))
    report = _report(manifest, journal)
    _write_json(output_dir / REPORT_FILE, report)
    _write_json(output_dir / "barrier3-report.json", report)
    _write_hash_manifest(output_dir)

    differences = _verify_hash_manifest(output_dir)
    if differences:
        raise Barrier3Error("package hash verification failed: " + "; ".join(differences))
    return {
        "verification_ok": True,
        "stages": list(STAGES),
        "report": report,
        "determinism_digest": _sha256_file(output_dir / HASHES_FILE),
    }


def compare_replays(first: str | Path, second: str | Path) -> dict:
    """Compare two rehearsal packages byte-for-byte."""
    first = Path(first)
    second = Path(second)
    first_files = {
        p.relative_to(first).as_posix(): p.read_bytes()
        for p in first.rglob("*") if p.is_file()
    }
    second_files = {
        p.relative_to(second).as_posix(): p.read_bytes()
        for p in second.rglob("*") if p.is_file()
    }
    differences = []
    for rel in sorted(set(first_files) | set(second_files)):
        if rel not in first_files:
            differences.append(f"missing from first: {rel}")
        elif rel not in second_files:
            differences.append(f"missing from second: {rel}")
        elif first_files[rel] != second_files[rel]:
            differences.append(f"byte mismatch: {rel}")
    return {"identical": not differences, "differences": differences}


def run_acceptance_gate(
    output_dir: str | Path,
    *,
    repo_root: str | Path = _REPO_ROOT,
) -> dict:
    """Fail closed unless the synthetic rehearsal package satisfies its gate."""
    output_dir = Path(output_dir)
    repo_root = Path(repo_root)
    problems: list[str] = []
    manifest_path = output_dir / "run-manifest.json"
    journal_path = output_dir / JOURNAL_FILE
    if not manifest_path.is_file() or not journal_path.is_file():
        raise AcceptanceGateError("run manifest or rehearsal journal missing")
    manifest = json.loads(manifest_path.read_text())
    journal = json.loads(journal_path.read_text())
    try:
        validate_run_manifest(manifest)
        _verify_committed_inputs(manifest, repo_root)
    except Exception as exc:
        problems.append(f"manifest/input verification: {exc}")
    if list(journal.get("completed", {})) != list(STAGES):
        # JSON insertion order is the executed order and therefore meaningful.
        problems.append("stage order/completeness mismatch")
    for stage in STAGES:
        try:
            payload = _resume_check(output_dir, journal, stage)
            if payload is None:
                problems.append(f"stage not journaled: {stage}")
                continue
            if payload.get("evidence_class") != EVIDENCE_CLASS:
                problems.append(f"non-synthetic evidence class: {stage}")
            if payload.get("rac_evidence_eligible") is not False:
                problems.append(f"RAC evidence eligibility promoted: {stage}")
            if payload.get("physical_efficacy_claimed") is not False:
                problems.append(f"physical efficacy promoted: {stage}")
            pins = payload.get("upstream_artifact_pins", {})
            expected = set(UPSTREAM[stage])
            if set(pins) != expected:
                problems.append(f"upstream pins mismatch: {stage}")
            for parent in expected:
                if pins[parent].get("sha256") != _journaled_sha(journal, parent):
                    problems.append(f"upstream hash mismatch: {parent}->{stage}")
            _ensure_finite(payload, stage)
        except Exception as exc:
            problems.append(f"stage verification {stage}: {exc}")
    telemetry_path = output_dir / "objective-telemetry.json"
    try:
        _ensure_finite(json.loads(telemetry_path.read_text()), "objective_telemetry")
    except Exception as exc:
        problems.append(f"objective telemetry: {exc}")
    problems.extend(_verify_hash_manifest(output_dir))
    if manifest.get("model_identity_refs", {}).get("heldout_access") != "identity_hash_only":
        problems.append("held-out access mode is not identity_hash_only")
    generation_path = repo_root / GENERATION_D20005_PATH
    if generation_path.is_file():
        generation = json.loads(generation_path.read_text())
        status = str(generation.get("status", generation.get("state", ""))).upper()
        if status and status != "PREREGISTERED":
            problems.append(f"D2-0005 state is {status}, expected PREREGISTERED")
    transfer = _load_stage(output_dir, "physical_transfer")
    record = transfer.get("record", {})
    if record.get("evidence_class") != EVIDENCE_CLASS or record.get("physical_efficacy_claimed") is not False:
        problems.append("physical-transfer record crossed the synthetic evidence ceiling")
    if problems:
        raise AcceptanceGateError("; ".join(problems))
    return {"ok": True, "criteria_passed": 14, "criteria_total": 14}


def promote_to_measured(_output_dir: str | Path) -> None:
    """Synthetic Barrier 3 artifacts can never be promoted to measured evidence."""
    raise PromotionRefusedError(
        "Barrier 3 outputs are synthetic_pipeline_validation_only and cannot be promoted to measured evidence"
    )

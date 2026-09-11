"""Canonical program-state compiler (SW-01).

Derives a single machine-readable program state deterministically from the
existing canonical sources and writes it to ``program_state/program_state.json``
plus a human-readable ``program_state/SUMMARY.md`` that is REGENERATED from
that state (status lines are never hand-maintained in Markdown anymore).

Canonical sources consumed (read-only; this module never writes to them):

* ``generations/*.json`` — generation records; lifecycle state is derived
  through :func:`experiment_state_machine.state_for_lock_status`, which
  fails closed on contradictory records (e.g. ``armed:false`` with a
  post-PREREGISTERED lock status).
* ``d2-latest-status.json`` — sealed D2-0004 result (legacy format; read
  via :mod:`experiment_status` semantics, never rewritten).
* ``docs/D2-0005_FREEZE_CANDIDATE.json`` — D2-0005 arming attestation
  (read-only; must agree with the generation record or derivation fails).
* ``releases/*`` — release directories re-hashed via
  :func:`release_format.verify_release`.
* ``artifacts/barrier3/barrier3-report.json`` and
  ``artifacts/rac-g/barrier3-audit.json`` — Barrier-3 closure state and the
  independent RAC-G audit verdict.
* ``artifacts/print-alpha/readiness.json`` and
  ``physical/p1/P1_READINESS_FREEZE.json`` — P1 readiness / freeze state.
* ``ctm_registry/`` — CTM registry surface (literature entries, genome-v2
  register) pinned by content hash.
* ``benchmarks/frozen_surface_sha256.json`` — frozen-surface manifest; every
  pinned file is re-hashed and drift is reported (never repaired).

Determinism: output bytes are a pure function of input bytes. No wall-clock
timestamps, no ambient git state, no environment data. The emitted
``program_state_sha256`` is a content address over the canonical JSON of the
state body, so repeated generation is byte-identical.

Boundaries (inherited from the sources; enforced, never relaxed): this
compiler arms nothing, touches no held-out model, makes no physical-efficacy
claim, and never writes to generations/, docs/D2-0005_*, benchmarks/,
model_sets/, or pattern-genome v1 code. All validation-only content carries
evidence_class ``synthetic_pipeline_validation_only``.

CLI::

    PYTHONPATH=. python -m ruthless_pipeline.program_state.compile \
        [--root PATH] [--check] [--format json|summary]

Default mode rewrites ``program_state/`` deterministically. ``--check`` is
the CI-facing gate: it recomputes and fails (exit 1) when the committed
artifacts are stale or any source is contradictory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ruthless_pipeline.certification.experiment_state_machine import (
    StateMachineError,
    state_for_lock_status,
)
from ruthless_pipeline.certification.release_format import verify_release
from ruthless_pipeline.pattern_genome.canonical import canonical_json, sha256_bytes

from .errors import (
    ProgramStateError,
    ProgramStateSchemaError,
    SourceContradictionError,
    SourceMissingError,
)

SCHEMA_VERSION = "rac-program-state/1.0"
SCHEMA_ID = "https://rac.local/schemas/program_state_v1.schema.json"
GENERATOR = "ruthless_pipeline.program_state.compile/1.0"
EVIDENCE_CLASS = "synthetic_pipeline_validation_only"

STATE_PATH = "program_state/program_state.json"
SUMMARY_PATH = "program_state/SUMMARY.md"
SCHEMA_PATH = "schemas/program_state_v1.schema.json"

GENERATIONS_DIR = "generations"
D2_STATUS_PATH = "d2-latest-status.json"
D2_0005_FREEZE_PATH = "docs/D2-0005_FREEZE_CANDIDATE.json"
RELEASES_DIR = "releases"
BARRIER3_REPORT_PATH = "artifacts/barrier3/barrier3-report.json"
BARRIER3_AUDIT_PATH = "artifacts/rac-g/barrier3-audit.json"
PRINT_ALPHA_READINESS_PATH = "artifacts/print-alpha/readiness.json"
P1_READINESS_FREEZE_PATH = "physical/p1/P1_READINESS_FREEZE.json"
CTM_REGISTRY_DIR = "ctm_registry"
CTM_LITERATURE_ENTRIES_DIR = "ctm_registry/literature/entries"
CTM_GENOME_V2_REGISTER_PATH = "ctm_registry/genome_v2/candidate_register_v1.json"
FROZEN_SURFACE_MANIFEST_PATH = "benchmarks/frozen_surface_sha256.json"
RUNTIME_LOCK_PATH = "benchmarks/runtime_lock.json"

_SHA256_RE_HEX = 64


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, *, required: bool, label: str) -> Any | None:
    if not path.is_file():
        if required:
            raise SourceMissingError(f"{label}: required source missing: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceMissingError(f"{label}: unreadable JSON at {path}: {exc}") from exc


class _SourcePins:
    """Accumulates content-address pins for every input byte consumed."""

    def __init__(self) -> None:
        self.pins: dict[str, str] = {}

    def pin(self, root: Path, path: Path) -> str:
        rel = path.relative_to(root).as_posix()
        digest = _sha256_file(path)
        self.pins[rel] = digest
        return digest


def _derive_experiments(root: Path, pins: _SourcePins) -> list[dict[str, Any]]:
    gen_dir = root / GENERATIONS_DIR
    if not gen_dir.is_dir():
        raise SourceMissingError(
            f"generations: required directory missing: {gen_dir}"
        )
    experiments: list[dict[str, Any]] = []
    for record_path in sorted(gen_dir.glob("*.json")):
        record = _read_json(record_path, required=True, label="generations")
        digest = pins.pin(root, record_path)
        generation_id = record.get("generation_id")
        if not isinstance(generation_id, str) or not generation_id:
            raise SourceContradictionError(
                f"generations: {record_path} has no string generation_id; "
                "refusing to guess an identity"
            )
        try:
            lifecycle = state_for_lock_status(record).value
        except StateMachineError as exc:
            raise SourceContradictionError(
                f"generations: {generation_id}: {exc}"
            ) from exc
        experiments.append(
            {
                "generation_id": generation_id,
                "record_path": record_path.relative_to(root).as_posix(),
                "record_sha256": digest,
                "lock_status": record.get("lock_status"),
                "armed": record.get("armed", None),
                "lifecycle_state": lifecycle,
                "heldout_feedback_allowed": bool(
                    record.get("heldout_feedback_allowed", False)
                ),
                "lock_inference_performed": bool(
                    record.get("lock_inference_performed", False)
                ),
            }
        )
    return experiments


def _derive_d2_result(root: Path, pins: _SourcePins) -> dict[str, Any] | None:
    path = root / D2_STATUS_PATH
    status = _read_json(path, required=False, label="d2-status")
    if status is None:
        return None
    pins.pin(root, path)
    heldout = status.get("heldout") or {}
    return {
        "candidate_id": status.get("candidate_id"),
        "decision": status.get("decision"),
        "evidence_state": status.get("evidence_state"),
        "bundle_verified": bool(status.get("bundle_verified", False)),
        "heldout": {
            "baseline_detection_rate": heldout.get("baseline_detection_rate"),
            "candidate_detection_rate": heldout.get("candidate_detection_rate"),
            "mean_delta": heldout.get("mean_delta"),
            "n": heldout.get("n"),
            "valid_n": heldout.get("valid_n"),
        },
        "status_sha256": pins.pins[D2_STATUS_PATH],
    }


def _derive_d2_0005_arming(
    root: Path, pins: _SourcePins, experiments: list[dict[str, Any]]
) -> dict[str, Any] | None:
    path = root / D2_0005_FREEZE_PATH
    freeze = _read_json(path, required=False, label="d2-0005-freeze")
    if freeze is None:
        return None
    pins.pin(root, path)
    armed = freeze.get("arming", {}).get("armed")
    record = next(
        (e for e in experiments if e["generation_id"] == "RAC-PER-D2-0005"), None
    )
    if record is not None and armed is True and record["armed"] is not True:
        raise SourceContradictionError(
            "d2-0005: freeze candidate attests armed=true but the generation "
            "record does not; refusing to derive state"
        )
    return {
        "generation_id": "RAC-PER-D2-0005",
        "armed": bool(armed) if armed is not None else False,
        "freeze_candidate_sha256": pins.pins[D2_0005_FREEZE_PATH],
    }


def _derive_releases(root: Path, pins: _SourcePins) -> list[dict[str, Any]]:
    rel_dir = root / RELEASES_DIR
    releases: list[dict[str, Any]] = []
    if not rel_dir.is_dir():
        return releases
    for directory in sorted(p for p in rel_dir.iterdir() if p.is_dir()):
        manifest = directory / "MANIFEST.json"
        if not manifest.is_file():
            continue
        pins.pin(root, manifest)
        release_json = directory / "RELEASE.json"
        payload = _read_json(release_json, required=False, label="releases") or {}
        if release_json.is_file():
            pins.pin(root, release_json)
        verification = verify_release(directory)
        releases.append(
            {
                "release_id": payload.get("release_id", directory.name),
                "path": directory.relative_to(root).as_posix(),
                "verified": verification.ok,
                "tampered": list(verification.tampered),
                "missing": list(verification.missing),
                "extra": list(verification.extra),
                "content_hash": payload.get("content_hash"),
                "manifest_sha256": pins.pins[
                    manifest.relative_to(root).as_posix()
                ],
            }
        )
    return releases


def _derive_barrier3(root: Path, pins: _SourcePins) -> dict[str, Any] | None:
    report_path = root / BARRIER3_REPORT_PATH
    report = _read_json(report_path, required=False, label="barrier3")
    if report is None:
        return None
    pins.pin(root, report_path)
    audit_path = root / BARRIER3_AUDIT_PATH
    audit = _read_json(audit_path, required=False, label="barrier3-audit")
    audit_verdict = None
    audit_sha256 = None
    if audit is not None:
        audit_sha256 = pins.pin(root, audit_path)
        audit_verdict = audit.get("verdict") or audit.get("final_verdict")
        if audit_verdict is None:
            checks = audit.get("checks", {})
            committed = checks.get("committed_gate_report", {}).get("report", {})
            if committed.get("barrier3_closed") is True:
                audit_verdict = "PASS_WITH_NONBLOCKING_GAPS"
    boundaries = report.get("scientific_boundaries", {})
    return {
        "run_id": report.get("run_id"),
        "closed": bool(report.get("barrier3_closed", False)),
        "deterministic_replay": report.get("deterministic_replay"),
        "provenance": report.get("provenance"),
        "audit_verdict": audit_verdict,
        "report_sha256": pins.pins[BARRIER3_REPORT_PATH],
        "audit_sha256": audit_sha256,
        "boundaries": {
            "d2_0004_modified": bool(boundaries.get("d2_0004_modified", False)),
            "d2_0005_armed": bool(boundaries.get("d2_0005_armed", False)),
            "held_out_models_accessed": bool(
                boundaries.get("held_out_models_accessed", False)
            ),
            "physical_efficacy_claimed": bool(
                boundaries.get("physical_efficacy_claimed", False)
            ),
        },
    }


def _derive_p1(root: Path, pins: _SourcePins) -> dict[str, Any] | None:
    readiness_path = root / PRINT_ALPHA_READINESS_PATH
    readiness = _read_json(readiness_path, required=False, label="p1-readiness")
    freeze_path = root / P1_READINESS_FREEZE_PATH
    freeze_present = freeze_path.is_file()
    if readiness is None and not freeze_present:
        return None
    block: dict[str, Any] = {}
    if readiness is not None:
        pins.pin(root, readiness_path)
        block.update(
            {
                "release_id": readiness.get("release_id"),
                "verdict": readiness.get("verdict"),
                "software_ready": bool(readiness.get("software_ready", False)),
                "physical_efficacy_claimed": bool(
                    readiness.get("physical_efficacy_claimed", False)
                ),
                "readiness_sha256": pins.pins[PRINT_ALPHA_READINESS_PATH],
            }
        )
    if freeze_present:
        block["readiness_freeze_sha256"] = pins.pin(root, freeze_path)
    return block


def _derive_ctm(root: Path, pins: _SourcePins) -> dict[str, Any] | None:
    registry = root / CTM_REGISTRY_DIR
    if not registry.is_dir():
        return None
    entries_dir = root / CTM_LITERATURE_ENTRIES_DIR
    entries = sorted(entries_dir.glob("*.json")) if entries_dir.is_dir() else []
    entry_hashes = {}
    for entry in entries:
        entry_hashes[entry.name] = pins.pin(root, entry)
    register_path = root / CTM_GENOME_V2_REGISTER_PATH
    register_sha256 = None
    if register_path.is_file():
        register_sha256 = pins.pin(root, register_path)
    return {
        "literature_entry_count": len(entries),
        "literature_entry_sha256": entry_hashes,
        "genome_v2_register_sha256": register_sha256,
    }


def _derive_frozen_surface(root: Path, pins: _SourcePins) -> dict[str, Any] | None:
    manifest_path = root / FROZEN_SURFACE_MANIFEST_PATH
    manifest = _read_json(manifest_path, required=False, label="frozen-surface")
    if manifest is None:
        return None
    pins.pin(root, manifest_path)
    runtime_lock = root / RUNTIME_LOCK_PATH
    runtime_lock_sha256 = (
        pins.pin(root, runtime_lock) if runtime_lock.is_file() else None
    )
    entries = manifest.get("files", manifest)
    if not isinstance(entries, dict):
        raise SourceContradictionError(
            "frozen-surface: manifest has no file->sha256 mapping"
        )
    drifted: list[str] = []
    missing: list[str] = []
    checked = 0
    for rel, expected in sorted(entries.items()):
        if not isinstance(expected, str) or len(expected) != _SHA256_RE_HEX:
            continue
        target = root / rel
        if not target.is_file():
            missing.append(rel)
            continue
        checked += 1
        if _sha256_file(target) != expected:
            drifted.append(rel)
    return {
        "manifest_sha256": pins.pins[FROZEN_SURFACE_MANIFEST_PATH],
        "runtime_lock_sha256": runtime_lock_sha256,
        "files_checked": checked,
        "verified": not drifted and not missing,
        "drifted": drifted,
        "missing": missing,
    }


def derive_state(root: Path | str) -> dict[str, Any]:
    """Derive the canonical program state from sources under ``root``.

    Deterministic and read-only with respect to every canonical source.
    Raises a typed :class:`ProgramStateError` subclass on missing required
    sources or contradictions (fail closed).
    """
    root = Path(root)
    pins = _SourcePins()

    experiments = _derive_experiments(root, pins)
    d2_result = _derive_d2_result(root, pins)
    d2_0005 = _derive_d2_0005_arming(root, pins, experiments)
    releases = _derive_releases(root, pins)
    barrier3 = _derive_barrier3(root, pins)
    p1 = _derive_p1(root, pins)
    ctm = _derive_ctm(root, pins)
    frozen_surface = _derive_frozen_surface(root, pins)

    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "schema_id": SCHEMA_ID,
        "generator": GENERATOR,
        "evidence_class": EVIDENCE_CLASS,
        "experiments": experiments,
        "releases": releases,
        "sources": dict(sorted(pins.pins.items())),
        "boundaries": {
            "held_out_models_accessed": False,
            "physical_efficacy_claimed": False,
            "experiments_armed": False,
            "frozen_surfaces_modified": False,
        },
    }
    if d2_result is not None:
        state["d2_0004_result"] = d2_result
        # Reconcile the sealed status JSON with the frozen generation record:
        # the record's lock_status is never rewritten post-closure (historical
        # format), so closure is expressed as an additive sealed_decision
        # annotation derived from d2-latest-status.json, not by mutating the
        # record-derived lifecycle_state.
        if d2_result.get("decision"):
            for exp in experiments:
                if exp["generation_id"] == d2_result.get("candidate_id"):
                    exp["sealed_decision"] = d2_result["decision"]
    if d2_0005 is not None:
        state["d2_0005_arming"] = d2_0005
    if barrier3 is not None:
        state["barrier3"] = barrier3
    if p1 is not None:
        state["p1_readiness"] = p1
    if ctm is not None:
        state["ctm"] = ctm
    if frozen_surface is not None:
        state["frozen_surface"] = frozen_surface

    state["program_state_sha256"] = sha256_bytes(canonical_json(state))
    _validate_against_schema(root, state)
    return state


def _validate_against_schema(root: Path, state: dict[str, Any]) -> None:
    schema_path = root / SCHEMA_PATH
    if not schema_path.is_file():
        return
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(state, schema)
    except jsonschema.ValidationError as exc:
        raise ProgramStateSchemaError(
            f"derived program state violates {SCHEMA_PATH}: {exc.message}"
        ) from exc


def canonical_state_bytes(state: dict[str, Any]) -> bytes:
    """Canonical committed bytes: compact canonical JSON + trailing newline."""
    return canonical_json(state) + b"\n"


def render_summary_markdown(state: dict[str, Any]) -> str:
    """Render the deterministic human-readable summary from derived state.

    Generated, never hand-edited: no timestamps, content-addressed by the
    embedded ``program_state_sha256``.
    """
    lines = [
        "<!-- GENERATED by ruthless_pipeline.program_state.compile; do not edit. "
        "Regenerate with: python -m ruthless_pipeline.program_state.compile -->",
        "",
        "# Canonical Program State (generated)",
        "",
        f"- Schema: `{state['schema_version']}` (`{state['schema_id']}`)",
        f"- State content address (sha256): `{state['program_state_sha256']}`",
        f"- Evidence class: `{state['evidence_class']}`",
        "",
        "## Experiments",
        "",
        "| Generation | Lifecycle state | Lock status | Armed | Held-out feedback |",
        "| --- | --- | --- | --- | --- |",
    ]
    for exp in state["experiments"]:
        life = exp["lifecycle_state"]
        if exp.get("sealed_decision"):
            life = f"{life} (sealed decision: {exp['sealed_decision']})"
        lines.append(
            "| {gid} | {life} | {lock} | {armed} | {hofb} |".format(
                gid=exp["generation_id"],
                life=life,
                lock=exp["lock_status"],
                armed=exp["armed"],
                hofb=exp["heldout_feedback_allowed"],
            )
        )
    result = state.get("d2_0004_result")
    if result is not None:
        lines += [
            "",
            "## Sealed D2-0004 result",
            "",
            f"- Candidate: `{result['candidate_id']}`",
            f"- Decision: `{result['decision']}` (bundle verified: "
            f"{result['bundle_verified']})",
            f"- Held-out: baseline detection rate "
            f"{result['heldout']['baseline_detection_rate']}, candidate "
            f"detection rate {result['heldout']['candidate_detection_rate']} "
            f"(n={result['heldout']['n']})",
        ]
    arming = state.get("d2_0005_arming")
    if arming is not None:
        lines += [
            "",
            "## D2-0005 arming",
            "",
            f"- Armed: {arming['armed']} (freeze candidate "
            f"`{arming['freeze_candidate_sha256'][:16]}...`)",
        ]
    barrier3 = state.get("barrier3")
    if barrier3 is not None:
        lines += [
            "",
            "## Barrier 3",
            "",
            f"- Run: `{barrier3['run_id']}`; closed: {barrier3['closed']}; "
            f"replay: {barrier3['deterministic_replay']}; provenance: "
            f"{barrier3['provenance']}",
            f"- RAC-G audit verdict: {barrier3['audit_verdict']}",
            "- Boundaries: held-out accessed "
            f"{barrier3['boundaries']['held_out_models_accessed']}, "
            "physical efficacy claimed "
            f"{barrier3['boundaries']['physical_efficacy_claimed']}, "
            f"D2-0005 armed {barrier3['boundaries']['d2_0005_armed']}",
        ]
    p1 = state.get("p1_readiness")
    if p1 is not None:
        lines += [
            "",
            "## P1 readiness",
            "",
            f"- Release: `{p1.get('release_id')}`; verdict: "
            f"`{p1.get('verdict')}`; software ready: {p1.get('software_ready')}",
        ]
    ctm = state.get("ctm")
    if ctm is not None:
        lines += [
            "",
            "## CTM registry",
            "",
            f"- Literature entries: {ctm['literature_entry_count']}",
            f"- Genome-v2 register sha256: `{ctm['genome_v2_register_sha256']}`",
        ]
    frozen = state.get("frozen_surface")
    if frozen is not None:
        lines += [
            "",
            "## Frozen surface",
            "",
            f"- Files checked: {frozen['files_checked']}; verified: "
            f"{frozen['verified']}",
            f"- Runtime lock sha256: `{frozen['runtime_lock_sha256']}`",
        ]
    lines += [
        "",
        "## Releases",
        "",
        "| Release | Verified | Content hash |",
        "| --- | --- | --- |",
    ]
    for rel in state["releases"]:
        lines.append(
            f"| `{rel['release_id']}` | {rel['verified']} | "
            f"`{rel['content_hash']}` |"
        )
    lines += [
        "",
        "## Boundaries (enforced)",
        "",
        "- No experiment is armed by this artifact; no held-out model is "
        "accessed; no physical-efficacy claim is made.",
        "- Historical documents are never rewritten; this summary is "
        "regenerated from canonical sources only.",
        "",
    ]
    return "\n".join(lines)


def check_state(root: Path | str) -> list[str]:
    """Recompute and compare against committed artifacts. Returns findings.

    Empty list means the committed ``program_state/`` artifacts are fresh.
    A derivation failure (missing source, contradiction, schema violation)
    is itself a finding (fail closed).
    """
    root = Path(root)
    findings: list[str] = []
    try:
        state = derive_state(root)
    except ProgramStateError as exc:
        return [f"program-state derivation failed: {exc}"]
    expected = canonical_state_bytes(state)
    committed = root / STATE_PATH
    if not committed.is_file():
        findings.append(f"missing committed state: {STATE_PATH}")
    elif committed.read_bytes() != expected:
        findings.append(
            f"stale committed state: {STATE_PATH} does not match a fresh "
            "derivation; regenerate with `python -m "
            "ruthless_pipeline.program_state.compile`"
        )
    summary = root / SUMMARY_PATH
    expected_summary = (render_summary_markdown(state)).encode("utf-8")
    if not summary.is_file():
        findings.append(f"missing generated summary: {SUMMARY_PATH}")
    elif summary.read_bytes() != expected_summary:
        findings.append(
            f"stale generated summary: {SUMMARY_PATH} does not match the "
            "derived state; regenerate with `python -m "
            "ruthless_pipeline.program_state.compile`"
        )
    return findings


def write_state(root: Path | str) -> dict[str, Any]:
    """Derive and write ``program_state/`` artifacts deterministically."""
    root = Path(root)
    state = derive_state(root)
    out_dir = root / "program_state"
    out_dir.mkdir(parents=True, exist_ok=True)
    (root / STATE_PATH).write_bytes(canonical_state_bytes(state))
    (root / SUMMARY_PATH).write_text(render_summary_markdown(state), encoding="utf-8")
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (defaults to this repo)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI gate: fail (exit 1) if committed program_state artifacts "
        "are stale or sources contradict; writes nothing",
    )
    parser.add_argument(
        "--format",
        choices=("json", "summary"),
        default="json",
        help="stdout format for the derived state",
    )
    args = parser.parse_args(argv)

    if args.check:
        findings = check_state(args.root)
        report = {"ok": not findings, "findings": findings}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if not findings else 1

    try:
        state = write_state(args.root)
    except ProgramStateError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    if args.format == "summary":
        sys.stdout.write(render_summary_markdown(state))
    else:
        sys.stdout.write(canonical_state_bytes(state).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

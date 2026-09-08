"""Ingest a CLOSED measured-benchmark generation into a canonical RAC-EXP release.

This tool is run once, after a measured benchmark generation (e.g.
RAC-PER-D2-0004) closes. It converts the run artifacts into:

1. An optimization-telemetry record (telemetry_contract): the pre-held-out
   portion from surrogate-phase artifacts plus the append-only HeldOutOutcome
   from the measured result JSON.
2. An ExperimentArtifact registered into an ExperimentRegistry JSON
   (created or appended).
3. A sealed RAC-EXP-YYYY-NNN/ release bundle per docs/RESEARCH_RELEASE_FORMAT.md
   (experiment.json, stages/, REPORT.md, FAILURE.json on FAIL, RELEASE.json,
   REVISIONS.json, MANIFEST.json), verified with verify_release.

Field-source policy (see INGEST_NOTES.md for the full mapping table):

* MANDATORY fields must come from real artifacts; the tool never fabricates
  them. In the default (strict) mode, the surrogate-selection report must carry
  an ``optimization_telemetry`` block (the D2-0005+ contract shape) providing
  per-surrogate rates, transformation variance, spectral band energy, fidelity,
  printability, objective trajectory, coverage metrics, and optimizer config.
* ``--legacy-d20004`` documents the D2-0004 gap: fields the D2-0004 pipeline
  never recorded (spectral_band_energy, objective_trajectory, coverage_metrics,
  optimizer_config) are recorded as JSON null with the gap listed under
  ``validity_flags.not_recorded_fields``; per-surrogate rates and the
  transformation sweep are reconstructed from the measured result's
  surrogate-role model entries and rows (surrogate-only measurements, taken
  before any held-out feedback was used).

Guardrails: refuses to run when the generation JSON is not closed
(``lock_inference_performed`` false or status not containing "CLOSED"),
refuses to overwrite an existing release directory, and fails loudly on any
missing input file. Stdlib + the repo package only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruthless_pipeline.certification.experiment import (
    ExperimentArtifact,
    ExperimentRegistry,
    StageRef,
)
from ruthless_pipeline.certification.failure_taxonomy import classify_failure
from ruthless_pipeline.certification.schema_version import require_schema_version
from ruthless_pipeline.certification.release_format import (
    ReleaseManifest,
    ReleaseRevisionLog,
    compute_content_hash,
    hash_file,
    verify_release,
)
from ruthless_pipeline.certification.telemetry_contract import (
    CONTRACT_VERSION,
    CalibrationProfileRef,
    HeldOutOutcome,
    OptimizerConfig,
    PreHeldOutTelemetry,
    TelemetryRecord,
    cross_model_disagreement,
)

#: Sentinel recorded (as JSON null) for mandatory contract fields that the
#: source pipeline genuinely did not record; only allowed in legacy mode.
NOT_RECORDED = "not_recorded"

#: Contract fields that must never be null, in any mode.
NON_NULLABLE_FIELDS: tuple[str, ...] = (
    "candidate_sha256",
    "generation_id",
    "recorded_utc",
    "surrogate_mean_detection_rate",
    "surrogate_worst_case_detection_rate",
    "per_surrogate_detection_rates",
    "cross_model_disagreement",
    "transformation_sweep_variance",
    "pattern_fidelity",
    "printability",
)

#: Contract fields the D2-0004 pipeline did not record; --legacy-d20004
#: records them as null with a validity flag instead of fabricating values.
LEGACY_D20004_NOT_RECORDED: tuple[str, ...] = (
    "spectral_band_energy",
    "objective_trajectory",
    "coverage_metrics",
    "optimizer_config",
)

#: Downstream stages invalidated when the generation closes as FAIL.
FAIL_INVALIDATES: tuple[str, ...] = (
    "calibration_profile",
    "sku",
    "physical_session",
    "certificate",
)


class IngestError(RuntimeError):
    """Fatal ingest problem; reported to stderr with exit code 2."""


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise IngestError(f"missing required {label}: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise IngestError(f"{label} is not valid JSON ({path}): {exc}") from exc


def _require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise IngestError(f"missing required {label}: {path}")
    return path


def _check_generation_closed(generation: dict[str, Any], path: Path) -> str:
    require_schema_version(generation, "1.0", label=f"generation record {path}")
    if not generation.get("lock_inference_performed", False):
        raise IngestError(
            f"generation {path} has lock_inference_performed=false; "
            "the generation is not closed — run the measured benchmark first"
        )
    status = str(generation.get("status", ""))
    if "CLOSED" not in status.upper():
        raise IngestError(
            f"generation status {status!r} does not indicate closure "
            "(expected a status containing 'CLOSED')"
        )
    generation_id = str(generation.get("generation_id", ""))
    if not generation_id:
        raise IngestError(f"generation {path} has no generation_id")
    return generation_id


def _transformation_sweep(rows: list[dict[str, Any]]) -> tuple[float | None, list[float]]:
    """Per-condition surrogate candidate detection rates + population variance.

    Uses only baseline-qualified surrogate rows from the measured result; one
    rate per transformation condition (mean across surrogate models).
    """
    by_condition: dict[tuple, list[float]] = {}
    for row in rows:
        if row.get("split") != "surrogate" or not row.get("baseline_qualified"):
            continue
        detected = row.get("candidate_detected")
        if detected is None:
            continue
        key = (
            row.get("brightness"),
            row.get("scale"),
            row.get("blur_sigma"),
            row.get("rotation_deg"),
        )
        by_condition.setdefault(key, []).append(float(detected))
    if not by_condition:
        return None, []
    rates = [sum(v) / len(v) for v in by_condition.values()]
    mean = sum(rates) / len(rates)
    variance = sum((r - mean) ** 2 for r in rates) / len(rates)
    return variance, rates


def _model_rates(measured: dict[str, Any], role: str) -> dict[str, float]:
    rates: dict[str, float] = {}
    for model_id, entry in (measured.get("models") or {}).items():
        if entry.get("role") != role:
            continue
        rate = entry.get("candidate_detection_rate")
        if rate is None:
            raise IngestError(
                f"measured result model {model_id!r} (role={role}) has no "
                "candidate_detection_rate"
            )
        rates[model_id] = float(rate)
    return rates


def build_pre_telemetry(
    *,
    candidate_sha256: str,
    generation_id: str,
    recorded_utc: str,
    surrogate_selection: dict[str, Any],
    measured: dict[str, Any],
    legacy_d20004: bool,
) -> tuple[dict[str, Any], list[str]]:
    """Build the pre-held-out telemetry dict; returns (pre, not_recorded_fields).

    Strict mode requires the surrogate-selection report's
    ``optimization_telemetry`` block (D2-0005+ contract shape). Legacy D2-0004
    mode reconstructs what it can from surrogate-phase and surrogate-role
    measured artifacts and records the rest as null.
    """
    winner = surrogate_selection.get("winner") or {}
    not_recorded: list[str] = []

    if legacy_d20004:
        per_surrogate = _model_rates(measured, "surrogate")
        if len(per_surrogate) < 2:
            raise IngestError(
                "legacy D2-0004 mode needs at least 2 surrogate-role models in "
                "the measured result to reconstruct per-surrogate rates"
            )
        surrogate_mean = winner.get("candidate_detection_rate")
        if surrogate_mean is None:
            surrogate_mean = sum(per_surrogate.values()) / len(per_surrogate)
        variance, _ = _transformation_sweep(measured.get("rows") or [])
        if variance is None:
            raise IngestError(
                "measured result rows contain no baseline-qualified surrogate "
                "transformation sweep; transformation_sweep_variance cannot be "
                "reconstructed"
            )
        pre: dict[str, Any] = {
            "contract_version": CONTRACT_VERSION,
            "candidate_sha256": candidate_sha256,
            "generation_id": generation_id,
            "recorded_utc": recorded_utc,
            "surrogate_mean_detection_rate": float(surrogate_mean),
            "surrogate_worst_case_detection_rate": max(per_surrogate.values()),
            "per_surrogate_detection_rates": per_surrogate,
            "cross_model_disagreement": cross_model_disagreement(per_surrogate),
            "transformation_sweep_variance": variance,
            "pattern_fidelity": float(winner.get("reference_fidelity_score") or 0.0),
            "printability": float(winner.get("printability_proxy") or 0.0),
            "calibration_profile": None,
        }
        for field_name in LEGACY_D20004_NOT_RECORDED:
            pre[field_name] = None
            not_recorded.append(field_name)
        return pre, not_recorded

    # Strict mode: the surrogate-phase telemetry block (D2-0005+ contract).
    block = surrogate_selection.get("optimization_telemetry")
    if not isinstance(block, dict):
        raise IngestError(
            "surrogate-selection report has no 'optimization_telemetry' block; "
            "for D2-0004 artifacts re-run with --legacy-d20004"
        )
    required = (
        "per_surrogate_detection_rates",
        "transformation_sweep_variance",
        "spectral_band_energy",
        "pattern_fidelity",
        "printability",
        "objective_trajectory",
        "coverage_metrics",
        "optimizer_config",
    )
    missing = [k for k in required if block.get(k) is None]
    if missing:
        raise IngestError(
            "surrogate-phase optimization_telemetry block is missing mandatory "
            f"fields {missing}; if the pipeline genuinely did not record them, "
            "re-run with --legacy-d20004 to record them as null"
        )
    per_surrogate = {k: float(v) for k, v in block["per_surrogate_detection_rates"].items()}
    pre = {
        "contract_version": CONTRACT_VERSION,
        "candidate_sha256": candidate_sha256,
        "generation_id": generation_id,
        "recorded_utc": recorded_utc,
        "surrogate_mean_detection_rate": sum(per_surrogate.values()) / len(per_surrogate),
        "surrogate_worst_case_detection_rate": max(per_surrogate.values()),
        "per_surrogate_detection_rates": per_surrogate,
        "cross_model_disagreement": cross_model_disagreement(per_surrogate),
        "transformation_sweep_variance": float(block["transformation_sweep_variance"]),
        "spectral_band_energy": block["spectral_band_energy"],
        "pattern_fidelity": float(block["pattern_fidelity"]),
        "printability": float(block["printability"]),
        "objective_trajectory": block["objective_trajectory"],
        "coverage_metrics": block["coverage_metrics"],
        "optimizer_config": block["optimizer_config"],
        "calibration_profile": block.get("calibration_profile"),
    }
    # Validate strictly via the frozen contract.
    opt = block["optimizer_config"]
    cal = block.get("calibration_profile")
    strict_pre = dict(pre)
    strict_pre["optimizer_config"] = OptimizerConfig(**opt)
    strict_pre["calibration_profile"] = (
        CalibrationProfileRef(**cal) if cal is not None else None
    )
    record = TelemetryRecord(pre=PreHeldOutTelemetry(**strict_pre))
    record.validate()
    return pre, not_recorded


def build_outcome(
    *,
    candidate_sha256: str,
    measured: dict[str, Any],
    measured_path: Path,
    run_id: str,
    recorded_utc: str,
    pass_threshold: float,
) -> tuple[HeldOutOutcome, dict[str, float]]:
    heldout_rates = _model_rates(measured, "heldout")
    if not heldout_rates:
        raise IngestError(f"measured result {measured_path} has no heldout-role models")
    locked = measured.get("status") == "measured_locked" and bool(
        measured.get("certification_eligible")
    )
    heldout_mean = sum(heldout_rates.values()) / len(heldout_rates)
    verdict = "PASS" if locked and heldout_mean <= pass_threshold else "FAIL"
    outcome = HeldOutOutcome(
        candidate_sha256=candidate_sha256,
        heldout_detection_rates=heldout_rates,
        verdict=verdict,
        recorded_utc=recorded_utc,
        benchmark_run_id=run_id,
    )
    outcome.validate()
    return outcome, heldout_rates


def _write_json(path: Path, payload: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=indent, sort_keys=True) + "\n")


def _render_report(
    *,
    artifact: ExperimentArtifact,
    verdict: str,
    pre: dict[str, Any],
    outcome: HeldOutOutcome,
    not_recorded: list[str],
    frozen_hash: str,
) -> str:
    """Structured REPORT.md summary (no physical trial-level data exists for
    a D2 digital run, so report_compiler's trial tables do not apply)."""
    lines = [
        f"# {artifact.experiment_id} — {artifact.generation_id} closed-generation report",
        "",
        f"- Verdict: **{verdict}** (held-out benchmark run `{outcome.benchmark_run_id}`)",
        f"- Evidence label: `{artifact.evidence_label}`",
        f"- Created (UTC): {artifact.created_utc}",
        f"- Optimization telemetry frozen SHA-256: `{frozen_hash}`",
        "",
        "## Surrogate (pre-held-out) summary",
        "",
        f"- Surrogate mean detection rate: {pre['surrogate_mean_detection_rate']:.4f}",
        f"- Surrogate worst-case detection rate: {pre['surrogate_worst_case_detection_rate']:.4f}",
        f"- Transformation sweep variance: {pre['transformation_sweep_variance']:.6f}",
        f"- Pattern fidelity: {pre['pattern_fidelity']}",
        f"- Printability: {pre['printability']}",
        "",
        "| Surrogate model | Candidate detection rate |",
        "|---|---|",
    ]
    for name, rate in sorted(pre["per_surrogate_detection_rates"].items()):
        lines.append(f"| {name} | {rate:.4f} |")
    lines += [
        "",
        "## Held-out outcome (appended at closure)",
        "",
        "| Held-out model | Candidate detection rate |",
        "|---|---|",
    ]
    for name, rate in sorted(outcome.heldout_detection_rates.items()):
        lines.append(f"| {name} | {rate:.4f} |")
    lines.append("")
    if not_recorded:
        lines += [
            "## Recorded gaps (legacy D2-0004 mode)",
            "",
            "The following contract fields were not recorded by the D2-0004 "
            "pipeline and are sealed as null (never fabricated):",
            "",
        ]
        lines += [f"- `{name}`" for name in not_recorded]
        lines.append("")
    lines += [
        "## Stage lineage",
        "",
        "| Stage | Artifact | SHA-256 |",
        "|---|---|---|",
    ]
    for stage in artifact.stages:
        lines.append(f"| {stage.stage} | {stage.artifact_id} | `{stage.sha256}` |")
    lines.append("")
    return "\n".join(lines)


def run_ingest(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir) if args.run_dir else None

    def resolve(explicit: str | None, default_name: str, label: str) -> Path:
        if explicit:
            return _require_file(Path(explicit), label)
        if run_dir is None:
            raise IngestError(f"--run-dir or an explicit path is required for {label}")
        return _require_file(run_dir / default_name, label)

    surrogate_selection_path = resolve(args.surrogate_selection, "surrogate-selection.json", "surrogate-selection report")
    candidate_config_path = resolve(args.candidate_config, "candidate-config.json", "candidate config")
    candidate_png_path = resolve(args.candidate_png, "candidate.png", "candidate image")
    measured_path = resolve(args.measured_result, "benchmark-results.json", "measured benchmark result")
    generation_path = _require_file(Path(args.generation), "generation JSON")
    release_root = Path(args.release_root)
    release_dir = release_root / args.experiment_id

    created_utc = args.timestamp or _utcnow()

    # -- guardrails ---------------------------------------------------------
    generation = _load_json(generation_path, "generation JSON")
    generation_id = _check_generation_closed(generation, generation_path)
    if release_dir.exists():
        raise IngestError(f"release directory already exists, refusing to overwrite: {release_dir}")

    surrogate_selection = _load_json(surrogate_selection_path, "surrogate-selection report")
    candidate_config = _load_json(candidate_config_path, "candidate config")
    measured = _load_json(measured_path, "measured benchmark result")

    candidate_sha256 = hash_file(candidate_png_path)
    measured_candidate_hash = (measured.get("candidate") or {}).get("sha256")
    if measured_candidate_hash and measured_candidate_hash != candidate_sha256:
        raise IngestError(
            "candidate.png hash does not match the measured result's "
            f"candidate.sha256: {candidate_sha256} != {measured_candidate_hash}"
        )

    # -- telemetry ----------------------------------------------------------
    pre, not_recorded = build_pre_telemetry(
        candidate_sha256=candidate_sha256,
        generation_id=generation_id,
        recorded_utc=created_utc,
        surrogate_selection=surrogate_selection,
        measured=measured,
        legacy_d20004=bool(args.legacy_d20004),
    )
    outcome, heldout_rates = build_outcome(
        candidate_sha256=candidate_sha256,
        measured=measured,
        measured_path=measured_path,
        run_id=args.run_id,
        recorded_utc=created_utc,
        pass_threshold=float(args.pass_threshold),
    )
    frozen_hash = hashlib.sha256(_canonical(pre)).hexdigest()

    validity_flags: dict[str, Any] = {"verdict": outcome.verdict}
    if args.legacy_d20004:
        validity_flags["mode"] = "legacy-d20004"
        validity_flags["not_recorded_fields"] = not_recorded
        validity_flags["not_recorded_policy"] = (
            "mandatory telemetry-contract fields the D2-0004 pipeline did not "
            "record are sealed as null; values were never fabricated"
        )

    # -- experiment artifact + registry ------------------------------------
    certificate_path = Path(args.certificate) if args.certificate else None
    if certificate_path is not None:
        _require_file(certificate_path, "certificate")

    candidate_id = str(candidate_config.get("candidate_id") or generation_id)
    stages: list[StageRef] = [
        StageRef(
            stage="candidate",
            artifact_id=candidate_id,
            sha256=candidate_sha256,
            metadata={"files": ["stages/candidate/candidate.png", "stages/candidate/candidate-config.json"]},
        ),
        StageRef(
            stage="generation",
            artifact_id=generation_id,
            sha256=hash_file(generation_path),
            metadata={"files": [f"stages/generation/{generation_path.name}"]},
        ),
        StageRef(
            stage="optimization_telemetry",
            artifact_id=f"{generation_id}-telemetry",
            sha256=frozen_hash,
            metadata={"files": ["stages/optimization_telemetry/pre-held-out.json"]},
        ),
    ]
    if certificate_path is not None:
        stages.append(StageRef(
            stage="certificate",
            artifact_id=certificate_path.stem,
            sha256=hash_file(certificate_path),
            metadata={"files": [f"stages/certificate/{certificate_path.name}"]},
        ))

    artifact = ExperimentArtifact(
        experiment_id=args.experiment_id,
        hypothesis_id=args.hypothesis_id,
        generation_id=generation_id,
        created_utc=created_utc,
        stages=stages,
        evidence_label="internally_measured",
        validity_flags=validity_flags,
    )
    artifact.validate()

    registry_path = Path(args.registry)
    if registry_path.is_file():
        registry = ExperimentRegistry.from_json(registry_path.read_text())
    else:
        registry = ExperimentRegistry()
    try:
        registry.add(artifact)
    except ValueError as exc:
        raise IngestError(f"registry rejected the experiment: {exc}") from exc

    # -- release bundle ------------------------------------------------------
    release_dir.mkdir(parents=True)
    try:
        _write_json(release_dir / "experiment.json", artifact.to_dict())

        cand_dir = release_dir / "stages" / "candidate"
        cand_dir.mkdir(parents=True)
        shutil.copyfile(candidate_png_path, cand_dir / "candidate.png")
        shutil.copyfile(candidate_config_path, cand_dir / "candidate-config.json")

        gen_dir = release_dir / "stages" / "generation"
        gen_dir.mkdir(parents=True)
        shutil.copyfile(generation_path, gen_dir / generation_path.name)

        tele_dir = release_dir / "stages" / "optimization_telemetry"
        tele_dir.mkdir(parents=True)
        # pre-held-out.json is exactly the canonical frozen bytes, so its file
        # hash equals the telemetry frozen hash and the StageRef digest.
        (tele_dir / "pre-held-out.json").write_bytes(_canonical(pre))
        outcome_dir = tele_dir / "outcome"
        outcome_dir.mkdir()
        _write_json(outcome_dir / "held-out-outcome.json", asdict(outcome))
        _write_json(tele_dir / "telemetry.json", {"pre": pre, "outcome": asdict(outcome)})

        if certificate_path is not None:
            cert_dir = release_dir / "stages" / "certificate"
            cert_dir.mkdir(parents=True)
            shutil.copyfile(certificate_path, cert_dir / certificate_path.name)

        (release_dir / "REPORT.md").write_text(_render_report(
            artifact=artifact,
            verdict=outcome.verdict,
            pre=pre,
            outcome=outcome,
            not_recorded=not_recorded,
            frozen_hash=frozen_hash,
        ))

        failure_payload: dict[str, Any] | None = None
        if outcome.verdict == "FAIL":
            _, transformation_rates = _transformation_sweep(measured.get("rows") or [])
            winner = surrogate_selection.get("winner") or {}
            metrics: dict[str, Any] = {
                "baseline_detection_rate": winner.get("baseline_detection_rate"),
                "surrogate_detection_rate": pre["surrogate_mean_detection_rate"],
                "heldout_detection_rate": sum(heldout_rates.values()) / len(heldout_rates),
                "heldout_same_family": bool(args.heldout_same_family),
                "transformation_rates": transformation_rates or None,
            }
            coverage = pre.get("coverage_metrics")
            if isinstance(coverage, dict) and coverage.get("coverage_entropy") is not None:
                metrics["coverage_entropy"] = coverage["coverage_entropy"]
            record = classify_failure(
                metrics,
                experiment_id=args.experiment_id,
                generation_id=generation_id,
                record_id=f"FR-{args.experiment_id}",
                created_utc=created_utc,
            )
            classification = asdict(record)
            classification["category"] = record.category.value
            failure_payload = {
                "failure_stage": "generation",
                "failure_reason": record.explanation,
                "detected_utc": created_utc,
                "invalidates": list(FAIL_INVALIDATES),
                "classification": classification,
            }
            _write_json(release_dir / "FAILURE.json", failure_payload)

        # Seal in the documented order (RESEARCH_RELEASE_FORMAT.md §3):
        # 1) manifest over content files, 2) content_hash, 3) RELEASE.json,
        # 4) rebuild manifest, 5) REVISIONS.json freeze + final manifest.
        manifest = ReleaseManifest.build(release_dir)
        content_hash = compute_content_hash(manifest)
        _write_json(release_dir / "RELEASE.json", {
            "release_id": args.experiment_id,
            "created_utc": created_utc,
            "source_commit": args.source_commit,
            "content_hash": content_hash,
        })
        ReleaseManifest.build(release_dir).write(release_dir)
        log = ReleaseRevisionLog(release_id=args.experiment_id)
        for stage in artifact.stages:
            log = log.record(stage.stage, created_utc, detail=f"ingest {stage.artifact_id}")
        log = log.freeze(created_utc, stage="generation", detail=f"closed with verdict {outcome.verdict}")
        (release_dir / "REVISIONS.json").write_text(log.to_json())
        final_manifest = ReleaseManifest.build(release_dir)
        final_manifest.write(release_dir)

        verification = verify_release(release_dir)
        if not verification.ok:
            raise IngestError(
                "freshly sealed release failed verification: "
                f"tampered={verification.tampered} missing={verification.missing} "
                f"extra={verification.extra}"
            )
    except Exception:
        shutil.rmtree(release_dir, ignore_errors=True)
        raise

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(registry.to_json() + "\n")

    summary = {
        "experiment_id": args.experiment_id,
        "generation_id": generation_id,
        "verdict": outcome.verdict,
        "release_dir": str(release_dir),
        "registry": str(registry_path),
        "content_hash": content_hash,
        "final_manifest_content_hash": compute_content_hash(final_manifest),
        "lineage_hash": artifact.lineage_hash,
        "telemetry_frozen_sha256": frozen_hash,
        "candidate_sha256": candidate_sha256,
        "generation_sha256": hash_file(generation_path),
        "verify_release_ok": verification.ok,
        "legacy_d20004": bool(args.legacy_d20004),
        "not_recorded_fields": not_recorded,
    }
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest a CLOSED measured-benchmark generation into a sealed RAC-EXP release."
    )
    parser.add_argument("--run-dir", help="benchmark runtime dir holding the default artifact names")
    parser.add_argument("--surrogate-selection", help="path to surrogate-selection.json")
    parser.add_argument("--candidate-config", help="path to candidate-config.json")
    parser.add_argument("--candidate-png", help="path to candidate.png")
    parser.add_argument("--measured-result", help="path to the measured benchmark result JSON")
    parser.add_argument("--generation", required=True, help="path to the generation JSON (must be CLOSED)")
    parser.add_argument("--experiment-id", required=True, help="RAC-EXP-YYYY-NNN")
    parser.add_argument("--hypothesis-id", required=True, help="hypothesis id for the experiment artifact")
    parser.add_argument("--run-id", required=True, help="benchmark run identity (e.g. CI run id)")
    parser.add_argument("--registry", required=True, help="ExperimentRegistry JSON (created or appended)")
    parser.add_argument("--release-root", required=True, help="parent dir; release dir is <root>/<experiment-id>")
    parser.add_argument("--certificate", help="optional certificate artifact to attach")
    parser.add_argument("--source-commit", default=os.getenv("GITHUB_SHA", "local"))
    parser.add_argument("--pass-threshold", type=float, default=0.5,
                        help="max mean held-out candidate detection rate for a PASS verdict")
    parser.add_argument("--heldout-same-family", action="store_true",
                        help="held-out detectors share the surrogate architecture family")
    parser.add_argument("--legacy-d20004", action="store_true",
                        help="record fields the D2-0004 pipeline did not capture as null "
                             "with a validity flag, instead of refusing")
    parser.add_argument("--timestamp", help="override UTC timestamp (YYYY-MM-DDTHH:MM:SSZ); testing only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_ingest(args)
    except IngestError as exc:
        print(f"ingest refused: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ingest failed validation: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

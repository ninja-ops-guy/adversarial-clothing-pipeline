# ingest_closed_generation.py — D2-0004 field-mapping notes

Converts a CLOSED measured-benchmark generation (e.g. RAC-PER-D2-0004) into the
first canonical RAC-EXP release. Stdlib + `ruthless_pipeline.certification` only.
Run only after the benchmark closes; never against an open generation JSON.

> **Dated note (2026-09-08):** D2-0004 closed FAIL / RAC-D0 (log-attested; `docs/D2-0004_CLOSURE_NOTE.md`). The actual minted release is `releases/RAC-EXP-2026-001/`; the `RAC-EXP-2025-001` id in the CLI example below is illustrative only.

## CLI (typical)

```
python scripts/ingest_closed_generation.py \
  --run-dir benchmarks/runtime \
  --measured-result benchmark-results.json \
  --generation generations/RAC-PER-D2-0004.json \
  --experiment-id RAC-EXP-2025-001 --hypothesis-id HYP-D2-0004-01 \
  --run-id <ci-run-id> --registry registry/experiments.json \
  --release-root releases --legacy-d20004
```

`--run-dir` supplies the default names (surrogate-selection.json,
candidate-config.json, candidate.png); each can be overridden explicitly.

## Field-mapping table (benchmark artifact -> telemetry/release field)

| Source artifact.field | Target field | Mode |
|---|---|---|
| candidate.png (sha256, cross-checked vs benchmark-results `candidate.sha256`) | `pre.candidate_sha256`; StageRef(candidate).sha256 | both |
| generation JSON `generation_id`, file sha256 | `pre.generation_id`; StageRef(generation) | both |
| surrogate-selection `winner.candidate_detection_rate` | `pre.surrogate_mean_detection_rate` (legacy) | legacy |
| surrogate-selection `winner.reference_fidelity_score` | `pre.pattern_fidelity` | legacy |
| surrogate-selection `winner.printability_proxy` | `pre.printability` | legacy |
| surrogate-selection `optimization_telemetry.*` (D2-0005+ block) | all strict `pre.*` fields incl. spectral bands, objective trajectory, coverage, optimizer config | strict |
| benchmark-results `models[role=surrogate].candidate_detection_rate` | `pre.per_surrogate_detection_rates` (+ worst-case, disagreement via `cross_model_disagreement`) | legacy |
| benchmark-results `rows` (baseline-qualified surrogate rows) | `pre.transformation_sweep_variance` (population variance of per-condition rates); FAILURE metrics `transformation_rates` | legacy |
| benchmark-results `models[role=heldout].candidate_detection_rate` | `outcome.heldout_detection_rates` | both |
| benchmark-results `status`/`certification_eligible` + `--pass-threshold` (default 0.5) | `outcome.verdict` (PASS iff measured_locked and held-out mean <= threshold) | both |
| `--run-id`, `--timestamp` | `outcome.benchmark_run_id`, `recorded_utc` | both |
| **not recorded by D2-0004**: spectral_band_energy, objective_trajectory, coverage_metrics, optimizer_config | sealed as JSON null; listed in `experiment.json validity_flags.not_recorded_fields` | **requires `--legacy-d20004`** |

## Notes

- Guardrails: refuses when `lock_inference_performed` is false or the
  generation status lacks "CLOSED"; refuses to overwrite an existing release
  dir; fails loudly (exit 2) on any missing input or candidate-hash mismatch.
- `stages/optimization_telemetry/pre-held-out.json` is exactly the canonical
  frozen bytes, so its file hash == the telemetry `frozen_sha256()` == the
  StageRef sha256 == the MANIFEST entry (satisfies both contracts).
- Seal order follows RESEARCH_RELEASE_FORMAT.md §3: manifest -> content_hash ->
  RELEASE.json -> manifest -> REVISIONS.json (freeze) -> final manifest;
  then `verify_release` must pass and the content_hash is printed.
- REPORT.md is a structured summary (D2 runs have no physical trial-level data,
  so `report_compiler` tables do not apply).
- FAILURE.json (verdict FAIL only) carries `failure_stage=generation`,
  `invalidates=[calibration_profile, sku, physical_session, certificate]`, and
  a `failure_taxonomy.classify_failure` classification built from the telemetry
  metrics (`--heldout-same-family` selects overfit vs transfer-failure).

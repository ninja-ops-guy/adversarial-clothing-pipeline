# Barrier 3 Integration Survey

**Document ID:** BARRIER3-INTEGRATION-SURVEY-001
**Date:** 2026-09-10
**Wave:** RAC Parallel Swarm R1, Lane A

## Classification

**CAN_COMPOSE_EXISTING_ENGINE = YES**

All six stages already expose deterministic, contract-validated entrypoints
with frozen Barrier 1 schemas. No new orchestration framework was built; Lane
A adds only a thin coordinator
(`ruthless_pipeline/integration/barrier3.py`, coordinator version 1.0.0) that
wires the existing stages together and pins provenance and hashes. No stage
math was reimplemented.

## Stage survey

| Stage | Existing entrypoint | Input contract | Output contract | Seed handling | Hash handling | Provenance handling | Failure behavior | Missing adapter |
|---|---|---|---|---|---|---|---|---|
| Optimization V3 | `optimization/optimizer.py::CandidatePoolSearchOptimizer` + `optimization/objective_registry.py::Objective` | validated `ObjectiveSpec` (frozen `schemas/optimization_objective.schema.json`), finite candidate pool | `OptimizerResult` + per-term `ObjectiveEvaluation`; trajectory via `TrajectoryRecorder` | `seed` field in frozen objective contract; recorder is timestamp-free | params hashed per trajectory step (`hash_params`); checkpoints sha256-pinned | trajectory checkpoint manifest | `NaNRefusalError` on any non-finite term/total; duplicate/empty pool refused | none |
| EOT | `transformations/distribution.py::TransformationDistributionSpec` + `Sampler` | frozen `schemas/transformation_distribution.schema.json` (4 dimension groups) | per-sample parameter dicts | per-sample sub-seed = sha256(distribution_id \| canonical manifest \| seed \| index) | `manifest_sha256` property over canonical JSON | reproducibility note embedded in spec | `validate_spec_dict` fails closed on unknown distribution types / missing groups | none |
| Detector Science | `detector_science/adapters.py::SyntheticDetectionAdapter` | detection dicts + model/family/condition ids | `DetectorResponse` (frozen `schemas/detector_response.schema.json`) | no internal entropy; response is a pure function of inputs | response record hashable via canonical JSON | `raw_provenance_ref` field | `FabricationGuardError` when an adapter emits a capability it does not expose; `UnknownFamilyError` for unregistered families | none for the synthetic proof; real detectors bind via `AdapterRegistry` |
| Pareto / Style | `optimization/pareto.py::classify` + `optimization/style.py::StyleFamilyScorer` | candidate rows with four metric keys | `ClassifiedCandidate` per candidate, rule-documented classes | none (pure function of inputs) | metrics table hashed by coordinator | metrics lineage recorded in stage-4 artifact | missing metrics treated as worst-case (documented); unknown style family refused | none |
| Printability | `physical_transfer/printability.py::printability_loss` | candidate array + production profile | `PrintabilityLoss` (value + per-component results, `partial` flag) | none (pure function) | profile carries sha256 (`production_profiles.py`) | profile provenance fields required (`profile_id`, `version`, `source`) | `PrintabilityInputError` on invalid candidate; unavailable components degrade to `partial`, never fabricated | none |
| Physical Transfer | `physical_transfer/transfer_record.py::emit` | artifact bytes + capture metadata | validated record (frozen `schemas/physical_transfer_record.schema.json`) | none; coordinator passes deterministic `record_id` | sha256 of every artifact embedded in record | `detector_response_refs`, `measured_evidence_ref` | fail-closed: `synthetic_generator=True` forces `synthetic_pipeline_validation_only`; measured class requires `measured_evidence_ref`; `physical_efficacy_claimed` const false | none |

## Coordinator guarantees

- single-process, seed-controlled: all entropy derives from
  `Barrier3Config.master_seed` via sha256 sub-seed chaining;
- hash-pinned: every stage artifact carries input/output sha256 and is bound
  in `run-manifest.json` + `hashes.sha256`;
- replayable: `verify_replay` compares two runs across inputs, config, seeds,
  stage outputs, telemetry, provenance, artifact hashes; only
  `runtime-environment.json` is excluded from scientific equivalence;
- synthetic/non-held-out integration proof only: no held-out inference, no
  D2-0005 arming, `physical_efficacy_claimed=false` enforced by contract;
- no silent stage skipping: `verify_provenance` fails on any missing stage
  artifact or broken lineage edge.

## Run

```
PYTHONPATH=. python3 scripts/run_barrier3_integration.py --output-dir artifacts/barrier3
```

Runs the engine twice, compares, writes the full artifact package
(`artifacts/barrier3/`), and exits nonzero unless every gate passes.
Independent audit tooling: `tools/rac_g_barrier3_audit_prep.py` (final RAC-G
verdict deferred until this wave's completion handoff is byte-confirmed).

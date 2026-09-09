# Barrier 3 Integrated Rehearsal Report

**Status:** implementation ready for independent close; final Barrier 3 PASS/FAIL is reserved for the single-agent closer.

## Scope

Barrier 3 composes the existing six-stage synthetic engine path without changing stage internals:

1. Optimization V3
2. EOT / Transformation Distribution
3. Detector Science
4. Pareto / Style
5. Printability
6. Physical Transfer

The coordinator is `ruthless_pipeline/certification/rehearsal_barrier3.py` with CLI `scripts/rehearsal_barrier3.py`.

## Governance boundary

This rehearsal is an integration proof only.

- `CAN_COMPOSE_EXISTING_ENGINE = YES`
- `STAGE_COUNT = 6`
- `SINGLE_PROCESS = true`
- `SEED_CONTROLLED = true`
- `HASH_PINNED = true`
- `HELDOUT_ACCESSED = false`
- `D2_0005_ARMED = false`
- `PHYSICAL_EFFICACY_CLAIMED = false`
- evidence class is always `synthetic_pipeline_validation_only`

The held-out set `PERSON-HO-v3` is represented only by its frozen identity and SHA-256. The coordinator has no held-out evaluator path and never loads or scores the held-out model set.

## Frozen D2-0005 bindings

The run-manifest schema binds the already-reviewed D2-0005 design values without changing them:

- candidate pool seed: 1337
- bootstrap seed: 20260907
- design simulation seed: 20261209
- CVaR alpha: 0.5
- z: 1.959963984540054
- bootstrap resamples: 10000
- width gate: 0.2
- minimum clusters supported by analysis module: 8
- design K: 72
- members per cluster: 36
- ICC gate: 0.25
- confirmatory floor delta: 0.2

## Integration design

Every stage is a thin adapter over an existing public API.

The coordinator:
- validates the Barrier 3 run manifest;
- verifies the frozen-surface manifest hash and committed input hashes;
- derives stage seeds deterministically from run id, root seed, stage id and stable config;
- executes the six stages in fixed order;
- writes canonical JSON artifacts;
- journals stage completion with SHA-256;
- verifies hashes before resume;
- supports deliberate `--crash-after <stage>` failure injection;
- refuses non-finite stage-boundary values;
- creates provenance and objective-telemetry records;
- content-addresses the completed run with the existing ReleaseManifest verifier;
- refuses promotion to measured/physical evidence.

## Replay and failure-injection coverage

`tests/test_barrier3_rehearsal.py` covers:
- full six-stage completion;
- byte-equivalent deterministic replay;
- deliberate crash after every stage followed by verified resume;
- tampered intermediate refusal;
- wrong frozen-surface hash refusal;
- wrong committed-input hash refusal;
- non-synthetic evidence-class refusal;
- held-out access-mode refusal;
- NaN stage-boundary refusal;
- synthetic-to-measured promotion refusal;
- physical-transfer evidence-class guard;
- schema exclusion of held-out outcome fields.

## Required closer checks

The implementation lane does not self-certify Barrier 3. A separate closer must independently execute the rehearsal twice, verify deterministic artifacts, inspect provenance, record exact test counts, and re-read the scientific boundary files from the final HEAD.

Required final closer fields:

- `REPLAYABLE = true/false`
- `PROVENANCE_VERIFIED = true/false`
- `BARRIER_3_RESULT = PASS/FAIL`

## Lane A handoff

`LANE_A_IMPLEMENTATION_COMPLETE = true`

`READY_FOR_SINGLE_AGENT_CLOSER = true`

Boundary assertions at implementation handoff:

- `D2_0004_MODIFIED=false`
- `D2_0005_ARMED=false`
- `NEW_HELDOUT_ACCESS=false`
- `SCIENTIFIC_THRESHOLDS_CHANGED=false`
- `PHYSICAL_EFFICACY_CLAIMED=false`
- `FORCE_PUSH_USED=false`
- `UNVERIFIED_PLACEHOLDER_CONTENT=false`

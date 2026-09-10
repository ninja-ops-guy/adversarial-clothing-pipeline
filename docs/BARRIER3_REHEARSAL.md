# Barrier 3 Rehearsal — Design, Manifest, Gate, Determinism

Companion to `docs/BARRIER_3_REHEARSAL_REPORT.md`. This document describes the
runnable rehearsal: the run manifest, the six-stage composition, the
executable acceptance gate, and the determinism proof.

**Governance flags (constant for every run):**

- `physical_test_executed = false`
- `physical_efficacy_claimed = false`
- `D2-0005 not armed, not executed` — the generation record
  `generations/RAC-PER-D2-0005.json` must remain `PREREGISTERED`; the gate
  hard-fails otherwise.
- D2-0004 records are pinned by hash and never modified.
- The held-out set `PERSON-HO-v3` is referenced by identity/SHA-256 only and
  is never opened, loaded, or scored.
- Every emitted artifact is `synthetic_pipeline_validation_only`,
  `rac_evidence_eligible = false`.

## 1. Run manifest

`schemas/barrier3_run_manifest.schema.json` (schema_id
`barrier3-run-manifest`, schema_version `1.0`) binds, per run:

| Field group | Content |
|---|---|
| identity | `run_id`, `schema_version`, `schema_id`, `created_utc` (pinned default), `source_commit` |
| governance | `evidence_class`, `rac_evidence_eligible`, `physical_efficacy_claimed`, `generation_ref`, `arm_ref` (synthetic rehearsal arms mirroring the D2-0005 preregistered arm *structure* — referenced, never executed) |
| seeding | `root_seed`; per-stage seeds derived as `sha256(run_id \| root_seed \| stage_id \| stage_config)` |
| frozen bindings | `frozen_parameters` — REFERENCED from `docs/D2-0005_FREEZE_CANDIDATE.json` and `ruthless_pipeline/certification/config/d20005_freeze/seeds.json`; never restated as new literals, moved, or changed |
| stage configs | `stage_configs` for optimization, eot, detector_science, pareto_style, printability (pinned versioned production profile `ruthless_pipeline/certification/config/barrier3/barrier3-production__v1.json` (deliberately outside the frozen `design_profiles/` surface)), physical_transfer |
| model identity | `model_identity_refs` — surrogate/held-out set ids + SHA-256, `heldout_access = identity_hash_only` |
| input pins | `input_hashes` (freeze candidate, freeze seeds, runtime lock `benchmarks/runtime_lock.json`, design profile, production profile, D2-0004/D2-0005 generation records), `frozen_surface_manifest_sha256` |
| ordering | `expected_stage_order` — frozen six-stage order |

The schema carries no outcome fields (`heldout_results`, `heldout_scores`,
`measured_evidence`, `physical_efficacy` are rejected by the coordinator even
if smuggled past JSON Schema).

## 2. Composition

`ruthless_pipeline/certification/rehearsal_barrier3.py` (CLI:
`scripts/rehearsal_barrier3.py`) composes the six existing stage libraries
single-process; adapters only — no stage internals are rewritten:

1. **optimization** — seeded candidate-pool search over a schema-validated
   synthetic objective (`NaNRefusalError` path preserved; non-finite output
   hard-fails at the stage boundary).
2. **eot** — `TransformationDistributionSpec` + `Sampler` with hash-derived
   sub-seeds; robustness grid only (`scalar_only_permitted = false`).
3. **detector_science** — hash-seeded MOCK adapter
   (`MOCK-DETECTOR-SYNTHETIC-NOT-A-MODEL`) bridging EOT output to a
   schema-validated `DetectorResponse`. It is not a model and produces no
   capability claims.
4. **pareto_style** — deterministic Pareto front + documented style proxy
   (`art_direction_proxy_only_not_efficacy`), `certification = None`.
5. **printability** — `printability_loss` against the pinned profile;
   unavailable vendor measurements stay `MEASUREMENT_UNAVAILABLE` with
   renormalized weights (`partial = true`), never silently defaulted.
6. **physical_transfer** — `transfer_record.emit` over artifact bytes with a
   pinned record id (no uuid in hashed artifacts); synthetic frames force
   `evidence_class = synthetic_pipeline_validation_only`. The
   nondeterministic tier-benchmark wall-clock path is not part of this
   rehearsal.

Journal/resume semantics reuse the rehearsal_d20005.py pattern: append-only
journal, atomic per-stage artifacts under `stages/`, hash-verified resume,
fail-closed on changed intermediate bytes, `--crash-after` fault injection.

## 3. Output package

`artifacts`-style package under the chosen output dir:
`run-manifest.json`, `input-hashes.json`, `environment-lock.json`,
`stages/<stage>.json` (six), `objective-telemetry.json`, `provenance.json`
(repository provenance vocabulary: `frozen_config` / `inference_record` /
`model_manifest` nodes; `records` / `derived_from` / `pins_hash` edges with
`expected_sha256` pins, re-verified by `provenance_graph.verify_graph`),
`rehearsal-report.json` (+ `barrier3-report.json` copy), `hashes.sha256`,
`rehearsal_journal.json`.

## 4. Acceptance gate

`run_acceptance_gate(output_dir)` hard-fails (`AcceptanceGateError`) unless
all of these hold; latest run: **14/14 PASS**.

1. run manifest valid (schema + governance guards)
2. all six stages executed, none silently skipped
3. stage artifacts hash-verified against the journal
4. each stage consumes its expected upstream artifact (journaled hash pins
   injected into every stage payload)
5. synthetic-only labels on every stage artifact
6. input hashes re-verified against the repository
7. model locks verified (surrogate/held-out identity pins; D2-0004/D2-0005
   generation records unchanged)
8. seed + config recorded
9. objective telemetry finite (no NaN/Inf anywhere in telemetry or stages)
10. provenance graph complete and re-verifies (zero unexpected edges)
11. `hashes.sha256` verifies (no missing, mismatching, or unlisted files)
12. no held-out access (manifest mode + artifact scan)
13. D2-0004 untouched and D2-0005 still `PREREGISTERED`/unarmed
14. no physical efficacy claim (transfer record inspected)

## 5. Determinism

Two independent runs of `scripts/rehearsal_barrier3.py` with the same
manifest produce byte-identical packages (`compare_replays` → `identical:
true`). The package determinism digest is
`_determinism_digest`: SHA-256 over sorted `path=sha256` lines for every
artifact; no wall-clock metadata exists in the package (`created_utc` is
pinned), so nothing is excluded.

Delivery-run digest (run id `BARRIER3-D20005-SYNTHETIC-001`, root seed from
the CLI default, recorded at the delivery commit): see `rehearsal-report.json`
and the Barrier 3 delivery note; reproduce locally with:

```
python3 scripts/rehearsal_barrier3.py --output-dir /tmp/b3a
python3 scripts/rehearsal_barrier3.py --output-dir /tmp/b3b
# compare_replays("/tmp/b3a", "/tmp/b3b")["identical"] is True
```

## 6. Boundaries honored

No D2-0004 modification; no D2-0005 arming/execution; no held-out access; no
threshold changes; no synthetic→measured promotion (`promote_to_measured`
always raises `PromotionRefusedError`); stage implementations untouched.

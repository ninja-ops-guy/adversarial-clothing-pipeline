# RAC-R3 Readiness Audit — Existing Experiments and Releases

<!-- provenance: MANUAL source=auditor inspection of in-repo evidence derived=manual
     This audit is an INPUT to Swarm B's RAC-R3 consolidated-manifest module
     (contract: schemas/rac_r3_manifest.schema.json). It implements none of
     that module. Classifications are PASS / PARTIAL / MISSING /
     NOT_APPLICABLE per field, with evidence paths. Detection-only: nothing
     here re-runs, re-derives, or mutates D2-0004/D2-0005 scientific state. -->

Audit HEAD at writing: `b215412` (2026-09; post Barrier-2, incl.
`ruthless_pipeline/transformations/` — which supplies the distribution
framework going forward but does not retroactively manifest D2-0003/0004). The 12
charter fields are those of `schemas/rac_r3_manifest.schema.json`:
source_commit, dependency_lock, model_hashes, fixture_hashes, seed_manifest,
optimizer_config_ref, transformation_manifest_ref, candidate_sha256,
analysis_sha256, environment_manifest, journal_ref, release_manifest_ref.

Legend — **PASS**: attested in-repo with hash pin; **PARTIAL**: present but
with documented attestation gaps; **MISSING**: no attested artifact;
**NOT_APPLICABLE**: field has no meaning for this experiment class.

## 1. RAC-PER-D2-0003 (closed, FAIL / RAC-D0, archived-in-repo evidence)

| R3 field | Class | Evidence |
|---|---|---|
| source_commit | PASS | `65646777151966729ab6c06cdbdfe71671e5266d` in `manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json` and `benchmark-results.json: source_commit` |
| dependency_lock | PARTIAL | `benchmarks/runtime_lock.json` (python 3.11, torch 2.14.0+cpu, torchvision, transformers, ultralytics pins); `benchmarks/requirements.txt`. No single consolidated lock hash pinned into the release record. |
| model_hashes | PASS | `benchmarks/model_manifest_v1.locked.json`, `benchmarks/model_manifest.json`; per-model manifests in `model_manifests/`; sets `model_sets/PERSON-SUR-v2.json`, `model_sets/PERSON-HO-v2.json` (hashes pinned in provenance graph) |
| fixture_hashes | PARTIAL | fixture described in `benchmark-results.json: fixture` ("ultralytics-zidane-two-crop-convenience-fixture", digital CI convenience fixture); no standalone fixture-manifest file with per-image hashes |
| seed_manifest | PARTIAL | optimizer seed attested (`benchmark-results.json: candidate.config.seed = 271`); no named multi-seed manifest |
| optimizer_config_ref | PARTIAL | `benchmark-results.json: candidate.config` carries the config inline; no separate hash-pinned optimizer-config artifact |
| transformation_manifest_ref | MISSING | D2-0003 predates any transformation-distribution manifest; fixed augment grid only (`ruthless_pipeline/benchmark.py`) |
| candidate_sha256 | PASS | `8f4f79a3…51e8` (`benchmark-results.json: candidate.sha256`, dashboard `key_hashes.candidate_sha256`) |
| analysis_sha256 | PARTIAL | analysis outputs attested via `benchmark-results.json` sha256 `d21b2ef6…f112` (citation matrix + provenance graph); analysis *code* is module-hashless (no code pin) |
| environment_manifest | PARTIAL | runner block in `benchmark-results.json: runner` (device/platform/python/torch); no standalone environment manifest |
| journal_ref | MISSING | no append-only experiment journal existed for D2-0003 (journaling arrived later with `experiment_state_machine.py`) |
| release_manifest_ref | PARTIAL | archived status file `manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json` (sha256 `f55732d6…b5d1`); the sealed `releases/RAC-EXP-2026-001/MANIFEST.json` bundles D2-0004 evidence, not D2-0003 |

## 2. RAC-PER-D2-0004 (closed, FAIL / RAC-D0, log-attested; no rerun authorized)

| R3 field | Class | Evidence |
|---|---|---|
| source_commit | PASS | `b4fe0e5942b56b7fffb8de6f1cb3172744269f59` in `d2-latest-status.json: source_commit` and `releases/RAC-EXP-2026-001/` evidence |
| dependency_lock | PARTIAL | `benchmarks/runtime_lock.json` (sha256 `3c7ca469…1186` per dashboard); D2-0004 run environment itself is log-attested only |
| model_hashes | PASS | `model_sets/PERSON-SUR-v3.json` (sha256 `2f06c19e…5876`), `model_sets/PERSON-HO-v3.json` (sha256 `ad112765…5e7c`) — both pinned in `registry/experiments.json` validity_flags and the provenance graph |
| fixture_hashes | PARTIAL | same convenience-fixture lineage as D2-0003; per-image fixture hashes not separately manifested |
| seed_manifest | PARTIAL | seeds log-attested in `manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json` (sha256 `8c5cf861…3ba3`); no named seed manifest |
| optimizer_config_ref | PARTIAL | surrogate-phase optimizer telemetry/config is a documented unattested gap (`registry/experiments.json: validity_flags.not_recorded_fields`) |
| transformation_manifest_ref | MISSING | as D2-0003 — fixed augment grid, no distribution manifest |
| candidate_sha256 | PASS | `9c8ae08d…3803`, attested identically in step-18/20 logs (`log-attested-evidence.json`); candidate.png bytes never archived (MISSING-by-design gap, disclosed) |
| analysis_sha256 | PARTIAL | decision fields attested in `d2-latest-status.json` (sha256 `d761fd94…4b9`); per-model held-out rates unattested (aggregate only) — disclosed gap |
| environment_manifest | PARTIAL | log-attested run environment only; no standalone manifest |
| journal_ref | PARTIAL | stage records in `releases/RAC-EXP-2026-001/experiment.json` + `registry/experiments.json`; not the later append-only journal format |
| release_manifest_ref | PASS | `releases/RAC-EXP-2026-001/MANIFEST.json` (sealed per-file sha256 entries, verified by `tests/test_release_format.py` / `verify_release`) |

## 3. Production Alpha / P1 (planned; no physical sample received)

| R3 field | Class | Evidence |
|---|---|---|
| source_commit | NOT_APPLICABLE | no run yet; SKU intent in `production_alpha/SKU_MANIFEST.json` (sha256 `8f6d7614…4f8d`) |
| dependency_lock | PARTIAL | `benchmarks/runtime_lock.json` governs the digital side; physical pipeline has no dependency dimension yet |
| model_hashes | NOT_APPLICABLE | no model evaluation in the P1 physical capture protocol itself |
| fixture_hashes | MISSING | fixture image manifest explicitly missing (dashboard `user_actions_required`: "Fixture image manifest missing."); templates `physical/p1/SESSION_MANIFEST_TEMPLATE.json`, `physical/p1/PHYSICAL_TRIAL_INGESTION_TEMPLATE.json` unfilled |
| seed_manifest | NOT_APPLICABLE | no stochastic optimization scheduled for P1 capture |
| optimizer_config_ref | NOT_APPLICABLE | as above |
| transformation_manifest_ref | NOT_APPLICABLE | as above |
| candidate_sha256 | PARTIAL | expected artwork/pattern hashes declared in `production_alpha/SKU_MANIFEST.json` (`expected_pattern_sha256`, `print_test_kit_sha256`); per-placement artwork hashes pending real vendor template download (UA-1) |
| analysis_sha256 | NOT_APPLICABLE | no analysis run; stopping rule frozen at `physical/p1/STOPPING_RULE.json` |
| environment_manifest | PARTIAL | capture rig environment specified (`physical/p1/CAMERA_LIGHTING_SETUP.md`, `physical/p1/RIG_MEASUREMENT_CHECKLIST.md`, `physical/p1/CALIBRATION_MANIFEST.json`); no measured session environment yet |
| journal_ref | MISSING | no capture session journal (no session has run) |
| release_manifest_ref | MISSING | no release; `production_alpha/` is pre-order workspace |

## 4. Gap summary (input to Swarm B's RAC-R3 module)

1. **No experiment currently satisfies all 12 R3 fields.** D2-0003 and
   D2-0004 are strong on source_commit / model_hashes / candidate_sha256
   but both predate journal and transformation-manifest machinery.
2. **Cross-cutting MISSING**: `transformation_manifest_ref` for the closed
   digital experiments (they predate the framework; the Barrier-2
   `ruthless_pipeline/transformations/` namespace now exists for future
   experiments but no historical release references a distribution
   manifest).
3. **Cross-cutting PARTIAL**: `dependency_lock`, `seed_manifest`,
   `environment_manifest`, `analysis_sha256` — data exists scattered across
   `benchmark-results.json` / runtime lock / log-attested evidence but is
   not consolidated into single hash-pinned manifests.
4. **D2-0004-specific**: known unattested gaps (candidate bytes, per-model
   held-out rates, surrogate-phase telemetry) are MISSING-by-design and
   disclosed in `registry/experiments.json: validity_flags.not_recorded_fields`;
   an R3 manifest must carry these as disclosed gaps, not silently PASS.
   No D2-0004 rerun is authorized to fill them.
5. **Production Alpha/P1** cannot produce an R3 manifest until the fixture
   image manifest is frozen and a capture session runs (user actions UA-1
   and checklist items 3/7 outstanding).

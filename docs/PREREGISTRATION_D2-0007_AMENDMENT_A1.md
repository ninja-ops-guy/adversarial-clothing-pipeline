# PREREGISTRATION AMENDMENT A1 — D2-0007 Stage-1 Execution Serialization

**Status:** PRE-EXECUTION FROZEN CLARIFICATION — **NO STAGE-1 SCREENING HAD RUN** when this amendment was committed.

**Generation:** `RAC-PER-D2-0007`  
**Parent preregistration:** `docs/PREREGISTRATION_D2-0007.md` (left byte-for-byte unchanged)  
**Machine-readable execution freeze:** `configs/d2007_stage1_screening_v1.json` (introduced at commit `71cb0f6101d0939fcd88460696d1d016ad5a8016`)  
**Stage-0 prerequisite:** PASS receipt `evidence/d2-0007/stage0-landmark-free-smoke-closure.json`

## Why A1 exists

The frozen preregistration correctly fixed the Stage-1 generator set, 8 compositions per generator, the three root seeds `[20270110, 20270111, 20270112]`, the 64-composition upper bound, the survivor rule, the four-candidate optimization cap, and the prohibition on optional stopping. It also says the root seed is composed deterministically with generator index and that the full schedule is recorded in the freeze manifest.

Before any Stage-1 scoring was performed, the implementation audit found that the repository had not serialized the final generator-index/composition-index seed expansion or the generator-local geometry needed by PATTERNS generators that syntactically require landmarks/bboxes. Guessing those details after seeing screening outcomes would weaken the prospective design. A1 closes that implementation gap **before outcome access** without editing the frozen parent preregistration.

Stage 0 does not count as Stage-1 outcome access: it used one `FeatureCollageGenerator` wiring candidate solely to prove fixture → PATTERNS → PERSON-SUR-v3 → telemetry plumbing, produced no motif-family comparison, opened no screening/optimization state, and touched no held-out model.

## Frozen clarifications

1. **Seed expansion.** Composition `i` uses frozen root seed `root_seeds[i mod 3]`. The final integer seed is the first eight bytes of SHA-256 over
   `RAC-PER-D2-0007|stage1|generator_index={g}|composition_index={i}|root_seed={root}`,
   interpreted unsigned big-endian and masked to 63 bits. All 64 derived integers are serialized in `configs/d2007_stage1_screening_v1.json`. The schedule cannot be changed after Stage-1 observation.

2. **Generator-local geometry is not a body/garment anchor.** PATTERNS generators that require landmark/bbox-shaped inputs use the fixed `PATTERNS_CANONICAL_128_V1` 128×128 local motif-construction geometry serialized in the config. These coordinates exist only inside the motif generator canvas. They are not person keypoints, garment anchors, a pose provider, or Stage-2 anchor support. No `torso_region`, `shoulder_axis`, `silhouette_mask`, `panel_region`, or other body/garment provider is built during Stage 1.

3. **Screening surface.** Stage 1 uses the existing `ultralytics-zidane-two-crop-convenience-fixture` and the committed `benchmarks/model_manifest.json#transform_sweep`: brightness `{0.7,1.0,1.3}` × blur `{0,0.8}` × rotation `{-20,0,20}` at scale `1.0`. It uses matched control/candidate conditions and the existing `ComparativeBenchmark` `baseline_qualified` control-undetected exclusion semantics.

4. **Model exposure.** Exactly `PERSON-SUR-v3` is permitted. `PERSON-HO-v3` remains reference-by-hash only and must not be instantiated, queried, enumerated for inference, or used for ranking during Stage 1.

5. **Decision rule.** A generator family survives only when its best of eight fixed compositions has mean absolute per-surrogate detection-rate reduction ≥ `0.15`, has strictly positive improvement on at least `4/6` surrogates, and has `invalid_condition_fraction <= 0.10`. Best-composition ranking and survivor tie-breaks are serialized before execution in the machine-readable config. At most four motif families can be admitted downstream.

6. **No premature engineering.** Body/garment anchor support, optimization/EOT, candidate freeze, held-out evaluation, and `RAC-PRINT-ALPHA-002` remain closed during Stage 1. Anchor support may be implemented only for motif families that survive this frozen screening rule.

## Regression boundaries

A1 does **not** modify `RAC-PER-D2-0005`, inject any D2-0007 candidate into its pool, alter any existing frozen scientific artifact, access held-out data, or rebind `RAC-PRINT-ALPHA-001`. Any such change is a critical regression. `RAC-PRINT-ALPHA-001` remains permanently associated with the D2-0003 specimen.

## Scientific interpretation

Stage-1 results, once produced, are `internally_measured` **surrogate-only hypothesis-screening observations**. A survivor licenses only Stage-2 engineering. It is not evidence of held-out transfer, real-world effectiveness, or physical evasion. If no family survives the fixed 64-composition screen, the preregistered H0 outcome stands and no anchor adapter or optimization stage is opened.

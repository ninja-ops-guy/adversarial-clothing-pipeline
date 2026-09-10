# RAC End-to-End Research SOP

**Version:** 1.0.0  
**Last updated:** 2026-09-07  
**Purpose:** Pick-up-and-run operating procedure from experiment selection through digital generation, textile production, physical capture, statistics, immutable release, and manuscript update.

> **Critical boundary:** The browser pages are design, configuration, visualization, mapping, and result-view surfaces. They are not a substitute for the Python research/evidence pipeline. A browser score is never detector evidence unless it is explicitly imported from a measured, provenance-bearing benchmark result.

## 0. What each page is for

### Pattern Lab — `index.html`

Use for:

- procedural candidate exploration;
- seed/parameter capture;
- simulation previews;
- gallery/history;
- PNG/JSON export;
- viewing/importing measured benchmark results with provenance.

Do **not** treat local heuristic/proxy values as measured detector results.

### RAC Textile Generator / Product Studio — `product-studio.html`

Use for:

- selecting canonical RAC product/family;
- Reference Match / Creative generation;
- motif selection;
- deterministic seed/scale/density/distress controls;
- reference-fidelity search;
- 4096×4096 tile export;
- technical garment/reference-board export;
- production manifest generation.

This is the primary creative surface for producing the textile candidate that later enters the research pipeline.

### Production Mapper — `production-studio.html`

Use after a design is frozen:

- import exact vendor template JSON;
- map artwork to real panels;
- inspect bleed/safe areas;
- tune panel offset/scale/rotation;
- validate continuity groups;
- export panel PNGs;
- export mapping JSON;
- export hash-bound panel-pack ZIP;
- create production manifest.

A generic preview template remains draft-only. Vendor-ready status requires the exact provider template and source provenance.

## 1. Choose the experiment before generating results

Start from `docs/PAPER_SERIES.md`, `docs/papers/`, the PIM, or an approved preregistration.

For every experiment define before held-out access:

- experiment ID;
- hypothesis ID;
- directional hypothesis;
- primary endpoint;
- secondary endpoints;
- surrogate set;
- fresh held-out set;
- model/weight/preprocessing/threshold manifests;
- candidate-generation policy;
- optimization objective;
- candidate count;
- seeds;
- EOT/transformation policy;
- invalid-condition rule;
- statistical unit;
- stopping rule;
- practical effect threshold;
- PASS / FAIL / INCONCLUSIVE regions;
- allowed post-freeze appends;
- evidence label.

Do not open a fresh held-out generation until this contract is frozen.

## 2. Generate candidate textiles

Use Product Studio for canonical RAC visual-language candidates or the Python candidate-generation path for computational experiments.

Canonical families:

- Signal Shadow — canonical hat;
- Machine Static — canonical mask; hoodie extension;
- Error Garden — canonical oversized shirt;
- Broken Human — canonical cargo;
- Ghost Hound — canonical beanie.

Freeze:

- candidate ID;
- family/product;
- seed;
- scale/density/distress;
- motifs;
- generation mode;
- reference-fidelity score/subscores when used;
- 4096 master tile;
- production/reference board;
- manifest;
- SHA-256 of every artifact;
- source commit.
- Pattern Genome v1 sidecar for every candidate entering surrogate screening;
- genome index SHA-256 and selected-winner genome reference.

Pattern Genome extraction is automatic in the candidate-selection path. It is
an intrinsic digital measurement only (`derived_digital_measurement`): genome
features are frozen before surrogate evaluation, are not read by the v1
ranking function, and can never satisfy a physical evidence state.

### D2 generation rule

Candidate generation/ranking may use only the declared surrogate set. Fresh held-out models are forbidden during generation, ranking, mutation, fidelity selection, adaptive recoloring, or candidate freeze.

## 3. Surrogate research

For hypothesis-driven digital experiments, record pre-held-out telemetry using the telemetry contract:

- surrogate mean;
- surrogate worst case;
- per-model rates;
- cross-model disagreement;
- transformation mean/worst/variance;
- spectral-band telemetry;
- fidelity;
- printability;
- coverage/topology;
- objective trajectory;
- optimizer configuration;
- calibration-profile reference when applicable;
- candidate SHA-256.

Freeze the telemetry hash **before** held-out access.

### D2-0005 and later

The next planned objective study is equal-budget mean vs worst-case/min-max/CVaR. Only the objective changes; model sets, candidate budget, seeds, transformation policy, thresholds, and held-out rules remain frozen according to the preregistration.

## 4. Freeze candidate

Before held-out evaluation:

1. verify candidate SHA-256;
2. verify source commit;
3. verify surrogate/held-out manifests;
4. verify held-out models have not been loaded by the candidate-selection process;
5. freeze telemetry;
6. freeze preregistration;
7. record generation marker;
8. prohibit candidate mutation.

If the candidate changes by one byte, it is a new artifact/generation.

## 5. Run held-out digital evaluation

Use the Python benchmark/workflow, not browser heuristics.

Rules:

- one-shot fresh held-out generation;
- no threshold changes after seeing candidate outcomes;
- no candidate regeneration;
- retain raw rows;
- retain model manifests;
- retain transformation conditions;
- retain failures;
- append held-out outcome to the frozen telemetry record;
- permanently retire the generation from being described as unseen.

PASS, FAIL, and INCONCLUSIVE are all publishable research outcomes.

## 6. Close and ingest the generation

After closure:

1. verify benchmark candidate hash matches frozen candidate;
2. verify model-lock hashes;
3. verify protocol/model-set identity;
4. verify held-out feedback boundary;
5. verify bundle integrity;
6. run closed-generation ingestion;
7. create/update the ExperimentRegistry entry;
8. append held-out outcome without changing frozen telemetry hash;
9. classify failure if verdict is FAIL;
10. mint `RAC-EXP-YYYY-NNN/`;
11. verify release content hash;
12. compile automated report;
13. append manuscript-ready rows/figures;
14. update `docs/PROJECT_PROGRESS.md`.

Legacy generations with unavailable telemetry fields use explicit null/unavailable values. Never reconstruct missing pre-held-out telemetry from post-held-out knowledge.

## 7. Move frozen textile into Production Alpha

Do not wait for every digital research question to finish before starting the manufacturing clock.

Current first-SKU decision:

- provider: Printful;
- category: all-over-print unisex crew-neck tee;
- substrate: white-base 100% polyester;
- size: M;
- process: cut-and-sew dye sublimation;
- candidate: frozen RAC artwork;
- control: matched solid-fill/control artwork;
- same provider/product/variant/size/substrate/process/order where practical.

Before ordering, resolve and freeze:

- Printful account/API access;
- exact `product_id`;
- exact `variant_id`;
- exact downloadable vendor template ZIP;
- original template ZIP SHA-256;
- template version/source URL/date;
- panel geometry;
- artwork hash;
- mapping hash;
- panel-pack hash;
- SKU manifest.

Open vendor questions remain: effective on-fabric resolution, numeric registration tolerance, template-version policy, and fulfillment-region consistency.

## 8. Printful ordering procedure

See `PRINTFUL_PRODUCTION_SOP.md` for the full provider workflow.

Minimum rule: candidate and control must be as identical as practical except for the experimental artwork.

Order enough material to support:

- matched control;
- candidate;
- calibration/durability reserve;
- replacement/failure reserve when budget permits.

Do not serially discover after delivery that another identical article was needed.

## 9. Prepare calibration before garments arrive

Use `CALIBRATION_TARGET_SPEC.md` and `PHYSICAL_TEST_INFRASTRUCTURE.md`.

Calibration target includes:

- ≥24 color patches;
- 11-step neutral ramp;
- horizontal/vertical line pairs;
- 2/4/8/16/32/64 px checkerboards;
- frequency wedges;
- registration marks;
- 100 mm / 200 mm rulers;
- RAC motif fragments;
- high-frequency random region;
- low-frequency control;
- target ID/version/hash prefix.

Freeze target bytes and manufacturing metadata before printing.

## 10. Prepare P1 rig before garments arrive

Use `P1_CAPTURE_RIG_SPEC.md`.

Mark:

- camera position/height;
- 1 m, 3 m, 5 m, optional 8 m distances;
- actor center;
- yaw 0°, ±45°, ±90° or preregistered subset;
- repeatable movement path;
- named lighting states;
- background;
- camera/lens/settings;
- exposure/white-balance behavior.

Primary statistical unit:

**garment × actor × session**

Frames are nested observations, not independent trials.

## 11. Synthetic dry run

Before real garments arrive, run the entire P1 data path with synthetic inputs labeled:

`synthetic_pipeline_validation_only`

Exercise:

capture manifest → ingestion → validity → statistics → report → evidence bundle → refusal/non-physical status.

Synthetic observations must never become RAC-P evidence.

## 12. Receive and QA physical articles

Before efficacy capture:

- photograph package/product labels;
- verify SKU/variant/size/substrate;
- verify obvious manufacturing defects;
- verify control/candidate are matched;
- photograph front/back/detail under fixed lighting;
- record receipt date;
- assign immutable physical artifact IDs;
- hash all digital records/photos;
- record deviations.

If the articles are not matched, stop and document the manufacturing deviation before testing.

## 13. Calibration capture

Capture calibration target under frozen conditions.

At minimum:

- perpendicular close capture;
- 1 m / 3 m / 5 m frequency-survival captures;
- ≥2 controlled lighting states;
- rawest practical output plus normal processed camera output.

Ingest with calibration software and produce a versioned `print_camera_profile.json`.

Measure:

- RGB/color response;
- CIEDE2000/color error where applicable;
- geometric scale;
- placement/registration;
- frequency attenuation;
- distance attenuation;
- repeatability.

Do not use the profile for measured-EOT until its acceptance gate passes on held-out calibration regions.

## 14. Run P1 matched physical experiment

For each preregistered condition:

1. capture control;
2. capture candidate;
3. retain complete sequence;
4. run detector telemetry;
5. determine control validity;
6. mark control-undetected condition INVALID;
7. never count an invalid control condition as candidate success;
8. aggregate at session level;
9. retain frame telemetry beneath session;
10. run paired statistics.

No threshold changes after candidate results are observed.

## 15. Statistics

Use `trial_statistics.py`.

Report:

- valid/invalid trial counts;
- control detection rate;
- candidate detection rate;
- paired risk difference;
- Wilson intervals;
- deterministic bootstrap interval;
- odds ratio where specified;
- stopping-rule decision;
- per-condition invalid accounting.

Do not rely on point estimates alone.

## 16. Physical evidence release

If P1 data are complete:

- attach calibration-profile hash;
- attach physical artifact IDs;
- attach capture metadata;
- attach raw-data index;
- attach statistical outputs;
- attach invalid conditions;
- seal experiment release;
- run certificate/evidence-state logic.

A digital PASS cannot substitute for P1. A P1 result is valid only for the tested artifact and conditions.

## 17. Durability program

Preserve the same garments.

Planned states:

- W0;
- W1;
- W5;
- W10;
- later states if preregistered.

Record laundering process, detergent, temperature, drying method, color shift, registration, frequency attenuation, and detector outcomes.

Never replace a degraded garment merely because it performs worse.

## 18. Technological aging

Keep the physical artifact fixed while later detector generations change.

Do not reprint/re-optimize the garment for model-aging analysis.

This creates two independent longitudinal axes:

- physical aging;
- model aging.

## 19. Manufacturing evidence

After a repeatable physical design exists:

- freeze golden sample;
- define color/scale/placement/registration tolerances;
- measure production samples;
- run lot-conformity logic;
- retain failures;
- progress M1/M2 only with real manufacturing evidence.

## 20. Paper update procedure

The manuscripts live under `docs/papers/`.

When an experiment closes:

1. cite its immutable RAC-EXP release;
2. insert Results only from released data;
3. generate tables/figures from the report compiler;
4. update Discussion;
5. preserve preregistered hypotheses;
6. discuss failures and alternative explanations;
7. update limitations;
8. never rewrite Methods to make results appear expected.

Priority:

- Paper 1: prospective transfer prediction;
- Paper 5: objective/CVaR ablation;
- Paper 2: manufacturing-calibrated optimization;
- Paper 3: geometry/coverage/deformation;
- Paper 4: physical + technological aging.

## 21. Production gates

### Alpha

- frozen design;
- exact vendor template;
- validated panel pack;
- complete SKU manifest;
- matched order placed.

### Beta

- garments received;
- calibration complete;
- P1 complete;
- uncertainty report complete;
- evidence release verifies.

### v1

- repeatable SKU;
- physical evidence;
- durability evidence;
- golden sample;
- lot tolerances;
- reviewed, condition-specific claims;
- reproducible public evidence package.

## 22. Stop conditions

Stop and document rather than improvise when:

- held-out contamination occurs;
- candidate hash changes;
- model manifest changes;
- threshold changes after result access;
- control garment fails validity;
- control/candidate manufacturing differs materially;
- calibration profile fails acceptance;
- physical metadata are incomplete;
- evidence bundle verification fails.

A stopped experiment is preferable to contaminated evidence.

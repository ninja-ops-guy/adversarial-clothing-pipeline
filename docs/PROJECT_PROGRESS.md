# RAC Project Progress Ledger

**Version:** 1.0.0  
**Last updated:** 2026-09-07  
**Tracking baseline:** `main` at `81cc794` plus the active D2-0004 generation marker.  
**Purpose:** Single source of truth for what has been completed, what is in progress, what is externally blocked, and what constitutes the next production/research gates.

> This ledger tracks engineering and research progress. A software-complete capability is not automatically physical evidence, manufacturing evidence, or a product-efficacy claim.

## Executive status

RAC has moved from a browser pattern prototype into a multi-layer research and production system:

1. **Design factory** — deterministic textile families, reference-fidelity scoring, high-resolution artwork and garment boards.
2. **Research plane** — surrogate optimization, environment-adaptive candidate generation, deformation/physics, frozen held-out evaluation and generation rotation.
3. **Research OS** — experiment registry, telemetry contracts, calibration ingestion, automated reporting, failure taxonomy and content-addressed research releases.
4. **Production compiler** — vendor-template ingestion, seam-aware mapping, panel packs and artifact hashes.
5. **Evidence system** — fail-closed RAC-D0 → D2 → P1/P2 → M1/M2 boundaries.
6. **Physical program** — specified and instrumented in software/docs, but real garments/calibration/P1 evidence are not yet complete.

## Current completion snapshot

| Workstream | Status | Completion meaning |
| --- | --- | --- |
| Core software / research infrastructure | **Advanced / substantially complete** | Major research-OS and evidence primitives exist; continued work should be experiment-driven |
| Product Studio / reference-fidelity system | **Implemented** | Five canonical families, product mapping, reference scoring/search and production exports exist |
| Digital certification architecture | **Implemented** | Frozen manifests, generation isolation, held-out model rotation and bundle verification exist |
| D2-0004 | **IN PROGRESS** | Fresh held-out generation is running; published status must remain D2-0003 until completion |
| Production Alpha preparation | **IN PROGRESS** | First SKU decision/spec exists; exact provider IDs/template/order remain external |
| Statistical P1 infrastructure | **Implemented** | Paired statistics, uncertainty, stopping rules and invalid-condition accounting are in code |
| Calibration infrastructure | **Implemented as software/spec** | Calibration ingestion + target spec exist; real printed calibration measurements do not |
| P1 capture infrastructure | **Implemented as software/spec** | Capture protocol and synthetic dry-run path exist; real garment trials do not |
| Research release / publication infrastructure | **Implemented** | Content-addressed releases, report compiler, telemetry contract and paper plan exist |
| RAC-P physical evidence | **OPEN — EXTERNAL** | Requires matched physical control/candidate testing |
| RAC-M manufacturing evidence | **OPEN — EXTERNAL** | Requires production samples, golden sample and lot measurements |
| Product efficacy claim | **NOT SUPPORTED YET** | Must remain condition-specific and evidence-backed |

## Completed milestones

### A. Core adversarial research platform

- [x] Production Python package under `ruthless_pipeline/`.
- [x] NAP / black-box optimization path with explicit query accounting.
- [x] Neural deformation module.
- [x] Differentiable native cloth baseline.
- [x] Garment scene composition.
- [x] Evaluator interfaces and comparative benchmark.
- [x] Surrogate / held-out split support.
- [x] Transformation sweeps.
- [x] Environment-adaptive candidate generation inspired by CAPGen without vendoring external AGPL implementation code.
- [x] Palette extraction, pattern/color decomposition and surrogate-only adaptive optimization.
- [x] Candidate artifacts explicitly record zero held-out use.

### B. Design factory and Product Studio

- [x] Five canonical design families: Signal Shadow, Machine Static, Ghost Hound, Broken Human, Error Garden.
- [x] Canonical product mapping for hat, mask, shirt, cargo and beanie; hoodie extension.
- [x] Deterministic seeded generation.
- [x] 4096×4096 master tile export.
- [x] High-resolution technical product-board export.
- [x] Product manifests.
- [x] Selectable motif system.
- [x] Reference Fidelity v1 style profiles.
- [x] Product-aware hero/suppression zones.
- [x] Guided multi-pass composition and deterministic sub-seeds.
- [x] 0–100 reference-fidelity scorer.
- [x] Reference Match / Creative modes.
- [x] Find Best Match with preserve-or-improve behavior.
- [x] Fidelity-ranked batch generation.
- [x] Motif propagation bug fixed and covered by E2E tests.
- [x] Low-resolution obsolete showcase path removed from production generation.

### C. Production compiler

- [x] Vendor-template JSON contract.
- [x] Generic AOP preview template clearly marked non-vendor-ready.
- [x] Exact pixel panel dimensions from imported templates.
- [x] Per-panel X/Y offset, scale and rotation.
- [x] Continuity groups and seam-aware mapping.
- [x] Bleed / safe-area visualization.
- [x] Continuity validation.
- [x] Selected-panel PNG export.
- [x] Mapping JSON export.
- [x] Panel-pack ZIP export.
- [x] 4096 master included in panel pack.
- [x] SHA-256 binding for artwork/template/mapping/panels.
- [x] Vendor provenance guardrails.
- [x] Draft vs vendor-template status distinction.
- [x] Production Alpha SKU decision documented for a Printful AOP sublimation tee.
- [ ] Exact provider product/variant IDs fetched.
- [ ] Exact first-SKU vendor template downloaded and frozen.
- [ ] First control/candidate order placed.

### D. Evidence and certification

- [x] RAC evidence ladder: D0 → D1 → D2 → P1 → P2 → M1 → M2.
- [x] Fail-closed evidence transitions.
- [x] Evidence-type/state mismatch rejection.
- [x] Pattern/artifact SHA-256 validation.
- [x] Bundle sealing and tamper verification.
- [x] Physical evidence cannot be substituted by boolean flags.
- [x] Manufacturing evidence cannot be substituted by boolean flags.
- [x] Physical and manufacturing measurement-domain validation.
- [x] Frozen model manifests and model-set contracts.
- [x] Generation rotation and one-shot held-out discipline.
- [x] D2-0003 negative result retained as FAIL / RAC-D0.
- [x] D2-0004 fresh held-out generation preregistered.
- [x] D2-0004 fixture source hash-pinned, cached once per workspace and given verified fallbacks.
- [ ] D2-0004 closed and published.
- [ ] P1 physical evidence.
- [ ] P2 durability evidence.
- [ ] M1 golden-sample evidence.
- [ ] M2 lot-conformity evidence.

### E. Research OS — Wave A

- [x] `experiment.py`: unified experiment artifact + registry.
- [x] Candidate → generation → telemetry → calibration → SKU → physical session → certificate lineage.
- [x] Duplicate experiment / lineage rejection.
- [x] `calibration_ingest.py`: calibration profile ingestion.
- [x] CIEDE2000 color error implementation and validation.
- [x] Scale/resolution/registration validation.
- [x] Hash-stable calibration profiles and acceptance gates.
- [x] `report_compiler.py`: automatic experiment reporting.
- [x] Condition tables, Wilson intervals, risk differences and invalid-condition reporting.
- [x] Markdown / LaTeX / figure-spec outputs.
- [x] `failure_taxonomy.py`: deterministic failure classification.
- [x] Failure atlas and append-only failure records.

### F. Research OS — Wave B

- [x] `telemetry_contract.py`: preregistered next-generation telemetry contract.
- [x] Surrogate mean/worst rates and verified cross-model disagreement.
- [x] Transformation-sweep variance.
- [x] Spectral telemetry.
- [x] Fidelity / printability / objective / coverage telemetry.
- [x] Optimizer configuration and optional calibration-profile reference.
- [x] Frozen pre-held-out SHA-256.
- [x] Immutable held-out outcome append.
- [x] Double-append and candidate-hash mismatch rejection.
- [x] Standalone telemetry JSON Schema.
- [x] `release_format.py`: content-addressed RAC experiment releases.
- [x] Per-file SHA-256 manifest and release content hash.
- [x] Tampered/missing/extra artifact verification.
- [x] Revision log enforcing post-freeze append rules.
- [x] `docs/RESEARCH_RELEASE_FORMAT.md`.

### G. Statistics and physical-test preparation

- [x] Paired control/candidate statistics.
- [x] Wilson confidence intervals.
- [x] Deterministic bootstrap CI for paired risk difference.
- [x] Haldane-corrected odds ratio.
- [x] Exact minimum-valid-trials planner.
- [x] Preregistered stopping-rule evaluation.
- [x] Invalid-trial accounting where control-undetected is invalid, never candidate success.
- [x] Calibration target specification.
- [x] P1 capture rig specification.
- [x] Physical test infrastructure specification.
- [x] Synthetic P1 dry-run path explicitly labeled non-evidence.
- [x] Paper-series pre-results build plan.
- [ ] Physical calibration target manufactured/captured.
- [ ] Real P1 rig dry run with ordinary garments/hardware.
- [ ] Real matched control/candidate P1 sessions.

## Active work

### D2-0004 — do not mutate

Current marker:

- generation: `RAC-PER-D2-0004`
- protocol: `RAC-PERSON-DETECT-1.2`
- surrogate set: `PERSON-SUR-v3`
- held-out set: `PERSON-HO-v3`
- fresh held-out: Faster R-CNN R50-FPN-v2 + Mask R-CNN R50-FPN-v2
- selection boundary: `SURROGATE_ONLY`
- held-out feedback: forbidden
- pool: 100 candidates
- status: running / awaiting publication

The published `d2-latest-status.json` still names D2-0003. This is correct until D2-0004 closes. Do not interpret the old published status as the new generation.

## Immediate next tasks

### Can execute in software now

- [ ] Close D2-0004 and ingest the immutable result into the research release/telemetry system.
- [ ] Instantiate the first canonical `RAC-EXP-YYYY-NNN` release from a closed generation.
- [ ] Wire automatic failure-taxonomy classification into generation closure.
- [ ] Generate manuscript-ready tables/figures automatically from the first canonical release.
- [ ] Preregister D2-0005 around a research hypothesis rather than generic candidate improvement.
- [ ] Recommended D2-0005 study: equal-budget mean vs worst-case/CVaR optimization.
- [ ] Begin longitudinal transfer-predictor dataset with D2-0003, D2-0004 and later generations.

### External / physical critical path

- [ ] Create/authorize first POD provider account and API access.
- [ ] Fetch exact product_id / variant_id.
- [ ] Download exact vendor template and record source/version.
- [ ] Freeze Production Alpha artwork/template/mapping/SKU hashes.
- [ ] Order matched control/candidate garments.
- [ ] Produce and order/print calibration target through the same process.
- [ ] Complete P1 capture-rig hardware setup and preregistration.
- [ ] Run W0 matched physical sessions.
- [ ] Run calibration ingestion and measured-EOT profile acceptance.
- [ ] Begin wash cohort: W1 → W5 → W10 and later states.
- [ ] Establish golden sample and lot-conformity measurements.

## Production gates

### Production Alpha

Complete when:

- [ ] design is frozen;
- [ ] exact POD template is frozen;
- [ ] panel pack passes validation;
- [ ] golden SKU manifest is complete;
- [ ] matched control/candidate order is placed.

### Production Beta

Complete when:

- [ ] physical garments are received;
- [ ] calibration is complete;
- [ ] matched P1 protocol is executed;
- [ ] uncertainty/statistical report is complete;
- [ ] evidence bundle verifies.

### Production v1

Complete when:

- [ ] repeatable SKU exists;
- [ ] condition-specific physical evidence exists;
- [ ] durability/wash evidence exists;
- [ ] golden sample is frozen;
- [ ] lot tolerances are defined and measured;
- [ ] product claims are reviewed against actual evidence;
- [ ] public evidence/release artifacts are reproducible.

## Research publication gates

### Paper 1 — prospective transfer prediction

- [x] Methodology and telemetry infrastructure.
- [x] Closed-generation discipline.
- [ ] D2-0004 closed.
- [ ] At least three comparable closed generations for first serious predictor analysis.
- [ ] Results/discussion populated without post-hoc contamination.

### Paper 2 — manufacturing-calibrated optimization

- [x] Calibration target specification.
- [x] Calibration ingestion software.
- [ ] First physical calibration target.
- [ ] Validated print-camera profile.
- [ ] Heuristic-EOT vs measured-EOT experiment.

### Paper 3 — geometry / coverage / deformation

- [x] Differentiable deformation and cloth baselines.
- [ ] Frozen coverage/topology experiment.
- [ ] Flat → affine → TPS → cloth ablation.

### Paper 4 — aging

- [ ] W0 physical artifact frozen.
- [ ] W1/W5/W10 durability measurements.
- [ ] Same physical artifact evaluated against later model generations.

### Paper 5 — objective / surrogate ablations

- [x] Telemetry/release infrastructure.
- [ ] Mean vs min-max/CVaR experiment.
- [ ] Leave-one-architecture-family-out surrogate experiment.

## Progress accounting

The project should now be measured by **closed evidence loops**, not feature count.

### Software-complete loops

- design generation → artifact export
- surrogate selection → frozen candidate
- held-out generation isolation → evidence decision
- experiment registration → immutable telemetry
- calibration ingestion → versioned profile
- experiment bundle → automated report
- failure → taxonomy / failure atlas
- release directory → content-addressed verification

### Loops still requiring closure

- exact SKU → physical order
- physical order → calibration
- calibration → measured EOT
- physical garment → P1
- P1 → durability
- durability → manufacturing golden sample
- manufacturing → evidence-backed public product claim

## Change log for this ledger

### 2026-09-07

- Recorded D2-0004 fixture reliability fix and active fresh-generation run.
- Recorded P1 trial-statistics implementation.
- Recorded Production Alpha SKU decision/spec.
- Recorded calibration and P1 capture infrastructure.
- Recorded Research OS Wave A: experiment registry, calibration ingestion, report compiler, failure taxonomy.
- Recorded Research OS Wave B: telemetry contract, schema, content-addressed release format.
- Recorded 168/168 green validation reported for Wave B pushed tree.
- Reframed completion tracking around closed experimental/production loops rather than UI or feature count.

Update this ledger whenever a hard gate closes, an evidence state changes, a production artifact is frozen, or a new research generation is opened/closed.

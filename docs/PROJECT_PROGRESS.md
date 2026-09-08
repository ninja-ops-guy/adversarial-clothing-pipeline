# RAC Project Progress Ledger

**Version:** 1.0.0  
**Last updated:** 2026-09-08  
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

### 2026-09-08

- Recorded Wave D (commit 49902d7 + fixup ef14a0a): preregistered D2-0005 selection objectives in certification/objectives.py (mean and CVaR-0.5 worst-k, k = max(1, ceil((1-alpha)*n)), deterministic model-id tie-break), select_surrogate_candidate.py --objective/--cvar-alpha/--objective-telemetry with default mean path byte-identical to legacy, full validation matrix (ties, n=1/3/5/7, empty/NaN rejection, mean-arm legacy parity, pristine-checkout byte comparison).
- Recorded Wave E (commits 9cd2707 + 1554dce): certification/paired_arm_statistics.py (paired arm Delta = R_M - R_C, Wilson intervals, deterministic SHA-256-seeded bootstrap 10000 resamples seed 20260907, discordant b/c counts, success/negative/null/inconclusive decision regions with 0.20 width budget), and PREREGISTRATION_D2-0005.md amendments A1-A4 (evidence label internally_measured; paired-arm statistics module; Stage-A mean screen declared shared nuisance/preselection; objective telemetry mandatory for both arms), section 9 amendment log.
- Recorded Wave F Track E (commit b1116c6): PREREGISTRATION_D2-0006_DRAFT.md — interpretation-policy decision tree keyed to D2-0005 outcome regions; no directional hypothesis; not armed.
- Recorded Wave F Track C (commits b7b7575, 463f4a7, fixups 5b0ec4b/18111382): P1 executable artifacts — deterministic calibration-target generator (RAC-CALT-P1-0001, 48 CIELAB-referenced patches), calibration manifest, camera/lighting setup sheet, rig measurement checklist, session manifest template, capture naming convention, physical trial ingestion template, frozen stopping rule RAC-P1-STOP-2026-001 (min 93 valid trials, max 144), and synthetic end-to-end dry run that fails closed against RAC-P evidence promotion.
- Recorded Wave F Track D: manuscript_export.py — paper1_longitudinal.csv, paper5_arms.csv, paper5_comparison.json exporters plus 8 deterministic figure-input scaffolds (F1-F8) with declared data lineage; empty/awaiting_data states only, zero fabricated results.
- Recorded Wave F Track B: Production Alpha resolution — Printful product_id 388 (AOP recycled unisex hoodie, cut-and-sew sublimation; fallback product_id 257 crew-neck tee) with v1 catalog IDs verified unauthenticated; printfile/template archive and v2 mapping auth-gated (user action); SKU_MANIFEST_DRAFT.json with explicit UNKNOWN fields; ORDER_CHECKLIST.md (ordering is a user action).
- Recorded user-side RAC Capture Lab addition (commits 9a55dac..2546c57): physical research workflow, session validator, evidence boundaries, SOP coverage.
- Recorded D2-0004 run 34147902820 infrastructure failure at workflow step 18 (Build D2 evidence bundle, exit 1) after steps 1-17 succeeded including held-out inference; steps 19-27 skipped, no artifact upload, no status publish — held-out outcome never recorded or observed, informational one-shot boundary intact; generation remains READY_FOR_FRESH_HELDOUT_RUN; D2-0004 has no infrastructure-rerun clause, so re-run is a user governance decision pending root-cause diagnosis.
- Validation: full suite 271 passed on the integrated tree.

### 2026-09-08 (update 2 — Wave G runtime lock, INFRA-001, D2-0004 re-run in flight, F0 design-analysis finding)

> **Status update (2026-09-08):** the earlier 2026-09-08 entry's statement that a D2-0004 re-run was "a user governance decision pending root-cause diagnosis" is superseded by this entry. Root cause is now confirmed and exactly one re-run has been authorized and dispatched; see below. The historical entry is retained unchanged for provenance.

- **Landed (recap, Waves D/E/F):** Wave D selection objectives + objective telemetry (49902d7/ef14a0a); Wave E `paired_arm_statistics` + D2-0005 amendments A1–A4 (9cd2707/1554dce); Wave F Track C P1 executable artifacts incl. frozen stopping rule RAC-P1-STOP-2026-001 (b7b7575/463f4a7/fixups), Track D manuscript exporters, Track B Production Alpha Printful resolution, Track E `PREREGISTRATION_D2-0006_DRAFT.md`; `DESIGN_ANALYSIS_D2-0005.md` operating-characteristics study. Validation: full suite 271 passed on the integrated tree.
- **D2-0004 step-18 failure — root cause confirmed and fixed:** run 34147902820 died at step 18 ("Build D2 evidence bundle") in ~1s, after held-out inference at step 17. Confirmed root cause: protocol-loader crash — `load_protocol()` constructing the frozen `CertificationProtocol` dataclass, which lacked the `generation_id` field introduced by protocol 1.2 (commit 581ba5e): `TypeError: ... unexpected keyword argument 'generation_id'`. Fixed on main by commit **7148202d** (optional `generation_id` field added to `ruthless_pipeline/certification/protocol.py`). The preregistered protocol was correct; the bug was in the loader. Framework-version drift is refuted as the cause (runner resolved exactly the frozen manifest versions; ultralytics 8.4.143 hit PyPI 19 minutes after the unpinned install — luck, not a control). The step-17 held-out output was never inspected, never published, never used; the informational one-shot boundary is intact.
- **Wave G — runtime lock + INFRA-001 + exactly-one-rerun authorization:** `benchmarks/runtime_lock.json` is now the single machine-readable runtime source of truth (python 3.11, torch 2.14.0+cpu, torchvision 0.29.0+cpu, ultralytics 8.4.142, transformers 4.57.6 — exactly matching the frozen model manifests). Both `model-lock-bootstrap.yml` and `measured-benchmark.yml` install the pinned strings and run `scripts/verify_runtime_lock.py` as a hard gate before any model download or inference (head commit b4fe0e5). `docs/AMENDMENT_D2-0004_INFRA-001.md` authorizes **exactly ONE (1) infrastructure re-run** of RAC-PER-D2-0004 under the loader fix and the pinned runtime; any further re-run requires a new amendment. No scientific parameter changed.
- **Run 34175028944 IN PROGRESS:** the authorized re-run of RAC-PER-D2-0004. Until it closes, the published `d2-latest-status.json` correctly remains D2-0003 (FAIL / RAC-D0). Do not mutate the generation; do not interpret the old published status as the new outcome.
- **F0 design-analysis finding (D2-0005):** `docs/DESIGN_ANALYSIS_D2-0005.md` shows the frozen D2-0005 analysis is **INCONCLUSIVE-dominated at the planned n = 72** for symmetric/sparse discordance structures (P(INCONCLUSIVE) ≈ 1.000 across |Δ_true| ≤ 0.3 under independent pairing; mean CI width ≈ 0.27–0.32 vs the 0.20 width gate), with decisive power only under maximum-concordance (`m_dominated`) pairing or at n = 144. **Pending user design decision:** either (a) amend the D2-0005 DESIGN pre-arming per its §7 deviations policy / §9 amendment log, or (b) declare D2-0005 an exploratory/pilot-sized prospective experiment. No threshold change has been proposed or made; D2-0005 remains frozen and NOT armed, gated on D2-0004 closing first.
- **Open user actions:** (1) Printful private API token (`PF_TOKEN`) — printfile/template archive and v2 catalog mapping are auth-gated (`production_alpha/ORDER_CHECKLIST.md` Step 0); (2) download + hash the exact product-388 template/printfile archive and fill `SKU_MANIFEST_DRAFT.json` UNKNOWNs; (3) place the matched control/candidate garment order (user-executed; the agent never orders/pays); (4) monitor re-run 34175028944 and, on closure, ingest the immutable result via `scripts/ingest_closed_generation.py` and publish status.

Update this ledger whenever a hard gate closes, an evidence state changes, a production artifact is frozen, or a new research generation is opened/closed.

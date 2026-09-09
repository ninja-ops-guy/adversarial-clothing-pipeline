# RAC World-Class Gap Analysis

**Swarm:** RAC Parallel Expansion Swarm — Barrier 0 inventory
**Repository:** ninja-ops-guy/adversarial-clothing-pipeline
**HEAD at inventory:** `b50f6b0` ("Add evidence recovery tool for non-scientific stage resume")
**Date:** 2026-09-09
**Method:** Static read-only inspection by 4 parallel inventory lanes (PRINT/PHY, OPT/EOT/DET, DEF/SCI/R3, GOV/CONFLICT). No file was modified. No test suite was executed against held-out surfaces. Classifications follow charter §4: COMPLETE / PARTIAL / MISSING / BLOCKED / USER_ACTION_REQUIRED / OWNED_BY_OTHER_SWARM. Nothing is marked COMPLETE merely because code exists.

---

## 0. Scientific state confirmation (charter §21)

| Item | Charter expectation | Observed | Verdict |
|---|---|---|---|
| D2-0004 | CLOSED / FAIL / RAC-D0 | `d2-latest-status.json`: decision FAIL, evidence_state RAC-D0, bundle_verified true; `docs/D2-0004_CLOSURE_NOTE.md`: "CLOSED. Decision FAIL / evidence_state RAC-D0, retained permanently" (log-attested; step-22 bundle archival FAILED — documented attestation gap) | CONFIRMED |
| D2-0005 | PREREGISTERED | `generations/RAC-PER-D2-0005.json`: status/lock_status PREREGISTERED, lock_source_commit null, lock_inference_performed false | CONFIRMED |
| D2-0005 READY_TO_ARM | NO | `docs/D2-0005_ARMING_PACKET.md` §8: "READY_TO_ARM: NO", AWAITING_USER_DECISION | CONFIRMED |
| D2-0005 ARMED | false | `docs/D2-0005_FREEZE_CANDIDATE.json`: armed false, FREEZE_CANDIDATE_NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT | CONFIRMED |

No inventory action touched any §2 boundary file.

---

## 1. P0 — PRINT ALPHA (charter §5) — **PARTIAL**

| Requirement | Class | Evidence | Gap to COMPLETE |
|---|---|---|---|
| `print-alpha/` charter tree (CONTROL/CANDIDATE/CALIBRATION/MANIFESTS/CAPTURE/QA) | **MISSING** | `find` for `print-alpha` = 0 hits | Create tree with charter-named files |
| SKU manifest | PARTIAL | `production_alpha/SKU_MANIFEST.json` (+DRAFT) | Fields are `PENDING_TEMPLATE_DOWNLOAD` / `PENDING-API-FETCH`; evidence_label `scenario_assumption`; status DRAFT |
| Capture protocol set | PARTIAL | `docs/CAPTURE_LAB.md`, `docs/P1_CAPTURE_RIG_SPEC.md`, `physical/p1/CAMERA_LIGHTING_SETUP.md`, `CAPTURE_NAMING_CONVENTION.md`, `RIG_MEASUREMENT_CHECKLIST.md`, `STOPPING_RULE.json`; `ruthless_pipeline/physical_protocol.py::capture_rows` (108 matched pairs, `tests/test_print_test_pipeline.py`) | Charter-named files `capture-protocol.md`, `camera-lighting-sheet.md`, `invalid-condition-rules.json`, `trial-sheet.csv` do not exist |
| QA set | PARTIAL | `production_alpha/RECEIPT_QA_FORM.md`, `protocols/RAC-PHYSICAL-PRINT-TEST-1.0.md` | `QA/garment-pairing-checklist.md` and `QA/chain-of-custody.md` absent repo-wide |
| Control/candidate matched pair (SKU/material/size/tech/vendor/batch) | PARTIAL | `docs/PRODUCTION_ALPHA_SKU.md` matched-pair spec (white 100% poly sublimation knit, size M, cut-and-sew dye sublimation); `control_rule` encoded in SKU_MANIFEST.json | Vendor `product_id`/`variant_id` unresolved — **USER_ACTION_REQUIRED** (Printful API token) |
| Candidate byte-identical to frozen source | PARTIAL | `expected_pattern_sha256` (b07b617f…) and `print_test_kit_sha256` pinned with no-regeneration note | Per-placement `artwork_sha256` pending template download — **USER_ACTION_REQUIRED** |
| `physical_efficacy_claimed = false` flag | **MISSING** | 0 grep hits; prose disclaimers only ("makes no efficacy claims", PRODUCTION_ALPHA_SKU.md) | Add explicit boolean to print-alpha manifests |
| `evidence_class = experimental_print_specimen` | **MISSING** | 0 grep hits; other classes exist (`synthetic_pipeline_validation_only`, `generated_digital_reference`, `log_attested`) | Add class to evidence taxonomy + manifests |
| User-action packets for vendor/payment | **COMPLETE** | `production_alpha/ORDER_WORKSHEET.md` (agent never orders/pays; cost blank by design), `TEMPLATE_INGESTION_CHECKLIST.md` (HTTP 401 recorded), `VENDOR_QUESTIONS.md` (OPEN → USER ACTION), `ORDER_CHECKLIST.md`; fail-closed fabrication guard in `certification/calibration_target.py` | — |

**Cross-cutting blocker:** Printful API token / order placement / physical capture are USER_ACTION_REQUIRED and gate A.2, A.3, and downstream calibration.

## 2. P1 — OPTIMIZATION ENGINE V3 (§6) — **PARTIAL (MISSING as specified)**

Existing assets (different names, weaker semantics):
- `ruthless_pipeline/nap.py` (402 LOC): fixed 4-term weighted objective (`adv=1.0, aesthetic=0.25, nps=0.10, tv=0.03`), seed pinning, periodic checkpoint writes, black-box modes. No registry, no checkpoint hashing, no resume integrity.
- `ruthless_pipeline/candidate_optimizer.py`: detector-driven candidate optimizer with held-out blindness metadata (`tests/test_candidate_optimizer.py`).
- `ruthless_pipeline/certification/objectives.py`: only CVaR code in repo — preregistered CVaR_α expected shortfall over surrogate detection rates (`tests/test_objectives.py`). Selection statistics, not an optimizer aggregator.

MISSING: `ruthless_pipeline/optimization/` (objective_registry, optimizer, gradient_backend, blackbox_backend, trajectory, constraints, pareto, schemas); composable J with λ_print/λ_style/λ_deformation/λ_reg; MEAN/CVAR/WORST_CASE aggregation enum; NaN/divergence refusal; checkpoint hashing + resume integrity; finite-difference gradient checks; trajectory provenance; baseline candidate-pool parity; `tests/optimization/`.

## 3. P1 — EXPECTATION OVER TRANSFORMATION (§7) — **MISSING**

- No `ruthless_pipeline/transformations/`, no `tests/transformations/`, no `schemas/transformation_distribution.*`; `distribution_id` = 0 hits.
- Adjacent: fixed augment grid in `benchmark.py` (`BenchmarkConfig` brightness/scales/blur/rotations) — hardcoded sweep, not a reproducible distribution; garment/geometry ingredients unconnected (`scene.py`, `physics.py`, `deformation.py`).
- MISSING: 4-dimension distribution system (geometry/imaging/garment/print-capture), reproducibility contract (distribution_id + manifest + seed + sample index), robustness surfaces.

## 4. P1 — DETECTOR RESPONSE SCHEMA (§8) — **PARTIAL (MISSING as specified)**

- Existing: `evaluators.py::DetectionBatch(boxes, labels, scores, target_scores)`; invalid-condition accounting in `benchmark.py`; 8 model manifests with weights sha256 (`model_manifests/`).
- MISSING: `detector_science/` package (response.py, family_registry.py, transfer_matrix.py); objectness / person_detected / condition_id / best_box / localization / segmentation fields; architecture `family` field (absent from manifests); surrogate diversity report; leave-one-family-out; cross-family transfer matrix; concentration warning.

## 5. P1 — PARETO SEARCH (§9) — **MISSING**

No dominance/frontier computation anywhere (only prose mentions). No candidate classes DIGITAL_BEST / TRANSFER_BEST / PHYSICAL_ROBUSTNESS_BEST / STYLE_BEST / BALANCED.

## 6. P1 — STYLE-CONSTRAINED OPTIMIZATION (§10) — **PARTIAL (design side only)**

- COMPLETE sub-item: five families preserved in `design_profiles/ruthless_reference_v1.json` (signal_shadow, machine_static, ghost_hound, broken_human, error_garden; schema 1.1, PREREGISTERED_DESIGN_PROFILE, explicit art-direction-only boundary).
- Deterministic 0–100 style scorer exists in the JS studio path only (`studio-style-profiles.js`, per RAC_STUDIO_UX_SPEC.md). NAP `aesthetic_loss_weight` uses a disabled-by-default backend, not the five families.
- MISSING: Python-side style term in objective; initial/final style+detector+printability tracking; style-vs-objective Pareto curves (depends on §9).

## 7. P2 — DEFORMATION / PHYSICS STACK (§11) — **PARTIAL**

| Tier | Status | Evidence |
|---|---|---|
| T0 affine/projective | PARTIAL (implicit) | `F.affine_grid` inside `benchmark.py:83`, `capgen.py:181`; not a named tier |
| T1 coordinate deformation field | COMPLETE (module-level) | `deformation.py` (272 LOC): NeuralDeformationField, FabricDeformationPrior, fit/predict/sample_warp; `tests/test_deformation.py` (smoke-level) |
| T2 mass-spring cloth | COMPLETE (module-level) | `physics.py` (204 LOC): NativeDifferentiableCloth, DifferentiableGarmentRenderer; `tests/test_physics.py` (smoke-level) |
| T3 empirically calibrated | **MISSING** | no empirical calibration terms in deformation/physics |
| Tier abstraction + cross-tier benchmark (cost/determinism/fidelity/predictive value) | **MISSING** | "tier" vocabulary absent; `docs/PROJECT_PROGRESS.md:267` lists "Flat → affine → TPS → cloth ablation" as unchecked TODO |
| `artifacts/deformation_benchmark/`, `docs/DEFORMATION_VALIDATION.md` | **MISSING** | 0 hits |

## 8. P2 — PRINTABILITY LOSS (§12) — **MISSING**

- `printability_loss(candidate, production_profile)` = 0 hits. No gamut distance, min feature size, high-frequency survivability, DPI/bleed/safe-area/panel checks, digital-to-camera discrepancy metric.
- Only a heuristic `printability` scalar in `certification/telemetry_contract.py:166`.
- Underwriting groundwork present: ΔE00 + MTF cutoff machinery in `certification/calibration_ingest.py`; frequency wedges in `docs/CALIBRATION_TARGET_SPEC.md`. Vendor tolerance/ΔE measurements OPEN — USER_ACTION_REQUIRED (`production_alpha/VENDOR_QUESTIONS.md` Q1/Q2).

## 9. P2 — DIGITAL→PHYSICAL TRANSFER (§13) — **MISSING (schema)**

- `physical_transfer_record` = 0 hits. No schema with the charter hash fields (artwork/template/mapping sha256, garment_sku, fabric, print_process, capture_id, camera, lighting, pose, view, captured_frame_sha256, detector_response_refs).
- `synthetic_pipeline_validation_only` flag: COMPLETE but lives on the experiment journal (`experiment_state_machine.py:78`), not on transfer records.

## 10. P2 — CALIBRATION FEEDBACK MODEL (§14) — **PARTIAL (SCAFFOLD_ONLY correctly enforced)**

- COMPLETE sub-items: digital-side scaffolding — `docs/CALIBRATION_TARGET_SPEC.md` v1.0.0 (48 patches, ramps, checkerboards 2–64px, frequency wedges, frozen production record hash list, 5-point acceptance gate); `calibration_target.py` fail-closed validator + promotion guard (rejects measured evidence_class; fabrication stays open USER ACTION) with `tests/test_calibration_target_contract.py`; `calibration_ingest.py` real CIEDE2000 ΔE00, scale/geometry error, MTF cutoff, PrintCameraProfile with profile_sha256/acceptance (`tests/test_calibration_ingest.py`).
- MISSING: measured data (no `print_camera_profile.json`; blocked on physical capture — USER_ACTION_REQUIRED); feedback consumer (no code consumes a calibration profile as a transformation source); explicit uncertainty-aware estimation model.
- Charter constraint `status = SCAFFOLD_ONLY until measured data`: **enforced by design — COMPLETE.**

## 11. P3 — AUTOMATED ABLATION LAB (§15) — **PARTIAL (1 of 9 comparisons)**

- Robust machinery exists for comparison #3 (mean vs CVaR) only: `rehearsal_d20005.py` (deterministic synthetic fixtures, surrogate selection arm, mock held-out cluster outcomes), `paired_arm_statistics.py`, `cluster_paired_arm_statistics.py` (draft amendment path, not preregistered), operating-characteristics artifacts `artifacts/design_analysis_d20005*/` with tests.
- MISSING: generalized experiment registry + synthetic fixtures for the other 8 comparisons (random vs Product Studio; PS vs adversarial optimizer; single vs ensemble; EOT on/off; deformation-aware; printability-aware; style-constrained; simulation vs physical).

## 12. P3 — MECHANISM ANALYSIS (§16) — **MISSING**

No tooling for confidence displacement, detection stability, localization change, threshold-crossing frequency, architecture-specific response, or transformation sensitivity; no competing-hypotheses harness. Terms appear only as narrative plans. Adjacent: `benchmark-results.json` mean-confidence reduction (coarse), `certification/failure_taxonomy.py` (classification, not analysis).

## 13. REPRODUCIBILITY RAC-R3 (§17) — **PARTIAL (strong spine)**

- COMPLETE sub-items: dependency lock (`benchmarks/runtime_lock.json` + requirements.txt, `tests/test_runtime_lock.py`); model hashes (8 manifests + model sets, `test_model_lock.py`); frozen-surface hashes (`benchmarks/frozen_surface_sha256.json`, `test_frozen_surface_integrity.py`); release manifest (`releases/RAC-EXP-2026-001/MANIFEST.json` per-file SHA-256); provenance graph (`provenance_graph.py` + committed `artifacts/provenance/graph.json`, VERIFIED/BROKEN/MISSING/MUTABLE verify mode); journal (CHANGELOG, PROJECT_PROGRESS, RESEARCH_EVIDENCE_REGISTER, REVISIONS.json).
- MISSING: consolidated RAC-R3 manifest as one checkable record; explicit **source commit** pin; consolidated **seed manifest**; named optimizer-config / transformation-manifest / candidate-hash / analysis-hash fields (currently implicit inside release entries). Known attestation gap: D2-0004 evidence bundle never archived (log-attested only) — inherited, documented, not introduced by this swarm.

## 14. ACCEPTANCE / TEST COVERAGE SURVEY (§18) — **PARTIAL**

- 64 files in `tests/` + 5 Playwright e2e specs. Direct tests exist for all of benchmark, candidate_optimizer, capgen, deformation, nap, physics, scene, and ~24 certification submodules.
- Gaps: `common.py` (no direct tests); `evaluators.py` and `physical_protocol.py` (indirect only); certification modules `artifact_bundle.py`, `manifest.py`, `manufacturing.py`, `registry.py`, `verification.py`, `calibration.py` (indirect only); physics/deformation/benchmark tests are smoke-level; no coverage threshold config.

## 15. OWNED_BY_OTHER_SWARM surfaces (conflict-avoid list)

Derived from `git log` (Wave I/J commits through HEAD `b50f6b0`). This swarm MUST NOT edit:
- Experiment-state/governance: `certification/experiment_state_machine.py`, `experiment_status.py`, `d20006_governance.py`, `rehearsal_d20005.py`, `cluster_paired_arm_statistics.py`, `paired_arm_statistics.py`, `telemetry_contract.py` + their tests.
- Evidence recovery: `certification/evidence_recovery.py`, `scripts/recover_evidence.py`, `tests/test_evidence_recovery.py`.
- Provenance/dashboard: `certification/provenance_graph.py`, `scripts/build_provenance_graph.py`, `scripts/export_dashboard_data.py`, `artifacts/provenance/graph.json`, `artifacts/dashboard/experiments.json` + tests.
- Calibration/citation: `certification/calibration_target.py`, `scripts/generate_calibration_target.py`, `scripts/export_citation_matrix.py`, `manuscript/exports/citation_evidence_matrix.json` + tests.
- Docs/threat-model/performance: `certification/doc_lint.py`, `scripts/lint_docs.py`, `scripts/profile_pipeline.py`, `.doclint-allow.json`, `docs/THREAT_MODEL_RESEARCH_PIPELINE.md`, `docs/PERFORMANCE_AND_COST.md`, `docs/DESIGN_ANALYSIS_D2-0005.md` + tests.
- Packaging/schema-contract: `schemas/product_studio_manifest.contract.json`, `scripts/build_d2_bundle.py`, `scripts/build_print_test_kit.js`, `scripts/package_print_test_kit.py` + tests.
- All §2 boundary files (generations/, d2-latest-status.json, PREREGISTRATION_D2-0005*, D2-0005_*, docs/audits/**, benchmarks/runtime_lock.json, model_sets/PERSON-HO-v3.json).

**Rule:** all new work lands in NEW namespaces (`ruthless_pipeline/optimization/`, `transformations/`, `detector_science/`, `print-alpha/`, new schemas/docs). Shared core files are not edited.

## 16. Repo health notes

- 6 CI workflows; bare `pytest` in ci.yml. **No pyproject.toml / setup.py / requirements at repo root** — packaging metadata gap for reproducible installs (candidate new-swarm task, additive only).
- JS frontend (Product Studio / capture-lab) + Playwright e2e present.
- `physical/p1/calibration-target/` referenced but absent.

## 17. USER_ACTION_REQUIRED register

| # | Action | Blocks |
|---|---|---|
| UA-1 | Printful API token + template ZIP download | SKU variant IDs, per-placement artwork_sha256, mapping manifest |
| UA-2 | Printful order placement + payment (matched pair) | physical specimens, receipt QA |
| UA-3 | Physical capture session (rig per P1_CAPTURE_RIG_SPEC) | calibration profile, transfer records |
| UA-4 | Vendor answers: placement tolerance, ΔE (VENDOR_QUESTIONS Q1/Q2) | versioned vendor measurements for printability loss |
| UA-5 | D2-0005 arming decision (governance swarm + user only) | out of this swarm's scope entirely |

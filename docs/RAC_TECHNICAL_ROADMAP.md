# RAC Technical Roadmap

**Swarm:** RAC Parallel Expansion Swarm
**Basis:** RAC_WORLD_CLASS_GAP_ANALYSIS.md @ HEAD `b50f6b0` (2026-09-09)
**Ordering:** P0 print readiness → P1 optimization infrastructure → P2 physical-transfer infrastructure → P3 science tooling. Merge barriers per charter §20.

---

## Barrier 0 — Inventory (THIS WAVE)
- [x] World-class inventory vs charter (gap analysis, acceptance matrix, inventory JSON, handoff).
- Exit: this document + acceptance matrix + handoff committed. **DONE.**

## Barrier 1 — Schema/interface freeze (next wave)
New files only; no shared-core edits. Deliver:
1. `schemas/physical_transfer_record.schema.json` — charter §13 hash fields; `evidence_class` enum incl. `synthetic_pipeline_validation_only` and `experimental_print_specimen`.
2. `schemas/transformation_distribution.schema.json` — distribution_id, parameter manifest, seed, sample index; geometry/imaging/garment/print-capture dimensions.
3. `schemas/detector_response.schema.json` — charter §8 fields; adapters emit only legitimately exposed fields.
4. `schemas/optimization_objective.schema.json` — composable J terms, MEAN/CVAR/WORST_CASE aggregation, λ vector.
5. `schemas/print_alpha_manifest.schema.json` — with `physical_efficacy_claimed` (must be false) and `evidence_class = experimental_print_specimen`.
6. Evidence-taxonomy addition: register `experimental_print_specimen` class (new file; do NOT edit certification/evidence.py — propose via additive module + note in handoff for governance swarm).
7. RAC-R3 consolidated manifest schema (12 charter fields incl. source commit, seed manifest, optimizer config, transformation manifest, candidate hash, analysis hash).
- Exit: schemas + contract tests (`tests/schemas/`) green.

## Wave 2 — P0 PRINT ALPHA (RAC-A)
Depends: Barrier 1 (schema 5). Blocked inputs: UA-1/UA-2.
1. Create `print-alpha/` charter tree: CONTROL/, CANDIDATE/, CALIBRATION/, MANIFESTS/, CAPTURE/, QA/.
2. Author charter-named files by reference (not duplication) to existing docs: capture-protocol.md, camera-lighting-sheet.md, invalid-condition-rules.json, trial-sheet.csv (generate CSV from `physical_protocol.py::capture_rows` deterministic export).
3. New QA docs: garment-pairing-checklist.md, chain-of-custody.md.
4. MANIFESTS: artwork/template/mapping/sku/print-alpha manifests; unresolved vendor fields explicitly `PENDING_USER_ACTION` (fail-closed, never fabricated).
5. User-action packet consolidating UA-1..UA-4.
- Acceptance: manifests validate against schema 5; `physical_efficacy_claimed=false` enforced by test.

## Wave 3 — P1 OPT + EOT + DET + PARETO + STYLE (RAC-B/C/D, parallel)
New namespaces only.
1. `ruthless_pipeline/optimization/`: objective_registry, optimizer, gradient_backend, blackbox_backend, trajectory, constraints, pareto, schemas. Validation: deterministic seeds, objective decomposition, NaN/divergence refusal, checkpoint hashing, resume integrity, finite-difference gradient checks, trajectory provenance, **candidate-pool parity test vs current finite-selection baseline** (baseline preserved, never replaced).
2. `ruthless_pipeline/transformations/` + `tests/transformations/`: 4-dimension distribution sampler; reproducible from (distribution_id, manifest, seed, index); robustness-surface outputs (not scalar averages).
3. `ruthless_pipeline/detector_science/`: response.py, family_registry.py, transfer_matrix.py; family annotations for the 8 model manifests (additive sidecar file, manifests untouched); surrogate diversity report; leave-one-family-out; concentration warning.
4. Pareto search over: detector objective, cross-model transfer, transformation robustness, printability, style. Candidate classes DIGITAL_BEST / TRANSFER_BEST / PHYSICAL_ROBUSTNESS_BEST / STYLE_BEST / BALANCED. No certification from this infra.
5. Style-constrained optimization: port deterministic style scorer to Python (five families from `design_profiles/ruthless_reference_v1.json` as priors); track initial/final style/detector/printability + optimization path; style-vs-objective Pareto curves. Style score is never RAC efficacy evidence.

## Wave 4 — P2 PHYSICAL-TRANSFER STACK (RAC-E)
1. Deformation tiers T0–T3 behind a common interface (wrap existing `deformation.py`/`physics.py`; T0 explicit affine/projective; T3 = SCAFFOLD until measured calibration exists). Cross-tier benchmark → `artifacts/deformation_benchmark/` (synthetic only) + `docs/DEFORMATION_VALIDATION.md`. Goal: cheapest model that predicts physical observations, not max complexity.
2. `printability_loss(candidate, production_profile)`: gamut distance, min feature size, high-freq survivability (build on calibration_ingest MTF/ΔE00), resolution/DPI/bleed/safe-area/panel geometry, digital-to-camera discrepancy. Versioned vendor measurement store; no assumed vendor behavior (UA-4 gates measured values).
3. `physical_transfer_record` emission/validation tooling; synthetic records flagged `synthetic_pipeline_validation_only`.
4. Calibration feedback model: estimation digital→print→fabric→camera→observed with uncertainty reporting; `status = SCAFFOLD_ONLY` until measured captures (UA-3); eventual consumer interface for transformations stack.

## Wave 5 — P3 SCIENCE TOOLING (RAC-F)
1. Ablation lab: generalize rehearsal machinery into an experiment registry covering all 9 charter comparisons with synthetic fixtures. Harness may NOT run held-out experiments.
2. Mechanism analysis: metrics for confidence displacement, detection stability, localization change, threshold-crossing frequency, architecture-specific response, transformation sensitivity; competing-hypotheses comparison tooling. No mechanism preregistered or asserted in advance.

## Wave 6 — RAC-R3 consolidation + independent verification (RAC-G)
1. Consolidated RAC-R3 release manifest generator (source commit, dependency lock, model/fixture hashes, seed manifest, optimizer config, transformation manifest, candidate/analysis hashes, environment manifest, journal, release manifest).
2. RAC-G independent numerical verification of Waves 3–5 (RAC-G authors nothing it verifies).
3. Repo-hygiene (additive): pyproject.toml + root requirements for reproducible install; direct tests for `common.py`, `evaluators.py`, `physical_protocol.py` — staged last to minimize collision with governance swarm.

## Dependency notes
- UA-1..UA-4 (user actions) gate Wave 2 completion and Wave 4 measured-data promotion only; all synthetic work proceeds independently.
- Nothing in Waves 2–6 touches D2-0004/D2-0005 surfaces; crossing Barrier 5 does not authorize D2-0005 execution.


## External research integration — noRecognition (2026-09-10)

**Status:** REVIEW COMPLETE; runtime audit and implementation PENDING.  
**Review:** [noRecognition review and RAC integration](research/NORECOGNITION_REVIEW_2026-09-10.md).

- [ ] Pass A: audit evaluation-exposure provenance, stage accounting, and report consistency (NR-01/04/05); implement only confirmed gaps.
- [ ] Pass B: reconcile observation-medium labels and control estimands with existing physical readiness (NR-02/03).
- [ ] Pass C: require predictor provenance and prospective evaluation when such a study is proposed; complete the physical-paper full-text review (NR-06).

Preserve current physical/production priorities and frozen experiment boundaries. The review maps acceptance checks to existing components; it does not certify implementation completeness or create a new performance claim.

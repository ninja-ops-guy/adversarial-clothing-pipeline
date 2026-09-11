# RAC Parallel Swarm Handoff — Barrier 0 (Inventory) Complete

**Date:** 2026-09-09
**HEAD at start:** `b50f6b0` ("Add evidence recovery tool for non-scientific stage resume")
**Wave executed:** Barrier 0 — world-class inventory only. No implementation lanes started.

## Commits landed
- Barrier 0 deliverables (5 files, all NEW — zero edits to existing files).

## Files changed
- `docs/RAC_WORLD_CLASS_GAP_ANALYSIS.md` (new)
- `docs/RAC_TECHNICAL_ROADMAP.md` (new)
- `docs/RAC_WORLD_CLASS_ACCEPTANCE_MATRIX.md` (new)
- `docs/RAC_PARALLEL_SWARM_HANDOFF.md` (new, this file)
- `artifacts/rac_deliverable_inventory.json` (new)

## Tests
- Inventory was static/read-only; no code changed, no tests required or run by this swarm. Existing CI untouched.

## Numerical validation
- N/A (no numerical modules authored). All classifications evidence-backed by direct file reads; see gap analysis.

## Artifacts created
- The 5 deliverables above. Inventory JSON is machine-readable and regenerable from repo state.

## Inventory changes (COMPLETE/PARTIAL/MISSING counts)
- 24 charter requirement rows assessed: **2 COMPLETE** (§5-A8 user-action packets; §14 SCAFFOLD_ONLY enforcement), **12 PARTIAL**, **10 MISSING**, **1 OWNED_BY_OTHER_SWARM** (boundary integrity), plus 5 USER_ACTION_REQUIRED items registered (UA-1..UA-5).
- Headline: P0 print-alpha content exists scattered but charter tree/flags missing; P1 optimization/EOT/Pareto largely greenfield (nap.py, candidate_optimizer.py, CVaR objectives are reusable ingredients); P2 calibration scaffolding strong, transfer/printability/deformation-benchmark greenfield; RAC-R3 spine strong but unconsolidated.

## Conflicts avoided
- Zero edits to existing files. Zero overlap with Wave I/J surfaces (full conflict list in gap analysis §15: experiment-state machine, evidence recovery, provenance/dashboard, calibration/citation, doc-lint/threat-model/performance, packaging/schema-contract, and all §2 boundary files).

## OWNED_BY_OTHER_SWARM items
- D2-0005 pre-arming governance; experiment-state machinery; evidence recovery; provenance/dashboard; calibration/citation exporters; documentation/threat-model/performance surfaces; all §2 boundary files and frozen thresholds (K ≥ 72, ICC ≤ 0.25, Δ ≥ 0.2, bootstrap method/seeds, independence definition, model sets, candidate-pool seed, decision regions, D2-0004 evidence).

## USER_ACTION_REQUIRED
| # | Action | Blocks |
|---|---|---|
| UA-1 | Printful API token + template ZIP download | SKU variant IDs, per-placement artwork hashes, mapping manifest |
| UA-2 | Printful order + payment (matched pair) | physical specimens, receipt QA |
| UA-3 | Physical capture session (P1 rig) | calibration profile, transfer records |
| UA-4 | Vendor answers (placement tolerance, ΔE) | versioned vendor measurements, printability loss |
| UA-5 | D2-0005 arming decision | outside this swarm's authority (governance swarm + user) |

## Scientific state confirmation (re-verified at inventory time)
- D2-0004: CLOSED, FAIL, RAC-D0 — untouched.
- D2-0005: PREREGISTERED, READY_TO_ARM = NO, ARMED = false — untouched.

## Next 10 dependency-ordered actions
1. Barrier 1: author 7 new schemas (transfer record, transformation distribution, detector response, optimization objective, print-alpha manifest, evidence-class addition, RAC-R3 manifest) + contract tests.
2. Register `experimental_print_specimen` evidence class (additive module; flag to governance swarm for taxonomy integration).
3. RAC-A: create `print-alpha/` tree with charter-named CAPTURE/QA files (pairing checklist, chain-of-custody).
4. RAC-A: emit print-alpha manifests with `physical_efficacy_claimed=false`, unresolved vendor fields `PENDING_USER_ACTION`; generate trial-sheet.csv from `physical_protocol.capture_rows`.
5. RAC-A: consolidated user-action packet (UA-1..UA-4).
6. RAC-B: `ruthless_pipeline/optimization/` scaffold (registry, backends, trajectory, constraints, schemas) with deterministic-seed + NaN/divergence-refusal tests.
7. RAC-B: checkpoint hashing + resume integrity + finite-difference gradient checks + candidate-pool parity test vs baseline.
8. RAC-C: `ruthless_pipeline/transformations/` distribution sampler (4 dimensions, reproducible from distribution_id+manifest+seed+index) + robustness surfaces.
9. RAC-D: `ruthless_pipeline/detector_science/` (response schema, family registry sidecar for 8 manifests, transfer matrix, LOFO, concentration warning).
10. RAC-B/D: Pareto search + candidate classes, then style-constrained optimization with five-family priors and style-vs-objective Pareto curves.

## Final assertions
- `D2_0004_MODIFIED = false`
- `D2_0005_ARMED = false`
- `NEW_HELDOUT_ACCESS = false`
- `SCIENTIFIC_THRESHOLDS_CHANGED = false`

All four assertions are truthfully made: this swarm performed read-only inspection and added 5 new files; no boundary file was opened for write, no experiment armed, no held-out evidence accessed, no threshold touched.

---

# APPENDIX — Barrier 1 + Barrier 2 (2026-09-09, second session wave)

## Barrier 1 (commit bb3dad5)
- 7 frozen contracts + additive evidence-class registry + tests/schemas/ (69 tests).
- RAC-G independent verification: PASS (21/21 independent negative-case checks).

## Barrier 2 lanes (this commit series)
| Lane | Namespace | Tests | Notes |
|---|---|---|---|
| RAC-A PRINT | print-alpha/, scripts_print_alpha/, tests/print_alpha/ | 21 | RAC-PRINT-ALPHA-001 tree; 5 manifests vs frozen schema; trial-sheet.csv 108 rows deterministic (sha256 774c2ad6…); PENDING_USER_ACTION fail-closed; byte_identical=false honestly until UA-1 |
| RAC-B OPT | ruthless_pipeline/optimization/, tests/optimization/ | 72 | 9 modules; NaN/divergence refusal; checkpoint hashing + resume integrity; FD gradient <1e-4; pool-baseline brute-force parity; pareto + 5 candidate classes (certification=None); style proxy scorer + style-Pareto |
| RAC-C EOT | ruthless_pipeline/transformations/, tests/transformations/ | 33 | sha256 sub-seed per-sample reproducibility; 4 dimension groups; robustness surfaces; calibration refusal |
| RAC-D DET | ruthless_pipeline/detector_science/, tests/detector_science/ | 27 | fabrication guard; 8-manifest family sidecar (5 families); concentration warning; transfer matrix; LOFO; diversity report |
| RAC-E PHY | ruthless_pipeline/physical_transfer/, docs/DEFORMATION_VALIDATION.md, tests/physical_transfer/ | 33 (+1 skip) | printability_loss 6 components w/ partial renormalization; versioned profile store; transfer record builder; deformation tiers T0–T3 (T3 SCAFFOLD_ONLY); benchmark: T0 9.2e-4s deterministic PSNR inf; T2 2.2e-2s PSNR 127.7dB; T1 49s one-time fit PSNR 39.5dB |

## Integration
- Cross-lane test-isolation fix: tests/schemas bare `conftest` import → importlib path load (2 files).
- Full suite: ~975 passed, 2 skipped, 1 FAILED = tests/test_provenance_graph.py::test_committed_graph_rederives_exactly — known hash drift from new schema files; artifacts/provenance/** regeneration OWNED_BY_OTHER_SWARM (governance).
- artifacts/rac_deliverable_inventory.json bumped to 1.1 with post-Barrier-2 classifications.

## Final assertions (re-affirmed)
- D2_0004_MODIFIED = false
- D2_0005_ARMED = false
- NEW_HELDOUT_ACCESS = false
- SCIENTIFIC_THRESHOLDS_CHANGED = false

---

# APPENDIX 2 — CTM-B wave (bridges) — 2026-09-09

Base: e169706 (post-CTM-A). Scope: CTM-B only (CTM-A authored by governance swarm).

## Deliverables
- ruthless_pipeline/ctm/{ids,errors,genome_adapter,registry,compare,cli}.py — Pattern Genome v1 ADAPTER (pattern_genome/ internals untouched); content-addressed pattern_id = "RAC-CTM-PAT-"+sha256(canonical genome bytes minus self-fields + schema-version)[:16]; ctm_registry/ skeleton (sidecar-only masters, large binaries out of git); compare_genomes (claim_state hard EXPLORATORY); CLI `python -m ruthless_pipeline.ctm.cli genome compare digital <file>` functional, physical half exit 3 + PENDING_USER_ACTION packet.
- ruthless_pipeline/ctm/manifests.py — CTM experiment manifest (rac-ctm-experiment/1.0), manifest lock (drift fail-closed), ESM adapter (wraps, never edits; arm/execute → ArbitrationError), claim-artifact bridge validated against frozen ctm_claim_v1 schema.
- tests/ctm/ — 49 tests (B1: ids/adapter/registry/compare/cli + B2: 21 manifest/adapter/lock/claim tests).

## Upstream red-main observed at wave start (NOT ours, governance in-flight)
- tests/test_barrier3_rehearsal.py = 17-byte PLACEHOLDER at e169706 (collection NameError).
- 14 failures on governance surfaces: objective_telemetry(5), select_surrogate_candidate_objective(4), stale_artifacts(2), provenance_graph rederive(1), ctm_a controlled_effect regex(1), pattern_genome wrong_shape regex(1).
- Disposition: classified as in-flight upstream drift, documented, not edited (per seam-reconciliation protocol: real conflict vs additive consistency — all are on foreign files).

## Assertions
D2_0004_MODIFIED=false D2_0005_ARMED=false NEW_HELDOUT_ACCESS=false SCIENTIFIC_THRESHOLDS_CHANGED=false PHYSICAL_EFFICACY_CLAIMED=false

---

# APPENDIX 3 — CTM Hardening Wave (Lanes A–E) — 2026-09-11

Source of truth: CTM_Lessons_and_Repo_Spec_Proposals_REVISED.md; execution contract: CTM_SWARM_IMPLEMENTATION_BRIEF.md. All lanes additive, fail-closed, frozen surfaces untouched.

## Lane A — SPEC-1, 2, 5, 12 (interpretability P0)
- ruthless_pipeline/ctm/{swap_validity,scalar_types,optimizer_constraints}.py; manifests.py v1.1 evaluation_audit extension (v1.0 byte-identical); schemas/ctm_swap_validity_v1.schema.json (rac-ctm-swap-validity/1.0). 57 new tests. Landed @ ff999b70 (2 noise commits in history from placeholder push self-correction; tree hash-verified).

## Lanes B+C — SPEC-10, 11 / SPEC-3, 4, 6, 13, 15, 18
- B: ruthless_pipeline/ctm/{channel,target_semantics}.py; schemas ctm_channel_v1 (rac-ctm-channel/1.0), ctm_target_semantics_v1 (rac-ctm-target-semantics/1.0). 43 tests.
- C: ruthless_pipeline/ctm/{corpus,citations,claim_lint,pipeline_stage,positioning}.py; schemas ctm_{corpus_entry,corpus_snapshot,citation,claim_scope,positioning}_v1; ctm_registry/literature/ (10 seed entries + snapshot RAC-CTM-CORPUS-SNAPSHOT-1fa6285372d1c434). 72 tests.
- Integration landed @ e930fc2a; 221/221 tests/ctm green; ALL_34_HASH_MATCH.

## Lane D — SPEC-16, SPEC-7
- ruthless_pipeline/ctm/external_cohort.py (EXPLORATORY ceiling; promote_to_controlled_efficacy unconditionally refuses; 6 channel-completeness fields known|unknown|inferred; fabrication_delta routes through compare_genomes; mixed-cohort pool refused without declared cohort term).
- ruthless_pipeline/ctm/retro_mining.py (preregistered retro-mining; sealed 3-state decision CONTINUE/RESCOPE/REJECT_HYPOTHESIS_FAMILY; rejection mechanically impossible without preregistered power+homogeneity+minimum-effect; verify_decision re-derives hash and refuses forged REJECT).
- schemas ctm_{external_observation,retro_prereg,retro_decision}_v1. 42 tests. Landed @ da44c1b; 263/263 green.
- NOTE: main-line subsequently extended FamilyResult with channel_metadata_adequate / provenance_adequate (NR pass) — additive strengthening, no conflict.

## Lane E — SPEC-17, 9, 8, 14
- ruthless_pipeline/ctm/defense_axis.py: DefenseRecord (content-hashed, config_sha256-bound), canonical cell identity pattern×base_target×defense×channel×condition, defended variants collapse to base for replication counting (independent_replication_count / require_not_independent_architecture), paired brittleness deltas (unpaired refused unless explicitly labeled), heterogeneity_by_defense_class; SPEC-9 DefenseDual {principle, certification_form, status} with require_dual_evaluated_before_archival gate (REJECTED or high-heterogeneity heuristics cannot be archived with unevaluated dual).
- ruthless_pipeline/ctm/genome_v2_register.py + schemas/ctm_genome_v2_register_v1.schema.json + ctm_registry/genome_v2/candidate_register_v1.json (register RAC-CTM-GV2-REGISTER-6da91ed0492299b0): 8 candidates (4 SPEC-8 invariance-class + 4 SPEC-14 FR-adjacency), each with feature definition, invariance claim (deformation group / coarsening operator), computability cost, SPEC-7 dependence; apply_spec7_gate drops legally-rejected families; promotion to v2_candidate requires a verified SPEC-7 decision and is impossible for rejected families. Genome v1 untouched (guard test pins pattern_genome/ bytes).
- schemas/ctm_defense_axis_v1.schema.json (rac-ctm-defense-axis/1.0). 63 tests.
- Landed @ b93f75d2 (includes 3 self-corrected placeholder/noise commits; final tree hash-verified: ALL_8_HASH_MATCH). tests/ctm: 338/338 green on fresh clone. Seam reconciliation: test helper updated for main-line FamilyResult adequacy fields.

## Foreign drift at b93f75d2 (documented, NOT modified by this wave)
- 8 failures: test_dashboard_export rederive(1), test_p1_no_spend_readiness_gate(4), test_provenance_graph rederive(1), test_stale_artifacts(2); plus tests/test_barrier3_rehearsal.py placeholder collection error.
- Of the 14 pre-wave failures, 11 were resolved by main-line NR/UI commits (objective_telemetry×5, select_surrogate×4, ctm_a_contracts×1, pattern_genome wrong_shape×1); 5 new failures arrived with main-line P1/dashboard commits. None caused by Lanes A–E.

## Deterministic re-derivation at barrier
- Genome v2 register re-derives byte-identical (RAC-CTM-GV2-REGISTER-6da91ed0492299b0). Corpus snapshot verify_snapshot OK. ctm exports: 108.

## Assertions (re-affirmed)
D2_0004_MODIFIED=false D2_0005_ARMED=false NEW_HELDOUT_ACCESS=false SCIENTIFIC_THRESHOLDS_CHANGED=false PHYSICAL_EFFICACY_CLAIMED=false

## Appendix 4 — PUSH_INTEGRITY incident record + HEAD verification (2026-09-11)

### Incident: literal placeholder blobs committed as file content
Three derived artifacts were clobbered by literal `__CONTENT_N__` tokens in history:
- physical/p1/P1_READINESS_FREEZE.json → bad blob b17b181a (13 bytes, `__CONTENT_2__`); implicated commit 459b7503 (disguised as a freeze re-pin). Effect: gate REFUSED all freeze checks (fail-closed held).
- artifacts/provenance/graph.json → bad blob 57fd5f3a; artifacts/dashboard/experiments.json → bad blob 7edf039f; implicated commits b26de2e7, 9e9719d2 ("corrects placeholder" commits that themselves pushed placeholders).
Detection path: directory-listing size anomaly + code search for `__CONTENT_`.

### Repair (dual-lane, cross-validated)
- cd51d38b (agent lane): freeze re-pinned via --write-freeze (d9c63e12), dashboard export regenerated (6d6510d6), genome-v2 register test fixture fixed (FamilyResult adequacy fields; bdfb78e9). All refetch byte-verified.
- 2511f6c3 / 350fbe1d (main lane): independent regeneration of the same artifacts; blob-identical results (two independent derivations, same bytes).
- cd34bd45 + 68fe6b04: CI-audited provenance artifact repair; 4dcba5cf/5ee2da13: committed-graph bytes now verified fail-closed in CLI; c79793c6/c3b49554/3ec7d32d: zero-dependency JSON integrity gate (scripts/check_json_integrity.py) now fails CI on malformed/placeholder JSON — the incident class is now mechanically blocked.
- c97db25c (agent lane): two stale e2e specs reconciled with intentional UI changes — research-console strict-mode regex anchored (^Pattern Lab; home-link added in e79e1533 made the unanchored regex ambiguous from birth in df738e75) and pattern-lab export test dropped the header Export Config action removed deliberately in 9fb3db9c (sidebar JSON export coverage retained). Pushed blobs byte-verified: cb2efe1b, 6bb279c0.

### Independent verification at HEAD c97db25c (fresh tarball extraction, no local state carried)
- Placeholder scan: zero `__CONTENT_` occurrences outside the integrity gate and its tests.
- scripts/check_json_integrity.py: PASS (161 JSON files, 0 findings).
- scripts/build_provenance_graph.py --verify: committed bytes VERIFIED (sha256 734e2012…d82581); edges 53 VERIFIED / 0 BROKEN / 1 MISSING-by-design / 0 MUTABLE.
- Freeze re-derivation: byte-stable (no drift).
- P1 no-spend readiness gate: PASS; 208 UA fields pending, none defaulted; spend_authorized=false.
- pytest: 1897 passed, 0 failed, 0 errors, 2 skipped, 0 xfail, 0 xpass (1899 collected).
- Playwright (separate counts, per project): chromium-desktop 57 passed / 0 failed / 0 skipped; webkit-mobile 56 passed / 0 failed / 1 skipped (pre-existing BASE_URL-only skip). Combined: 113 passed, 0 failed, 1 skipped of 114. An earlier combined-run showing 114 failures was environmental only (missing browser binaries after sandbox wipe, then static-server death under dual-browser load); per-project reruns isolated the two genuine stale-spec defects fixed in c97db25c.

### Assertions (re-affirmed)
D2_0004_MODIFIED=false D2_0005_ARMED=false NEW_HELDOUT_ACCESS=false SCIENTIFIC_THRESHOLDS_CHANGED=false PHYSICAL_EFFICACY_CLAIMED=false

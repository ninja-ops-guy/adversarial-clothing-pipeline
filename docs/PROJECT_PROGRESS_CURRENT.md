# RAC Current Project Progress Ledger

**Version:** 1.3.0  
**Last updated:** 2026-09-10 America/New_York (2026-09-11 UTC)  
**Verified governance baseline:** `7ff05187b223d7479a934bb6912799bb943e57f2` — CI run #836 (`34517061829`) PASS.  
**Authority:** detailed current-state overlay for RAC/CTM. For the fastest program-level status and barrier map, start with [`CURRENT_PROGRAM_STATE.md`](CURRENT_PROGRAM_STATE.md). `PROJECT_PROGRESS.md` remains the historical Sep. 8 ledger and is not rewritten retroactively.

> Engineering completion is not efficacy evidence. Software, schemas, simulations, governance, CI, and no-spend readiness can be complete while RAC-P physical evidence, RAC-M manufacturing evidence, or a product-efficacy claim remain unavailable.

## Executive state

RAC is a research and experimental-governance platform spanning design generation, controlled evaluation, provenance, claim certification, production preparation, and a gated physical program.

**Engineering Barriers 0–3 are closed for their declared scope.** Barrier 3 has an independent RAC-G verdict of `PASS_WITH_NONBLOCKING_GAPS`; its sole declared deferred check is finite-difference verification, applicable only when a gradient-backed generation is actually audited. The current program bottleneck is no longer system composition. It is the transition from verified software/readiness machinery to real vendor-bound inputs and measured physical evidence.

The September 10 CTM integration/hardening cycle is software-integrated and CI-green. Governance Passes 1 and 2 are **CLOSED / PASS** against the adopted Governance v1 contract. That does **not** advance the physical-evidence ladder.

## Canonical barrier ledger

| Barrier | Current state | What closed it | Remaining program implication |
| --- | --- | --- | --- |
| **Barrier 0 — Inventory** | **CLOSED / DONE** | World-class gap analysis, roadmap, acceptance matrix, handoff and inventory JSON | Historical baseline only |
| **Barrier 1 — Schema/interface freeze** | **CLOSED / PASS** | 7 frozen contracts, evidence-class registry, 69 tests; RAC-G negative-case verification 21/21 | Downstream code must honor frozen interfaces rather than redefine them |
| **Barrier 2 — Parallel subsystem implementation** | **CLOSED FOR DECLARED SOFTWARE SCOPE / INTEGRATED** | RAC-A/B/C/D/E subsystem deliveries plus later CTM integration/hardening | Physical/vendor inputs still gate measured promotion; research extensions may continue additively |
| **Barrier 3 — End-to-end integration** | **CLOSED — PASS_WITH_NONBLOCKING_GAPS** | Deterministic six-stage integration, fail-closed injection testing, completion handoff, independent RAC-G audit | Deferred finite-difference audit only if a gradient-backed path enters scope |

Authoritative details: `RAC_PARALLEL_SWARM_HANDOFF.md`, `BARRIER_3_COMPLETION_HANDOFF.md`, and `audits/RAC_G_BARRIER_3_AUDIT.md`.

## Current completion snapshot

| Workstream | Current state | Meaning |
| --- | --- | --- |
| Core research software | **ADVANCED / INTEGRATED** | Design, optimization, evaluation, reporting, provenance and certification primitives are present |
| Engineering Barriers 0–3 | **CLOSED FOR DECLARED SCOPE** | Inventory, interface freeze, subsystem implementation and synthetic end-to-end integration have all crossed their documented exits |
| CTM contracts / governance | **INTEGRATED** | CTM contract surfaces, matched-null logic, anti-optimization controls, channel/claim semantics and research-integrity layers are implemented and reconciled |
| CTM B–D integration audit | **PASS** | Semantic mismatches found during audit were corrected; the historical Barrier-3 blocker is resolved and retained only as provenance |
| Governance Pass 1 | **CLOSED / PASS** | Adopted IDs, append-only ledger, ledger-backed state transitions, structured HALT, schemas and semantic validation are CI-verified |
| Governance Pass 2 | **CLOSED / PASS** | Immutable constraint lineage, three-axis impact analysis, preregistered tolerance policy, migration decisions/logging and frozen-D2 protection are CI-verified |
| Governance Passes 3–7 | **AUDIT-GATED** | Later-pass modules may already exist, but code presence is not pass certification until each adopted-contract exit gate is independently closed |
| Provenance graph | **CURRENT / VERIFIED** | Deterministic graph is committed and independently verifiable; regeneration no longer requires the ML runtime |
| Repository CI | **GREEN at Pass-2 verification baseline** | Run #836 passed Python 3.10/3.11/3.12, package build, dependency audit and lightweight provenance |
| Pattern Genome v1 | **FROZEN** | v1 remains unchanged; later Genome work must be additive/versioned |
| D2-0004 | **CLOSED — NEGATIVE / RAC-D0** | Historical retained result remains immutable and log-attested |
| D2-0005 | **PREREGISTERED / NOT ARMED** | No arming occurred during CTM/governance/P1-readiness work |
| Production Alpha software | **SOFTWARE-READY / EXTERNAL INPUTS REMAIN** | Print/vendor manifests, readiness machinery and fail-closed binding path exist; real vendor values and human spend authorization remain external |
| P1 no-spend readiness | **CLOSED / PASS** | Frozen pairing/randomization, 144-trial schedule, operator runbook, readiness freeze/gate and deterministic rehearsal are in place |
| P1 UA binding | **READY / REAL VALUES UNBOUND** | `RAC-P1-UA-BINDER-001` can atomically bind the 208 pending fields once UA-1–UA-8 are known; `6b36dfe5` is the machinery-complete/unbound checkpoint |
| P1 physical evidence | **OPEN — NOT EXECUTED** | Software readiness is complete; matched physical testing has not yet produced RAC-P evidence |
| P2 durability evidence | **OPEN — EXTERNAL** | Requires real durability/wash evidence after a valid physical baseline |
| M1/M2 manufacturing evidence | **OPEN — EXTERNAL** | Requires golden-sample and lot-conformity measurements |
| Product efficacy claim | **NOT SUPPORTED** | Claims must remain scoped to evidence actually obtained |

## P1 authority and the 108 → 144 reconciliation

Earlier Print Alpha planning material used a **108-row trial sheet**. That planning artifact is no longer the P1 execution authority.

The frozen P1 readiness package now controls execution:

- `physical/p1/P1_CAPTURE_SCHEDULE.json` — **144 frozen trials**, derived deterministically from the pairing/randomization seed and pinned by `schedule_sha256`.
- `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json` — pairing/randomization authority.
- `physical/p1/P1_OPERATOR_RUNBOOK.md` — specimen-arrival through sealed-evidence procedure.
- `physical/p1/P1_READINESS_FREEZE.json` — pinned readiness surface.
- `tools/p1_no_spend_readiness_gate.py` — fail-closed verifier.
- `tools/p1_bind_ua_values.py` — atomic pending→real-value binder; it does not authorize spend.

Any older document that mentions executing 108 rows is subordinate to these frozen P1 surfaces and should be read as historical planning context only.

## P1 no-spend readiness and Friday transition

The no-spend readiness handoff is `docs/handoffs/P1_NO_SPEND_HANDOFF.md`.

Current state:

- 11/11 readiness checks PASS.
- 208 unresolved fields remain across 6 manifests; all remain explicit pending markers until real values exist.
- Pairing/randomization and the 144-trial schedule are frozen and reproducible.
- The operator runbook covers specimen arrival → calibration → capture → stopping-rule evaluation → validated ingestion → sealed packaging without improvisation.
- `RAC-P1-UA-BINDER-001` provides the audited transition from pending fields to bound real-world values.
- Successful binding and gate PASS do **not** authorize spend; the spend decision remains human-only.

The Friday playbook is therefore:

`Verified UA-1–UA-8 values → binder --check-only → require exactly 208 planned bindings → atomic bind + receipt → readiness gate PASS → verify scientific boundaries → separate human spend authorization → procurement → receipt QA → calibration acceptance → frozen 144-trial P1 execution → sealed evidence`

## September 10 CTM hardening closure

### Completed and mechanically enforced

- [x] CTM matched-property null contracts remain fail-closed.
- [x] Anti-optimization / held-out provenance firewall remains enforced.
- [x] Factor-swap validity semantics are represented explicitly.
- [x] Scalar values have typed epistemic/analysis semantics rather than implicit coercion.
- [x] Optimizer-imposed structure is kept in generation provenance rather than mutating Pattern Genome v1.
- [x] Camera / ISP / channel identity is a first-class validity dimension.
- [x] Target/mechanism semantics distinguish architecture accidents from broader mechanism classes.
- [x] Evaluation-surface / Goodhart-relevant configuration is part of experiment semantics.
- [x] Claim scope is structurally tied to pipeline stage rather than relying only on prose linting.
- [x] Citation/corpus/positioning infrastructure supports bounded literature claims and verification status.
- [x] Retrospective mining decisions are metadata/provenance-aware and sealed decisions are re-derived during verification.
- [x] External physical cohorts remain secondary evidence and cannot silently promote into controlled CTM physical efficacy.
- [x] CTM B–D integration audit is closed as PASS in `CTM_BD_INTEGRATION_AUDIT_2026-09-10.md`.

### Explicitly deferred

- [ ] Pattern Genome v2 candidate expansion — **deferred until its evidence gate justifies promotion**.
- [ ] `defense_dual` heuristic lifecycle — **deferred until the CTM-F heuristic-promotion lifecycle is active**.

These deferred items are not current integration blockers.

## Governance Pass 1 closure

Governance Pass 1 is formally closed in `experimental_governance/PASS1_CLOSURE_2026-09-10.md`.

The closure corrected prototype/adopted-contract drift without rewriting historical prototype records:

- [x] new IDs emit canonical Governance v1 forms such as `RAC-GOV-EVT-*`, `RAC-COHORT-*`, `RAC-SAMP-*`, `RAC-CS-*`, `RAC-OVERLAP-*` and `RAC-DIAG-*`;
- [x] legacy abbreviated IDs remain read-compatible aliases but map to the same semantic identity;
- [x] event payloads and event metadata are separately SHA-256 bound and previous-event chained;
- [x] reversal/supersession semantics are append-only;
- [x] lifecycle state is read-only outside the governance state machine;
- [x] every legal transition writes a governance event before changing state;
- [x] generic HALT bypass is unavailable; HALT requires a structured invariant-conflict event;
- [x] canonical identifiers are accepted consistently by Python semantic validation and JSON Schema;
- [x] adopted-contract tests cover happy-path completion, structured HALT, tamper detection, alias collision, invalid references and anti-bypass behavior.

A Pass-6 sampling/diagnostics merge landed during this hardening cycle and was preserved. CI #821 therefore verified the Pass-1 closure together with that merged sampling layer. Pass 6 itself remains roadmap-open until a pass-specific audit verifies all of its adopted exit criteria.

## Governance Pass 2 closure

Governance Pass 2 is formally closed in `experimental_governance/PASS2_CLOSURE_2026-09-10.md`.

The closure hardened the pre-existing constraint prototype into the adopted scientific-lineage contract:

- [x] `ConstraintSetRegistry` provides immutable parent-first registration and canonical alias collision protection;
- [x] prospective records carry explicit encoder version separately from software version and scientific impact;
- [x] `MigrationImpactAnalysis` requires population displacement, historical cohort impact, and estimand impact as separate axes;
- [x] `TolerancePolicy` is constraint-family-specific, preregistered-before-outcomes, schema-valid and SHA-256 bound into the decision;
- [x] migration outputs are formal `NO_IMPACT`, `MINOR_CORRECTION`, `BRIDGE_REQUIRED`, `COHORT_INVALIDATION`, or `NEW_REGIME` decisions;
- [x] semantic definition or estimand change forces `NEW_REGIME` regardless of permissive numerical tolerance;
- [x] patch-level software version changes cannot hide scientific population change;
- [x] `CONSTRAINT_MIGRATION` events log the complete decision append-only;
- [x] protected D2 snapshots must remain complete and hash-identical before migration logging can append;
- [x] the predecessor constraint artifact remains unchanged in the exit-gate fixture.

CI #836 verified this state on Python 3.10/3.11/3.12. The Python 3.11 lane reported **1,653 passed, 2 skipped, 16 warnings**, followed by **12/12 certification tests passed**, passing smoke test, and Ruff clean.

Independent Printful vendor-snapshot P0 commits landed after the Pass-2 verification commit. They are descendants of the verified governance state and do not alter the Pass-2 governance files covered by the closure.

## noRecognition research-integration status

The older roadmap wording that marked the whole runtime audit as pending is stale.

- [x] **NR-01:** evaluation-exposure ledger, independent-confirmation gate and feature-provenance review landed with acceptance tests/audit.
- [x] **NR-02/03:** observation-medium registry and physical/control reconciliation audit landed additively.
- [x] **NR-04/05:** stage-outcome integrity and one-snapshot report-consistency controls landed with acceptance tests/audit.
- [ ] **NR-06 / predictor provenance:** remains prospective until a concrete study and its evidence/exit criteria justify implementation or closure.

These controls improve evidence integrity; they do not create a new efficacy result.

## CI / reproducibility state

### Authoritative governance verification

GitHub Actions CI run #836 at `7ff05187b223d7479a934bb6912799bb943e57f2` completed successfully across all six jobs:

- Python 3.10 — PASS
- Python 3.11 — PASS
- Python 3.12 — PASS
- package build — PASS
- dependency audit — PASS
- lightweight provenance — PASS

The Python 3.11 repository-wide run reported **1,653 passed, 2 skipped, 16 warnings**, followed by **12/12 certification-contract tests passed** and a passing smoke test. Ruff passed.

Subsequent CI hardening adds earlier JSON/integrity refusal and makes dependency/integrity checks blocking before heavier jobs. Those later infrastructure commits do not alter the scientific state summarized here.

### Infrastructure hardening completed

- [x] Top-level `ruthless_pipeline` convenience exports are lazy-loaded while preserving the existing public API.
- [x] Provenance generation/verification can run from the repository source tree without installing Torch, torchvision, NumPy, SciPy or Pillow.
- [x] CI has a zero-install provenance/import-boundary gate.
- [x] Regression tests prevent accidental eager reintroduction of the ML dependency stack at package import time.
- [x] Hosted CPU CI installs CPU-only PyTorch wheels and asserts `torch.version.cuda is None` rather than downloading the CUDA runtime stack.
- [x] Full package requirements remain unchanged by the CI optimization.

## Scientific invariants preserved during hardening/readiness work

The barrier, CTM, governance and P1-readiness work described here did **not**:

- modify Pattern Genome v1;
- arm D2-0005;
- introduce new held-out access;
- alter scientific efficacy thresholds or decision-rule values;
- convert exploratory evidence into controlled evidence;
- execute P1 physical work;
- create RAC-P or RAC-M evidence;
- make a physical-efficacy claim.

## Immediate next work

### Software / research work that can proceed without physical evidence

- [ ] Audit Governance Pass 3 against its adopted seal/reproducibility contract and close only requirements demonstrated by code/tests.
- [ ] Continue the same pass-by-pass audit for Passes 4–6; do not infer completion from namespace presence.
- [ ] Keep Pass 7 adaptive/chaos lifecycle deferred until multiple sealed waves or an actual experimental need justify it.
- [ ] Keep manuscript/corpus exports synchronized with integrated CTM schemas and bounded-claim rules.
- [ ] Continue prospective evidence collection through preregistered research questions rather than generic feature accumulation.
- [ ] Keep Genome v2 and heuristic-promotion work behind their declared gates rather than expanding representation prematurely.

### External / physical critical path

This is now the primary program bottleneck:

- [ ] Obtain and independently verify all real UA-1–UA-8 vendor/operator inputs.
- [ ] Populate a copy of `physical/p1/UA_VALUES_TEMPLATE.json`.
- [ ] Run `tools/p1_bind_ua_values.py --check-only`; require exactly 208 planned bindings, zero writes and no refusal.
- [ ] Execute the atomic bind only after the dry-run is clean; preserve its receipt and resulting readiness-freeze hash.
- [ ] Re-run the no-spend readiness gate and require PASS with scientific-boundary assertions unchanged.
- [ ] Make the separate human spend-authorization decision.
- [ ] Order/receive matched control and candidate garments plus required calibration material.
- [ ] Perform receipt QA and specimen reconciliation against the bound manifests.
- [ ] Execute the frozen **144-trial** P1 schedule from `P1_OPERATOR_RUNBOOK.md`.
- [ ] Ingest and seal measured physical evidence before analysis or claim promotion.
- [ ] Begin P2 durability/wash cohorts only after a valid W0 physical artifact exists.
- [ ] Establish M1 golden-sample and M2 lot-conformity evidence before manufacturing claims.

## Operating rule

**Prioritize closed evidence loops over new feature count.**

The software platform is sufficiently elaborate that additional infrastructure should now be justified by a concrete validity, reproducibility, measurement, or publication need. Physical efficacy remains unproven until the physical evidence ladder is actually executed.

## Historical record

For the detailed pre-CTM milestone history, D2-0004 closure chronology, Product Studio status, production compiler milestones, and Sep. 7–8 change log, see [`PROJECT_PROGRESS.md`](PROJECT_PROGRESS.md). For the canonical current program map, use [`CURRENT_PROGRAM_STATE.md`](CURRENT_PROGRAM_STATE.md). Historical planning documents remain valuable provenance but do not outrank frozen execution contracts or closure handoffs.

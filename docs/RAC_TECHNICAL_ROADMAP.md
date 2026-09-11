# RAC Technical Roadmap

**Swarm:** RAC Parallel Expansion Swarm  
**Original basis:** `RAC_WORLD_CLASS_GAP_ANALYSIS.md` @ HEAD `b50f6b0` (2026-09-09)  
**Current status overlay:** 2026-09-10 America/New_York (2026-09-11 UTC)  
**Canonical current program state:** [`CURRENT_PROGRAM_STATE.md`](CURRENT_PROGRAM_STATE.md)

This document began as the dependency-ordered implementation plan produced at Barrier 0. It is now maintained as a **historical roadmap plus forward plan**. Completed items remain here so the original intent can be compared with what actually landed; they are not rewritten as if they were still future work.

> Frozen contracts, barrier handoffs, independent audits, and the frozen P1 readiness package outrank this roadmap if wording conflicts.

---

## Program status summary

| Program unit | Current status | Notes |
| --- | --- | --- |
| Barrier 0 — Inventory | **CLOSED / DONE** | Original gap analysis and dependency map complete |
| Barrier 1 — Schema/interface freeze | **CLOSED / PASS** | 7 contracts + evidence-class registry; contract and independent negative-case verification complete |
| Barrier 2 — Parallel subsystem implementation | **CLOSED FOR DECLARED SOFTWARE SCOPE / INTEGRATED** | RAC-A/B/C/D/E implementation landed; later CTM hardening strengthened the interfaces |
| Barrier 3 — End-to-end integration | **CLOSED — PASS_WITH_NONBLOCKING_GAPS** | Six-stage deterministic integration + RAC-G audit; finite-difference check conditional on future gradient-backed path |
| P1 no-spend readiness | **CLOSED / PASS** | Frozen 144-trial execution package, rehearsal, readiness gate and operator runbook |
| UA binding | **READY / REAL VALUES UNBOUND** | `RAC-P1-UA-BINDER-001`; 208 fields await real UA-1–UA-8 values |
| Physical evidence | **OPEN** | Real vendor/garment/calibration/capture evidence remains the critical path |

---

## Barrier 0 — Inventory

**Status: CLOSED / DONE.**

Original deliverables:

- [x] World-class inventory vs charter.
- [x] Gap analysis.
- [x] Acceptance matrix.
- [x] Machine-readable inventory JSON.
- [x] Swarm handoff and dependency order.

Exit evidence: `RAC_WORLD_CLASS_GAP_ANALYSIS.md`, `RAC_WORLD_CLASS_ACCEPTANCE_MATRIX.md`, `RAC_PARALLEL_SWARM_HANDOFF.md`, and `artifacts/rac_deliverable_inventory.json`.

## Barrier 1 — Schema/interface freeze

**Status: CLOSED / PASS.**

Delivered:

1. [x] `schemas/physical_transfer_record.schema.json` — physical-transfer hash/evidence fields.
2. [x] `schemas/transformation_distribution.schema.json` — distribution identity, parameters, seed/sample semantics.
3. [x] `schemas/detector_response.schema.json` — detector-response contract.
4. [x] `schemas/optimization_objective.schema.json` — composable objective terms and aggregation semantics.
5. [x] `schemas/print_alpha_manifest.schema.json` — Print Alpha evidence boundary with `physical_efficacy_claimed=false`.
6. [x] additive `experimental_print_specimen` evidence taxonomy surface.
7. [x] RAC-R3 consolidated-manifest contract.

Closure record: Barrier 1 landed at `bb3dad5` with 69 contract tests; independent RAC-G negative-case verification reported 21/21 PASS in the swarm handoff.

## Original Wave 2 — P0 Print Alpha / RAC-A

**Current status: SOFTWARE-READY; EXTERNAL INPUTS / HUMAN AUTHORIZATION REMAIN.**

Original plan and current disposition:

1. [x] `print-alpha/` charter tree: CONTROL/, CANDIDATE/, CALIBRATION/, MANIFESTS/, CAPTURE/, QA/.
2. [x] capture/lighting/invalid-condition documents and deterministic planning exports.
3. [x] garment-pairing and chain-of-custody QA surfaces.
4. [x] Print Alpha manifests with unresolved real-world values kept fail-closed rather than fabricated.
5. [x] consolidated UA packet.
6. [x] P1 no-spend readiness layer subsequently froze pairing/randomization, a 144-trial schedule, operator runbook, readiness freeze and deterministic gate.
7. [x] UA binder subsequently added an atomic path for binding the 208 pending values once UA-1–UA-8 are real.
8. [ ] Obtain real vendor/operator values and perform the external production transition.

**Important update:** the old 108-row Print Alpha trial sheet is planning history. P1 execution now follows `physical/p1/P1_CAPTURE_SCHEDULE.json` and `physical/p1/P1_OPERATOR_RUNBOOK.md`, which define the frozen **144-trial** workflow.

## Original Wave 3 — Optimization + EOT + Detector Science + Pareto/Style (RAC-B/C/D)

**Current status: IMPLEMENTED / INTEGRATED for the declared software scope.**

Delivered and later hardened:

1. [x] `ruthless_pipeline/optimization/` objective/optimizer/backends/trajectory/constraint/Pareto stack with deterministic behavior, refusal semantics, checkpoint integrity and finite-pool baseline parity.
2. [x] `ruthless_pipeline/transformations/` reproducible transformation-distribution and robustness-surface infrastructure.
3. [x] `ruthless_pipeline/detector_science/` response/family/transfer/LOFO/concentration infrastructure.
4. [x] Pareto candidate classes across detector/transfer/robustness/printability/style dimensions.
5. [x] deterministic style-scoring/Pareto infrastructure without promoting style score to efficacy evidence.
6. [x] CTM hardening added factor-swap validity, scalar epistemic typing, optimizer-constraint provenance, channel/target semantics, citations/claim scope, retrospective mining, external-cohort handling and defense-axis controls.

This software completion does not imply a physical result.

## Original Wave 4 — Physical-transfer stack / RAC-E

**Current status: SOFTWARE IMPLEMENTED; MEASURED PHYSICAL PROMOTION OPEN.**

Delivered:

1. [x] deformation tiers T0–T3 behind a common interface; higher-fidelity tiers remain evidence-gated where calibration is absent.
2. [x] printability-loss infrastructure with versioned vendor/production profile semantics.
3. [x] physical-transfer record emission/validation tooling with synthetic records explicitly labeled synthetic.
4. [x] calibration/channel feedback scaffolding and measured-evidence refusal rules.
5. [ ] ingest real calibrated physical observations and validate the digital→print→fabric→camera channel empirically.

Measured promotion is gated by the physical program, not by additional synthetic implementation.

## Original Wave 5 — Science tooling / RAC-F

**Current status: PARTIAL / ACTIVE RESEARCH TOOLING.**

Original goals:

1. Ablation/experiment registry covering the declared comparison families without granting held-out execution authority.
2. Mechanism-analysis metrics and competing-hypotheses tooling.

Substantial governance, CTM, reporting, evidence-view and experimental-integrity infrastructure now exists around these goals, but this roadmap does **not** declare the entire science-tooling research program closed merely because modules exist. Pass-specific and research-question-specific exit evidence still controls completion.

## Original Wave 6 — RAC-R3 consolidation + independent verification / RAC-G

**Current status: BARRIER-3 SYNTHETIC INTEGRATION VERIFICATION COMPLETE; FUTURE MEASURED-RELEASE VERIFICATION REMAINS EVIDENCE-DEPENDENT.**

Completed:

1. [x] Barrier 3 consolidated integration package with manifests, hashes, seeds, telemetry, provenance and replay artifacts.
2. [x] RAC-G independent audit of the Barrier 3 package.
3. [x] independent checks for aggregation, Pareto front, EOT reproduction, replay, provenance attacks, tamper detection, fabrication guard and promotion attacks.
4. [x] Barrier 3 verdict: `PASS_WITH_NONBLOCKING_GAPS`.
5. [ ] finite-difference verification only if a gradient-backed generation becomes part of the audited path.
6. [ ] future measured RAC-R3 release verification when real physical evidence exists; the synthetic Barrier-3 audit does not pre-certify future measured releases.

## Current physical critical path

The program is now constrained more by evidence acquisition than by software construction:

1. Obtain and independently verify all real UA-1–UA-8 values.
2. Populate a copy of `physical/p1/UA_VALUES_TEMPLATE.json`.
3. Run `tools/p1_bind_ua_values.py --check-only`; require exactly 208 planned bindings and zero writes/refusals.
4. Perform the atomic bind and retain its hash-bound receipt.
5. Re-run `tools/p1_no_spend_readiness_gate.py`; require PASS and unchanged scientific boundaries.
6. Make the separate human spend-authorization decision.
7. Produce/order the matched physical specimens and calibration material.
8. Perform arrival reconciliation and receipt QA.
9. Accept session calibration under the frozen limits.
10. Execute the frozen **144-trial** P1 schedule from `physical/p1/P1_OPERATOR_RUNBOOK.md`.
11. Validate ingestion, seal the evidence, then run preregistered analysis.
12. Only after a valid physical baseline: proceed to P2 durability and M1/M2 manufacturing evidence.

## Governance dependency notes

- Engineering Barriers 0–3 being closed does **not** authorize D2-0005.
- D2-0005 remains preregistered / not armed unless its own governance surface changes through the authorized process.
- Pattern Genome v1 remains frozen; successor representation work is additive/versioned and evidence-gated.
- Physical-efficacy claims remain unsupported until the physical evidence ladder is actually closed.
- Software work may proceed independently only where it does not cross held-out, frozen-threshold, or measured-evidence boundaries.

## External research integration — noRecognition

**Current status: review complete; NR-01 through NR-05 confirmed-gap work substantially implemented; NR-06 remains prospective.**

- [x] **NR-01:** evaluation-exposure provenance, independent-confirmation gate and feature-provenance review.
- [x] **NR-02/03:** observation-medium labeling and physical/control-estimand reconciliation.
- [x] **NR-04/05:** stage-outcome integrity and one-snapshot report consistency.
- [ ] **NR-06:** predictor provenance / prospective evaluation requirements when a concrete study is proposed; close only with explicit evidence and acceptance criteria.

These controls improve research integrity; they do not certify physical performance.

### Capability research following reported winners

**Status: static capability comparison complete; research decisions remain evidence-dependent.**

- [ ] Map generation/optimization components to retained measured results once sufficient measured results exist.
- [ ] Verify that any future experimental fixture represents the wearer/garment context required by the question being asked.
- [ ] Assess retrospective predictive signal and data sufficiency before selecting a learned representation.
- [ ] Treat context-aware prediction, learned generation and recipe-sequence representations as separate research hypotheses rather than assumed upgrades.
- [ ] Record explicit decisions and rejection criteria for each hypothesis.

## Roadmap rule

**Prioritize closed evidence loops over additional feature count.**

The next program-defining milestone is not another software barrier. It is a valid, provenance-preserving transition from vendor-bound physical specimens to measured P1 evidence under the frozen protocol.

# RAC Experimental Governance Roadmap

**Planning horizon:** coming weeks from 2026-09-10  
**Strategy:** preserve focus on the existing physical/production critical path; build governance in thin, testable increments around it.  
**Source spec:** `RAC_EXPERIMENTAL_GOVERNANCE_V1.md`  
**Detailed pass acceptance:** `IMPLEMENTATION_PASSES.md`

---

## Priority model

### P0 — Current RAC critical path: do first / do not block

These items already determine whether RAC advances from software-complete infrastructure toward physical evidence:

- [ ] obtain/authorize POD provider account/API access;
- [ ] fetch exact provider product/variant IDs;
- [ ] download and freeze the exact first-SKU vendor template;
- [ ] freeze Production Alpha artwork/template/mapping/SKU hashes;
- [ ] place matched control/candidate garment order;
- [ ] produce/order the physical calibration target through the same production path;
- [ ] finish P1 capture-rig setup/preregistration;
- [ ] execute W0/P1 physical work when garments arrive.

**Rule:** Governance v1 must not become an excuse to delay these external/physical tasks unless a specific experiment is about to be armed and would otherwise violate an existing evidence boundary.

---

## P1 — Governance foundation: highest software priority

### Week 1 — Pass 1: Governance Core

**Target:** 2026-09-10 through 2026-09-16  
**Effort posture:** thin foundation, no sampler research yet.

- [ ] typed immutable governance IDs;
- [ ] append-only hash-chained event ledger;
- [ ] reversal/supersession event support;
- [ ] governance state machine;
- [ ] `HALTED` invariant-conflict state;
- [ ] JSON schemas for manifests/events/constraint sets/overlap/diagnostics;
- [ ] semantic manifest validator;
- [ ] CI tests for Laws 1, 6, and 7.

**Exit:** synthetic experiment seals and completes; synthetic invariant conflict halts.

**Do not do yet:** d-DNNF, UniGen integration, treewidth routing, advanced sampler diagnostics.

---

### Week 2 — Pass 2: Constraint Lineage

**Target:** 2026-09-17 through 2026-09-23

- [ ] immutable constraint-set registry;
- [ ] parent/child lineage;
- [ ] semantic/rules/encoder hashes;
- [ ] software version separated from scientific-impact class;
- [ ] population/cohort/estimand impact model;
- [ ] preregistered tolerance-policy schema;
- [ ] migration decision classes;
- [ ] explicit read-only protection for existing frozen D2 artifacts.

**Exit:** synthetic bugfix migrates `CS-A -> CS-B` through an impact analysis without rewriting `CS-A`.

**Reason for priority:** this must exist before future constraint definitions start changing across waves.

---

### Week 3 — Pass 3: Seal + Reproducibility

**Target:** 2026-09-24 through 2026-09-30

- [ ] complete sampling/cohort manifest schema enforcement;
- [ ] referential integrity;
- [ ] source commit / seed / pipeline / calibration binding;
- [ ] artifact hash verification;
- [ ] deterministic seal identity;
- [ ] optional trusted-timestamp adapter interface;
- [ ] CTM precondition hook: unsealed cohort rejected.

**Exit:** complete synthetic cohort verifies from a clean checkout; missing/mutated artifacts fail closed.

**Milestone:** after Week 3, RAC has a useful governance foundation even without sophisticated sampling.

---

### Week 4 — Pass 4: Sentinel + Bridge + Overlap

**Target:** 2026-10-01 through 2026-10-07

- [ ] sentinel cohort definition/freeze;
- [ ] blind sentinel re-evaluation protocol;
- [ ] calibration isolation checks;
- [ ] old/new pipeline bridge;
- [ ] old/new constraint bridge cohort;
- [ ] support-overlap estimator;
- [ ] policy-overlap estimator;
- [ ] material-stratum rules;
- [ ] regime-reset decision logic;
- [ ] uncertainty/confidence interval persistence.

**Exit:** synthetic constraint migration produces sentinel + bridge + new cohort and a reproducible regime decision.

**Foundation milestone:** Passes 1-4 complete = `Governance Foundation Ready`.

At this point, stop and reassess whether current experiments actually need Passes 5-7 before doing more infrastructure work.

---

## P2 — CIC/formal-methods integration: build when foundation is stable

### Week 5 — Pass 5: CIC Adapter

**Suggested target:** 2026-10-08 through 2026-10-14, but only if P0 physical work is not consuming the available bandwidth.

- [ ] bounded `cic.check()` adapter;
- [ ] CNF/PB/SMT representation contracts;
- [ ] assignment verification;
- [ ] MUS/UNSAT-core integration;
- [ ] cross-solver verification mode;
- [ ] scientific projection enforcement;
- [ ] independent-support analysis restricted to semantic genome variables;
- [ ] structural metrics emitted for sampler routing;
- [ ] cross-encoding differential fixtures.

**Exit:** CIC verifies feasibility and returns routing telemetry without touching efficacy scoring.

**Defer:** research into SAT backdoor variables as predictors of transfer. That remains a side research question, not a RAC dependency.

---

## P2/P3 — Statistical sampling: high scientific value, lower immediate urgency than P0 physical closure

### Week 6 — Pass 6A: Sampler Interface + One Reliable Backend

**Suggested target:** 2026-10-15 through 2026-10-21

Do not implement all four backends at once.

- [ ] common target-distribution/sampler contract;
- [ ] scientific projection handling;
- [ ] one production-capable backend selected from current dependency/tool availability;
- [ ] exact small-fixture validation;
- [ ] sampler manifest output;
- [ ] basic coverage/duplicate/repeated-seed diagnostics.

**Exit:** RAC can construct an explicitly sampled cohort instead of taking arbitrary satisfying assignments.

---

### Week 7 — Pass 6B: Backend Routing + Diagnostics

**Suggested target:** 2026-10-22 through 2026-10-28

- [ ] exact/compiled backend adapter where tractable;
- [ ] hashing/near-uniform backend adapter;
- [ ] stratified constrained backend;
- [ ] degraded proposal backend;
- [ ] empirical backend selector using CIC structural telemetry;
- [ ] projected approximate counting integration where useful;
- [ ] cross-encoding/global distribution diagnostics;
- [ ] ESS/weight/support diagnostics;
- [ ] `diagnostic_debt` contract;
- [ ] `LOW_REPRESENTATIVENESS` confirmatory refusal.

**Exit:** deliberately biased proposal fixture is detected and refused for confirmatory use.

---

## P3 — Closed-loop adaptation: only after real need appears

### Week 8+ — Pass 7: CTM + Adaptive Governance + Chaos Lifecycle

**Suggested target:** 2026-10-29 onward; this should be driven by actual experimental use, not calendar pressure.

- [ ] sealed CTM -> next-wave policy transition;
- [ ] current-wave leakage firewall;
- [ ] overlap-aware CTM pooling restrictions;
- [ ] chaos candidate archive;
- [ ] minimal physical-admissibility gate;
- [ ] permanent failed-candidate retention;
- [ ] append-only re-screen/resurrection events;
- [ ] chaos yield / gate-bias reporting;
- [ ] full synthetic end-to-end integration test.

**Exit:** complete synthetic Wave N -> Wave N+1 cycle with one migration, one halt, one bridge, and one chaos resurrection.

---

# Recommended weekly work split

While physical work remains the real bottleneck, use this default allocation as a planning aid rather than a frozen experimental rule:

- **Primary:** whatever advances Production Alpha / calibration / P1 toward real physical evidence.
- **Secondary:** the current governance pass, only until its exit gate is satisfied.
- **Tertiary:** sampler/CIC research that is not required by an imminent experiment.

If a week contains a real external milestone (vendor template arrives, order is ready, garments arrive, P1 can run), pause lower-priority governance work and close the physical loop first.

---

# Stop conditions / anti-overengineering rules

Pause governance implementation if any of the following becomes true:

- P0 physical work is ready but waiting on developer attention;
- a pass starts duplicating an already-frozen RAC component under a new name;
- a mature external solver/sampler can satisfy an interface and the team starts reimplementing it without research justification;
- a feature cannot be tied to one of the seven governance laws or a concrete sampling/lineage failure mode;
- infrastructure work begins delaying collection of real evidence.

---

# Minimal useful milestone

If time becomes constrained, implement **Passes 1-4 only**.

That gives RAC:

- immutable governance history;
- formal constraint lineage;
- complete/reproducible cohort sealing;
- emergency halt behavior;
- sentinel/pipeline drift controls;
- bridge cohorts;
- explicit overlap/regime decisions.

This is enough to materially improve future experimental integrity. CIC routing, sophisticated uniform sampling, and closed-loop adaptive governance can be added later behind stable interfaces.

---

# Roadmap checkpoints

## Checkpoint A — Governance skeleton

- [ ] Pass 1 complete
- [ ] Pass 2 complete

**Decision:** are any imminent experiments changing constraints? If no, keep P0 ahead of Pass 3.

## Checkpoint B — Reproducible experimental foundation

- [ ] Pass 3 complete
- [ ] Pass 4 complete

**Decision:** does the next planned RAC study require formal constrained population sampling? If no, stop infrastructure work and focus on physical evidence/research execution.

## Checkpoint C — CIC operational integration

- [ ] Pass 5 complete

**Decision:** are current constraint instances hard enough to justify multiple sampler backends? If no, use one validated backend.

## Checkpoint D — Sampling research system

- [ ] Pass 6 complete

**Decision:** only proceed to Pass 7 when multiple sealed waves exist or the chaos/adaptive lifecycle is actually needed.

## Checkpoint E — Closed loop

- [ ] Pass 7 complete
- [ ] Governance v1 end-to-end fixture green
- [ ] docs/index updated from planned to implemented

---

# Non-goals for the coming weeks

Unless driven by actual experiment evidence, do not prioritize:

- proving SAT-backdoor variables correlate with transfer performance;
- building a custom d-DNNF compiler;
- replacing mature SAT/model-counting/sampling tools for ownership reasons;
- blockchain anchoring;
- generalized distributed governance ledger;
- automatic policy adaptation without a human-visible preregistration/seal boundary;
- retrofitting frozen D2 releases merely to satisfy Governance v1.

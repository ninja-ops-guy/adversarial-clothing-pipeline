# RAC Experimental Governance — Seven Implementation Passes

**Status:** planned  
**Authority:** implementation plan for `RAC_EXPERIMENTAL_GOVERNANCE_V1.md`  
**Principle:** each pass must be independently testable, mergeable, and reversible without mutating prior frozen evidence.

---

## Pass 1 — Governance Core

**Priority:** P1 — first governance implementation priority  
**Goal:** establish immutable identity, append-only history, formal schemas, and fail-closed state transitions before sophisticated sampling work begins.

### Deliverables

- `ruthless_pipeline/governance/ids.py`
  - stable typed IDs;
  - strict parsing/validation;
  - collision tests.
- `ruthless_pipeline/governance/ledger.py`
  - single-writer append-only event ledger;
  - SHA-256 hash chain;
  - chain verifier;
  - reversal/supersession references.
- `ruthless_pipeline/governance/state.py`
  - DRAFT/PREFLIGHT/SEALED/RUNNING/COMPLETE/HALTED states;
  - legal transition table;
  - no generic bypass.
- `ruthless_pipeline/governance/schemas/`
  - governance event;
  - sampling manifest;
  - cohort manifest;
  - constraint set;
  - overlap analysis;
  - diagnostic bundle.
- schema + semantic validators.

### Required tests

- corrupt previous hash -> chain verification fails;
- edited historical event -> fails;
- reversal event preserves original bytes;
- missing required manifest field -> seal denied;
- malformed seed/hash/ID -> denied;
- illegal state transition -> denied;
- conflicting invariant -> `HALTED`;
- no code path can silently skip governance checks.

### Exit gate

Pass 1 is complete only when a synthetic experiment can transition:

`DRAFT -> PREFLIGHT -> SEALED -> RUNNING -> COMPLETE`

and a separate synthetic fault produces:

`RUNNING -> HALTED`.

---

## Pass 2 — Constraint Lineage and Scientific-Impact Classification

**Priority:** P1  
**Depends on:** Pass 1  
**Goal:** make constraint evolution explicit, immutable, and scientifically classified.

### Deliverables

- `constraint_set` registry;
- parent/child lineage;
- `semantic_hash`, `rules_hash`, `encoder_hash`, projection version;
- software SemVer stored separately from scientific compatibility;
- impact enum:
  - `NONE`;
  - `SEMANTIC_CORRECTION`;
  - `POPULATION_CHANGE`;
  - `DEFINITION_CHANGE`.
- historical-impact decision output:
  - `NO_IMPACT`;
  - `MINOR_CORRECTION`;
  - `BRIDGE_REQUIRED`;
  - `COHORT_INVALIDATION`;
  - `NEW_REGIME`.
- preregistered tolerance policy schema by constraint family.

### Required tests

- software patch may still yield scientific population change;
- semantic redefinition forces regime reset regardless of small numerical population impact;
- historical cohort impact is measured separately from global feasible-population impact;
- missing scientific-impact classification blocks migration;
- frozen D2 artifacts are read-only inputs, never rewritten by migration code.

### Exit gate

A fixture must demonstrate:

`CS-001 -> CS-002`

with an encoder bugfix that generates a logged impact analysis and one of the formal migration outcomes without editing `CS-001`.

---

## Pass 3 — Seal and Reproducibility Layer

**Priority:** P1  
**Depends on:** Passes 1-2  
**Goal:** ensure a cohort is reproducible and cryptographically bound before it can produce CTM evidence.

### Deliverables

- `seal.py` validator/orchestrator;
- complete sampling/cohort manifest validation;
- referential-integrity checks;
- artifact SHA-256 verification;
- code commit + version binding;
- seed binding;
- pipeline/calibration references;
- diagnostic-threshold hash;
- signed Git provenance where available;
- optional RFC 3161 timestamp adapter, not required for local development.

### Seal order

1. manifest exists;
2. JSON Schema valid;
3. semantic validation;
4. referential integrity;
5. artifact/hash verification;
6. governance invariants;
7. diagnostics gate;
8. provenance/timestamp output;
9. transition to `SEALED`.

### Required tests

- absent seed -> seal fails;
- invalid referenced constraint set -> fails;
- cohort count != manifest count -> fails;
- duplicate specimen ID -> fails;
- hash mismatch -> fails;
- changed diagnostic threshold after manifest generation -> fails;
- same complete inputs produce deterministic seal identity.

### Exit gate

Generate a synthetic sealed cohort from a clean checkout and verify it independently.

---

## Pass 4 — Sentinel, Calibration, Bridge, and Overlap Engine

**Priority:** P1/P2 — highest-value methodology pass  
**Depends on:** Passes 1-3  
**Goal:** prevent wave-to-wave changes from silently masquerading as treatment effects.

### Deliverables

- sentinel schema + creator;
- immutable Wave N sentinel selection;
- blinded sentinel re-evaluation protocol;
- calibration-set isolation checks;
- pipeline bridge schema/executor;
- constraint bridge cohort schema;
- support-overlap estimator;
- policy-overlap estimator;
- material-stratum registry;
- confidence/error interval serialization;
- regime-reset decision engine.

### Sentinel invariants

- sentinel fixed at Wave N seal;
- Wave N outcomes unavailable to Wave N+1 initialization;
- frozen seeds;
- stateless preprocessing or separately fitted calibration state;
- calibration set disjoint from sentinel/bridge/treatment/held-out sets.

### Constraint migration groups

- Sentinel: fixed old-regime anchor;
- Bridge: newly sampled from common support;
- New Regime: full new constraint population.

### Overlap implementation

Provide two estimators:

- projected approximate-count path where tractable;
- bidirectional Monte Carlo feasibility path with confidence intervals.

Materiality is hypothesis-aware, not merely mass-based.

### Required tests

- sentinel cannot be resampled in the later wave;
- old outcomes cannot be used by calibration/preprocessing inputs;
- changed pipeline requires explicit bridge classification;
- migration without overlap analysis fails Law 4;
- rare hypothesis-named stratum remains material;
- inadequate common support emits `REGIME_RESET`;
- estimator uncertainty is retained.

### Exit gate

Synthetic `CS-A -> CS-B` migration generates:

sentinel + bridge + new cohort + dual overlap analysis + logged comparable/new-regime decision.

---

## Pass 5 — CIC Formal-Methods Integration

**Priority:** P2  
**Depends on:** Passes 1-4 interfaces  
**Goal:** consume CIC as a bounded verification/routing service without making it responsible for adversarial efficacy.

### Deliverables

- `ruthless_pipeline/governance/cic_adapter.py`;
- RAC semantic constraints -> CNF/PB/SMT adapters or stable interface to existing encoders;
- SAT/UNSAT/UNKNOWN results;
- satisfying-assignment verification;
- MUS/UNSAT-core support where available;
- cross-solver check mode;
- optional proof artifact hook;
- semantic vs compiled hash separation;
- scientific projection definition;
- independent support constrained to semantic genome variables;
- structural feature report for backend routing.

### Cross-encoding validation

Implement fixtures where equivalent CNF/PB/SMT encodings generate projected samples that pass a frozen global multivariate comparison. If the global test fails, produce marginal/pairwise diagnostic reports with multiplicity control.

### Required tests

- auxiliary variables cannot enter scientific projection;
- independent support is subset of semantic projection;
- invalid SAT assignment rejected by independent verifier;
- contradictory fixture produces explainable UNSAT result;
- semantically equivalent encodings agree on exact small fixtures;
- CIC adapter can be replaced with external solver backend without changing RAC manifest semantics.

### Exit gate

RAC can preflight one synthetic experiment through CIC, return verified feasibility, and produce a structural backend recommendation without influencing efficacy scoring.

---

## Pass 6 — Sampling Backends and Diagnostics

**Priority:** P2/P3  
**Depends on:** Passes 1-5  
**Goal:** sample scientific populations explicitly rather than treating arbitrary SAT witnesses as specimens.

### Backend contract

Implement a common sampler interface with four lanes:

1. exact/compiled;
2. projected hashing / near-uniform;
3. stratified constrained;
4. degraded proposal/rejection/importance sampling.

Initial adapters may wrap external tools; do not reimplement mature samplers solely for ownership.

### Backend selector

Inputs may include:

- treewidth/decomposition estimates;
- variable/constraint counts;
- arity;
- graph density;
- independent-support size;
- historical runtime/memory;
- propagation/solver telemetry.

Outputs:

- selected backend;
- alternate backend;
- predicted cost/confidence;
- selector version.

Thresholds are empirical and versioned, not hard scientific constants.

### Diagnostics

Versioned diagnostic bundles should include as applicable:

- exact small-instance calibration;
- material-stratum coverage;
- marginal and dependency checks;
- duplicate/concentration checks;
- repeated-seed stability;
- global target-distribution tests;
- ESS and importance-weight diagnostics;
- support-coverage estimates;
- approximate projected model counts + uncertainty;
- constraint sensitivity + propagated uncertainty.

### Backend 4 debt

Record quantitative `diagnostic_debt` and deny confirmatory eligibility if preregistered representativeness thresholds fail.

### Required tests

- first SAT witness is never implicitly treated as uniform sample;
- sampler manifest records target and achieved/estimated distribution;
- Backend 4 failure produces `LOW_REPRESENTATIVENESS`;
- sampler diagnostic version/threshold changes invalidate a would-be seal;
- selected exact small fixtures match known population distributions;
- approximate-count uncertainty survives serialization and downstream sensitivity calculations.

### Exit gate

Run one fixture through each available backend, issue comparable diagnostic bundles, and demonstrate fail-closed confirmatory refusal for a deliberately biased proposal sampler.

---

## Pass 7 — CTM, Adaptive Governance, and Chaos Lifecycle Integration

**Priority:** P3  
**Depends on:** Passes 1-6  
**Goal:** close the research loop while preventing current-wave outcome leakage and survivorship bias.

### Deliverables

- CTM intake refuses unsealed cohorts;
- Wave N evidence seal -> Wave N+1 policy proposal flow;
- preregister/freeze next-wave policy before cohort construction;
- no current-wave outcome access from current-wave sampler;
- constraint/pipeline migration awareness in CTM comparisons;
- no naive pooling after regime reset;
- chaos-candidate archive;
- physical-admissibility promotion gate;
- `SIMULATION_ONLY` reason codes;
- append-only re-screen/resurrection events;
- chaos yield/admissibility/gate-bias reports.

### Chaos invariants

- failed candidates retained;
- original failure status never rewritten;
- changed capabilities trigger new re-screen events;
- promoted old candidate becomes a new hypothesis event referencing its source;
- current-wave held-out outcomes cannot tune current-wave chaos allocation.

### Required tests

- unsealed cohort rejected by CTM;
- unsealed prior wave cannot drive new sampling policy;
- regime-reset waves cannot be pooled through default analysis path;
- chaos failures remain visible in yield statistics;
- re-screen event preserves original failure;
- adaptive allocation is based only on sealed prior-wave evidence.

### Exit gate

End-to-end synthetic demonstration:

`constraints -> cohort -> seal -> CTM -> sealed result -> next-wave adaptation -> constraint migration -> bridge/overlap -> next cohort`

with one intentionally triggered HALT and one chaos re-screen lifecycle.

---

# Global implementation rules

- Prefer additive namespaces over edits to frozen evidence surfaces.
- Every pass must ship tests and documentation with the same commit/wave.
- No pass may claim physical efficacy or manufacturing validation.
- Do not block current physical/POD critical-path work unless a governance change is required for the specific experiment being armed.
- Avoid speculative solver research inside RAC when a stable adapter to CIC/external tools is sufficient.
- Passes 1-4 are the governance foundation milestone; Passes 5-7 may evolve behind those interfaces.

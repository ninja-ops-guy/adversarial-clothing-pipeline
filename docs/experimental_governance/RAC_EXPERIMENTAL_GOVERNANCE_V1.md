# RAC Experimental Governance v1.0

**Status:** PROSPECTIVE IMPLEMENTATION SPEC  
**Date:** 2026-09-10  
**Applies to:** future RAC experimental waves after explicit adoption  
**Does not retroactively mutate:** D2-0003, D2-0004, frozen D2-0005 preregistration, or any sealed release  
**Primary objective:** make cohort construction, constraint evolution, sampling, pipeline changes, and CTM adaptation auditable and resistant to silent methodological drift.

---

## 1. Scope and authority

This specification extends the existing RAC Engineering Constitution, certification system, research release format, CTM contracts, and experiment-state machinery. It is additive: existing frozen evidence remains immutable.

The governance layer does **not** decide whether an adversarial pattern works. Its job is to define and preserve the experimental population, verify that constraints are represented correctly, construct auditable cohorts, prevent outcome leakage, and preserve comparability across changing constraint and evaluation regimes.

The architecture intentionally separates four responsibilities:

1. **CIC/formal verification:** satisfiability, contradiction explanation, independent-support analysis, structural routing, and optional proof/cross-solver checks.
2. **RAC constraint layer:** scientific, manufacturing, null/control, and experimental rules.
3. **RAC sampling layer:** target distributions, counting, sampling, weighting, diagnostics, and degraded-backend accounting.
4. **CTM/evidence layer:** outcome measurement, inference, cross-wave comparison, and inputs to the next preregistered policy.

---

## 2. Seven governance laws

These invariants are fail-closed.

### LAW 1 — Complete manifest before cohort

No cohort exists unless its sampling manifest is present, schema-valid, semantically valid, and referentially complete.

### LAW 2 — Sealed cohort before CTM

No CTM wave may execute or accept evidence from a cohort that has not passed seal validation.

### LAW 3 — Sealed evidence before adaptation

No sampling, constraint, optimization, or allocation policy may adapt from an unsealed CTM wave.

### LAW 4 — Overlap analysis before constraint migration

No constraint-set migration may be treated as comparable with its predecessor until support overlap and sampling-policy overlap have been analyzed.

### LAW 5 — Scientific-impact classification before methodological change

No semantic, encoder, calibration, preprocessing, detector/evaluator, or sampling-policy change may enter a running or future comparable wave without explicit scientific-impact classification.

### LAW 6 — Historical artifacts are append-only

No historical governance, cohort, constraint, sampling, calibration, or evaluation artifact is rewritten. Corrections are represented as append-only reversal, supersession, invalidation, or re-screen events.

### LAW 7 — Emergency halt on unresolved invariant conflict

No invariant may be silently bypassed. An unresolved conflict transitions the affected experiment to `HALTED`. Resumption requires a logged governance-resolution event.

There must be no production `force=True`, `skip_governance=True`, or equivalent generic bypass.

---

## 3. Experiment state machine

Minimum prospective state machine:

```text
DRAFT
  -> PREFLIGHT
  -> SEALED
  -> RUNNING
       |-> COMPLETE
       |-> HALTED
             |-> ABORTED
             |-> INVALIDATED
             |-> BRIDGED
             |-> RESEALED
```

Each transition must be an append-only governance event. Illegal transitions fail closed.

`HALTED` records must identify:

- violated invariant IDs;
- affected experiment/cohort/artifact IDs;
- discovery timestamp;
- current evidence status;
- whether data collection has already occurred;
- required governance decision;
- resolution event ID when resolved.

---

## 4. Immutable identity and lineage

Introduce stable IDs for at least:

- `RAC-CS-*` — constraint sets;
- `RAC-COHORT-*` — cohorts;
- `RAC-SAMP-*` — sampling manifests;
- `RAC-SENT-*` — sentinel cohorts;
- `RAC-BRIDGE-*` — bridge cohorts;
- `RAC-CAL-*` — calibration sets/states;
- `RAC-PIPE-*` — evaluation pipeline definitions;
- `RAC-GOV-EVT-*` — governance events;
- `RAC-OVERLAP-*` — overlap analyses;
- `RAC-DIAG-*` — sampler-diagnostic bundles.

Every artifact must carry content hashes and explicit parent/predecessor references when lineage exists.

---

## 5. Append-only governance ledger

The ledger is hash chained.

Each event includes at minimum:

```json
{
  "event_id": "RAC-GOV-EVT-...",
  "event_type": "...",
  "created_at": "...",
  "actor": "...",
  "payload_sha256": "...",
  "previous_event_sha256": "...",
  "event_sha256": "..."
}
```

Required event types include:

- `CREATE`;
- `SEAL`;
- `HALT`;
- `RESUME`;
- `REVERSAL`;
- `SUPERSESSION`;
- `INVALIDATION`;
- `CONSTRAINT_MIGRATION`;
- `PIPELINE_MIGRATION`;
- `RESCREEN`;
- `BRIDGE_DECISION`;
- `REGIME_RESET`.

An erroneous event is never edited. Append a `REVERSAL` referencing the erroneous event hash, then append the corrected event.

Initial implementation should use one authoritative linear append writer. Concurrency/Merkle batching is deferred until there is an actual multi-writer requirement.

---

## 6. Constraint-set contract

A constraint set is an immutable scientific artifact, not a mutable Python configuration.

Minimum record:

```json
{
  "constraint_set_id": "RAC-CS-0013",
  "software_version": "1.3.3",
  "parent_constraint_set_id": "RAC-CS-0012",
  "semantic_hash": "sha256:...",
  "rules_hash": "sha256:...",
  "encoder_version": "0.4.2",
  "encoder_hash": "sha256:...",
  "scientific_projection_version": "RAC-PG-1.3",
  "scientific_impact": "NONE|SEMANTIC_CORRECTION|POPULATION_CHANGE|DEFINITION_CHANGE"
}
```

### 6.1 Software version != scientific compatibility

Use normal software SemVer for implementation compatibility, but separately classify scientific impact.

Examples:

- pure performance optimization with byte-equivalent feasible population -> `NONE`;
- encoder bug correction -> `SEMANTIC_CORRECTION` or `POPULATION_CHANGE` depending on effect;
- new optional constraint type -> software minor; scientific effect depends on whether activated;
- redefinition of `NULL_SPECTRAL_MATCHED` -> `DEFINITION_CHANGE` and new experimental regime.

A software patch can still scientifically invalidate a cohort.

### 6.2 Retroactive impact procedure

When a correction is discovered, evaluate three axes before reusing historical evidence:

1. **Population impact:** estimated displacement of the feasible population.
2. **Cohort impact:** number/proportion of already sealed specimens whose validity/classification changes.
3. **Estimand impact:** whether the meaning of the experimental quantity changes.

Output classification:

- `NO_IMPACT`;
- `MINOR_CORRECTION`;
- `BRIDGE_REQUIRED`;
- `COHORT_INVALIDATION`;
- `NEW_REGIME`.

Numerical tolerance thresholds must be preregistered by constraint family before outcome inspection. Magnitude alone never overrides a semantic redefinition.

---

## 7. Scientific projection and independent support

Define two disjoint classes of variables:

```text
P = scientific projection = semantic genome variables
A = auxiliary encoding variables
P intersect A = empty
```

The scientific population is defined over `P`, never over `A`.

Independent-support analysis may compute `I subseteq P` for hashing/counting efficiency. Auxiliary Tseitin/encoder variables must not be admitted into the scientific projection.

The RAC/CIC adapter must explicitly pass only semantic genome variables to any projection/independent-support computation.

---

## 8. Constraint compiler verification

Encoder correctness and sampler quality are separate release gates.

Each scientific constraint family should provide:

1. **Reference semantic oracle** — a direct implementation of intended semantics.
2. **Property-based tests** — random/boundary genomes compared against the oracle.
3. **Metamorphic tests** — transformations that must preserve or predictably alter the property.
4. **Cross-encoding differential tests** — CNF/PB/SMT representations must induce statistically compatible projected genome distributions.

Each constraint declares its valid metamorphic transformation group. Do not assume rotation/translation invariance for seam-, weave-, garment-zone-, or anisotropic-physics-aware constraints.

Cross-encoding release gate:

```text
same semantic constraint set
 -> CNF / PB / SMT
 -> projected samples
 -> global multivariate distribution test
 -> PASS or diagnostic decomposition
```

Use a frozen global distribution-test configuration per wave. Per-variable and pairwise tests are diagnostic follow-ups and must use family-wise error control (e.g. Holm) when interpreted inferentially.

---

## 9. Sentinel and calibration protocol

### 9.1 Sentinel definition

At Wave N seal time, create `SENTINEL-N` as a fixed random sample from the Wave N feasible population under the Wave N sampling policy.

The sentinel is immutable:

- specimen IDs fixed;
- artifacts fixed;
- original sampling probabilities retained;
- outcomes not included in any Wave N+1 preprocessing/calibration state.

### 9.2 Blind re-evaluation

Wave N+1 sentinel re-evaluation must use:

- frozen code revision;
- frozen random seeds;
- deterministic/stateless preprocessing **or** preprocessing fitted only on a separate calibration set;
- no access to previous sentinel outcomes;
- no calibration set overlap with sentinel, bridge, treatment, or held-out evaluation specimens.

### 9.3 Pipeline bridge

If the evaluation pipeline changes, evaluate the sentinel under both old and new pipeline definitions in parallel when feasible.

Store observations append-only:

```text
sentinel specimen
  - Wave N / Pipeline old / measurement
  - Wave N+1 / Pipeline old / measurement
  - Wave N+1 / Pipeline new / measurement
```

This separates ordinary temporal/measurement drift from pipeline-version effects.

---

## 10. Constraint migration and bridge cohorts

For `CS_old -> CS_new`, Wave N+1 must distinguish:

1. **Sentinel:** fixed Wave N anchor; not resampled.
2. **Bridge:** newly sampled from `F(CS_old) intersect F(CS_new)`.
3. **New regime cohort:** sampled from full `F(CS_new)`.

No naive pooling is allowed when overlap is insufficient.

### 10.1 Dual overlap metrics

Measure both:

- **support overlap** within scientifically material strata;
- **sampling-policy overlap** between the old and new target distributions.

Recommended directional support estimates per stratum `s`:

```text
O_old_to_new(s) = |F_old(s) intersect F_new(s)| / |F_old(s)|
O_new_to_old(s) = |F_old(s) intersect F_new(s)| / |F_new(s)|
```

Policy overlap should measure probability-mass commonality under the two preregistered sampling policies.

Use projected approximate counting when tractable and bidirectional Monte Carlo feasibility checking as a scalable estimator. Store confidence/error intervals, method, seeds, and estimator version.

### 10.2 Material strata

A stratum is material if any is true:

- mass under old population >= preregistered threshold;
- mass under new population >= preregistered threshold;
- explicitly named in the preregistered hypothesis;
- mandatory safety/manufacturing stratum.

Do not allow a rare but hypothesis-critical stratum to disappear behind an average overlap statistic.

### 10.3 Regime reset

If a material stratum loses preregistered common support, policy overlap is below its preregistered bound, or the estimand changes semantically, emit `REGIME_RESET`. CTM may compare regimes descriptively but must not pool them as though they were sampled from one unchanged population.

---

## 11. Sampling subsystem

SAT feasibility is not specimen sampling. The sampler owns the target distribution.

Common API concept:

```python
cohort = sampler.sample(
    constraint_set_id="RAC-CS-...",
    projection="RAC-PG-...",
    target_distribution="uniform|stratified|weighted",
    n=...,
    seed=...,
)
```

### 11.1 Backend lanes

Support four routing lanes:

1. **Exact compiled sampling** — knowledge compilation / exact methods when tractable.
2. **Hashing / near-uniform sampling** — projected hash-based methods.
3. **Stratified constrained sampling** — CP-SAT/SMT/custom constrained generation with explicit strata and diagnostics.
4. **Degraded proposal-based sampling** — rejection/importance/proposal methods for hard instances.

CIC structural metrics (treewidth, density, arity, decomposition metrics, prior runtime/memory) inform routing, but do **not** use fixed universal treewidth cutoffs as scientific law. Backend thresholds are empirical and versioned.

### 11.2 Backend 4 diagnostic debt

Backend 4 cannot silently claim equivalence to uniform/exact sampling.

Record a diagnostic-debt vector including, as applicable:

- ESS ratio;
- support-coverage estimate;
- normalized-weight concentration/tail metrics;
- missing material strata;
- target-distribution test status;
- count/normalization uncertainty;
- proposal model/version/provenance.

If preregistered representativeness bounds fail, mark cohort `LOW_REPRESENTATIVENESS`. Such cohorts may be used for exploratory/hypothesis generation but not confirmatory inference.

---

## 12. Sampler diagnostics

Sampler diagnostics are first-class, versioned, immutable wave artifacts.

Minimum diagnostic families:

- exact small-instance calibration where enumeration is possible;
- marginal frequency checks when expectations are available;
- pairwise/dependency checks;
- material-stratum occupancy/support;
- duplicate/concentration diagnostics;
- repeated-seed stability;
- sampler-vs-target distribution tests;
- ESS/weight diagnostics for weighted or correlated schemes;
- approximate projected counts for expected stratum mass where useful;
- constraint sensitivity with uncertainty propagation.

Do not treat approximate counts as ground truth. Store estimator error/confidence parameters and propagate them into downstream sensitivity conclusions.

Freeze per wave:

- diagnostic software version;
- diagnostic configuration/kernel;
- thresholds;
- random seeds;
- decision logic.

Changing diagnostics mid-wave is a scientific-impact event.

---

## 13. Chaos / discovery lane

RAC keeps an unconstrained or weakly constrained discovery lane. Its existence is frozen; its budget may adapt only through a preregistered policy using sealed prior-wave evidence.

Current-wave held-out outcomes may not alter current-wave discovery allocation.

Every chaos candidate that reaches evaluation is retained, including physical-admissibility failures.

Promotion path:

```text
chaos candidate
 -> simulation evaluation
 -> minimal physical/manufacturing admissibility gate
    -> PASS: eligible to become a confirmatory hypothesis
    -> FAIL: SIMULATION_ONLY archive with reason codes
```

The admissibility gate contains hard physical/manufacturing feasibility only; it must not add aesthetic or theory-derived filters that would suppress unusual discoveries.

### 13.1 Zombie prevention / re-screening

When constraints/capabilities evolve, archived chaos candidates may be re-screened. Re-screening creates a new append-only event; the original failure remains immutable.

If a prior failure becomes admissible, create a new hypothesis event referencing the original chaos candidate. Never rewrite the original status.

Track:

- chaos yield;
- admissibility rate;
- high-performing-but-impossible rate;
- failure reason distribution;
- re-screen resurrection rate;
- gate bias by topology/spectral/print/deformation/generator family.

---

## 14. Sampling manifest and seal contract

A manifest is complete only if schema-valid **and** semantically/referentially valid.

Required fields should include at minimum:

- manifest schema/version;
- cohort ID;
- experiment/wave ID;
- constraint set ID + semantic hash;
- scientific projection version;
- encoder/compiler versions + hashes;
- sampler backend/version/policy;
- target distribution;
- seed(s);
- requested and realized sample counts;
- per-specimen stable IDs and hashes;
- sampling probabilities/weights when applicable;
- diagnostic bundle ID/version;
- diagnostic thresholds hash;
- calibration/pipeline references;
- source commit;
- parent/bridge/sentinel references when applicable;
- seal metadata.

Seal procedure:

```text
manifest exists
 -> JSON Schema validation
 -> semantic validation
 -> referential integrity
 -> artifact/hash verification
 -> governance invariant checks
 -> diagnostics gate
 -> signed repository provenance
 -> optional trusted timestamp
 -> SEALED
```

For higher-assurance publication releases, support RFC 3161 timestamp tokens or equivalent trusted timestamp evidence. Blockchain anchoring is optional, not required.

---

## 15. CIC integration contract

RAC consumes CIC as a bounded formal-methods service. RAC must not make claims that CIC predicts adversarial efficacy.

Minimum conceptual API:

```python
result = cic.check(
    constraints=experiment_constraints,
    constraint_set_id="RAC-CS-...",
    projection=semantic_genome_variables,
    explain_unsat=True,
)
```

Result metadata:

- SAT/UNSAT/UNKNOWN;
- satisfying assignment for SAT;
- assignment verification status;
- UNSAT core/MUS support where available;
- solver(s) and versions;
- optional proof artifact for sealed/high-assurance UNSAT decisions;
- semantic constraint hash;
- compiled problem hash;
- encoder version;
- structural metrics;
- backend-routing recommendation.

Routine development may use cross-solver verification. Proof logging is optional for development and can be required for publication/high-assurance constraint-compiler claims.

The intended CIC contribution is:

> Given structural features of a constrained RAC design problem, predict which verification/counting/sampling backend offers the best accuracy-runtime-memory tradeoff.

It is **not**:

> Use SAT structural features to predict whether a clothing pattern will defeat a detector.

---

## 16. Leakage firewall

Define three distributions/concepts separately:

- feasible scientific population;
- sampling distribution;
- experimental outcome distribution.

The current-wave outcome distribution may not influence current-wave cohort construction.

Allowed adaptation:

```text
Wave N
 -> seal CTM evidence
 -> derive policy candidate
 -> preregister/freeze Wave N+1 policy
 -> construct Wave N+1 cohort
```

Forbidden:

```text
Wave N outcome <-> Wave N sampling
```

Historical CTM data may inform a later wave only after the source wave is sealed and the new policy is frozen before new outcomes are observed.

---

## 17. CI and acceptance requirements

Governance v1 must eventually include automated tests proving at minimum:

- incomplete manifests cannot seal;
- malformed IDs/hashes fail;
- missing referenced artifacts fail;
- historical ledger events cannot be mutated through the API;
- hash-chain corruption is detected;
- reversal/supersession events preserve history;
- illegal state transitions fail;
- invariant conflict forces `HALTED`;
- no generic bypass flag exists;
- CTM rejects unsealed cohorts;
- policy adaptation rejects unsealed source waves;
- constraint migration rejects missing overlap analysis;
- semantic-impact classification is mandatory for affected changes;
- auxiliary variables cannot enter the scientific projection;
- sentinel labels cannot enter calibration/preprocessing inputs;
- calibration set cannot overlap sentinel/bridge/treatment/held-out sets;
- cross-encoding tests execute against fixtures;
- Backend 4 cannot receive confirmatory eligibility when diagnostic-debt thresholds fail;
- chaos re-screening appends rather than overwrites;
- exact/approximate estimator uncertainty is preserved in analysis artifacts.

---

## 18. Adoption boundary

This specification is prospective.

Do not retroactively rewrite or reinterpret already frozen RAC generations/releases merely to satisfy this specification. Historical work may be **referenced** or **migrated through explicit governance events**, but immutable evidence remains immutable.

D2-0005 or any other already-frozen preregistration must not be silently modified to adopt Governance v1. Adoption requires an explicit amendment or later-wave transition consistent with the existing preregistration authority.

---

## 19. Definition of done for Governance v1

Governance v1 is implementation-complete when:

- Passes 1-7 in `IMPLEMENTATION_PASSES.md` meet their acceptance criteria;
- end-to-end tests demonstrate a complete `DRAFT -> PREFLIGHT -> SEALED -> RUNNING -> COMPLETE` path;
- a synthetic invariant violation demonstrates `RUNNING -> HALTED -> documented resolution`;
- a synthetic constraint migration demonstrates sentinel + bridge + overlap analysis + regime decision;
- a hard sampling fixture demonstrates Backend 4 diagnostic debt and confirmatory refusal;
- all generated governance artifacts verify from a clean checkout;
- documentation index and roadmap identify Governance v1 as prospective/current without overstating physical evidence.

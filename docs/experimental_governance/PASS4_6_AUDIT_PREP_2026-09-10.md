# Governance Passes 4–6 Audit Preparation — 2026-09-10

**Status:** AUDIT PREP ONLY — **NOT A CLOSURE RECORD**  
**Adopted source:** `RAC_EXPERIMENTAL_GOVERNANCE_V1.md` + `IMPLEMENTATION_PASSES.md`  
**Purpose:** inventory demonstrated implementation/test surfaces so later formal audits start from evidence rather than namespace presence.  
**Boundary:** no physical-efficacy claim, no frozen-D2 mutation, and no Pass 7 expansion.

---

## Pass 4 — Sentinel, Calibration, Bridge, and Overlap

### Demonstrated implementation surfaces

- `ruthless_pipeline/governance/sentinel.py`
  - sentinel creation bound to a sealed source cohort;
  - registry refusal of later-wave sentinel resampling;
  - frozen selection seed/policy hash;
  - stateless vs separately calibrated preprocessing modes;
  - prior-wave outcome leakage refusal;
  - calibration isolation checks;
  - pipeline-transition bridge requirements.
- `ruthless_pipeline/governance/bridge.py`
  - constraint bridge cohort representation;
  - common-support membership validation.
- `ruthless_pipeline/governance/overlap.py`
  - bidirectional feasibility overlap with retained uncertainty;
  - approximate-count overlap with propagated count uncertainty;
  - material-stratum handling, including hypothesis-named rare strata;
  - sampling-policy overlap;
  - overlap binding to the exact old/new constraint pair;
  - explicit `REGIME_RESET` decisions when support or policy overlap is inadequate.
- `tests/governance/test_pass4_hardening.py` and `test_pass4_schemas.py`
  - direct negative cases for resampling, leakage, contaminated calibration, missing bridge, invalid common support, missing Law-4 overlap, rare-stratum materiality and regime reset.

### Audit questions still requiring formal closure work

1. Demonstrate the **single adopted Pass 4 exit fixture** end to end: `CS-A -> CS-B` must produce the sealed sentinel, constraint bridge, new-regime cohort, **both** overlap analyses and one logged comparable/new-regime decision in one reproducible flow.
2. Confirm the projected approximate-count and bidirectional Monte Carlo paths are both invoked through the adopted orchestration surface rather than only tested as independent helpers.
3. Confirm every serialized overlap estimate retains the required confidence/error interval through downstream decision logging.
4. Confirm the material-stratum registry used by the exit fixture is hash/version bound rather than supplied ad hoc.

**Prep disposition:** implementation is strong and most required negative cases are directly demonstrated. **Remain AUDIT-GATED until the integrated exit fixture and serialization/logging chain are verified.**

---

## Pass 5 — CIC Formal-Methods Integration

### Demonstrated implementation surfaces

- `ruthless_pipeline/governance/cic_adapter.py`
  - CNF/PB/SMT/external representation contracts;
  - semantic vs compiled hashes;
  - semantic-variable/scientific-projection boundaries;
  - independent support restricted to semantic variables;
  - SAT / UNSAT / UNKNOWN response handling;
  - satisfying-assignment verification;
  - guarded UNSAT-core/proof handling;
  - external CIC-core adapter boundary;
  - structural metrics for downstream routing.
- `ruthless_pipeline/governance/cic_semantics.py`
  - differential validation of compiled encodings against frozen semantic behavior on explicit probes.
- `tests/governance/test_cic_adapter.py`
- `tests/governance/test_pass5_external_cic.py`
- `tests/governance/test_pass5_semantics.py`
- `tests/governance/test_pass5_unsat_core.py`
  - coverage includes auxiliary-variable/projection restrictions, external-backend substitution, semantic mismatch refusal, missing probe variables, verified assignment requirements and suppression of unverified UNSAT cores.

### Audit questions still requiring formal closure work

1. Run one **integrated Pass 5 preflight fixture** from RAC semantic constraint input through CIC feasibility verification and structural telemetry into a backend recommendation, while proving efficacy scoring is unavailable to CIC.
2. Verify an explainable contradictory fixture produces the adopted UNSAT/core behavior with provenance for the solver/backend used.
3. Confirm equivalent CNF/PB/SMT fixtures are compared on a common scientific projection and that the adopted global multivariate comparison requirement is satisfied—not merely pointwise probe equivalence.
4. Confirm proof/core artifacts are either independently verified or explicitly marked unavailable/unverified and cannot be elevated into a scientific claim.

**Prep disposition:** major contract pieces and defensive tests exist. **Remain AUDIT-GATED until the adopted end-to-end preflight/routing exit gate and global cross-encoding comparison are explicitly demonstrated.**

---

## Pass 6 — Sampling Backends and Diagnostics

### Demonstrated implementation surfaces

- `ruthless_pipeline/governance/sampling.py`
  - explicit `PopulationIdentity` separating the full scientific projection from independent support;
  - common sampling request/result contracts;
  - explicit exact projected-population backend;
  - target vs achieved distribution fields;
  - first-SAT-witness refusal;
  - sampling manifest construction with population/sampler/diagnostic-policy binding;
  - `LOW_REPRESENTATIVENESS` and confirmatory-refusal path;
  - diagnostic debt and weighted/correlated-draw ESS handling.
- `ruthless_pipeline/governance/sampling_diagnostics.py`
  - exact small-population total-variation/marginal/pairwise checks;
  - repeated-seed instability measurement on the full projection;
  - retained approximate-count and sensitivity uncertainty.
- `ruthless_pipeline/governance/sampling_routing.py`
  - empirical backend selection from caller-supplied/frozen calibrated coefficients rather than hard-coded universal scientific cutoffs.
- `tests/governance/test_pass6_certification.py`
  - exact-population calibration;
  - projection/auxiliary-variable fail-closed cases;
  - biased-sample global/dependency failure;
  - ESS/degraded-backend debt;
  - repeated-seed refusal;
  - manifest threshold binding;
  - empirical routing constraints.
- `tests/governance/test_pass6_external_sampler_adapters.py`
- `tests/governance/test_pass6_public_api.py`
  - external adapter and public-surface coverage associated with the current Pass 6 implementation.

### Audit questions still requiring formal closure work

1. The adopted exit gate requires **one fixture through each available backend**, comparable diagnostic bundles and a deliberately biased proposal sampler refused for confirmatory use. Verify this as one explicit integrated exit sequence.
2. Inventory which of the four adopted lanes are genuinely production-capable today versus interface/adaptor-only: exact/compiled, projected hashing/near-uniform, stratified constrained and degraded proposal/rejection/importance sampling.
3. Confirm projected approximate-count uncertainty survives manifest serialization and every downstream sensitivity consumer, not only the in-memory diagnostic object.
4. Confirm all sampler selection/diagnostic thresholds are version/hash bound at cohort sealing so a post-manifest threshold change invalidates the would-be seal.
5. Verify external sampler adapters cannot leak auxiliary variables into the scientific population and cannot silently fall back to a first SAT witness.

**Prep disposition:** Pass 6 is substantially implemented and has certification-oriented tests, but this document intentionally does **not** interpret commit names such as “certify Pass 6” as governance closure. **Remain AUDIT-GATED until the adopted multi-backend integrated exit gate and seal-binding audit are recorded.**

---

## Cross-pass recommendation

Run formal audits in dependency order: **Pass 4 → Pass 5 → Pass 6**. Do not use Pass 7 prototype presence as evidence for any earlier pass. If an earlier pass fails an adopted exit requirement, keep downstream passes implemented-but-audit-gated until the dependency is repaired.

The physical/Production Alpha critical path remains higher priority whenever external inputs become actionable.

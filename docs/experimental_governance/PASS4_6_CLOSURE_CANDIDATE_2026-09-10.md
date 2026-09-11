# Governance Passes 4–6 Closure Candidate — 2026-09-10

**Status:** CLOSURE CANDIDATE — requires branch CI before promotion to a formal closure record.  
**Scope:** software/governance exit gates only.  
**Scientific boundary:** no physical-efficacy claim, no frozen-D2 mutation, no D2-0005 arming, no held-out outcome access, no scientific-threshold change, no matched-null relaxation, and no certification-firewall weakening.

This record addresses the outstanding questions in `PASS4_6_AUDIT_PREP_2026-09-10.md` in dependency order.

## Pass 4 — integrated migration exit

Added `ruthless_pipeline/governance/pass4_exit.py` and `tests/governance/test_pass4_exit_fixture.py`.

The exit fixture now executes one `CS-A -> CS-B` path that:

1. consumes a previously sealed source cohort;
2. creates and registers the immutable sentinel;
3. validates a constraint bridge against common support;
4. identifies the new-regime cohort;
5. invokes projected approximate-count overlap;
6. invokes bidirectional Monte Carlo overlap;
7. computes material-stratum-aware support plus sampling-policy overlap;
8. binds the material-stratum registry by version and SHA-256;
9. retains every interval/confidence field in the serialized decision payload; and
10. appends one `BRIDGE_DECISION` event to the governance ledger.

The negative fixture removes one registered material stratum and requires `REGIME_RESET`.

**Candidate disposition:** all previously listed Pass-4 audit questions are represented by executable acceptance fixtures. Closure remains contingent on CI execution of those fixtures.

## Pass 5 — integrated CIC preflight and cross-encoding gate

Added `ruthless_pipeline/governance/pass5_exit.py` and `tests/governance/test_pass5_exit_fixture.py`.

The integrated preflight now:

1. binds CNF/PB/SMT compiled representations to one frozen RAC semantic input;
2. independently verifies SAT assignments;
3. requires cross-encoding semantic/status agreement;
4. compares projected sample sets using a global joint-distribution total-variation test over the full scientific projection;
5. uses a caller-supplied acceptance bound rather than a hard scientific constant;
6. routes from structural CIC telemetry into the existing sampler selector; and
7. exposes no efficacy input or output.

A contradictory fixture separately requires an independently verified proof artifact, retained UNSAT core, backend provenance, and the explicit proof scope `compiled_problem_only`. Unverified proof/core material cannot satisfy that exit.

**Candidate disposition:** the integrated preflight/routing and global cross-encoding comparison questions are represented by executable acceptance fixtures. Closure remains contingent on CI.

## Pass 6 — integrated multi-backend sampling exit and seal binding

Added `ruthless_pipeline/governance/pass6_exit.py` and `tests/governance/test_pass6_exit_fixture.py`.

The exit sequence now:

1. inventories all four adopted lanes as `BUILTIN_PRODUCTION`, `EXTERNAL_ADAPTER_PRODUCTION`, or `INTERFACE_ONLY`;
2. requires the supplied backend set to exactly match lanes classified as available;
3. runs every available lane through one scientific population and one versioned diagnostic policy;
4. computes exact-population global/marginal/pairwise calibration metrics;
5. retains projected model-count uncertainty and constraint-sensitivity intervals through JSON serialization;
6. refuses confirmatory eligibility for the deliberately biased degraded proposal sampler;
7. binds the sampling manifest's diagnostic-policy hash to canonical policy bytes; and
8. seals an eligible backend run through the adopted Pass-3 cohort seal.

A separate acceptance case changes the diagnostic policy after manifest construction and requires the would-be seal to fail closed. External sampler fixtures also prove that auxiliary-variable leakage and `first_sat_witness` distributions are rejected.

**Candidate disposition:** the multi-backend exit, capability inventory, uncertainty propagation, seal binding, and external-adapter boundary questions are represented by executable acceptance fixtures. Closure remains contingent on CI.

## Promotion rule

This document must not be treated as a formal closure record merely because it exists or because commits contain the word `certify`. Promote Passes 4–6 to `CLOSED` only after the branch/PR workflow demonstrates the new acceptance fixtures pass in the repository test environment. If any earlier pass fails, keep downstream passes implemented-but-audit-gated until repaired and rerun.

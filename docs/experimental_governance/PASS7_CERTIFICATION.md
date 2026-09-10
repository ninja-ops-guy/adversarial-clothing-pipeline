# RAC Experimental Governance — Pass 7 Certification

**Scope:** CTM/adaptive-governance/chaos-loop closure  
**Evidence boundary:** prospective governance only; no physical-efficacy claim  
**Depends on:** certified Passes 1–6 plus the existing CTM intake and provenance-firewall surfaces

## Certified architecture

```text
sealed cohort
    ↓
CTM intake verification
    ↓
CTM evidence / claim provenance firewall
    ↓
sealed Wave N evidence
    ↓
freeze Wave N+1 policy + allocation
    ↓
construct Wave N+1 cohort
    ↓
constraint / pipeline changed?
    ├── no  → direct comparison path
    └── yes → overlap + migration classification
                 ├── comparable      → common-support path
                 ├── bridge required → explicit bridge cohort
                 └── regime reset    → separate regime; no default pooling

chaos lane
    ↓
append-only failure archive
    ↓
capability-triggered re-screen
    ↓
physical-admissibility gate
    ↓
new hypothesis event referencing original candidate
```

## Temporal firewall

A next-wave policy may be produced only from a `SEALED` prior-wave evidence record. The policy artifact binds the prior evidence hash, source seal, target wave, policy payload, and (when used) the allocation policy. Supplying a current-wave outcome container is rejected even when that container is empty; this avoids converting outcome access into a timing-dependent convention.

Allocation is not a universal fixed split. Each wave freezes explicit constrained/chaos fractions plus a versioned stopping rule and reallocation rule. Reallocation may be informed only by a later sealed evidence wave, never by held-out observations from the wave currently being sampled.

## CTM migration gate

`governance.ctm_comparison` sits outside the scientific CTM comparator. It does not compute an effect. It establishes whether two sealed cohort contexts may enter the same analysis path.

A constraint-set change requires an overlap-analysis identity. A pipeline identity/version change requires an explicit migration classification. `BRIDGE_REQUIRED` requires an explicit bridge cohort. `REGIME_RESET` and `INCOMPARABLE` produce a separate-regime decision and fail the default comparison eligibility gate.

The underlying CTM intake verifier and CTM dependency-graph firewall remain authoritative for seal integrity and held-out leakage respectively; Pass 7 does not duplicate them.

## Chaos lifecycle and survivorship-bias accounting

The original failed candidate record is immutable. Re-screening appends events, and promotion is legal only when the **latest** re-screen is `ADMISSIBLE`. A formerly admissible candidate that later fails a re-screen cannot be promoted through stale historical status.

The archive now exposes three complementary views:

- legacy event-count/yield report;
- current admissibility report, including original and latest re-screen reason distributions;
- descriptive gate-bias reports grouped by pre-outcome generator, topology, or spectral class.

These reports characterize what the physical gate filters out. They are not adversarial-efficacy evidence.

## Exit-gate fixture

`tests/governance/test_pass7_certification.py` composes the real repository primitives into the required synthetic loop:

`constraint identity → cohort → seal → CTM intake → sealed evidence → Wave N+1 policy freeze → changed constraint → overlap/bridge decision → next cohort`

The same fixture intentionally triggers a ledger-backed Law-7 `HALTED` state and executes a chaos failure → re-screen → physically admissible new-hypothesis lifecycle while preserving the original failed record.

## Hard rules after Pass 7

```text
NO CTM INTAKE WITHOUT A VERIFIED SEALED COHORT
NO CURRENT-WAVE OUTCOME ACCESS DURING CURRENT-WAVE POLICY CONSTRUCTION
NO SAMPLING WITHOUT A FROZEN POLICY FOR THAT WAVE
NO CONSTRAINT MIGRATION COMPARISON WITHOUT OVERLAP ANALYSIS
NO PIPELINE MIGRATION COMPARISON WITHOUT EXPLICIT CLASSIFICATION
NO BRIDGE-REQUIRED COMPARISON WITHOUT A BRIDGE COHORT
NO DEFAULT POOLING AFTER REGIME RESET
NO CHAOS PROMOTION WITHOUT A CURRENT PHYSICAL-ADMISSIBILITY PASS
NO DELETION OF FAILED CHAOS CANDIDATES
```

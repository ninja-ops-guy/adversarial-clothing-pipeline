# Governance Pass 1 Closure — 2026-09-10

**Status:** PASS / CLOSED  
**Adopted contract:** `RAC_EXPERIMENTAL_GOVERNANCE_V1.md`  
**Verification commit:** `d7eed338e404dc287cce416147523dd37828112e`  
**Authoritative CI:** run #821 (`34515747476`)  
**Verification date:** 2026-09-10

## Closure decision

Governance Pass 1 is closed against the adopted Governance v1 contract. The earlier governance prototype already contained most of the required primitives, but its abbreviated identifiers and directly mutable lifecycle did not fully satisfy the adopted specification. The closure work hardened that existing namespace rather than introducing a parallel implementation.

## What is now enforced

- Canonical Governance v1 identifiers are emitted for new objects, including `RAC-GOV-EVT-*`, `RAC-COHORT-*`, `RAC-SAMP-*`, `RAC-CS-*`, `RAC-OVERLAP-*`, and `RAC-DIAG-*`.
- Pre-adoption abbreviated identifiers remain read-compatible aliases so prototype development records do not need to be rewritten.
- Alias and canonical spellings resolve to one semantic identity; duplicate event identities are rejected.
- Governance events carry separately bound payload and event SHA-256 digests plus previous-event chaining.
- Historical mutation is detected by chain verification.
- Reversal and supersession are append-only event relationships; corrective history does not edit the original event.
- Experiment lifecycle state is read-only outside the state machine.
- Every legal lifecycle transition appends a governance event before mutating in-memory state.
- Generic transition to `HALTED` is forbidden. HALT requires a structured invariant-conflict record identifying violated invariants, affected objects, evidence status, data-collection status, and required governance action.
- JSON Schema and semantic validators accept the adopted canonical identifier forms while retaining read compatibility for legacy aliases.
- Missing required fields, malformed identifiers, malformed hashes, invalid seeds, unsupported event types, invalid reversal/supersession relationships, illegal state transitions, and payload/history tampering fail closed.

## Exit-gate evidence

The Pass-1 test suite demonstrates the required happy path:

`DRAFT -> PREFLIGHT -> SEALED -> RUNNING -> COMPLETE`

Every transition is present in the append-only ledger.

A separate synthetic invariant conflict demonstrates:

`RUNNING -> HALTED`

The HALT is represented by a structured `HALT` governance event rather than a generic bypass.

Additional regression coverage verifies:

- previous-hash corruption is rejected;
- historical payload editing is rejected;
- reversal preserves the original event bytes/meaning and leaves the chain valid;
- unknown or future event references are rejected;
- canonical/legacy alias collisions cannot create two semantic event identities;
- direct lifecycle state assignment is unavailable;
- canonical constraint/overlap/diagnostic identifiers validate against their JSON Schemas;
- emitted governance events pass the semantic validator, while payload tampering fails.

## CI attestation

GitHub Actions run #821 completed successfully on commit `d7eed338e404dc287cce416147523dd37828112e`.

Passed jobs:

- package build;
- dependency audit;
- zero-install lightweight provenance verification;
- Python 3.10 full test/smoke/certification lane;
- Python 3.11 full test/smoke/certification lane;
- Python 3.12 full test/smoke/certification lane.

The Python 3.11 lane recorded **1,638 passed, 2 skipped** in the full suite and **12/12 certification tests passed**. Ruff also passed.

## Integration note

A Governance Pass-6 sampling/diagnostics merge landed while Pass 1 was being hardened. The Pass-1 closure changes were reconciled on top of that merge rather than force-updating `main`; run #821 therefore verifies the tightened Pass-1 contract together with the merged sampling layer.

This closure does not certify Passes 2-7. Existing later-pass modules may be prototypes or partially implemented and require their own adopted-contract audits/exit gates before their roadmap boxes are closed.

## Evidence boundaries unchanged

This governance closure is software/methodology infrastructure only. It does not:

- arm D2-0005;
- access new held-out outcomes;
- change scientific thresholds;
- modify frozen Pattern Genome v1;
- mutate D2-0003/D2-0004 or sealed releases;
- create physical evidence;
- support a physical-efficacy claim.

The external Production Alpha / calibration / P1 path remains the project-level critical path when its required user/vendor inputs are available.

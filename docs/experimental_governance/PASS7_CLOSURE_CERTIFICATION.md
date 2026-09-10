# Governance Pass 7 Closure Certification

Status: implementation-complete, CI-gated

This closure package exercises the final adaptive-governance invariants without altering frozen evidence or claiming physical efficacy.

## Certified flow

`sealed Wave N evidence -> frozen Wave N+1 policy -> sampling eligibility -> migration/regime decision -> next-wave construction`

The closure helper refuses unsealed prior-wave evidence, rejects current-wave outcome inputs, requires a frozen policy before sampling, and routes regime-reset comparisons through the existing fail-closed pooling prohibition.

## HALT rehearsal

The certification test constructs a governed experiment and intentionally triggers an invariant conflict. The experiment must enter `HALTED` only through the ledger-backed `halt_for_conflict()` path, and the conflict record must remain attached to the terminal state.

## Chaos lifecycle

Original failures remain immutable. Re-screening is appended as a new event; successful re-screening plus the physical-admissibility gate may create a new hypothesis event, but the original failure remains present in yield statistics.

## Scientific boundaries

This closure does not:

- mutate D2-0004;
- arm D2-0005;
- access held-out outcomes;
- change scientific thresholds;
- relax matched-null promotion rules;
- weaken the certification firewall;
- create RAC-P/RAC-M evidence;
- claim physical efficacy.

## Exit condition

Pass 7 is certifiable when the focused closure tests and repository CI pass on the merge commit. Until CI evidence is attached, this document records implementation closure rather than a global-green claim.

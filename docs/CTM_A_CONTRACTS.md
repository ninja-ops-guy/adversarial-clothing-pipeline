# CTM-A — Frozen Contracts, Anti-Optimization Invariant, Firewall, and Matched Nulls

**Schema family:** rac-ctm/1.0  
**Status:** implemented software contract; no CTM efficacy result is implied.

## Purpose

CTM-A is the contract layer for the Cumulative Transfer Map. It deliberately
does not optimize patterns or inspect new held-out outcomes. It defines what a
CTM claim is allowed to mean and makes held-out leakage a certification
failure rather than a policy statement.

## Claim ladder

1. **correlation** — a feature and outcome co-vary in a cohort.
2. **association** — the relationship replicates across at least two
   independent cohorts.
3. **controlled_effect** — the relationship is supported by a matched-property
   intervention/control design and at least two independent cohorts.

Replication alone cannot promote an unmatched association to
`controlled_effect`. Five unmatched replications remain an association.

## Matched-property nulls

v1 recognizes exactly:

- `NULL-COLOR-MATCHED`
- `NULL-SPECTRAL-MATCHED`
- `NULL-TOPOLOGY-MATCHED`

Every null binds candidate/null SHA-256s, one manipulated feature, the
properties held matched, a hash-pinned tolerance contract, and the design
commit. Candidate and null bytes must differ.

## Anti-optimization invariant

Artifacts with role `doe`, `generator`, or `acceptance` are pre-outcome
machinery. They must have:

- `heldout_access = false`
- `heldout_feedback_used = false`
- selection influence limited to `SURROGATE_ONLY` or `NOT_APPLICABLE`

Violation is a hard certification refusal.

## Mechanical provenance firewall

`certify_ctm_claim()` walks dependency edges from every pre-outcome artifact.
If any path reaches a node marked as a held-out observation
(`ctm_role=heldout_observation`, `heldout_observation=true`, or
`data_split=heldout`), certification fails.

This is stronger than a unit-test-only policy: the certification function
executes the firewall on every claim.

The dependency-edge vocabulary in v1 is frozen to:

- `consumes`
- `derived_from`
- `generated_from`
- `selected_by`
- `accepted_by`
- `uses_genome`
- `uses_null_design`
- `uses_surrogate_observation`

CTM graph convention: **source consumes/depends on target**.

## Versioning rule

The public v1 semantics are immutable. Any semantic change to claim levels,
firewall behavior, matched-null meaning, or required fields creates a new
version. Existing v1 records are never silently reinterpreted.

A v2 may add fields or alter promotion logic, but it must not rewrite v1
artifacts in place.

## Scientific boundary

CTM-A is infrastructure. It does not:

- arm D2-0005;
- alter D2-0004;
- access held-out models;
- change efficacy thresholds;
- assert a physical effect;
- treat Pattern Genome features as validated predictors.

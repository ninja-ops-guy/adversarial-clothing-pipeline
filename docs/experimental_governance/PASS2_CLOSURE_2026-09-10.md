# Governance Pass 2 Closure — 2026-09-10

**Status:** PASS / CLOSED  
**Adopted contract:** `RAC_EXPERIMENTAL_GOVERNANCE_V1.md` §6 and `IMPLEMENTATION_PASSES.md` Pass 2  
**Verification commit:** `7ff05187b223d7479a934bb6912799bb943e57f2`  
**Authoritative CI:** run #836 (`34517061829`)  
**Verification date:** 2026-09-10

## Closure decision

Governance Pass 2 is closed against the adopted constraint-lineage and scientific-impact contract. The pre-existing prototype correctly separated software versioning from a small scientific-impact enum, but it did not yet satisfy the adopted requirements for immutable registration, explicit three-axis impact analysis, preregistered tolerance policy, append-only migration recording, or protected frozen-D2 inputs.

The closure hardened the existing namespace rather than replacing it. The original `classify_migration()` API remains available as a compatibility wrapper for pre-adoption callers; prospective Governance v1 work uses the stricter adopted path.

## What is now enforced

### Immutable constraint lineage

- `ConstraintSet` remains a frozen scientific artifact.
- New prospective records serialize with canonical Governance v1 fields including `constraint_set_id`, `parent_constraint_set_id`, `encoder_version`, `scientific_projection_version`, and `scientific_impact`.
- Canonical constraint identity is `RAC-CS-*`; legacy `RAC-CST-*` identifiers remain read-compatible aliases only.
- `ConstraintSetRegistry` is append-only, canonicalizes aliases, rejects duplicate semantic identities, and requires a parent to be registered before a child.
- Prospective registry writes require an explicit encoder version; the legacy unspecified default is accepted only for read compatibility.

### Software version is not scientific compatibility

Scientific impact is represented independently as:

- `NONE`;
- `SEMANTIC_CORRECTION`;
- `POPULATION_CHANGE`;
- `DEFINITION_CHANGE`.

A patch-level software change therefore cannot suppress a measured population or cohort impact.

### Three-axis historical-impact analysis

`MigrationImpactAnalysis` requires all three adopted axes before prospective evidence reuse:

1. population displacement;
2. changed/total sealed-cohort specimens, with a derived change fraction;
3. estimand impact (`UNCHANGED` or `CHANGED`).

The decision output is an immutable `MigrationDecisionRecord` carrying the measured axes, scientific-impact class, tolerance-policy hash, and one formal migration outcome:

- `NO_IMPACT`;
- `MINOR_CORRECTION`;
- `BRIDGE_REQUIRED`;
- `COHORT_INVALIDATION`;
- `NEW_REGIME`.

A semantic definition change or estimand change always yields `NEW_REGIME`; numerical tolerance cannot override it.

### Preregistered tolerance policy

`TolerancePolicy` is constraint-family-specific, time-stamped, hash-bound, and requires an explicit attestation that it was registered before outcome inspection. Numerical population/cohort materiality thresholds must remain in `[0,1]` and are sealed into the migration record by SHA-256.

A dedicated JSON Schema is committed at `ruthless_pipeline/governance/schemas/tolerance_policy.schema.json`. The constraint-set schema and shared semantic validator now both accept the adopted canonical record while retaining legacy-read compatibility.

### Append-only migration record

`record_migration_decision()` writes the complete decision into the Governance Pass-1 ledger as a `CONSTRAINT_MIGRATION` event. The predecessor constraint set is not edited.

Before a migration event can be appended, the adapter requires before/after content-hash snapshots for the protected pre-Governance D2 artifacts and refuses the event if any protected input is missing or changed.

Protected identifiers currently include:

- `RAC-PER-D2-0003`;
- `RAC-PER-D2-0004`;
- the frozen D2-0005 preregistration reference.

This is a software guard against migration code silently rewriting the historical evidence basis; it does not change those artifacts.

## Exit-gate evidence

The adopted Pass-2 tests demonstrate a synthetic encoder-correction lineage:

`RAC-CS-PASS2-LOG-001 -> RAC-CS-PASS2-LOG-002`

with:

- a patch-level software/encoder update;
- explicit population, cohort, and estimand impact analysis;
- a preregistered tolerance-policy hash;
- a formal `MINOR_CORRECTION` decision;
- a `CONSTRAINT_MIGRATION` ledger event containing that decision;
- the predecessor constraint record unchanged after the operation;
- the governance hash chain still valid.

Additional coverage verifies:

- parent-first immutable registration;
- canonical/legacy alias collision rejection;
- prospective encoder-version requirement;
- JSON Schema and semantic-validator agreement for adopted constraint records;
- tolerance policy schema/semantic validation;
- population change remains scientifically material despite a software patch version;
- definition or estimand change forces `NEW_REGIME` even under permissive numerical tolerances;
- `NONE` cannot hide measured population/cohort change;
- family mismatch between impact analysis and tolerance policy fails closed;
- changed or missing frozen-D2 snapshots refuse migration logging before ledger append.

## CI attestation

GitHub Actions run #836 completed successfully on commit `7ff05187b223d7479a934bb6912799bb943e57f2`.

Passed jobs:

- package build;
- dependency audit;
- zero-install lightweight provenance verification;
- Python 3.10 full test/smoke/certification lane;
- Python 3.11 full test/smoke/certification lane;
- Python 3.12 full test/smoke/certification lane.

The Python 3.11 lane recorded **1,653 passed, 2 skipped** in the repository-wide suite and **12/12 certification tests passed**. Ruff and the smoke test also passed.

Two subsequent commits added the independent Printful vendor-snapshot P0 workstream. They are descendants of the verified Pass-2 commit and do not modify the governance files covered by this closure.

## Evidence boundaries unchanged

Pass 2 is governance/methodology infrastructure only. It does not:

- arm D2-0005;
- access new held-out outcomes;
- change scientific efficacy thresholds;
- mutate Pattern Genome v1;
- rewrite D2-0003, D2-0004, or the frozen D2-0005 preregistration;
- create P1/P2/M1/M2 physical or manufacturing evidence;
- support a physical-efficacy claim.

## Next governance gate

Pass 3 remains open. Existing `seal.py` and CTM intake code are prototypes until audited against the adopted seal/reproducibility requirements, including complete manifest enforcement, referential integrity, source commit/seed/pipeline/calibration binding, diagnostic-threshold binding, deterministic seal identity, and clean-checkout failure cases.

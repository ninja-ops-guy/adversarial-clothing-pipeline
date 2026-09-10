# CTM Lanes B–D Integration Audit — 2026-09-10

**Scope:** Reconcile implemented CTM Lanes B–D against the revised CTM hardening proposal after P1 no-spend readiness closure.

## Result

**CTM_BD_INTEGRATION_AUDIT = PASS_WITH_FOREIGN_CI_BLOCKER**

Two material semantic mismatches were found and corrected. Lane C and the SPEC-16 evidence ceiling were already consistent with the revised contract.

## Corrected mismatch 1 — SPEC-11 mechanism classification

The prior `is_architecture_accident_bound()` implementation treated every mechanism with lower expected-generality rank than `task_invariant` as architecture-accident-bound. That incorrectly classified `training_data`, `pipeline_structure`, `physics`, and `hardware` mechanisms.

Correct invariant:

> Expected generality and mechanism class are separate semantics. Only the explicit `architecture_accident` mechanism class is architecture-accident-bound.

Regression coverage now iterates the entire mechanism enum and requires exactly one positive class.

Relevant commits:

- `03afeb3b` — initial semantic correction.
- `f21857d1` — regression test.
- `8c177857` — restored the parent file structure/comments and reduced the production diff to the intended classification change.

## Corrected mismatch 2 — SPEC-7 metadata validity and sealed-decision verification

The prior retro-mining gate documented poor channel metadata/comparability as a reason to `RESCOPE`, but `FamilyResult` did not encode channel/provenance adequacy. Therefore the rule was not mechanically enforceable.

The prior sealed-decision verifier also validated schema/hash integrity but did not fully reconstruct the preregistered decision logic. A mutated decision plus a recomputed digest was therefore not as strongly bound to the generating evidence as the revised specification requires.

The additive `rac-ctm-retro-decision/1.1` contract now:

- requires `channel_metadata_adequate` on every family result;
- requires `provenance_adequate` on every family result;
- records explicit `metadata_gaps`;
- forces metadata-inadequate families to `RESCOPE`, even if an incremental signal is reported;
- makes `REJECT_HYPOTHESIS_FAMILY` illegal when channel metadata or provenance is inadequate;
- embeds the preregistration payload in the sealed decision;
- hash-binds that embedded preregistration to its declared preregistration hash/id;
- reconstructs every family result and fully re-runs `seal_decision()` during `verify_decision()`;
- therefore rejects a forged decision even if an attacker recomputes `report_sha256` and `decision_id`.

Relevant commits:

- `0fc08a50` — additive decision schema v1.1.
- `d3df2144` — retro-mining validity and full re-derivation.
- `7798b690` — expanded regression tests.

The old v1 schema remains present and untouched; new decisions use the additive v1.1 contract.

## Reviewed and accepted without corrective changes

### SPEC-10 — channel / camera / ISP semantics

The existing channel layer already treats camera/ISP identity as a first-class validity factor, separates inferred/unknown metadata from observed metadata, and applies conservative claim ceilings when physical channel identity is incomplete.

### SPEC-16 — external physical cohort

The existing external-cohort layer already uses the dedicated `external_physical_observation` evidence class and prevents secondary physical imagery from becoming CTM-controlled physical-efficacy evidence. External fabrication deltas remain exploratory/observational unless separate CTM physical-channel requirements are satisfied.

### Lane C — research-integrity layer

Reviewed surfaces already conform to the revised proposal:

- cascade-stage scope is structural for efficacy/robustness/transfer claims;
- citation verification distinguishes abstract-only vs. full-text/reproduced evidence and gates load-bearing citations;
- corpus entries and snapshots are content-addressed;
- survey taxonomy mappings are explicit;
- manuscript positioning is pinned to a verified corpus snapshot rather than handwritten comparison claims;
- universal-negative manuscript language is corpus-bounded and snapshot-referenced.

## Scientific boundaries

This audit did **not**:

- modify Pattern Genome v1;
- arm D2-0005;
- access held-out evidence;
- change scientific thresholds or decision-rule values;
- make a physical-efficacy claim;
- execute P1 physical work;
- alter P1 UA values.

## CI disposition

Current CI is blocked before pytest by a **pre-existing foreign lint failure**:

```text
F821 Undefined name `PLACEHOLDER_TESTS`
 --> tests/test_barrier3_rehearsal.py:1:1
1 | PLACEHOLDER_TESTS
```

The same failure is reproduced on the pre-audit parent head `d43f9077`, so it was not introduced by this integration audit. Per seam-reconciliation rules, this audit does not opportunistically repair that unrelated Barrier-3 surface.

Build, package, dependency-audit, and Pages/deploy checks reached success on the audited head before the Python matrix stopped at the foreign Ruff gate. Pytest cannot provide a fresh repository-wide result until the upstream placeholder is restored by its owning lane.

## Remaining action

The owning Barrier-3/governance lane should restore `tests/test_barrier3_rehearsal.py` from its substantive version or otherwise resolve the placeholder provenance. After that repair, rerun the full Python matrix and CTM tests; no CTM B–D semantic blocker remains from this audit.

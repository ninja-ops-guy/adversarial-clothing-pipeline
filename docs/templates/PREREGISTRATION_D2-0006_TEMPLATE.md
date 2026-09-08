# TEMPLATE — Preregistration — RAC-PER-D2-0006: Prospective Replication

> **How to use this template.** This is the mandatory structural skeleton for
> the future D2-0006 preregistration. It becomes a preregistration ONLY via
> the mechanical ceremony of `docs/PREREGISTRATION_D2-0006_DRAFT.md` §6 —
> after D2-0005 has closed (or been formally discontinued) and its release
> has been cut per `docs/RESEARCH_RELEASE_FORMAT.md`. Until then, every
> `{{SLOT}}` below MUST remain unfilled. Filling any slot early is a
> governance violation (retrofitting the replication agenda to an unobserved
> or partially observed outcome). Validated by
> `ruthless_pipeline/certification/d20006_governance.py::validate_preregistration_document`
> and `scripts/validate_d20006_readiness.py`; a document with unfilled slots
> fails validation.

**Status:** TEMPLATE — NOT A PREREGISTRATION. Filling and freezing this
document arms nothing (policy §6 step 5: model-lock freeze, generation
skeleton, and trigger arming are separate, later, individually reviewed
changes).
**Generation:** RAC-PER-D2-0006 (replication generation; no generation
skeleton file exists or may be created at this stage — policy §5).
**Depends on:** D2-0005 closed (or formally discontinued) and released;
branch selection memo `{{BRANCH_MEMO_SHA256}}` produced by
`scripts/d20006_branch_router.py` against the frozen interpretation policy.

---

## 1. Selected branch and closure evidence (fill per policy §6 step 2)

- **Selected interpretation-policy branch:** `{{SELECTED_BRANCH}}` (one of
  2.1 SUCCESS / 2.2 NULL / 2.3 NEGATIVE / 2.4 INCONCLUSIVE / 2.5
  INFRASTRUCTURE FAILURE), cited verbatim from the frozen tree.
- **Branch-selection memo SHA-256:** `{{BRANCH_MEMO_SHA256}}`.
- **D2-0005 closure evidence:** sealed release id, content_hash, and the
  preregistered analysis's decision-region output — referenced, never
  reinterpreted.
- **Timing disclosure (policy §6 step 6):** the §2 tree was committed at
  commit `{{TREE_COMMIT_SHA}}`, before D2-0005 closed.

## 2. Hypothesis (unblocked only after D2-0005 closes)

- **Directional hypothesis:** `{{HYPOTHESIS}}`
  - Form is dictated by the selected branch: directional same-sign (2.1),
    equivalence/bounds claim with a justified SESOI (2.2), directional
    reversed-sign (2.3), or the form chosen by the amended design's decision
    regions (2.4). Under branch 2.5 this field stays blocked until the
    authorized re-run closes under §2.1–§2.4 semantics.
  - Evidence label pre-execution: `target`.

## 3. Protocol, model sets, seeds

- **Protocol:** `{{PROTOCOL_VERSION}}` (RAC-PERSON-DETECT lineage; any
  revision recorded as a documented design parameter).
- **Surrogate model set:** `{{SURROGATE_MODEL_SET}}`.
- **Held-out model set:** `{{HELDOUT_MODEL_SET}}` — fresh held-out
  conditions, disjoint from D2-0005's; **PERSON-HO-v3 is never reused as a
  held-out set**.
- **Fresh candidate pool seed:** `{{POOL_SEED}}` — never the D2-0005
  seed-1337 pool.

## 4. Decision regions

- **Decision regions:** `{{DECISION_REGIONS}}`
  - Anchored on D2-0005's sealed observed interval and/or the
    operating-characteristic evidence (labeled `scenario_assumption`), never
    on desired outcomes. State the success/null/negative/inconclusive
    regions and the width budget explicitly.

## 5. Budgets and caps

- **Budget caps:** `{{BUDGET_CAPS}}` — candidate count, search budget,
  protocol grid size, observation-unit/cluster count, seeds, compute and
  re-run budgets. Fixed here, informed by the design analysis where
  relevant; never tuned to a desired result.

## 6. Runtime and lock references

- **Runtime lock reference:** `{{RUNTIME_LOCK_REFERENCE}}` (the
  `benchmarks/runtime_lock.json` hard-gate pattern; the re-run/runtime
  pinning discipline of AMENDMENT_D2-0004-INFRA-001 §6).
- Model-lock freeze under `model-lock-bootstrap` is a separate, later,
  reviewed change; it is referenced here once executed, not anticipated.

## 7. Infrastructure-failure clause (mandatory, adopts policy §2.5 by reference)

- **Infrastructure-failure clause:** this preregistration adopts the
  infrastructure-failure policy of `docs/PREREGISTRATION_D2-0006_DRAFT.md`
  §2.5 **by reference, in full, before D2-0006 executes**: the
  outcome-never-observed criterion, the exactly-one-rerun discipline, the
  prohibition on scientific parameter changes in any re-run, the root-cause
  record requirement, and the published failure disclosure, following the
  `docs/AMENDMENT_D2-0004_INFRA-001.md` pattern. Any D2-0006 infrastructure
  failure is handled ONLY through this clause.

## 8. Evidence labels and publication commitment

- Closed results `internally_measured`; pre-execution hypothesis `target`;
  mechanistic interpretations `speculative_open`; transfer beyond the fresh
  held-out set `external_replication_needed`; design-analysis/OC numbers
  `scenario_assumption`.
- **All branches publish.** Publication is never conditional on the result
  supporting the program's thesis; null, negative, inconclusive, and
  infrastructure-failure records are publishable closed-generation
  datapoints per `docs/RESEARCH_RELEASE_FORMAT.md`.

## 9. Amendment log

Pre-arming amendments are permitted and recorded here with rationale; silent
changes are not. Post-arming changes are forbidden (D2-0005 §7/§9 semantics,
inherited).

# DRAFT — D2-0006 Prospective Replication: Predeclared Interpretation Policy

**Status: DRAFT — NOT A PREREGISTRATION.** This document does **not** arm, trigger, open, or preregister any experiment. It preregisters **no directional hypothesis**. It exists so that the *policy* for choosing the D2-0006 hypothesis is fixed **before** D2-0005 closes, rather than being retrofitted to D2-0005's observed outcome. The exact D2-0006 hypothesis, effect-size regions, and budgets are decided **later**, via a documented pre-arming preregistration, only after D2-0005 closes (§3, §5).

**Depends on:** D2-0005 (`docs/PREREGISTRATION_D2-0005.md`) — preregistered, not yet executed; itself gated on D2-0004 closing first. D2-0006 cannot be opened, executed, or trigger-wired until D2-0005 has closed and its release has been cut per `docs/RESEARCH_RELEASE_FORMAT.md`.

---

## 1. Purpose

D2-0006 is the prospective **replication** generation of the RAC research program.

Replication is where research programs most often decay into post-hoc storytelling: the team sees the result of the controlled experiment and then chooses the "next experiment" that best flatters it — retesting a success under friendlier conditions, quietly dropping a negative line, or re-running an inconclusive design until it says something. The purpose of this document is to remove that freedom in advance.

**The exact hypothesis of D2-0006 is selected ONLY after D2-0005 closes, and it is selected mechanically, according to the interpretation-policy decision tree in §2, keyed to the preregistered D2-0005 decision regions (§4 of `PREREGISTRATION_D2-0005.md`).** The tree — not the D2-0005 outcome — is what is frozen now. Once D2-0005 closes, its closed decision region is looked up, and the corresponding branch of §2 determines the *form* of the D2-0006 hypothesis. Only then is the hypothesis written, made directional where the branch calls for directionality, and preregistered before D2-0006 opens.

This is the prospective analogue of D2-0005's own one-shot rule, applied one level up: the *experimental agenda itself* is not open to post-hoc revision.

---

## 2. The interpretation-policy decision tree

The tree is keyed **exactly** to the four preregistered decision regions of D2-0005 §4. Let Δ = R_M − R_C (mean held-out detection rate, Arm M minus Arm C) with its preregistered 95% two-sided CI from `paired_arm_statistics` (Wilson z = 1.959963984540054; deterministic bootstrap, 10000 resamples, seed 20260907). WILSON_WIDTH_MAX = 0.20.

### 2.1 If D2-0005 closes as SUCCESS

*Region: Δ > 0 with CI lower bound > 0 — CVaR superiority (Arm C held-out detection rate significantly below Arm M's, one-sided in the preregistered direction).*

**D2-0006 replicates CVaR superiority on a FRESH generation:**

- **Fresh candidate pool** — a new pool, new seed; never the D2-0005 seed-1337 pool.
- **Fresh held-out conditions** — a new held-out set (new held-out detector architectures and/or new condition grid), disjoint from PERSON-HO-v3; never a re-run of D2-0005's held-out fixtures.
- **Same protocol family** — RAC-PERSON-DETECT protocol lineage; any protocol revision is recorded as a documented design parameter, not silently substituted.
- **Hypothesis form: directional** (H1′: same-sign effect — CVaR transfers better than mean), preregistered **before D2-0006 opens**.
- **Success criterion: same-sign effect with CI excluding 0.** The exact decision region is defined at D2-0006 preregistration time, and it must be **informed by the D2-0005 observed effect size and interval — not by desired outcomes**. I.e., the replication region is set relative to what D2-0005 actually measured (e.g., a point estimate and a width budget anchored on the D2-0005 interval), never re-derived to make a borderline expected result come out "significant".

### 2.2 If D2-0005 closes as NULL

*Region: CI includes 0 (either sign), width within budget — an informative null.*

**D2-0006 tests whether the interval meaningfully excludes the desired effect — an equivalence / minimum-effect framing:**

- The hypothesis becomes a **bounds claim**: that any true effect is smaller than a preregistered **smallest effect size of interest (SESOI)**, or equivalently that |Δ| lies inside a preregistered equivalence margin.
- The **exact SESOI is fixed at D2-0006 preregistration time**, justified from D2-0005's closed interval and from what effect magnitude would matter for the program's downstream claims — never tuned to guarantee the equivalence test passes.
- Fresh candidate pool and fresh held-out conditions, per §3.

### 2.3 If D2-0005 closes as NEGATIVE

*Region: CI entirely below 0 — reversal: the mean objective transfers better than CVaR.*

**D2-0006 investigates the REVERSAL:**

- **Confirm the reversal** on a fresh generation (fresh pool, fresh held-out conditions): directional hypothesis of the *reversed* sign, preregistered before D2-0006 opens.
- Add **mechanistic secondary endpoints from the objective telemetry** (the sealed `--objective-telemetry` artifacts mandated by D2-0005 §5 amendment A4): per-checkpoint CVaR tail membership and turnover, mean-vs-CVaR candidate rank changes, ensemble dispersion — used to characterize *why* worst-case optimization transferred worse. Mechanistic interpretations remain labeled `speculative_open`; the telemetry endpoints are descriptive unless a confirmatory claim is separately preregistered.
- **No-silent-abandonment rule:** the CVaR line is never quietly dropped after a reversal. Either it is investigated (this branch), or its discontinuation is itself documented as a governance decision with reasons, in writing.

### 2.4 If D2-0005 closes as INCONCLUSIVE

*Region: risk-difference interval width > 0.20, or valid-trial counts below the stopping-rule minimum.*

- The inconclusive D2-0005 is **still published as a closed datapoint** (its arm-level rates with Wilson intervals, per D2-0005 §4). It is never re-run silently.
- **D2-0006 is a design-amended generation**, informed by the design-analysis capability table in `docs/DESIGN_ANALYSIS_D2-0005.md` **when that document exists** (it is produced after D2-0005 closes; at the time of this DRAFT it does not yet exist). Example design amendments: more observation units (larger condition grid / more held-out models / more fixture crops), or a different inferential-unit definition, targeted at shrinking interval width below the width budget.
- Every design amendment is **documented as an amendment** in the D2-0006 preregistration, with its rationale traceable to the design analysis — not to a desired sign or magnitude of effect.
- The D2-0006 hypothesis in this branch is set after the design analysis exists; its form (directional replication or equivalence) is chosen per the amended design's decision regions at preregistration time.

---

## 3. What is frozen NOW vs decided LATER

### Frozen now (by committing this interpretation policy)

1. **The decision tree itself (§2)** — the mapping from D2-0005's four preregistered decision regions to the *form* of the D2-0006 experiment. This mapping may be amended only via a documented, hash-committed amendment **before D2-0005 closes**; once D2-0005 has closed, the tree is applied, not edited.
2. **The no-silent-abandonment rule** — no result region (including negative and inconclusive) permits quietly discontinuing the line of inquiry.
3. **The fresh-generation requirement** — D2-0006 always uses a **new candidate pool (new seed) and fresh held-out conditions**, disjoint from D2-0005's. D2-0006 is **never a re-run of D2-0005** on the same pool or the same held-out set. (Replication of a *finding* requires new data; re-running the same fixtures would only re-measure the same artifact.)
4. **Evidence-label commitments** — D2-0006 results, once closed, are labeled `internally_measured` per the repo's six-label governance (D2-0005 §7 amendment A1 semantics); cross-architecture transfer claims beyond the fresh held-out set remain `external_replication_needed`; mechanistic interpretations remain `speculative_open`; the pre-execution hypothesis is `target`.
5. **Publication commitment for null and negative results** — a null, negative, or inconclusive D2-0006 is a publishable closed-generation datapoint, released per `docs/RESEARCH_RELEASE_FORMAT.md` with `FAILURE.json`/revision-log semantics where applicable. Publication is not conditional on the result supporting the program's thesis.

### Decided later (after D2-0005 closes, via a documented pre-arming preregistration)

1. The **exact directional hypothesis** of D2-0006 (or equivalence/bounds claim, per the selected branch).
2. The **effect-size regions**: the exact success region informed by the D2-0005 effect size (success branch), the exact SESOI (null branch), the reversal-confirmation region (negative branch), or the amended width budget (inconclusive branch).
3. The **budgets**: candidate count, search budget, protocol grid size, observation-unit count, seeds — all fixed in the D2-0006 preregistration, informed by the design analysis where relevant.

Nothing in the "decided later" list may be filled in before D2-0005 closes; filling any of it early converts this policy into the post-hoc storytelling it exists to prevent.

---

## 4. Relationship to the research program

D2-0006 is the replication link in the longitudinal structure that Paper 1 reports:

| Generation | Role | Status at time of this DRAFT |
|---|---|---|
| D2-0003 | Retained **negative** result — published falsifying datapoint, not discarded | closed |
| D2-0004 | **Prospective closure** + canonical release (first fully preregistered measured generation) | closing |
| D2-0005 | **Controlled ablation** — mean vs CVaR_0.5 objective at final selection, fully paired | PREREGISTERED, not executed |
| D2-0006 | **Replication** — prospective, hypothesis form selected by this policy after D2-0005 closes | this DRAFT; not preregistered |

The scientific content of Paper 1 is this *sequence*, not any single generation: a program that keeps its negatives (D2-0003), preregisters before executing (D2-0004, D2-0005), publishes nulls, and replicates on fresh generations under a predeclared interpretation policy (D2-0006). A D2-0006 that replicated D2-0005's conditions on the same fixtures, or whose hypothesis was chosen after seeing D2-0005's numbers, would damage precisely the claim the paper makes.

---

## 5. Explicit non-goals

- This draft **does not arm, trigger, or preregister anything.** No generation skeleton, no lock freeze, no trigger revision, no CI wiring.
- **CI-safety of committing this document:** `measured-benchmark.yml` triggers **only** on the `generations/RAC-PER-D2-0004.json` path. This DRAFT touches no generation file and no workflow; committing it cannot fire the benchmark pipeline. The same discipline that keeps the D2-0005 skeleton inert (trigger fields present but NOT armed) applies here in stronger form: there is no D2-0006 generation file at all.
- This draft does not select, hint at, or constrain the *sign* of any future hypothesis beyond what the §2 tree dictates from D2-0005's closed region.
- This draft does not amend D2-0005's preregistration in any way; the D2-0005 amendment log (§9 there) is the only place D2-0005 changes are recorded.
- This draft makes no claim that D2-0006 will be executed; execution requires D2-0005 closed, its release cut, a fresh model-lock freeze under `model-lock-bootstrap`, a D2-0006 preregistration, and an explicit trigger arming in separately reviewed changes.

---

## 6. Deviation and amendment policy for this document

- Amendments to §2 (the tree) or §3 (the frozen commitments) are permitted **only before D2-0005 closes**, must be documented here with rationale, and must never be made in response to partial or leaked information about D2-0005's outcome.
- After D2-0005 closes, this document is applied as-is; any change to the tree at that point is treated as a governance violation, disclosed as such, and the affected downstream claim is labeled `scenario_assumption` or invalidated, per the deviations semantics of D2-0005 §7.

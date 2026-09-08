# DRAFT — D2-0006 Prospective Replication: Predeclared Interpretation Policy

**Status: DRAFT — NOT A PREREGISTRATION.** This document does **not** arm, trigger, open, or preregister any experiment. It preregisters **no directional hypothesis**. It exists so that the *policy* for choosing the D2-0006 hypothesis is fixed **before** D2-0005 closes, rather than being retrofitted to D2-0005's observed outcome. The exact D2-0006 hypothesis, effect-size regions, and budgets are decided **later**, via a documented pre-arming preregistration, only after D2-0005 closes (§3, §6).

**Directional hypothesis field: `BLOCKED until D2-0005 closes`.** Reason: selecting the hypothesis (or its sign, or its effect-size regions) before D2-0005's decision region is known would retrofit the replication agenda to an observed outcome — the exact failure mode this policy exists to prevent. The field is unblocked mechanically by §6 only after D2-0005 has closed and its release has been cut.

**Depends on:** D2-0005 (`docs/PREREGISTRATION_D2-0005.md`) — preregistered, not yet executed; itself gated on D2-0004 closing first. D2-0006 cannot be opened, executed, or trigger-wired until D2-0005 has closed and its release has been cut per `docs/RESEARCH_RELEASE_FORMAT.md`.

---

## 1. Purpose

D2-0006 is the prospective **replication** generation of the RAC research program.

Replication is where research programs most often decay into post-hoc storytelling: the team sees the result of the controlled experiment and then chooses the "next experiment" that best flatters it — retesting a success under friendlier conditions, quietly dropping a negative line, or re-running an inconclusive design until it says something. The purpose of this document is to remove that freedom in advance.

**The exact hypothesis of D2-0006 is selected ONLY after D2-0005 closes, and it is selected mechanically, according to the interpretation-policy decision tree in §2, keyed to the preregistered D2-0005 decision regions (§4 of `PREREGISTRATION_D2-0005.md`).** The tree — not the D2-0005 outcome — is what is frozen now. Once D2-0005 closes, its closed decision region is looked up, and the corresponding branch of §2 determines the *form* of the D2-0006 hypothesis. Only then is the hypothesis written, made directional where the branch calls for directionality, and preregistered before D2-0006 opens.

This is the prospective analogue of D2-0005's own one-shot rule, applied one level up: the *experimental agenda itself* is not open to post-hoc revision.

---

## 2. The interpretation-policy decision tree

The tree has **five explicit branches**. Branches 2.1–2.4 are keyed **exactly** to the four preregistered decision regions of D2-0005 §4; branch 2.5 (INFRASTRUCTURE FAILURE) is keyed not to an outcome but to a *failure class* — an execution that produces no outcome at all — and follows the precedent of `docs/AMENDMENT_D2-0004_INFRA-001.md`. Let Δ = R_M − R_C (mean held-out detection rate, Arm M minus Arm C) with its preregistered 95% two-sided CI from `paired_arm_statistics` (Wilson z = 1.959963984540054; deterministic bootstrap, 10000 resamples, seed 20260907). WILSON_WIDTH_MAX = 0.20.

Every branch shares the following predeclared commitments (restated per branch for completeness, frozen once in §3):

- **Fresh-generation requirement** — D2-0006 always uses a new candidate pool (new seed) and fresh held-out conditions, disjoint from D2-0005's. The held-out set is **never PERSON-HO-v3 as the held-out set** and never a re-run of D2-0005's held-out fixtures; HO-v3 models may appear only in the *surrogate/training* side of a future generation if a future design explicitly re-roles them and documents it (HO-v3 may never again serve as *held-out* evidence for any RAC generation that has touched it).
- **Evidence labels** — closed D2-0006 results are `internally_measured`; the pre-execution hypothesis is `target`; mechanistic interpretations are `speculative_open`; cross-architecture transfer claims beyond the fresh held-out set are `external_replication_needed`; design-analysis numbers remain `scenario_assumption` (D2-0005 §7 amendment A1 semantics).
- **Publication commitment — all branches publish.** Every closed branch (success, null, negative, inconclusive, or infrastructure-failure record) is a publishable closed-generation datapoint, released per `docs/RESEARCH_RELEASE_FORMAT.md` with `FAILURE.json`/revision-log semantics where applicable. Publication is never conditional on the result supporting the program's thesis.
- **Budget caps: TBD** — candidate count, search budget, protocol grid size, observation-unit/cluster count, seeds, and compute caps are **TBD placeholders** in this DRAFT, fixed only in the D2-0006 preregistration (§6), informed by the design analysis where relevant — never tuned to a desired result.

### 2.1 If D2-0005 closes as SUCCESS

*Region: Δ > 0 with CI lower bound > 0 — CVaR superiority (Arm C held-out detection rate significantly below Arm M's, one-sided in the preregistered direction).*

**D2-0006 replicates CVaR superiority on a FRESH generation:**

- **Next-generation requirements:**
  - **Fresh candidate pool** — a new pool, new seed; never the D2-0005 seed-1337 pool.
  - **Fresh held-out conditions** — a new held-out set (new held-out detector architectures and/or new condition grid), disjoint from PERSON-HO-v3; never a re-run of D2-0005's held-out fixtures.
  - **Same protocol family** — RAC-PERSON-DETECT protocol lineage; any protocol revision is recorded as a documented design parameter, not silently substituted.
  - **Hypothesis form: directional** (H1′: same-sign effect — CVaR transfers better than mean), preregistered **before D2-0006 opens**.
  - **Success criterion: same-sign effect with CI excluding 0.** The exact decision region is defined at D2-0006 preregistration time, and it must be **informed by the D2-0005 observed effect size and interval — not by desired outcomes**. I.e., the replication region is set relative to what D2-0005 actually measured (e.g., a point estimate and a width budget anchored on the D2-0005 interval), never re-derived to make a borderline expected result come out "significant".
- **Evidence labels:** hypothesis `target` until armed; closed result `internally_measured`; transfer beyond the fresh held-out set `external_replication_needed`.
- **Publication commitment:** published regardless of whether replication succeeds; a failed replication after a D2-0005 success is itself a headline datapoint about the finding's robustness.
- **Budget caps: TBD** (fixed at D2-0006 preregistration; must be adequate to the replication region anchored on the D2-0005 interval, per the design-analysis route of §2.4 where applicable).

### 2.2 If D2-0005 closes as NULL

*Region: CI includes 0 (either sign), width within budget — an informative null.*

**D2-0006 tests whether the interval meaningfully excludes the desired effect — an equivalence / minimum-effect framing:**

- **Next-generation requirements:**
  - The hypothesis becomes a **bounds claim**: that any true effect is smaller than a preregistered **smallest effect size of interest (SESOI)**, or equivalently that |Δ| lies inside a preregistered equivalence margin.
  - The **exact SESOI is fixed at D2-0006 preregistration time**, justified from D2-0005's closed interval and from what effect magnitude would matter for the program's downstream claims — never tuned to guarantee the equivalence test passes.
  - Fresh candidate pool and fresh held-out conditions, per the shared requirements above (never PERSON-HO-v3 as held-out).
- **Evidence labels:** bounds claim `target` until armed; closed result `internally_measured`.
- **Publication commitment:** published as an informative-null/equivalence datapoint; the equivalence result is reported with its SESOI justification intact, whether or not equivalence is established.
- **Budget caps: TBD** (sized at preregistration so the equivalence test has adequate precision against the chosen SESOI).

### 2.3 If D2-0005 closes as NEGATIVE

*Region: CI entirely below 0 — reversal: the mean objective transfers better than CVaR.*

**D2-0006 investigates the REVERSAL:**

- **Next-generation requirements:**
  - **Confirm the reversal** on a fresh generation (fresh pool, fresh held-out conditions; never PERSON-HO-v3 as held-out): directional hypothesis of the *reversed* sign, preregistered before D2-0006 opens.
  - Add **mechanistic secondary endpoints from the objective telemetry** (the sealed `--objective-telemetry` artifacts mandated by D2-0005 §5 amendment A4): per-checkpoint CVaR tail membership and turnover, mean-vs-CVaR candidate rank changes, ensemble dispersion — used to characterize *why* worst-case optimization transferred worse. Mechanistic interpretations remain labeled `speculative_open`; the telemetry endpoints are descriptive unless a confirmatory claim is separately preregistered.
  - **No-silent-abandonment rule:** the CVaR line is never quietly dropped after a reversal. Either it is investigated (this branch), or its discontinuation is itself documented as a governance decision with reasons, in writing.
- **Evidence labels:** reversed-direction hypothesis `target` until armed; closed result `internally_measured`; mechanistic commentary `speculative_open` unless separately preregistered.
- **Publication commitment:** published; the reversal and its telemetry-mechanistic characterization are reported in full. The no-silent-abandonment rule makes non-publication a governance violation.
- **Budget caps: TBD** (fixed at D2-0006 preregistration; telemetry collection is mandatory, not budget-optional, under the A4 pattern).

### 2.4 If D2-0005 closes as INCONCLUSIVE

*Region: risk-difference interval width > 0.20, or valid-trial counts below the stopping-rule minimum.*

- **Next-generation requirements:**
  - The inconclusive D2-0005 is **still published as a closed datapoint** (its arm-level rates with Wilson intervals, per D2-0005 §4). It is never re-run silently.
  - **D2-0006 is a design-amended generation**, informed by the pre-arming operating-characteristic evidence: `docs/DESIGN_ANALYSIS_D2-0005.md` (the F0 unit-level OC study — which showed the frozen n = 72 design is INCONCLUSIVE-dominated, P(INCONCLUSIVE) = 1.000 at every simulated Δ_true, and flagged pseudoreplication among the 72 clustered units) and, where executed, the cluster-robust redesign evidence of the Wave H proposal (`docs/DESIGN_AMENDMENT_D2-0005_PROPOSAL.md`; cluster-aware OC study: inferential unit redefined as the independent image cluster, K ≥ 108 clusters for P(SUCCESS) ≥ 0.8 at Δ_true = +0.2 under ρ = 0.5; within-cluster replication does not substitute for cluster count). All such OC numbers remain `scenario_assumption` — synthetic DGPs, not measurements — but they are the legitimate, outcome-independent basis for sizing the amended design.
  - Every design amendment is **documented as an amendment** in the D2-0006 preregistration, with its rationale traceable to the design analysis — not to a desired sign or magnitude of effect. If D2-0005 itself was design-amended pre-arming (e.g., via the proposed A5 cluster-robust amendment), D2-0006 inherits the amended design family rather than re-deriving it.
  - The D2-0006 hypothesis in this branch is set after the applicable design analysis is consulted at preregistration time; its form (directional replication or equivalence) is chosen per the amended design's decision regions at preregistration time.
  - Fresh candidate pool and fresh held-out conditions per the shared requirements (never PERSON-HO-v3 as held-out); sizing is done in independent inferential units (clusters), not views, per the F0/cluster-OC evidence.
- **Evidence labels:** design-analysis numbers `scenario_assumption`; hypothesis `target` until armed; closed result `internally_measured`.
- **Publication commitment:** both the inconclusive D2-0005 and the design-amended D2-0006 are published; the amendment rationale is published alongside, traceable to the OC evidence.
- **Budget caps: TBD** (fixed at D2-0006 preregistration from the OC capability table — e.g., cluster count K — targeted at shrinking interval width below the width budget; never at changing the width gate, α, or decision regions).

### 2.5 If D2-0005 (or D2-0006, once opened) ends in INFRASTRUCTURE FAILURE

*Failure class, not an outcome region: the execution fails to produce an outcome at all — e.g., a CI/runner crash, loader defect, or artifact-pipeline failure before any evidence bundle is built — as occurred at D2-0004 step 18 and was handled by `docs/AMENDMENT_D2-0004_INFRA-001.md`.*

**Policy: amendment-authorized re-run, never a silent re-run, following the INFRA-001 pattern:**

- **Outcome-never-observed criterion (mandatory):** an infrastructure re-run is permissible **only if the experiment's outcome was never observed** — no evidence bundle built, nothing published, no held-out result seen by any person, and no partial output consumed by any candidate modification, selection, or scientific decision. If the outcome (or any usable part of it) was observed, the one-shot boundary is broken: the generation closes as-is under §2.1–§2.4 semantics (or as INCONCLUSIVE if no valid decision region applies), and **no re-run is authorized**.
- **Exactly-one-rerun discipline:** exactly **ONE (1)** infrastructure re-run is authorized per failure event, via a documented amendment following `AMENDMENT_D2-0004-INFRA-001` in form: failure record with true root cause, status of prior partial output, explicit authorization clause, and unchanged-scientific-parameters list. Any further re-run requires a new amendment; re-running until a desired result appears is categorically forbidden.
- **No scientific parameter changes:** the re-run amendment changes **no** scientific parameter — no threshold, model set, candidate policy, seed, boundary check, or decision region. Infrastructure fixes (e.g., a loader defect fix) and runtime pinning (the `benchmarks/runtime_lock.json` hard-gate pattern) are the only permitted changes, and each is disclosed in the amendment.
- **Root-cause requirement:** the failure's true root cause is recorded and reproduced before authorization; speculative causes are labeled as such (per INFRA-001 §1, where framework-version drift was explicitly refuted as the cause).
- **Next-generation requirements:** D2-0006's own preregistration (§6) must include an infrastructure-failure clause adopting this §2.5 policy by reference, so the re-run policy for D2-0006 exists *before* D2-0006 executes — not written after a failure occurs.
- **Evidence labels:** the failure record and diagnosis are `internally_measured` operational facts; any inference drawn from partial, non-contract output is forbidden (not merely unlabeled).
- **Publication commitment:** the infrastructure failure and its amendment are published with the generation's release (failure record + authorization + re-run provenance), as with INFRA-001. An infrastructure failure is a disclosed program event, never a silent retry.
- **Budget caps: TBD** (re-run compute budget fixed in the D2-0006 preregistration; the exactly-one-rerun cap itself is frozen, not TBD).

---

## 3. What is frozen NOW vs decided LATER

### 3.1 Frozen now (by committing this interpretation policy)

| # | Frozen commitment | Amendment rule |
|---|---|---|
| 1 | **The decision tree itself (§2)** — the five-branch mapping from D2-0005's four preregistered decision regions plus the infrastructure-failure class to the *form* of the D2-0006 experiment | Amendable only via a documented, hash-committed amendment **before D2-0005 closes**; once D2-0005 has closed, the tree is applied, not edited |
| 2 | **The no-silent-abandonment rule** — no result region (including negative and inconclusive) permits quietly discontinuing the line of inquiry | Same as above |
| 3 | **The fresh-generation requirement** — new candidate pool (new seed) and fresh held-out conditions for D2-0006, disjoint from D2-0005's; **PERSON-HO-v3 never reused as a held-out set**; D2-0006 is never a re-run of D2-0005 on the same pool or fixtures | Same as above |
| 4 | **Evidence-label commitments** — closed results `internally_measured`; transfer beyond the fresh held-out set `external_replication_needed`; mechanistic interpretations `speculative_open`; pre-execution hypothesis `target`; OC/design-analysis numbers `scenario_assumption` | Same as above |
| 5 | **Publication commitment for ALL branches** — success, null, negative, inconclusive, and infrastructure-failure records are all publishable closed-generation datapoints per `docs/RESEARCH_RELEASE_FORMAT.md`; publication is never conditional on supporting the thesis | Same as above |
| 6 | **The infrastructure-failure re-run policy (§2.5)** — outcome-never-observed criterion, exactly-one-rerun discipline, no scientific parameter changes, root-cause record, published failure disclosure | Same as above |
| 7 | **The amendment path (§6)** — the mechanical procedure by which this DRAFT becomes the D2-0006 preregistration after D2-0005 closes | Same as above |

### 3.2 Decided later (after D2-0005 closes, via a documented pre-arming preregistration)

| # | Decided-later item | Branch dependence |
|---|---|---|
| 1 | The **exact directional hypothesis** of D2-0006 — currently **`BLOCKED until D2-0005 closes`** (reason: choosing it earlier would retrofit the agenda to an observed outcome) | All branches; form set by the selected §2 branch |
| 2 | The **effect-size regions**: success-region anchored on the D2-0005 interval (2.1); exact SESOI / equivalence margin (2.2); reversal-confirmation region (2.3); amended width/precision target (2.4) | Branch-specific |
| 3 | The **budgets and caps (TBD here)**: candidate count, search budget, protocol grid size, observation-unit/cluster count, seeds, compute and re-run budgets | All branches; informed by the design analysis where relevant (2.4) |
| 4 | The **fresh held-out set definition** (new detector architectures / condition grid) and the fresh pool seed | All branches |
| 5 | **Mechanistic confirmatory claims**, if any, upgraded from the descriptive telemetry endpoints | 2.3 only; requires separate preregistration |

Nothing in the "decided later" table may be filled in before D2-0005 closes; filling any of it early converts this policy into the post-hoc storytelling it exists to prevent.

---

## 4. Relationship to the research program

D2-0006 is the replication link in the longitudinal structure that Paper 1 reports:

| Generation | Role | Status at time of this DRAFT |
|---|---|---|
| D2-0003 | Retained **negative** result — published falsifying datapoint, not discarded | closed |
| D2-0004 | **Prospective closure** + canonical release (first fully preregistered measured generation); infrastructure-failure precedent INFRA-001 | closing |
| D2-0005 | **Controlled ablation** — mean vs CVaR_0.5 objective at final selection, fully paired; pre-arming design analysis (F0) and cluster-robust redesign proposal exist | PREREGISTERED, not executed |
| D2-0006 | **Replication** — prospective, hypothesis form selected by this policy after D2-0005 closes | this DRAFT; not preregistered |

The scientific content of Paper 1 is this *sequence*, not any single generation: a program that keeps its negatives (D2-0003), preregisters before executing (D2-0004, D2-0005), discloses its infrastructure failures (INFRA-001), publishes nulls, and replicates on fresh generations under a predeclared interpretation policy (D2-0006). A D2-0006 that replicated D2-0005's conditions on the same fixtures, or whose hypothesis was chosen after seeing D2-0005's numbers, would damage precisely the claim the paper makes.

---

## 5. Explicit non-goals

- This draft **does not arm, trigger, or preregister anything.** No generation skeleton, no lock freeze, no trigger revision, no CI wiring.
- **CI-safety of committing this document:** `measured-benchmark.yml` triggers **only** on the `generations/RAC-PER-D2-0004.json` path. This DRAFT touches no generation file and no workflow; committing it cannot fire the benchmark pipeline. The same discipline that keeps the D2-0005 skeleton inert (trigger fields present but NOT armed) applies here in stronger form: there is no D2-0006 generation file at all.
- This draft does not select, hint at, or constrain the *sign* of any future hypothesis beyond what the §2 tree dictates from D2-0005's closed region.
- This draft does not amend D2-0005's preregistration in any way; the D2-0005 amendment log (§9 there) is the only place D2-0005 changes are recorded. Nor does it execute the Wave H design-amendment proposal; that proposal takes effect only through D2-0005's own §7/§9 mechanism.
- This draft makes no claim that D2-0006 will be executed; execution requires D2-0005 closed, its release cut, a fresh model-lock freeze under `model-lock-bootstrap`, a D2-0006 preregistration, and an explicit trigger arming in separately reviewed changes.

---

## 6. Amendment path — how this DRAFT becomes a preregistration

The conversion is a mechanical ceremony, predeclared here so that no step is invented after D2-0005's outcome is known:

1. **Precondition gate.** D2-0005 has closed (a decision region of §4 there has been entered, or an infrastructure-failure amendment under §2.5 has been executed and the authorized re-run completed), and its release has been cut per `docs/RESEARCH_RELEASE_FORMAT.md`. If D2-0005's closure is pending an infrastructure re-run, this ceremony waits for the re-run's closure.
2. **Branch selection.** The closed D2-0005 decision region is looked up and the matching §2 branch is cited verbatim in the new preregistration, with the closure evidence (release SHA, decision-region output of the preregistered analysis) referenced — not reinterpreted.
3. **Fill the decided-later table.** Items §3.2 (1)–(5) are filled per the selected branch: the directional hypothesis field is unblocked and written (directional, equivalence, or reversal form per the branch); effect-size regions are anchored on D2-0005's observed interval / the design analysis, never on desired outcomes; budgets replace the TBD placeholders; the fresh held-out set (never PERSON-HO-v3 as held-out) and fresh pool seed are defined; the §2.5 infrastructure-failure clause is adopted by reference.
4. **Hash/freeze ceremony.** The completed document is renamed/committed as the D2-0006 preregistration (this DRAFT's banner is replaced by a preregistration banner); its content hash is committed and recorded in the research evidence register (`docs/RESEARCH_EVIDENCE_REGISTER.md`) per repo convention, in the same commit or a referenced commit; from that commit the document is frozen — later changes follow the same deviations/amendment semantics as D2-0005 §7/§9 (pre-execution amendments only, logged with rationale; post-arming changes forbidden).
5. **No arming at freeze.** Freezing the preregistration arms nothing. Model-lock freeze, generation skeleton, and trigger arming for D2-0006 are separate, later, individually reviewed changes (§5).
6. **Disclosure of timing.** The preregistration records that the §2 tree was committed (with commit SHA) *before* D2-0005 closed, establishing prospectively that the branch was selected by the frozen tree and not fitted to the outcome.

---

## 7. Deviation and amendment policy for this document

- Amendments to §2 (the tree), §3 (the frozen commitments), or §6 (the amendment path) are permitted **only before D2-0005 closes**, must be documented here with rationale, and must never be made in response to partial or leaked information about D2-0005's outcome.
- After D2-0005 closes, this document is applied as-is; any change to the tree at that point is treated as a governance violation, disclosed as such, and the affected downstream claim is labeled `scenario_assumption` or invalidated, per the deviations semantics of D2-0005 §7.

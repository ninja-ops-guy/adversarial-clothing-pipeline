# Preregistration — RAC-PER-D2-0005: Mean vs. CVaR Objective Ablation

**Status:** PREREGISTERED — AMENDED THROUGH A5 (NOT ARMED; NOT EXECUTED).
**Generation:** RAC-PER-D2-0005 (first hypothesis-driven generation).
**Supersedes/depends on:** D2-0004 (RAC-PER-D2-0004) is CLOSED as FAIL / RAC-D0. That predecessor gate is satisfied; D2-0005 remains unarmed until the A5 prospective fixture/cluster inputs and normal model-lock prerequisites are frozen.
**Protocol:** `protocols/RAC-PERSON-DETECT-1.2.json` (RAC-PERSON-DETECT-1.2).
**Model sets:** surrogate `PERSON-SUR-v3` (6 models: yolov8n, fasterrcnn_mobilenet_v3_320, detr_resnet50, ssdlite320_mobilenet_v3, retinanet_resnet50_fpn_v2, fcos_resnet50_fpn); held-out `PERSON-HO-v3` (fasterrcnn_resnet50_fpn_v2, maskrcnn_resnet50_fpn_v2).
**Generation skeleton:** `generations/RAC-PER-D2-0005.json` (frozen, `lock_status: PREREGISTERED`, `lock_inference_performed: false`, trigger fields present but NOT armed).

---

## 1. Hypotheses

Let R_M and R_C be the **mean held-out detection rates** (fraction of valid benchmark conditions on which the person is detected, per RAC-PERSON-DETECT-1.2, on the fresh held-out set PERSON-HO-v3) of the winning candidates selected by each arm from a 100-candidate surrogate-only search.

- **H1 (directional, falsifiable):** R_C < R_M. A candidate optimized against a worst-case/CVaR objective over the surrogate ensemble (Arm C) achieves a **lower** detection rate on fresh, previously unseen held-out detector architectures than a candidate optimized against the mean objective (Arm M). Equivalently: CVaR optimization transfers better cross-architecture than mean optimization.
- **H0 (null):** R_C ≥ R_M. CVaR optimization does not reduce the held-out detection rate relative to mean optimization.

H1 is falsifiable: if the paired risk difference R_M − R_C ≤ 0, or its confidence interval includes 0 and no directional separation is observed, H1 is not supported. See §4 for the exact decision regions.

---

## 2. Design

Two-arm ablation. The arms differ **only** in the surrogate optimization objective; everything else is identical to D2-0004 and to each other.

| | Arm M (mean, control/baseline) | Arm C (CVaR / worst-case) |
|---|---|---|
| Objective | Minimize **mean** per-surrogate detection rate over PERSON-SUR-v3 (the D2-0004 objective — within-generation baseline) | Minimize **CVaR_α** (expected shortfall) of the per-surrogate detection rates, **α = 0.5** (average of the worst half of the 6-surrogate ensemble, i.e., the 3 highest per-surrogate rates) |
| Candidate budget | 100 selection evaluations over the shared pool | 100 over the same shared pool |
| Surrogate set | PERSON-SUR-v3 | PERSON-SUR-v3 |
| Held-out set | PERSON-HO-v3 | PERSON-HO-v3 |
| Protocol | RAC-PERSON-DETECT-1.2 | same |
| Search | two-stage adaptive surrogate search (`scripts/select_surrogate_candidate.py`: Stage A nominal sweep, top-k=6, Stage B full `selection_sweep`) | same |
| Selection boundary | SURROGATE_ONLY | same |
| Candidate pool & seed | **shared with Arm C: one common 100-candidate pool, seed 1337** | **shared with Arm M: same pool, seed 1337** |
| Fixture / thresholds | identical (§5) | identical (§5) |

**Held constant:** the candidate pool itself — both arms search the **same single 100-candidate pool** generated once with seed 1337 (matching the benchmark seed), so every candidate is evaluated under both objectives and the comparison is fully paired at the candidate level. Also constant: candidate generation pipeline and design profile (`ruthless-reference-v1.1`), fixture and fixed crops/ROIs (`prepare_fixture` in `scripts/run_measured_benchmark.py`), transformation sweeps, decision thresholds (per-model `decision_threshold` from the manifest), budgets, invalid-condition rule (`invalid_condition_fraction ≤ 0.10`), tie-break order (`sort_key`: candidate_detection_rate, candidate_mean, then creative proxies), seeds, and the one-shot rule.

**Differs:** only the surrogate objective used in ranking. Implementation point: `sort_key`/`evaluate_candidate` in `scripts/select_surrogate_candidate.py` ranks by `candidate_detection_rate` (ensemble mean, Arm M). Arm C substitutes the per-surrogate rate vector's CVaR_0.5 (mean of the 3 worst of 6) as the primary key; all downstream tie-breaks unchanged.

**Objective scope (AMENDED — see §9):** the objective is the independent variable **only at Stage B final selection**. Stage A (the nominal-sweep screen reducing the shared 100-candidate pool to the top-6 finalists) uses the legacy mean-oriented `sort_key` for **both arms** as a **shared nuisance/preselection stage**; the arms diverge only when the winner is chosen from the identical finalist set in Stage B. Rationale: (a) it preserves full pairing/comparability — both arms select from the identical finalist set, so the comparison remains exactly paired at the candidate level with no between-arm sampling variability; (b) it avoids doubling the heaviest computation (the full-pool Stage-A sweep). The precise experimental claim therefore reads: **this ablation tests the effect of objective choice (mean vs CVaR_0.5) at final selection, given a shared mean-screened candidate pool** — not the effect of the objective over the entire 100-candidate search.

**CVaR α = 0.5 justification (preregistered):** the surrogate ensemble has 6 models, so α = 0.5 averages exactly the worst 3 — a symmetric, non-degenerate split. α → 1 would approach the single-worst-model (minimax) objective, which is maximally sensitive to one miscalibrated surrogate; α → 0 collapses to the mean objective and the ablation loses contrast. α = 0.5 is the midpoint of this continuum: it is large enough to penalize left-behind surrogate architectures (the failure mode — CROSS_ARCHITECTURE_TRANSFER_FAILURE / SURROGATE_OVERFIT — that prior generations exposed) while retaining ensemble averaging over half the models, bounding the influence of any single outlier surrogate. It is fixed a priori; no α sweep is performed (that would be post-hoc tuning, forbidden by the one-shot rule).

**Publication commitment:** both arms are preregistered. Both arms' results are recorded and published regardless of outcome, including null and negative outcomes, as a closed-generation datapoint (evidence label `internally_measured`, §7).

**A5 design amendment:** the primary inferential unit is prospectively changed from individual transformed/cropped observations to independent base-image clusters. The amended fixture contains a minimum of **K = 72 independent base images**, each contributing the same 18-transform × 2-crop grid (36 paired pseudoreplicate members). Primary inference resamples image clusters, not individual views, using `cluster_paired_arm_statistics`. This does not change H1/H0, Δ, α, model sets, decision thresholds, bootstrap seed/resample count, or the 0.20 interval-width gate. See §9 A5 and `DESIGN_AMENDMENT_D2-0005_PROPOSAL.md` v2.

---

## 3. Endpoints

**Primary endpoint:** held-out detection rate per arm on PERSON-HO-v3, computed from `benchmark.rows` restricted to `role == "heldout"` and `baseline_qualified` trials (lower = better transfer). Per-arm aggregation follows `aggregate()` in `scripts/run_measured_benchmark.py` (`candidate_detection_rate` over valid conditions). The per-candidate record is the `TelemetryRecord` of `ruthless_pipeline/certification/telemetry_contract.py` (CONTRACT_VERSION "1.0"): pre-held-out telemetry frozen and hashed (`frozen_sha256()`) before any held-out inference; held-out outcome attached append-only (`append_outcome()`) after the arm closes.

**Primary comparison (AMENDED A5):** paired risk difference Δ = R_M − R_C on matched conditions. All members from one base fixture image belong to one inferential cluster; the two arms are paired on the same rendered member. The interval for Δ is produced by deterministic cluster bootstrap via `ruthless_pipeline/certification/cluster_paired_arm_statistics.py::cluster_paired_arm_statistics`, with bootstrap_resamples = 10000, bootstrap_seed = 20260907 and the existing decision regions. Wilson score intervals remain descriptive arm-level summaries. One-sided interpretation remains preregistered in favor of Arm C (H1). The amended cluster design supersedes the earlier unit-level bootstrap reference in A2 for the primary confirmatory comparison.

**Secondary endpoints (per arm):**
1. Cross-model disagreement over the surrogate ensemble: population variance, spread, max pairwise delta — `cross_model_disagreement()` in `telemetry_contract.py`.
2. Transformation-sweep variance of candidate detection rates across the RAC-PERSON-DETECT-1.2 transform grid (brightness 0.7/1/1.3 × blur 0/0.8 × rotation −20/0/20).
3. Worst-surrogate detection rate (`surrogate_worst_case_detection_rate` in the telemetry contract).
4. Failure-taxonomy classification distribution per arm: `classify_failure` in `ruthless_pipeline/certification/failure_taxonomy.py`, with the expectation (descriptive, not a success criterion) that Arm C shows a lower incidence of CROSS_ARCHITECTURE_TRANSFER_FAILURE / SURROGATE_OVERFIT. **This endpoint is descriptive only: no confirmatory claim is made on taxonomy incidence, and no inferential test is applied to it.**
5. A5 cluster diagnostics: realized ICC estimate/design effect/effective sample-size diagnostics are reported to disclose dependence, not used for post-outcome tuning.

---

## 4. Success criteria and decision regions

Let Δ = R_M − R_C with its 95% two-sided cluster-bootstrap CI (equivalently, the preregistered one-sided interpretation toward Arm C). Under A5, individual transformed/cropped views are pseudoreplicate members nested within independent base-image clusters; they are not counted as independent units.

- **Success (H1 supported):** Δ > 0 with the CI excluding 0 in the preregistered direction (CI lower bound > 0), i.e., Arm C's held-out detection rate is significantly below Arm M's, one-sided.
- **Null (H0 not rejected; informative):** the CI includes 0 (either sign). Recorded and published as a closed-generation null datapoint.
- **Negative (direction reversed):** CI entirely below 0 — CVaR optimization transfers *worse*. Published as-is; this is a legitimate falsifying result, not a failed experiment.
- **Inconclusive region (preregistered):** if the risk-difference interval width exceeds `WILSON_WIDTH_MAX = 0.20` (matching the failure-taxonomy `STATISTICAL_INCONCLUSIVE` threshold) or valid cluster/member requirements fall below the preregistered minimum (§6/A5), the primary comparison is declared INCONCLUSIVE; the arm-level rates are still reported with their Wilson intervals, and the generation closes as inconclusive — never re-run silently.

A null/negative/inconclusive result is a publishable closed-generation datapoint. No re-optimization, re-selection, or re-analysis may be performed to "improve" the outcome.

---

## 5. Procedures

- **Seeds (fixed):** one shared seed 1337 for candidate generation, selection, and benchmark (as in `make_config` and `run_measured_benchmark.py`); bootstrap seed 20260907. There are no per-arm seeds: both arms draw from the identical pool, recorded in each candidate's `OptimizerConfig.seed` (= 1337) telemetry.
- **Candidate generation:** a **single shared 100-candidate pool** (not 100 per arm) from design profile `ruthless-reference-v1.1` with reference-fidelity scorer `reference-fidelity-v1`, generated once with seed 1337 and used by both arms; pool must declare `heldout_feedback_allowed: false` and `design_profile_sha256` (enforced by `select_surrogate_candidate.py`). Each arm's budget is 100 selection evaluations over this shared pool.
- **A5 fixture:** before arming, freeze a manifest of at least 72 independent base fixture images, each content-pinned by SHA-256 and selected without outcome access. Each image contributes the existing 18 transformation views × 2 crop specifications = 36 paired members. More views do not substitute for the minimum number of independent image clusters.
- **A5 outcome-free ICC gate:** rehearsal must estimate realized ICC without D2-0005 held-out outcomes. The K = 72 design is authorized only when the preregistered rehearsal estimate is ≤ 0.25. If it materially exceeds 0.25, D2-0005 MUST NOT arm; a new pre-arming amendment must increase independent-cluster replication. No post-outcome sample-size adaptation is permitted.
- **Preregistered precondition (CVaR implementation):** the CVaR_0.5 objective must be reviewed and unit-tested before D2-0005 execution; its implementation commit/hash is recorded at model-lock freeze.
- **Lock-freeze fields:** `lock_source_commit` and `required_commits` in `generations/RAC-PER-D2-0005.json` are filled only at the D2-0005 model-lock freeze, after all approved A5 fixture/design inputs are frozen.
- **Surrogate search config:** two-stage — Stage A nominal sweep over all 100 candidates, eligibility `invalid_condition_fraction ≤ 0.10` (shared mean-oriented screen for both arms, per the §2 objective-scope amendment); Stage B full `selection_sweep` on top-k = 6 finalists; winner = minimum under the arm objective. Only the Stage-B objective key differs between arms.
- **Objective telemetry (MANDATORY, AMENDED — see §9):** BOTH arms MUST be run with `--objective-telemetry PATH` (`scripts/select_surrogate_candidate.py`), and the resulting per-checkpoint objective telemetry JSON is a **required sealed artifact** in each arm's release, sealed at the `optimization_telemetry` stage (before any held-out inference for that arm). This telemetry — per-checkpoint per-surrogate rates, worst-k CVaR tail membership and turnover, mean/CVaR/worst-model losses, ensemble dispersion, and mean-vs-CVaR candidate rank changes — is the designated evidence base for explaining WHY one objective behaved differently (Paper 5 dataset). An arm run without its sealed telemetry artifact is invalid in full.
- **Freeze order (per arm):** (1) A5 fixture manifest + cluster identifiers frozen; (2) model-lock frozen via `model-lock-bootstrap` workflow — every manifest model's `state_dict_sha256` preregistered — **before any inference**; (3) candidate pool and design-profile hash frozen; (4) surrogate-only selection; (5) per-candidate pre-held-out telemetry frozen and hashed (`TelemetryRecord.frozen_sha256()`); (6) **only then** held-out inference (`run_measured_benchmark.py`), which hard-fails on any lock mismatch (`status: measured_unlocked` ⇒ certification ineligible). Telemetry is frozen before held-out inference per arm, per candidate.
- **One-shot rule:** no held-out feedback, no post-hoc tuning, no re-selection after held-out results, no α or seed sweeps. Each arm runs its held-out evaluation exactly once.
- **Invalidation/exclusion rules:** a condition where the control/baseline is not detected is invalid and never counted as candidate success (`split_valid_invalid`); arms with `invalid_condition_fraction > 0.10` in selection are flagged per the selection script; held-out trials excluded only by the same control-undetected rule, reported via `invalid_condition_report`. Any run with a model-lock mismatch, missing preregistered hash, pool-guard failure, missing A5 fixture hash, or cluster-count/ICC preflight failure is invalid in full and documented, not patched.
- **Model-lock requirements:** detector lock (all surrogate + held-out `state_dict_sha256`) frozen by `model-lock-bootstrap` before any candidate or benchmark inference for D2-0005; `lock_inference_performed: false` in the generation file attests no inference occurred under the lock at freeze time.

---

## 6. Analysis plan

- **Exact statistical calls (AMENDED A5):** the primary comparison uses `ruthless_pipeline/certification/cluster_paired_arm_statistics.py::cluster_paired_arm_statistics` over paired binary outcomes grouped by independent base-image cluster. All transformed/cropped views belonging to an image move together in each deterministic bootstrap resample. Primary Δ = R_M − R_C (one-sided toward Arm C, H1: Δ > 0); Wilson score intervals per arm rate use z = 1.959963984540054 for descriptive comparability; cluster bootstrap uses 10000 resamples and bootstrap_seed = 20260907; decision regions remain §4 with the interval declared INCONCLUSIVE when its width exceeds 0.20. Exactly one primary comparison is performed; no multiplicity correction is applied. The prior unit-level module remains frozen and is not modified; A5 prospectively supersedes it for D2-0005 confirmatory inference.
- **Minimum independent replication:** K = 72 base-image clusters is the approved minimum when the outcome-free preregistered rehearsal confirms realized ICC ≤ 0.25. The analysis implementation's hard lower guard remains `min_clusters >= 8`, but that software-safety minimum is not the D2-0005 design target and may not be substituted for K = 72.
- **Multiple-comparison handling:** exactly one primary comparison (Arm M vs Arm C risk difference) — no correction needed for the primary test. Secondary endpoints (disagreement, sweep variance, worst-surrogate rate, taxonomy distribution, cluster diagnostics) are descriptive/hypothesis-generating: reported with intervals where applicable, not subjected to confirmatory claims; any confirmatory claim beyond the primary comparison requires a new preregistration.
- **Stopping rules:** fixed-budget generation and fixed prospective cluster count — the full 100-candidate search and the full frozen A5 fixture grid run to completion per arm; there is no optional stopping on held-out data. Early termination is permitted only on infrastructure failure, in which case the arm is documented as aborted and may be re-run once from frozen inputs under a documented amendment consistent with the one-shot policy.

---

## 7. Evidence labels and deviations policy

All outputs carry the repo's six-label governance (`ruthless_pipeline/certification/experiment.py::EVIDENCE_LABELS`):

- Arm-level held-out results and the primary comparison: **`internally_measured`**.
- Any cross-architecture transfer claim beyond PERSON-HO-v3 (e.g., to untested detectors): **`external_replication_needed`**.
- Hypothesis H1 itself, pre-execution: **`target`**.
- Assumed scenario framing (CI digital fixture; A5 pre-arming OC model and ICC design assumptions; no physical garment): **`scenario_assumption`**.
- Mechanistic interpretations of why CVaR did/did not transfer: **`speculative_open`**.
- D2-0005 results, once closed and reported per `docs/RESEARCH_RELEASE_FORMAT.md`: **`internally_measured`**. A closed RAC D2-0005 result is internally measured evidence by construction: the experiment is designed, executed, and analyzed inside this repository's governance. `published_observation` is reserved for evidence originating from an *external* published source; even after a RAC paper reporting D2-0005 is published, the underlying experiment remains `internally_measured` and MUST NOT be relabeled `published_observation`.

**Deviations policy:** any deviation from this preregistration — objective implementation, seeds, budgets, sweeps, fixture/cluster definition, exclusion rules, analysis calls — requires a documented, hash-committed amendment **before** the affected step is executed; if discovered after execution, the affected result is labeled `scenario_assumption` (or invalidated) and the deviation disclosed in the release. Deviations are never silent.

---

## 8. Operational constraints on this preregistration

- This document and `generations/RAC-PER-D2-0005.json` remain a **document + frozen skeleton only**. D2-0005 is not opened and no trigger is armed. The A5 design decision removes the undocumented design-choice blocker; it does not waive the required fixture freeze, outcome-free ICC rehearsal gate, model lock, source-commit binding, or explicit later arming review.
- D2-0005 execution requires: the approved A5 fixture manifest and cluster identities frozen; outcome-free ICC gate satisfied at the authorized K; a new model-lock freeze under `model-lock-bootstrap`; and an explicit trigger arming in a later, separately reviewed change.

---

## 9. Amendment log

Pre-arming amendments are permitted and recorded here; silent changes are not (§7 deviations policy). All amendments below were made **before D2-0005 was armed or executed**. The generation skeleton remains `lock_status: PREREGISTERED`, `lock_inference_performed: false`, with trigger fields NOT armed.

- **A1 — Evidence-label correction (§7).** Closed D2-0005 results are `internally_measured`, not `published_observation`. Per the evidence constitution, `published_observation` denotes an external published source; publication of a RAC paper about D2-0005 does not change the underlying experiment's label. Reason: methodological alignment with `experiment.py::EVIDENCE_LABELS` semantics.
- **A2 — Statistical module correction (§3, §5, §6).** The original primary-comparison plan moved from `trial_statistics.paired_trial_statistics` to `paired_arm_statistics`, because the physical-control assumptions of the former do not apply to a digital two-arm ablation. This amendment is retained as lineage; **A5 prospectively supersedes A2's unit-level bootstrap for the D2-0005 primary confirmatory interval** while leaving the estimand and fixed statistical constants unchanged.
- **A3 — Objective-scope clarification (§2, §5).** The Stage-A nominal screen is defined as a shared nuisance/preselection stage (mean-oriented `sort_key`, both arms); the objective (mean vs CVaR_0.5) is the independent variable ONLY at Stage B final selection from the identical top-6 finalist set. The experimental claim is narrowed accordingly: objective choice at final selection given a shared screened pool. This documents the as-implemented selector behavior rather than changing it.
- **A4 — Mandatory objective telemetry (§5).** Both arms MUST run the selector with `--objective-telemetry`; the per-checkpoint telemetry JSON is a required sealed artifact in each arm's release at the `optimization_telemetry` stage, providing the evidence base for explaining why the objectives behaved differently. An arm without sealed telemetry is invalid in full.
- **A5 — Cluster-robust DESIGN amendment (§2–§6), APPROVED 2026-09-10 before arming.** Based solely on the pre-arming F0 operating-characteristic study and the corrected/red-teamed Wave-H cluster study documented in `docs/DESIGN_AMENDMENT_D2-0005_PROPOSAL.md` v2, D2-0005 remains a confirmatory two-arm ablation but changes its inferential unit from individual transformed/cropped observations to **independent base-image clusters**. The prospective fixture requires **K ≥ 72 independent base images**, content-pinned before arming, with the existing 18-transform × 2-crop grid treated as 36 pseudoreplicate members within each image. Primary inference uses `cluster_paired_arm_statistics` and resamples image clusters. H1/H0, Δ = R_M − R_C, CVaR α = 0.5, z = 1.959963984540054, bootstrap seed 20260907, 10000 resamples, the 0.20 width gate, model sets and decision regions are unchanged. K = 72 is conditional on a preregistered **outcome-free** rehearsal estimate of realized ICC ≤ 0.25; if realized ICC materially exceeds 0.25, D2-0005 MUST NOT arm and a new pre-arming amendment must increase independent-cluster replication. No D2-0005 outcome data existed or informed A5. The proposal's earlier v1 `K=108 × m=6` recommendation remains superseded by its corrected v2 analysis. This A5 entry is the governing design decision; the proposal document is its justification record, not a separate source of authority.

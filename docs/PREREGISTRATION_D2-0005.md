# Preregistration — RAC-PER-D2-0005: Mean vs. CVaR Objective Ablation

**Status:** PREREGISTERED (frozen at commit time of this document; NOT yet executed).
**Generation:** RAC-PER-D2-0005 (first hypothesis-driven generation).
**Supersedes/depends on:** D2-0004 (RAC-PER-D2-0004, status READY_FOR_FRESH_HELDOUT_RUN) must close first; D2-0005 MUST NOT be opened, executed, or trigger-wired while D2-0004 is open.
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

**CVaR α = 0.5 justification (preregistered):** the surrogate ensemble has 6 models, so α = 0.5 averages exactly the worst 3 — a symmetric, non-degenerate split. α → 1 would approach the single-worst-model (minimax) objective, which is maximally sensitive to one miscalibrated surrogate; α → 0 collapses to the mean objective and the ablation loses contrast. α = 0.5 is the midpoint of this continuum: it is large enough to penalize left-behind surrogate architectures (the failure mode — CROSS_ARCHITECTURE_TRANSFER_FAILURE / SURROGATE_OVERFIT — that prior generations exposed) while retaining ensemble averaging over half the models, bounding the influence of any single outlier surrogate. It is fixed a priori; no α sweep is performed (that would be post-hoc tuning, forbidden by the one-shot rule).

**Publication commitment:** both arms are preregistered. Both arms' results are recorded and published regardless of outcome, including null and negative outcomes, as a closed-generation datapoint (evidence label `internally_measured`, §7).

---

## 3. Endpoints

**Primary endpoint:** held-out detection rate per arm on PERSON-HO-v3, computed from `benchmark.rows` restricted to `role == "heldout"` and `baseline_qualified` trials (lower = better transfer). Per-arm aggregation follows `aggregate()` in `scripts/run_measured_benchmark.py` (`candidate_detection_rate` over valid conditions). The per-candidate record is the `TelemetryRecord` of `ruthless_pipeline/certification/telemetry_contract.py` (CONTRACT_VERSION "1.0"): pre-held-out telemetry frozen and hashed (`frozen_sha256()`) before any held-out inference; held-out outcome attached append-only (`append_outcome()`) after the arm closes.

**Primary comparison:** paired risk difference Δ = R_M − R_C on matched conditions (identical fixture, crops, sweep grid, **and the same underlying candidate pool** for both arms — the pairing is exact: each arm's selected winner comes from the identical candidate set, so the comparison isolates the objective with no sampling variability between pools), with Wilson score intervals for each marginal rate and a deterministic-seed bootstrap interval for the difference, via `ruthless_pipeline/certification/trial_statistics.py` (`paired_trial_statistics`, `wilson_interval`, `_bootstrap_risk_difference_interval`; bootstrap_resamples = 10000, bootstrap_seed = 20260907, z = 1.959963984540054). One-sided interpretation preregistered in favor of Arm C (H1).

**Secondary endpoints (per arm):**
1. Cross-model disagreement over the surrogate ensemble: population variance, spread, max pairwise delta — `cross_model_disagreement()` in `telemetry_contract.py`.
2. Transformation-sweep variance of candidate detection rates across the RAC-PERSON-DETECT-1.2 transform grid (brightness 0.7/1/1.3 × blur 0/0.8 × rotation −20/0/20).
3. Worst-surrogate detection rate (`surrogate_worst_case_detection_rate` in the telemetry contract).
4. Failure-taxonomy classification distribution per arm: `classify_failure` in `ruthless_pipeline/certification/failure_taxonomy.py`, with the expectation (descriptive, not a success criterion) that Arm C shows a lower incidence of CROSS_ARCHITECTURE_TRANSFER_FAILURE / SURROGATE_OVERFIT. **This endpoint is descriptive only: no confirmatory claim is made on taxonomy incidence, and no inferential test is applied to it.**

---

## 4. Success criteria and decision regions

Let Δ = R_M − R_C with its 95% two-sided CI (equivalently, the preregistered one-sided 97.5% upper bound). Conditions-per-model = 3 brightness × 1 scale × 2 blur × 3 rotation = 18; with 2 held-out models and 2 fixture crops, the valid-trial count per arm is fixed by the protocol grid (up to 72 condition-model-crop trials before invalid-condition exclusion).

- **Success (H1 supported):** Δ > 0 with the CI excluding 0 in the preregistered direction (CI lower bound > 0), i.e., Arm C's held-out detection rate is significantly below Arm M's, one-sided.
- **Null (H0 not rejected; informative):** the CI includes 0 (either sign). Recorded and published as a closed-generation null datapoint.
- **Negative (direction reversed):** CI entirely below 0 — CVaR optimization transfers *worse*. Published as-is; this is a legitimate falsifying result, not a failed experiment.
- **Inconclusive region (preregistered):** if the risk-difference interval width exceeds `WILSON_WIDTH_MAX = 0.20` (matching the failure-taxonomy `STATISTICAL_INCONCLUSIVE` threshold) or valid-trial counts fall below the stopping-rule minimum (§6), the primary comparison is declared INCONCLUSIVE; the arm-level rates are still reported with their Wilson intervals, and the generation closes as inconclusive — never re-run silently.

A null/negative/inconclusive result is a publishable closed-generation datapoint. No re-optimization, re-selection, or re-analysis may be performed to "improve" the outcome.

---

## 5. Procedures

- **Seeds (fixed):** one shared seed 1337 for candidate generation, selection, and benchmark (as in `make_config` and `run_measured_benchmark.py`); bootstrap seed 20260907 (as in `paired_trial_statistics`). There are no per-arm seeds: both arms draw from the identical pool, recorded in each candidate's `OptimizerConfig.seed` (= 1337) telemetry.
- **Candidate generation:** a **single shared 100-candidate pool** (not 100 per arm) from design profile `ruthless-reference-v1.1` with reference-fidelity scorer `reference-fidelity-v1`, generated once with seed 1337 and used by both arms; pool must declare `heldout_feedback_allowed: false` and `design_profile_sha256` (enforced by `select_surrogate_candidate.py`). Each arm's budget is 100 selection evaluations over this shared pool.
- **Preregistered precondition (CVaR implementation):** the CVaR_0.5 objective will land as reviewed code with unit tests in `scripts/select_surrogate_candidate.py` **before** D2-0005 execution; the implementation commit must precede the D2-0005 model-lock freeze, and the objective function's commit/hash is recorded at freeze time as part of the lock evidence.
- **Lock-freeze fields:** `lock_source_commit` and `required_commits` in `generations/RAC-PER-D2-0005.json` are intentionally `null`/`[]` now; they are filled **only** at the D2-0005 model-lock freeze, which occurs after D2-0004 closes and after the CVaR implementation commit above.
- **Surrogate search config:** two-stage — Stage A nominal sweep over all 100 candidates, eligibility `invalid_condition_fraction ≤ 0.10`; Stage B full `selection_sweep` on top-k = 6 finalists; winner = minimum under the arm objective. Only the objective key differs between arms.
- **Freeze order (per arm):** (1) model-lock frozen via `model-lock-bootstrap` workflow — every manifest model's `state_dict_sha256` preregistered — **before any inference**; (2) candidate pool and design-profile hash frozen; (3) surrogate-only selection; (4) per-candidate pre-held-out telemetry frozen and hashed (`TelemetryRecord.frozen_sha256()`); (5) **only then** held-out inference (`run_measured_benchmark.py`), which hard-fails on any lock mismatch (`status: measured_unlocked` ⇒ certification ineligible). Telemetry is frozen before held-out inference per arm, per candidate.
- **One-shot rule:** no held-out feedback, no post-hoc tuning, no re-selection after held-out results, no α or seed sweeps. Each arm runs its held-out evaluation exactly once.
- **Invalidation/exclusion rules:** a condition where the control/baseline is not detected is invalid and never counted as candidate success (`split_valid_invalid`); arms with `invalid_condition_fraction > 0.10` in selection are flagged per the selection script; held-out trials excluded only by the same control-undetected rule, reported via `invalid_condition_report`. Any run with a model-lock mismatch, missing preregistered hash, or pool-guard failure is invalid in full and documented, not patched.
- **Model-lock requirements:** detector lock (all surrogate + held-out `state_dict_sha256`) frozen by `model-lock-bootstrap` before any candidate or benchmark inference for D2-0005; `lock_inference_performed: false` in the generation file attests no inference occurred under the lock at freeze time.

---

## 6. Analysis plan

- **Exact statistical calls:** `trial_statistics.paired_trial_statistics(trials, z=DEFAULT_Z, bootstrap_resamples=10000, bootstrap_seed=20260907)` over valid matched trials; marginal rates via `statistics.wilson_interval`; invalid accounting via `split_valid_invalid` / `invalid_condition_report`; effect sizes reported as risk difference and Haldane-corrected odds ratio (as returned by `PairedTrialStatistics`).
- **Multiple-comparison handling:** exactly one primary comparison (Arm M vs Arm C risk difference) — no correction needed for the primary test. Secondary endpoints (disagreement, sweep variance, worst-surrogate rate, taxonomy distribution) are descriptive/hypothesis-generating: reported with intervals, not subjected to confirmatory claims; any confirmatory claim beyond the primary comparison would require a new preregistration.
- **Stopping rules:** fixed-budget generation — the full 100-candidate search and the full protocol grid run to completion per arm; there is no optional stopping on held-out data. The `PreregisteredStoppingRule` machinery (`evaluate_stopping_rule`) governs any downstream physical P1-style extension, not this digital generation; for the record, `min_valid_trials` follows `minimum_valid_trials(target_interval_width=0.20)` and `max_valid_trials` equals the full protocol grid size. Early termination is permitted only on infrastructure failure, in which case the arm is documented as aborted and may be re-run once from frozen inputs under an amendment (§7).

---

## 7. Evidence labels and deviations policy

All outputs carry the repo's six-label governance (`ruthless_pipeline/certification/experiment.py::EVIDENCE_LABELS`):

- Arm-level held-out results and the primary comparison: **`internally_measured`**.
- Any cross-architecture transfer claim beyond PERSON-HO-v3 (e.g., to untested detectors): **`external_replication_needed`**.
- Hypothesis H1 itself, pre-execution: **`target`**.
- Assumed scenario framing (CI digital convenience fixture; fixed two-crop ROIs; no physical garment): **`scenario_assumption`**.
- Mechanistic interpretations of why CVaR did/did not transfer: **`speculative_open`**.
- D2-0005 results, once closed and reported per `docs/RESEARCH_RELEASE_FORMAT.md`: **`published_observation`**.

**Deviations policy:** any deviation from this preregistration — objective implementation, seeds, budgets, sweeps, exclusion rules, analysis calls — requires a documented, hash-committed amendment **before** the affected step is executed; if discovered after execution, the affected result is labeled `scenario_assumption` (or invalidated) and the deviation disclosed in the release. Deviations are never silent.

---

## 8. Operational constraints on this preregistration

- This document and `generations/RAC-PER-D2-0005.json` are a **document + frozen skeleton only**. D2-0005 is not opened, and no CI wiring is added: `measured-benchmark.yml` continues to trigger only on the `generations/RAC-PER-D2-0004.json` path; the D2-0005 trigger fields are present but NOT armed (no `trigger_revision` bump), so committing the skeleton cannot fire the workflow.
- D2-0005 execution requires D2-0004 closed, a new lock freeze under `model-lock-bootstrap`, and an explicit trigger arming in a later, separately reviewed change.

# Design Analysis (Pre-Arming Operating Characteristics) — RAC-PER-D2-0005

**Status:** PRE-ARMING capability characterization. **NO D2-0005 outcome data exists.** The generation skeleton (`generations/RAC-PER-D2-0005.json`) is frozen with `lock_status: PREREGISTERED`, `lock_inference_performed: false`, trigger fields NOT armed; D2-0004 has since closed (FAIL / RAC-D0, log-attested, 2026-09-08 — see `docs/D2-0004_CLOSURE_NOTE.md`). Nothing in this document executes, arms, or modifies D2-0005.

**What this is:** a deterministic simulation that characterizes **what question the frozen design can answer** — the operating characteristics (power / decision-region probabilities) of the preregistered analysis under hypothetical true effects.

**What this is NOT:** it is **NOT tuning**. It MUST NOT be used to propose changing the preregistered thresholds — the 0.20 interval-width gate (`INCONCLUSIVE_WIDTH_MAX`), the CVaR level α = 0.5, or the §4 decision regions — on the basis of expected favorable outcomes. Changing thresholds after seeing an operating-characteristics curve because the curve is unfavorable is post-hoc tuning wearing pre-arming clothes, and it is forbidden here. The only legitimate outputs are:

- **(a)** a capability characterization of the frozen design (this document), and
- **(b)** if the design proves badly underpowered, the two scientifically correct **pre-arming** options:
  1. **amend the DESIGN before arming** — a documented, hash-committed amendment per the §7 deviations policy of `docs/PREREGISTRATION_D2-0005.md`, recorded in its §9 amendment log (exactly the route amendments A1–A4 took); or
  2. **deliberately declare D2-0005 an exploratory / pilot-sized prospective experiment**, so its eventual results are interpreted as hypothesis-generating rather than confirmatory.

This document makes no recommendation between those options and proposes **no** threshold change.

**Evidence labels (per §7 and the six-label governance):** every number below is `scenario_assumption` (synthetic data-generating processes over assumed detection-rate regimes). H1 remains `target`. Mechanistic commentary is `speculative_open`.

---

## 1. Methods — exact, disclosed in full

**Analysis under study (the ACTUAL preregistered path, amendment A2):**
`ruthless_pipeline/certification/paired_arm_statistics.py::paired_arm_statistics` with the preregistered defaults — Δ = R_M − R_C one-sided toward Arm C (H1: Δ > 0), Wilson z = 1.959963984540054, deterministic hash-seeded bootstrap over observation units, `bootstrap_seed = 20260907`, decision regions via `classify_decision`, INCONCLUSIVE when the interval width exceeds 0.20. The simulation classifies every synthetic dataset through the module's own `bootstrap_paired_difference_interval` + `classify_decision` — the exact functions `paired_arm_statistics` calls internally. No decision logic is reimplemented (enforced by `tests/test_design_analysis_d20005.py::test_simulation_uses_preregistered_decision_path`, which checks each sampled dataset against `paired_arm_statistics(...).decision`).

**Driver:** `scripts/design_analysis_d20005.py` (stdlib-only, deterministic; no `random` module state).

**Synthetic outcome generation.** Each observation unit (a held-out model × transform × fixture-crop trial) receives a paired outcome (arm M detected?, arm C detected?) in one of four joint states: both / M-only / C-only / neither. For dataset `d`, unit `i`, cell `c`, a uniform draw
`u = SHA256("design-analysis-d20005|<sim_seed>|<cell>|<d>|<i>")[:8] / 2^64`
(same hash-draw style as `paired_arm_statistics._hash_draw`) selects the state under the cell's joint model. **sim_seed = 20261204** (fixed, disclosed here and in the artifact).

**Grid.**
- true paired difference Δ_true ∈ {−0.1, 0.0, 0.1, 0.2, 0.3, 0.5} (spanning reversed, null, small, the 0.20 width gate itself, and large effects);
- discordance structures:
  - `symmetric` — arms conditionally independent given the marginals (baseline p_M = 0.5, maximum-entropy pairing);
  - `m_dominated` — nested pairing (for Δ ≥ 0, Arm-C detections ⊂ Arm-M detections; all discordance M-only), the minimum-variance / maximum-concordance pairing given the marginals;
  - `sparse` — independent pairing at a low baseline p_M = 0.3 (low-rate regime). The cell (Δ_true = 0.5, sparse) is **infeasible** (p_C = −0.2) and is excluded and disclosed, not silently dropped;
- observation-unit counts n ∈ {36, 72, 144}: 72 is the planned protocol grid (2 held-out models × 2 fixture crops × 18 transform conditions), 36 a half-grid (e.g., one model, or heavy invalid-condition exclusion), 144 a doubled grid (amendment-scale sensitivity).

**Replicates:** 500 simulated datasets per cell (`DATASETS_PER_CELL = 500`); Monte Carlo standard error on a probability near 0.5 is ≤ √(0.25/500) ≈ 0.022.

**Disclosed deviation from preregistered execution:** the grid uses **1000 bootstrap resamples** per dataset; the preregistered execution uses 10000. A **confirmation block** re-runs all six symmetric-structure cells at the planned n = 72 with the full preregistered **10000** resamples (§2, bottom table) — probabilities agree with the 1000-resample grid within Monte Carlo error. Intervals are memoized on the sufficient statistic (n, n_M-only, n_concordant, n_C-only, resamples); memoization does not change any value.

**Outputs:** canonical-JSON artifact (sort_keys, separators `(",", ":")`, trailing newline) at `artifacts/design_analysis_d20005/results.json` (regenerate with `python scripts/design_analysis_d20005.py`; byte-identical across runs) and the markdown table reproduced below.

---

## 2. Results

Monte Carlo error per probability ≤ ~0.022 (500 datasets/cell). The infeasible sparse Δ_true = +0.5 cells (p_C would be −0.2) are excluded and listed below the tables.

| Delta_true | discordance | n | P(SUCCESS) | P(NULL) | P(NEGATIVE) | P(INCONCLUSIVE) | mean CI width | bootstrap R |
|---|---|---|---|---|---|---|---|---|
| -0.1 | symmetric | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.445 | 1000 |
| -0.1 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.322 | 1000 |
| -0.1 | symmetric | 144 | 0.000 | 0.002 | 0.012 | 0.986 | 0.219 | 1000 |
| -0.1 | m_dominated | 36 | 0.000 | 0.504 | 0.222 | 0.274 | 0.183 | 1000 |
| -0.1 | m_dominated | 72 | 0.000 | 0.066 | 0.934 | 0.000 | 0.127 | 1000 |
| -0.1 | m_dominated | 144 | 0.000 | 0.000 | 1.000 | 0.000 | 0.092 | 1000 |
| -0.1 | sparse | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.428 | 1000 |
| -0.1 | sparse | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.307 | 1000 |
| -0.1 | sparse | 144 | 0.000 | 0.038 | 0.110 | 0.852 | 0.211 | 1000 |
| +0.0 | symmetric | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.452 | 1000 |
| +0.0 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.322 | 1000 |
| +0.0 | symmetric | 144 | 0.000 | 0.018 | 0.000 | 0.982 | 0.218 | 1000 |
| +0.0 | m_dominated | 36 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1000 |
| +0.0 | m_dominated | 72 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1000 |
| +0.0 | m_dominated | 144 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1000 |
| +0.0 | sparse | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.417 | 1000 |
| +0.0 | sparse | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.291 | 1000 |
| +0.0 | sparse | 144 | 0.010 | 0.378 | 0.008 | 0.604 | 0.201 | 1000 |
| +0.1 | symmetric | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.449 | 1000 |
| +0.1 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.319 | 1000 |
| +0.1 | symmetric | 144 | 0.020 | 0.022 | 0.000 | 0.958 | 0.212 | 1000 |
| +0.1 | m_dominated | 36 | 0.214 | 0.506 | 0.000 | 0.280 | 0.188 | 1000 |
| +0.1 | m_dominated | 72 | 0.936 | 0.064 | 0.000 | 0.000 | 0.134 | 1000 |
| +0.1 | m_dominated | 144 | 1.000 | 0.000 | 0.000 | 0.000 | 0.097 | 1000 |
| +0.1 | sparse | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.387 | 1000 |
| +0.1 | sparse | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.274 | 1000 |
| +0.1 | sparse | 144 | 0.394 | 0.418 | 0.000 | 0.188 | 0.190 | 1000 |
| +0.2 | symmetric | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.432 | 1000 |
| +0.2 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.307 | 1000 |
| +0.2 | symmetric | 144 | 0.120 | 0.008 | 0.000 | 0.872 | 0.209 | 1000 |
| +0.2 | m_dominated | 36 | 0.076 | 0.046 | 0.000 | 0.878 | 0.256 | 1000 |
| +0.2 | m_dominated | 72 | 0.948 | 0.000 | 0.000 | 0.052 | 0.179 | 1000 |
| +0.2 | m_dominated | 144 | 1.000 | 0.000 | 0.000 | 0.000 | 0.131 | 1000 |
| +0.2 | sparse | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.345 | 1000 |
| +0.2 | sparse | 72 | 0.018 | 0.000 | 0.000 | 0.982 | 0.247 | 1000 |
| +0.2 | sparse | 144 | 0.986 | 0.014 | 0.000 | 0.000 | 0.169 | 1000 |
| +0.3 | symmetric | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.409 | 1000 |
| +0.3 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.290 | 1000 |
| +0.3 | symmetric | 144 | 0.534 | 0.000 | 0.000 | 0.466 | 0.197 | 1000 |
| +0.3 | m_dominated | 36 | 0.008 | 0.004 | 0.000 | 0.988 | 0.291 | 1000 |
| +0.3 | m_dominated | 72 | 0.322 | 0.000 | 0.000 | 0.678 | 0.205 | 1000 |
| +0.3 | m_dominated | 144 | 1.000 | 0.000 | 0.000 | 0.000 | 0.146 | 1000 |
| +0.3 | sparse | 36 | 0.010 | 0.002 | 0.000 | 0.988 | 0.290 | 1000 |
| +0.3 | sparse | 72 | 0.294 | 0.000 | 0.000 | 0.706 | 0.205 | 1000 |
| +0.3 | sparse | 144 | 1.000 | 0.000 | 0.000 | 0.000 | 0.146 | 1000 |
| +0.5 | symmetric | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.326 | 1000 |
| +0.5 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.223 | 1000 |
| +0.5 | symmetric | 144 | 1.000 | 0.000 | 0.000 | 0.000 | 0.153 | 1000 |
| +0.5 | m_dominated | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.327 | 1000 |
| +0.5 | m_dominated | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.223 | 1000 |
| +0.5 | m_dominated | 144 | 1.000 | 0.000 | 0.000 | 0.000 | 0.153 | 1000 |

Confirmation block (full preregistered bootstrap_resamples = 10000):

| Delta_true | discordance | n | P(SUCCESS) | P(NULL) | P(NEGATIVE) | P(INCONCLUSIVE) | mean CI width | bootstrap R |
|---|---|---|---|---|---|---|---|---|
| -0.1 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.316 | 10000 |
| +0.0 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.318 | 10000 |
| +0.1 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.316 | 10000 |
| +0.2 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.305 | 10000 |
| +0.3 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.289 | 10000 |
| +0.5 | symmetric | 72 | 0.000 | 0.000 | 0.000 | 1.000 | 0.222 | 10000 |

Infeasible cells (marginal rate outside [0, 1]; excluded and disclosed):

- Delta_true = +0.5, sparse, n = 36: infeasible cell: rate_c = -0.2 outside [0, 1] for true_delta=0.5 structure='sparse'
- Delta_true = +0.5, sparse, n = 72: infeasible cell: rate_c = -0.2 outside [0, 1] for true_delta=0.5 structure='sparse'
- Delta_true = +0.5, sparse, n = 144: infeasible cell: rate_c = -0.2 outside [0, 1] for true_delta=0.5 structure='sparse'

---

## 3. The independent-inferential-unit problem (pseudoreplication)

The protocol grid reads as **2 held-out models × 2 fixture crops × 18 transform conditions = 72 trials**, and the preregistered analysis bootstraps over those 72 observation units. **But these 72 units are not 72 independent pieces of information.** The 18 transform views of the same candidate under the same held-out model are deterministic functions of (candidate, model): if the candidate's perturbation fails to transfer to a given architecture, it tends to fail across many transforms of that model simultaneously. The resampling unit of the real underlying randomness is closer to (candidate × model) — **2 held-out models**, or at most 2 models × 2 crops = 4 — than to 72.

Quantification via the design effect: if the 18 transform views within a model×crop block have intraclass correlation ρ, the effective unit count is

n_eff ≈ 72 / (1 + (m − 1)·ρ), with cluster size m = 18 (per model×crop block of 18 transforms) or m = 36 (per model across both crops).

- ρ = 0.1, m = 18 → n_eff ≈ 72 / 2.7 ≈ **27**;
- ρ = 0.3, m = 18 → n_eff ≈ 72 / 6.1 ≈ **12**;
- ρ = 0.5, m = 36 → n_eff ≈ 72 / 18.5 ≈ **4**.

So under moderate within-model correlation the effective information may be **an order of magnitude below 72** — nearer a handful of (candidate, model) pairs, which is the honest replication level of a two-held-out-model design.

**What the preregistered bootstrap-over-units does:** it correctly propagates sampling variability of the 72 paired binary outcomes *as drawn*, treating each unit as exchangeable; the paired differencing (Δ per unit) legitimately removes shared nuisance across arms, and the interval is exactly valid if the 72 units are independent (or exchangeable) draws.

**What it does NOT account for:** within-model / within-crop correlation (clustering). A unit-level bootstrap under positively clustered outcomes **understates** the true variance of Δ̂ — intervals are too narrow relative to cluster-aware inference, so the SUCCESS/NEGATIVE probabilities in §2 are **optimistic upper bounds** and the INCONCLUSIVE region is entered *less* often in this simulation than clustered reality would produce. (The simulation's `symmetric`/`sparse` structures draw units independently; `m_dominated` changes the joint state distribution, not the cross-unit dependence.) This cuts in the conservative direction for the conclusion below: the frozen design's true operating characteristics are, if anything, **harder** than §2 shows wherever ρ > 0. A cluster-robust interval (e.g., bootstrap over model×crop clusters) would be a **design amendment** under option (b1) — it must be preregistered before arming, never patched in after outcomes exist.

---

## 4. Interpretation — what the frozen design can detect

Reading the §2 grid (independent-unit assumption; see §3 for the optimism caveat):

**At the planned n = 72 the frozen design is INCONCLUSIVE-dominated under independent (symmetric) discordance.** For every Δ_true in the grid — including a very large Δ_true = +0.5 — P(INCONCLUSIVE) = 1.000 (mean interval width 0.29–0.32, all above the 0.20 gate), confirmed at the full preregistered 10000 bootstrap resamples. The frozen design **cannot certify any effect at n = 72 if the two arms' outcomes are independent given their marginals.** This is driven by the width gate: the percentile interval for Δ under symmetric discordance at n = 72 has width ≈ 3.92·sd(δ)/√72 with sd(δ) ≈ 0.5–0.7, i.e. 0.23–0.33 — structurally above 0.20 regardless of how large Δ_true is.

**Where the design CAN answer H1 at n = 72:** only under the minimum-variance nested discordance structure (`m_dominated`, every Arm-C detection nested inside Arm-M detections), where the discordant-pair variance |Δ| − Δ² is small for modest |Δ|:

- Δ_true = +0.1 → P(SUCCESS) = 0.936; Δ_true = +0.2 → P(SUCCESS) = 0.948 (width ≈ 0.13–0.18, inside the gate).
- Δ_true = +0.3 → P(SUCCESS) drops to 0.322 (mean width 0.205 ≈ the gate — the *larger* effect is harder to certify because its variance is larger).
- Δ_true = +0.5 → P(INCONCLUSIVE) = 1.000 even nested: the discordant-pair variance Δ(1−Δ) peaks near Δ = 0.5, so the width (≈ 0.22) exceeds the gate. **The frozen width gate makes the very largest effects un-certifiable at n = 72** — a distinctive operating characteristic of an interval-width-based inconclusive region.
- Under `m_dominated` the design is directionally honest: Δ_true = −0.1 gives P(NEGATIVE) = 0.934 at n = 72 (1.000 at n = 144), and Δ_true = 0 gives P(NULL) = 1.000 — false SUCCESS probability is ~0 throughout (max observed 0.010, sparse Δ_true = 0 at n = 144, consistent with the 97.5% one-sided level).

**Sparse / low-rate regime (p_M = 0.3):** at n = 72 essentially everything is INCONCLUSIVE except a narrow band near Δ_true = +0.2 (P(SUCCESS) = 0.018) — low marginal rates leave too few discordant pairs. Doubling to n = 144 rescues moderate effects (P(SUCCESS) = 0.986 at Δ_true = +0.2; 1.000 at +0.3).

**n sensitivity:** doubling the grid to 144 units makes symmetric Δ_true = +0.3 detectable only half the time (0.534) and Δ_true = +0.2 rarely (0.120); even at n = 144, symmetric Δ_true = +0.5 reaches P(SUCCESS) = 1.000 only because its width (0.153) finally clears the gate. Halving to 36 makes the design uniformly INCONCLUSIVE outside the lowest-variance nested cells.

**Summary of detectability (independent units, planned n = 72):** the frozen design can confirm H1 at probability ≥ 0.8 only for effects in the approximate band **Δ_true ∈ [0.1, 0.2] under near-nested (maximally concordant) discordance**. Outside that band — independent discordance at any effect size, sparse rates, very large effects, or n = 36 — the preregistered decision regions return INCONCLUSIVE with probability ≈ 1. The INCONCLUSIVE region, not the NULL region, is the design's dominant attractor at the planned sample size; per §3, positive within-model correlation (pseudoreplication) makes the true picture strictly harder than these numbers, since the unit-level bootstrap understates clustered variance.

---

## 5. Pre-arming options (restated, no threshold tuning)

If the capability characterization above is judged inadequate for a confirmatory generation, the two scientifically correct options — both exercised **before arming**, both leaving the preregistered thresholds (0.20 width gate, α = 0.5, decision regions) untouched by this analysis — are:

1. **Amend the DESIGN before arming.** A documented, hash-committed amendment per the §7 deviations policy, logged in §9 of the preregistration (the A1–A4 route). Candidate design-level changes an amendment *could* consider on scientific grounds (listed for completeness, **not** recommended by this document): adding held-out models or crops to enlarge the genuine replication level; adopting a cluster-robust (cluster-bootstrap) interval that acknowledges pseudoreplication; or restructuring the primary endpoint to the model×crop-cluster level. Any such amendment requires its own pre-arming review and its own operating-characteristics check.
2. **Accept D2-0005 as an exploratory / pilot-sized prospective experiment.** Declare, before arming, that the generation is powered to detect only large effects and is expected to return INCONCLUSIVE or NULL across much of the plausible effect range; its results are then published as hypothesis-generating (descriptive) evidence that informs the design of a future, adequately replicated confirmatory preregistration.

What is **not** an option: widening the width gate, shifting α, or redrawing the decision regions because this simulation shows them to be stringent — that would be tuning the analysis to the expected data, the exact failure mode preregistration exists to prevent.

---

## 6. Reproduction

```
python scripts/design_analysis_d20005.py          # regenerates artifacts/ byte-identically
python -m pytest tests/test_design_analysis_d20005.py
```

Fixed constants: sim_seed 20261204; grid bootstrap resamples 1000 (confirmation 10000); bootstrap seed 20260907; z 1.959963984540054; INCONCLUSIVE_WIDTH_MAX 0.20; 500 datasets per cell. No timestamps, no `random` module state, no platform-dependent hashing anywhere in the pipeline.

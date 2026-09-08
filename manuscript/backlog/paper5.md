# Paper 5 Backlog — D2-0005 Mean-vs-CVaR Objective Ablation

> Fill-in protocol: see `README.md` in this directory. NO invented results.
> Every numeric placeholder is marked `[AWAITING: <source artifact>]`.

## 1. Working title and contribution claim

**Working title:** *Worst-Case or Average-Case? A Fully Paired, Preregistered Ablation of Mean vs CVaR₀.₅ Objectives for Cross-Architecture Transfer of Adversarial Clothing Patterns (RAC-PER-D2-0005)*

**Contribution claim (one paragraph):** We report D2-0005, the first hypothesis-driven
generation of the RAC program: a preregistered two-arm ablation in which the **only**
independent variable is the surrogate optimization objective at final selection —
ensemble mean (Arm M) vs CVaR at α = 0.5 over the worst 3 of 6 surrogate detectors
(Arm C) — with both arms searching the identical 100-candidate pool (seed 1337) under an
identical shared mean-oriented Stage-A screen, making the comparison exactly paired at the
candidate level. The directional, falsifiable hypothesis H1 (R_C < R_M on the fresh
held-out set PERSON-HO-v3) is evaluated with preregistered decision regions (success /
null / negative / inconclusive at interval width > 0.20), Wilson intervals at
z = 1.959963984540054, and a deterministic hash-seeded bootstrap (10000 resamples, seed
20260907); a pre-arming deterministic design analysis characterizes the operating
characteristics of the frozen design without tuning it, and both arms' results — including
null and negative outcomes — are committed to publication as closed-generation datapoints.

## 2. Methods skeleton

### 2.1 Hypotheses and decision regions
- H1 (directional) and H0 verbatim; falsifiability statement ← `docs/PREREGISTRATION_D2-0005.md` §1.
- Four decision regions (success / null / negative / inconclusive, WILSON_WIDTH_MAX = 0.20; up to 72 condition-model-crop trials per arm before invalid-condition exclusion) ← `docs/PREREGISTRATION_D2-0005.md` §4.
- Publication commitment for all outcomes ← `docs/PREREGISTRATION_D2-0005.md` §2 Publication commitment.

### 2.2 Two-arm paired design
- Arm table (objective, budget 100 selection evaluations, surrogate set PERSON-SUR-v3, held-out PERSON-HO-v3, protocol RAC-PERSON-DETECT-1.2, two-stage adaptive search, SURROGATE_ONLY boundary, shared pool seed 1337) ← `docs/PREREGISTRATION_D2-0005.md` §2.
- Held-constant list (pool, design profile ruthless-reference-v1.1, fixture/crops, sweeps, thresholds, invalid-condition rule ≤ 0.10, tie-break order, one-shot rule) ← `docs/PREREGISTRATION_D2-0005.md` §2.
- Objective-scope amendment A3: the objective is the independent variable ONLY at Stage B final selection from the identical top-6 finalist set; narrowed experimental claim verbatim ← `docs/PREREGISTRATION_D2-0005.md` §2 Objective scope; §9 A3.
- CVaR α = 0.5 justification (6 surrogates → worst 3; α→1 minimax fragility; α→0 collapse to mean; no α sweep) ← `docs/PREREGISTRATION_D2-0005.md` §2.

### 2.3 Endpoints
- Primary endpoint (held-out detection rate per arm on PERSON-HO-v3, `role == "heldout"` baseline-qualified rows; aggregation via `aggregate()` in `scripts/run_measured_benchmark.py`) ← `docs/PREREGISTRATION_D2-0005.md` §3.
- Primary comparison Δ = R_M − R_C via `ruthless_pipeline/certification/paired_arm_statistics.py` (Wilson + deterministic bootstrap, bootstrap_resamples = 10000, seed 20260907, z = 1.959963984540054) ← `docs/PREREGISTRATION_D2-0005.md` §3; amendment A2 (module correction from trial_statistics).
- Secondary endpoints 1–4 (cross-model disagreement; transformation-sweep variance; worst-surrogate rate; descriptive failure-taxonomy incidence with no inferential test) ← `docs/PREREGISTRATION_D2-0005.md` §3.

### 2.4 Telemetry and sealed artifacts
- TelemetryRecord contract (CONTRACT_VERSION "1.0"; pre-held-out frozen and hashed; outcome append-only) ← `docs/PREREGISTRATION_D2-0005.md` §3; `ruthless_pipeline/certification/telemetry_contract.py` docstring.
- Mandatory `--objective-telemetry` per checkpoint (amendment A4; sealed at the optimization_telemetry stage; an arm without sealed telemetry is invalid in full) ← `docs/PREREGISTRATION_D2-0005.md` §9 A4; produced by `build_objective_telemetry` per `manuscript/FIGURE_SPECIFICATIONS.md` F5.

### 2.5 Pre-arming design analysis (operating characteristics)
- Simulation of the exact preregistered decision path (`paired_arm_statistics` + `classify_decision`; enforced by `tests/test_design_analysis_d20005.py`); hash-draw synthetic outcomes; grid (Δ_true ∈ {−0.1…+0.5} × 3 discordance structures × n ∈ {36, 72, 144}; 500 datasets/cell; sim_seed = 20261204) ← `docs/DESIGN_ANALYSIS_D2-0005.md` §1.
- Key capability findings, quoted only with their evidence label `scenario_assumption`: e.g. under independent (symmetric) pairing at the planned n = 72 the design is inconclusive-bound across all tested effect sizes (P(INCONCLUSIVE) = 1.000 at Δ_true = +0.3, mean CI width ≈ 0.29), while under nested/max-concordance (m_dominated) pairing power at n = 72 reaches 0.936–0.948 at Δ_true = +0.1/+0.2; disclosed 1000-resample grid deviation with a 10000-resample confirmation block; infeasible sparse (Δ=+0.5) cells disclosed ← `docs/DESIGN_ANALYSIS_D2-0005.md` §2 tables and §1 (these are simulation outputs, NOT D2-0005 outcomes — label `scenario_assumption` must travel with every number).
- Anti-tuning rule (this analysis MUST NOT be used to change thresholds/α/decision regions; legitimate outputs (a) capability characterization, (b) pre-arming design amendment or exploratory declaration) ← `docs/DESIGN_ANALYSIS_D2-0005.md` preamble.
- Regeneration command and byte-identical artifact ← `scripts/design_analysis_d20005.py` → `artifacts/design_analysis_d20005/results.json`.

### 2.6 Amendment log
- A1 evidence-label correction (internally_measured); A2 statistics-module correction; A3 objective-scope clarification; A4 mandatory objective telemetry ← `docs/PREREGISTRATION_D2-0005.md` §9.

### 2.7 Execution and results (NOT YET RUN)
- Gating: D2-0004 closed 2026-09-08 (FAIL / RAC-D0, log-attested), so the open-order gate is satisfied; generation skeleton frozen, triggers NOT armed; the F0 user design decision remains pending ← `docs/PREREGISTRATION_D2-0005.md` header, `docs/DESIGN_ANALYSIS_D2-0005.md`.
- Arm-level rates, Δ, intervals, decision: [AWAITING: D2-0005 Arm M release id] / [AWAITING: D2-0005 Arm C release id].
- Objective-telemetry checkpoint series: [AWAITING: sealed optimization_telemetry stage artifacts per arm].

## 3. Figure caption drafts (F5–F8 scaffolds)

- **F5 — Objective trajectories.** Mean / CVaR / worst-model loss per optimization
  checkpoint, per arm, from sealed objective-telemetry JSON (`checkpoints[].losses`).
  Trajectory values: [AWAITING: D2-0005 sealed optimization_telemetry releases].
  Scaffold: `manuscript/figures/F5_objective_trajectories.json`.
- **F6 — CVaR tail-membership turnover.** Entered/left membership of the worst-k (k = 3,
  α = 0.5) tail per checkpoint; sealed entered/left lists rendered verbatim, never
  recomputed. Values: [AWAITING: D2-0005 sealed optimization_telemetry releases].
  Scaffold: `manuscript/figures/F6_cvar_tail_turnover.json`.
- **F7 — Mean-vs-CVaR candidate rank changes.** Dumbbell plot of `mean_rank` vs
  `cvar_rank` with `rank_delta` per candidate at the final checkpoint — direct evidence
  that objective choice changes the winner. Values: [AWAITING: D2-0005 sealed
  optimization_telemetry releases]. Scaffold: `manuscript/figures/F7_mean_vs_cvar_rank_changes.json`.
- **F8 — Paired-arm outcome (primary endpoint).** Arm M and Arm C held-out rates with
  Wilson intervals; Δ = R_M − R_C with deterministic-bootstrap interval against the
  preregistered decision regions; the `decision` string rendered verbatim from
  `paired_arm_statistics.to_canonical_json`, never restated. Values:
  [AWAITING: D2-0005 paper5_comparison.json from closed releases].
  Scaffold: `manuscript/figures/F8_paired_arm_outcome.json`.

## 4. Citation placeholder list

- [CITE: CVaR / expected shortfall optimization — foundational risk-measure literature (Rockafellar–Uryasev)]
- [CITE: distributionally robust / worst-case optimization over model ensembles]
- [CITE: adversarial-example transfer across model architectures; ensemble-based attack objectives]
- [CITE: surrogate overfitting and cross-architecture transfer failure in black-box attacks]
- [CITE: paired experimental designs and matched-unit randomization for variance reduction]
- [CITE: Wilson score intervals and bootstrap methods for paired binary outcome differences]
- [CITE: preregistration, pre-arming design analysis / prospective power characterization without threshold tuning]
- [CITE: ablation methodology and one-shot preregistered evaluation in ML robustness research]
- [CITE: publication of null/negative results in controlled ablations]

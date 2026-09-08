# Adversarial Review — Wave H D2-0005 Pre-Arming Cluster-Robust Design Analysis

Repo: ninja-ops-guy/adversarial-clothing-pipeline @ e2596cf (Wave H at b622507).
Artifact sha256 verified: `a57863f2…cc6d347` matches `artifacts/design_analysis_d20005_cluster/results.json` at HEAD.
Scratch clone + all recomputation in `/mnt/agents/output/redteam-waveH/repo` (read-only w.r.t. upstream).

## Verdict

The code is correct, deterministic, and exactly reproduces the attested artifact; the governance
process (pre-arming, no outcome data, no threshold changes) is genuinely clean. However, the
**statistical calibration story behind the K = 108 recommendation is not sound**: the DGP's "ρ" is
not the ICC it claims to be (ICC ≈ ρ²), the recommended cluster geometry (K = 108 × 6 members)
matches neither the preregistered protocol grid (18 transforms × 2 crops per model block) nor the
proposal's own drafted amendment text, and the real pinned fixture (ONE base image, 2 crops) has
K = 2 clusters under the proposal's own definition — a fact the proposal never confronts.
Recommendation: **do not execute amendment A5 as drafted**; fix F1–F4 first.

## What was independently verified (passed)

- **Artifact reproduction, bit-for-bit**: `simulate_cell(0.2, 0.5, 108, 6)` == artifact cell
  (cluster p_success 0.99, coverage 0.915, width 0.154977, p_null 0.01) exactly, 200 datasets ×
  1000 bootstrap resamples.
- **Singleton bit-for-bit equivalence**: `cluster_paired_arm_statistics` on singleton clusters vs
  frozen `paired_arm_statistics` — all shared fields identical (risk_difference, interval, width,
  decision, arms, discordants) on a random 37-unit input.
- **PYTHONHASHSEED independence**: identical cell output under PYTHONHASHSEED=7 and =42.
- **Boundary rates**: all-detected (Δ̂=0, interval (0,0) → "null"), all-missed ("null"),
  all-discordant ((1,1) → "success") — no crashes, sane decisions.
- **Claimed unit-level false-success 0.215**: reproduced from artifact cell (Δ=0, ρ=0.8, K=108,
  unit path p_success = 0.215, coverage 0.635). Honest and reproducible.
- **Cluster bootstrap mechanics**: resamples clusters with replacement via `_hash_draw`, carries
  all members, recomputes pooled `sum(Δ)/sum(m)`; pairing preserved within members; `min_clusters`
  fail-closed (module lines 270–281) with absolute floor; grid (1000) vs confirmation (10000)
  resample counts disclosed.
- **No leakage found**: simulation parameters (BASE_RATE = 0.5, Δ grid, ρ grid) are not derived
  from D2-0004 attested outcomes (which were boundary rates 1.0→1.0); the option set evaluated in
  §4 was predeclared in the F0 study. p_M = 0.5 is the max-variance (conservative) regime.

## Findings

### F1 — SERIOUS: the DGP's "ρ" is not the ICC; the grid axis is miscalibrated by a square
`scripts/design_analysis_d20005_cluster.py` lines 22–26 (docstring) and 197–206: each member
independently uses the cluster-shared uniform with probability ρ, so two members share their draw
with probability **ρ²**, not ρ. Measured empirically on the module's own DGP (200 clusters × 6
members × 60 datasets): pairwise corr of member deltas = **0.041 at "ρ"=0.2, 0.25 at "ρ"=0.5,
0.645 at "ρ"=0.8** ≈ ρ² in all cases. The docstring's claim "share their draw … with pairwise
probability rho" is false, and the proposal treats grid-ρ as the ICC throughout (proposal §1
"n_eff ≈ 72/(1+(m−1)ρ)", §2(b) "ρ = 0.5 — the mid-range correlation scenario").
Consequences: the K = 108 rule is keyed to "ρ = 0.5", which is actually **ICC ≈ 0.25** — a
benign correlation for same-image views. At grid ρ = 0.8 (ICC ≈ 0.64, entirely plausible for
brightness/rotation views of one base image), K = 108 delivers **P(SUCCESS) = 0.210** (artifact
cell Δ=0.2/ρ=0.8/K=108) and the proposal itself admits K ≥ 144 is needed there. The entire ρ
sensitivity discussion is shifted one square-root toward optimism.
**Remediation:** fix the DGP (one mixture decision per cluster, or per-pair coupling) or relabel
the axis as mixing probability and report realized ICC per cell; re-derive K at a defensible ICC
with justification for the value chosen.

### F2 — SERIOUS: recommended geometry (K=108, m=6) matches neither the protocol nor the proposal's own amendment text; the "members don't substitute" claim is contradicted by the proposal's own table
The main grid fixing the K choice uses `MEMBERS_PER_CLUSTER = 6` (script line 93). The drafted A5
replacement text (proposal lines 178–180, 204–206) says each cluster contributes "its full member
grid (**18 transformation views** per held-out-model block)" — and with the protocol's 2 fixture
crops (run_measured_benchmark.py `prepare_fixture`, 2 fixed crop specs) the real block has 18–36
members. **No simulated cell characterizes the design actually being proposed.** Worse, the
proposal's own members sweep (artifact members_sweep, ρ=0.5, K=72) shows cluster P(SUCCESS)
0.650 (m=6) → **0.995 (m=18) → 0.995 (m=36)**: adding members within the real 18-view grid at
K=72 already meets the ≥0.8 rule, so K=108 is not minimal under the protocol's true geometry, and
the §2(c) headline "more held-out models / crops per cluster does NOT substitute for clusters" is
misleading as stated (it holds only past the saturation point m≈18, which the protocol happens to
sit at). The "6 members each" figure in §4 (line 327) has no protocol referent.
**Remediation:** rerun the K-selection grid at the protocol's actual member structure
(18 views × 2 crops, or the intended amended structure) and make the drafted §4/§5 text and the
§4 memo cite the same geometry.

### F3 — SERIOUS: the real fixture has K = 2 clusters under the proposal's own definition; cross-cluster dependence is unmodeled
`run_measured_benchmark.py` pins ONE base image (`fetch_fixture_source` → single cached
`source-zidane.jpg`) with 2 fixed crops; cluster = "(base fixture image, held-out model) block"
(proposal §2(a)) ⇒ the current 72-row design has **K = 2 clusters**, far below `min_clusters = 8`
(the proposed analysis would fail closed on today's data — good guard, but it means the amendment
is not an analysis change, it is a **new fixture protocol requiring ~54–108 independent base
images**, with no sourcing, hash-pinning, or crop/ROI specification anywhere in the proposal).
Additionally, both held-out models score the *same* images, so (image×model) clusters sharing an
image are positively correlated; the DGP draws all clusters independently (script lines 197–207),
so even the amended design's realized variance is understated unless the cluster count equals the
base-image count.
**Remediation:** A5 must specify the multi-image fixture as a frozen protocol input; either define
cluster = base image (models as members) or add cross-model same-image correlation to the DGP and
re-run the OC grid.

### F4 — SERIOUS: "approximately nominal coverage" is overclaimed from the proposal's own numbers
Proposal §3/§1 claims the cluster path "maintains approximately nominal coverage". Artifact cells
at Δ=0.2: coverage **0.880** (ρ=0.5, K=216), 0.910 (ρ=0.2, K=216), 0.915 (ρ=0.5, K=108), 0.915
(ρ=0.2, K=144); confirmation block at full 10000 resamples: 0.915 (K=108), **0.890** (K=216).
With 200 datasets, SE at 0.88 ≈ 0.023, so 0.88–0.915 are 1.5–3 SE below the nominal 0.95 — a
systematic mild anti-conservatism of the percentile cluster bootstrap, not noise. Similarly the
false-success cell 0.070 (Δ=0, ρ=0, K=144) vs nominal 0.025 (~2.5 SE) is waved away as "within
Monte Carlo error" (proposal lines 276–278).
**Remediation:** report the undercoverage honestly; consider BCa or cluster-t/bootstrap-t
intervals, or state the calibrated coverage level explicitly before freeze.

### F5 — MINOR (disclosure): distinguishability of the mean-vs-CVaR hypothesis is limited to Δ ≥ 0.2 at low ICC — say so
At K=108: P(SUCCESS) = 0.69 at (Δ=0.1, ρ=0.5), 0.04 at (Δ=0.1, ρ=0.8), 0.495 at (Δ=0.3, ρ=0.8)
(artifact cells). The design is confirmatory only for effects ≥ 0.2 and only if realized ICC ≤
~0.25. Since the program's only attested held-out measurement (D2-0004, log-attested) showed
Δ ≈ 0 at boundary rates, the memo should state the design cannot detect small-to-moderate effects
rather than implying general confirmatory power.

### F6 — MINOR (researcher df): K = 108 is a post-hoc grid pick, and the grid coarseness drives it
The rule "smallest simulated K with P(SUCCESS) ≥ 0.8 at Δ=0.2, ρ=0.5" is declared (proposal lines
109–114), which is good — but the grid {36,72,108,144,216} brackets 0.650 (K=72) and 0.990
(K=108): any K between would also pass, and at the protocol's true m=18 even K=72 passes (F2).
The number 108 carries no robustness to the ρ assumption (F1). At minimum disclose that the rule's
answer is grid- and ρ-conditioned; better, derive K from the design-effect formula at a justified
ICC with the real m.

### F7 — MINOR (diagnostic correctness): ρ̂/n_eff degenerate at zero-variance boundaries
`intracluster_diagnostics` returns ρ̂=0, n_eff=N when both MSB and MSW are 0 — e.g. the
all-(True,False) dataset reports `intracluster_rho = 0.0, effective_sample_size = 72.0` despite
perfect within-cluster agreement (verified by direct call). The D2-0004 regime (rates ≈ 1.0)
makes near-boundary data likely, so the headline pseudoreplication diagnostic can report "no
clustering" exactly when outcomes are maximally clustered but variance-free.
**Remediation:** report NA (not 0) when total variance is 0.

### F8 — MINOR (shared with frozen path): percentile index off-by-one
`lo_idx = floor((α/2)·R)` → at R=1000 the interval uses order statistic 26 (≈2.6% quantile);
harmless, slightly conservative, identical in the frozen module. Note only.

### F9 — MINOR (process note): Wave H is post-D2-0004-outcome
No parameter leakage found (F0 option set predeclared; simulation constants are
scenario assumptions; p_M=0.5 is conservative vs the attested boundary rates). But the *decision
to commission* the cluster amendment followed the D2-0004 FAIL; the amendment mechanism permits
this pre-arming, so this is a disclosure note, not a violation. Keep the "no outcome data exists"
statement scoped to D2-0005 (it currently is).

## Summary by attack surface
1. Pseudoreplication/ESS: ICC simulated but mislabeled (F1); K=108 restores calibration only at
   ICC≤~0.25 cells, not at grid ρ=0.8 (F1, F5).
2. Dependence vs real pipeline: mismatched — single pinned base image, K=2 today, cross-model
   same-image correlation unmodeled (F3).
3. CI construction: resampling/determinism/min_clusters all correct; percentile bootstrap mildly
   anti-conservative, coverage overclaimed (F4, F8); boundary behavior safe; ρ̂ degenerate at
   zero variance (F7).
4. Bootstrap assumptions: exchangeability/pairing preserved; seed hygiene verified; 1000 vs 10000
   deviation disclosed and confirmed (Δ=0.2 column: 0.990 grid vs 0.995 at 10000).
5. Decision-region calibration: 0.215 false-success reproduced; Δ=−0.1 never SUCCESS (confirmed,
   p_success=0.000 all cells); but false-success 0.070 cell and coverage 0.880–0.915 underplayed
   (F4).
6. Researcher df: rule disclosed but post-hoc and grid/ρ-conditioned (F6); §4 memo overfit to the
   m=6 grid (F2).
7. Leakage: none found in parameters (F9 note only).
8. Distinguishability: only Δ≥0.2 at low ICC (F5).
9. Code correctness: artifact bit-for-bit reproducible; singleton equivalence bit-for-bit
   verified; no defects in bootstrap mechanics.

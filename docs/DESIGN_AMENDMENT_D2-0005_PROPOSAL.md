# DRAFT PROPOSAL — Pre-Arming Design Amendment for RAC-PER-D2-0005 (Cluster-Robust Redesign)

> **STATUS: DRAFT PROPOSAL — NOT AN EXECUTED AMENDMENT.** This document takes
> effect ONLY when the human governance lead approves it and the amendment is
> executed through the §7 deviations policy / §9 amendment log mechanism of
> `docs/PREREGISTRATION_D2-0005.md` (the same route amendments A1–A4 took).
> Until then, the frozen preregistration (amendments A1–A4) is the only
> governing design, and this document changes nothing.
>
> **Justification basis (mandatory disclosure):** this proposal is justified
> SOLELY by pre-arming operating-characteristic (OC) studies —
> `docs/DESIGN_ANALYSIS_D2-0005.md` (the F0 unit-level OC study) and
> `artifacts/design_analysis_d20005_cluster/results.json` (the cluster-aware
> OC study, `scripts/design_analysis_d20005_cluster.py`). **NO D2-0005 outcome
> data exists**: the generation skeleton is frozen with
> `lock_status: PREREGISTERED`, `lock_inference_performed: false`, trigger
> fields NOT armed; D2-0004 is still open. Every number below is a
> `scenario_assumption` (synthetic data-generating processes), not a
> measurement. Nothing here is tuned against observed outcomes, because none
> exist. No preregistered threshold is touched: the 0.20 interval-width gate,
> z = 1.959963984540054, CVaR α = 0.5, bootstrap seed 20260907, 10000 bootstrap
> resamples, and the §4 decision regions are all held fixed.
>
> **Freezing commitment:** once this amendment is approved and executed, the
> amended design is FROZEN and cannot be further modified — any later change
> would require its own pre-arming amendment under the same mechanism, and any
> change after arming or after outcomes exist is forbidden outright.

---

## 1. Why an amendment is needed (recap of the pre-arming evidence)

The F0 OC study established two facts about the frozen design (72 observation
units = 2 held-out models × 2 fixture crops × 18 transform conditions, analyzed
by the unit-level paired bootstrap of `paired_arm_statistics.py`):

1. **INCONCLUSIVE-dominated at n = 72 under symmetric discordance.**
   P(INCONCLUSIVE) = 1.000 at every simulated Δ_true (−0.1 … +0.5), confirmed
   at the full preregistered 10000 bootstrap resamples; P(SUCCESS) ≥ 0.8 only
   in a narrow near-nested band Δ_true ≈ 0.1–0.2.
2. **Pseudoreplication.** The 72 units are clustered (views/crops of the same
   candidate under the same held-out model); with intracluster correlation ρ
   the effective unit count is n_eff ≈ 72/(1 + (m−1)ρ) — roughly 4–27
   effective units for plausible ρ — so the unit-level bootstrap understates
   the variance of Δ̂ and the F0 decision probabilities are *optimistic*.

The cluster-aware OC study (this proposal's evidence base,
`scripts/design_analysis_d20005_cluster.py`) regenerates the grid under
clustered DGPs (ρ ∈ {0, 0.2, 0.5, 0.8}) and runs BOTH the frozen unit-level
analysis and the proposed cluster-robust analysis
(`ruthless_pipeline/certification/cluster_paired_arm_statistics.py`) on the
SAME synthetic datasets. It confirms both F0 findings directly: under ρ > 0
the unit-level path's intervals are systematically narrower and its coverage
of the true Δ degrades below nominal as ρ grows, while the cluster-robust
path maintains approximately nominal coverage (§3).

The design correction is therefore two-fold and inseparable: **(i) redefine
the inferential unit as the cluster** and **(ii) size the design in clusters,
not views**.

---

## 2. Proposed design correction

### (a) Inferential-unit definition — clusters, not views

The inferential unit of the primary comparison is redefined as the
**independent image cluster**: a base-image × held-out-model evaluation block
whose members (transformation views, fixture crops) are **explicitly declared
pseudoreplicates** — correlated re-observations of the same underlying
randomness — and are **never** counted as independent units. Concretely:

- one cluster = one (base fixture image, held-out model) evaluation block;
  all 18 transformation views (and any repeated crops) of that block are
  members of the cluster;
- the primary endpoint remains the paired per-member outcome
  (arm M detected?, arm C detected?) and Δ = R_M − R_C pooled over members,
  so the estimand is unchanged;
- inference (the bootstrap interval for Δ) resamples **clusters** with
  replacement, carrying all members of a resampled cluster, via
  `cluster_paired_arm_statistics.cluster_paired_arm_statistics` with the
  preregistered z, seed, resample count, and decision regions; per-arm Wilson
  intervals are still reported for descriptive comparability;
- a fail-closed guard (`min_clusters`, preregistered default
  `DEFAULT_MIN_CLUSTERS = 8`) aborts the primary comparison rather than
  emitting a cluster bootstrap over too few clusters;
- the module reports the intracluster-correlation / design-effect diagnostic
  (ρ̂, n_eff) alongside every result so the pseudoreplication level of the
  realized data is disclosed, not assumed.

### (b) Sample size — minimum cluster count

**Proposed: a minimum of `K = 108` independent image clusters** (each
contributing its full member grid), replacing the current "72 observation
units" framing.

Evidence (cluster-robust path, symmetric discordance, ρ = 0.5 — the mid-range
correlation scenario; full table in §3 and in
`artifacts/design_analysis_d20005_cluster/results.{json,md}`):

| K clusters | P(SUCCESS) at Δ_true=+0.2 | CLUSTER CI width | CLUSTER coverage |
|---|---|---|---|
| 36 | 0.025 (grid) / 0.035 (10000) | 0.266 | 0.945 |
| 72 | 0.650 (grid) / 0.630 (10000) | 0.192 | 0.945 |
| **108** | **0.990 (grid) / 0.995 (10000)** | 0.155 | 0.915 |
| 144 | 1.000 (grid) / 1.000 (10000) | 0.133 | 0.930 |
| 216 | 1.000 (grid) / 1.000 (10000) | 0.110 | 0.880 |

The proposed K is the **smallest simulated cluster count at which the
cluster-robust analysis achieves P(SUCCESS) ≥ 0.8 for Δ_true = +0.2** — the
smallest effect the program cares about (the F0 study's near-nested success
band started at Δ ≈ 0.1–0.2, and Δ = 0.2 is also the inconclusive width gate
itself) — **under ρ = 0.5 symmetric discordance**, confirmed at the full
preregistered 10000 bootstrap resamples (§3 confirmation block). The
sensitivity of this requirement to ρ is reported in the full OC table: at
ρ = 0.2 the requirement relaxes to K ≥ 72; at ρ = 0.8 it tightens
to K ≥ 144.

Note what this proposal does NOT do: it does not widen the width gate, move
α, or redraw decision regions. It buys power the only legitimate way — more
independent replication — and it makes the inference honest about clustering.

### (c) More held-out models / crops per cluster does NOT substitute for clusters

The members-per-cluster sweep (fixed Δ_true = +0.2, ρ = 0.5, K = 72 clusters;
m ∈ {2, 6, 18, 36} members per cluster) shows that increasing the number of
views/models/crops **within** a cluster does **not** increase the effective n
for cluster-level variance:

| m members/cluster | CLUSTER P(SUCCESS) | CLUSTER CI width | UNIT P(SUCCESS) (invalid under ρ>0) |
|---|---|---|---|
| 2 | 0.015 | 0.246 | 0.055 |
| 6 | 0.650 | 0.192 | 0.995 |
| 18 | 0.995 | 0.166 | 1.000 |
| 36 | 0.995 | 0.162 | 1.000 |

Cluster-level variance is governed by the number of independent clusters K.
Adding members can only remove the (1−ρ)/m share of member-level noise: the
variance floor ρ·σ²/K is untouched, so the gain saturates fast — at ρ = 0.5,
K = 72 the mean CI width falls 0.246 → 0.166 from m = 2 to m = 18, then
**m = 18 → 36 buys essentially nothing (0.166 → 0.162, P(SUCCESS) flat at
0.995)**: the within-cluster term is already exhausted and only the
cluster-level term remains. Quadrupling within-cluster replication cannot do
what even a 1.5× increase in K does (K = 72 → 108 at fixed m = 6 moves
P(SUCCESS) 0.650 → 0.990 with 648 members — a QUARTER of the 2592-member m = 36
sweep row). Worse, the invalid unit-level analysis *appears* to improve
monotonically with m (0.055 → 1.000 — spurious precision from counting
pseudoreplicates as units), which is exactly the failure mode this amendment
removes. **Design consequence: budget must go into more independent
base-image clusters, not more views per image.**

### (d) Preregistration sections to amend (via §7 / §9) — drafted replacement text

If approved, the following edits are executed as amendment **A5** in the §9
amendment log of `docs/PREREGISTRATION_D2-0005.md` (this proposal does NOT
edit the preregistration itself):

1. **§3 "Primary comparison"** — replace the analysis-module reference:

   > **Primary comparison:** paired risk difference Δ = R_M − R_C on matched
   > conditions, pooled over all cluster members, with Wilson score intervals
   > for each marginal rate (descriptive) and a deterministic-seed
   > **cluster-bootstrap** interval for the difference, via
   > `ruthless_pipeline/certification/cluster_paired_arm_statistics.py`
   > (`cluster_paired_arm_statistics`; bootstrap_resamples = 10000,
   > bootstrap_seed = 20260907, z = 1.959963984540054). The inferential unit
   > is the independent image cluster (one base-image × held-out-model
   > evaluation block); transformation views and repeated crops within a
   > cluster are declared pseudoreplicates and are never independent units.
   > The bootstrap resamples clusters with replacement, carrying all members.
   > The comparison fails closed (INCONCLUSIVE, not estimable) below
   > `min_clusters = 8` clusters. One-sided interpretation preregistered in
   > favor of Arm C (H1).

2. **§4 "Success criteria and decision regions"** — replace the trial-count
   sentence and restate regions in cluster terms:

   > The design comprises **K ≥ 108 independent image clusters**, each
   > contributing its full member grid (18 transformation views per
   > held-out-model block before invalid-condition exclusion). Decision
   > regions are unchanged — success: CI lower bound > 0; null: CI includes
   > 0 within the width budget; negative: CI entirely below 0; inconclusive:
   > interval width exceeds 0.20 or the cluster count falls below the
   > preregistered minimum — with the interval now the cluster-bootstrap
   > interval of §3.

3. **§6 "Analysis plan"** — replace the "Exact statistical calls" bullet's
   module and unit language:

   > The primary comparison uses
   > `cluster_paired_arm_statistics.cluster_paired_arm_statistics` over
   > paired per-member binary outcomes grouped by cluster key
   > (base-image × held-out-model block), with the exact preregistered
   > parameters: Δ = R_M − R_C one-sided toward Arm C; Wilson z =
   > 1.959963984540054 per arm rate (descriptive); deterministic hash-seeded
   > cluster bootstrap, resamples = 10000, seed = 20260907; decision regions
   > per §4 with INCONCLUSIVE at width > 0.20; fail-closed guard
   > `min_clusters = 8`. The intracluster-correlation / design-effect
   > diagnostic (ρ̂, n_eff) is reported with the primary result. Exactly one
   > primary comparison; no multiplicity correction.

4. **§5 "Procedures"** — add to the design-grid description:

   > The held-out evaluation grid is sized in independent image clusters:
   > K ≥ 108 base-image × held-out-model blocks per arm (paired across
   > arms), with the full transformation sweep within each block.

5. **§9 amendment log** — append:

   > **A5 — Cluster-robust inferential unit and cluster-count resizing (§3,
   > §4, §5, §6).** The inferential unit is redefined as the independent
   > image cluster (views/crops within a cluster declared pseudoreplicates);
   > the primary interval becomes the deterministic cluster bootstrap of
   > `cluster_paired_arm_statistics.py`; the design is resized to K ≥ 108
   > clusters. Justified SOLELY by the pre-arming OC studies
   > (`docs/DESIGN_ANALYSIS_D2-0005.md`,
   > `artifacts/design_analysis_d20005_cluster/results.json`,
   > `docs/DESIGN_AMENDMENT_D2-0005_PROPOSAL.md`); no outcome data exists.
   > All preregistered thresholds unchanged (z, seed, resamples, 0.20 width
   > gate, decision regions, α = 0.5). Once executed, the amended design is
   > frozen.

### (e) Governance statements (restated for the record)

- This proposal is justified **solely** by pre-arming operating-characteristic
  studies; **no D2-0005 outcome data exists** and none was used.
- This is a **DRAFT PROPOSAL**: it takes effect only on human governance-lead
  approval and execution of amendment A5 via the §7/§9 mechanism.
- Once frozen, the amended design **cannot be further modified**; any later
  deviation follows the §7 deviations policy (pre-execution amendment or
  `scenario_assumption`/invalidation with disclosure).
- If the governance lead judges K = 108 clusters operationally
  infeasible, the legitimate fallback is the F0 study's option (b2): declare
  D2-0005 an exploratory / pilot-sized prospective experiment — **not** a
  return to unit-level inference over pseudoreplicates.

---

## 3. Supporting OC tables (cluster-robust vs unit-level on the SAME datasets)

Source: `artifacts/design_analysis_d20005_cluster/results.{json,md}`
(regenerate byte-identically with
`python scripts/design_analysis_d20005_cluster.py`). Monte Carlo error per
probability ≤ √(0.25/200) ≈ 0.035 (200 datasets/cell). Grid cells use 1000
bootstrap resamples (disclosed deviation, as in F0); the confirmation block
re-runs the Δ_true = +0.2, ρ = 0.5 column at the full preregistered 10000.

Full Δ_true = +0.2 operating-characteristic table (all ρ × K cells; the complete grid including Δ_true ∈ {−0.1, 0.0, 0.1, 0.3} is in the artifact):

| rho | K clusters | CLUSTER P(SUCCESS) | CLUSTER P(INCONCL) | CLUSTER coverage | CLUSTER width | UNIT P(SUCCESS) | UNIT coverage |
|---|---|---|---|---|---|---|---|
| 0.0 | 36 | 0.845 | 0.155 | 0.955 | 0.178 | 1.000 | 0.975 |
| 0.0 | 72 | 1.000 | 0.000 | 0.945 | 0.127 | 1.000 | 0.945 |
| 0.0 | 108 | 1.000 | 0.000 | 0.945 | 0.103 | 1.000 | 0.950 |
| 0.0 | 144 | 1.000 | 0.000 | 0.900 | 0.089 | 1.000 | 0.915 |
| 0.0 | 216 | 1.000 | 0.000 | 0.960 | 0.073 | 1.000 | 0.955 |
| 0.2 | 36 | 0.740 | 0.260 | 0.950 | 0.190 | 0.985 | 0.955 |
| 0.2 | 72 | 1.000 | 0.000 | 0.950 | 0.139 | 1.000 | 0.920 |
| 0.2 | 108 | 1.000 | 0.000 | 0.920 | 0.113 | 1.000 | 0.915 |
| 0.2 | 144 | 1.000 | 0.000 | 0.915 | 0.097 | 1.000 | 0.885 |
| 0.2 | 216 | 1.000 | 0.000 | 0.910 | 0.080 | 1.000 | 0.890 |
| 0.5 | 36 | 0.025 | 0.975 | 0.945 | 0.266 | 0.905 | 0.770 |
| 0.5 | 72 | 0.650 | 0.340 | 0.945 | 0.192 | 0.995 | 0.775 |
| 0.5 | 108 | 0.990 | 0.000 | 0.915 | 0.155 | 1.000 | 0.760 |
| 0.5 | 144 | 1.000 | 0.000 | 0.930 | 0.133 | 1.000 | 0.800 |
| 0.5 | 216 | 1.000 | 0.000 | 0.880 | 0.110 | 1.000 | 0.760 |
| 0.8 | 36 | 0.000 | 1.000 | 0.940 | 0.360 | 0.830 | 0.635 |
| 0.8 | 72 | 0.000 | 1.000 | 0.940 | 0.261 | 0.970 | 0.675 |
| 0.8 | 108 | 0.210 | 0.785 | 0.945 | 0.212 | 0.990 | 0.660 |
| 0.8 | 144 | 0.905 | 0.085 | 0.945 | 0.185 | 1.000 | 0.610 |
| 0.8 | 216 | 0.990 | 0.000 | 0.935 | 0.150 | 1.000 | 0.650 |

### False-success control

At Δ_true = 0 and Δ_true = −0.1, P(SUCCESS) for the cluster-robust path stays
near the nominal one-sided 2.5% level across all ρ (max observed 0.070 over
the Δ ≤ 0 grid, at ρ = 0, K = 144 — within Monte Carlo error of nominal;
under ρ > 0 the max is 0.035). **The frozen unit-level path does NOT retain
this control under clustering:** at Δ_true = 0, ρ = 0.8 its false-success
rate reaches 0.215 (at K = 108; 0.085 already at ρ = 0.5) — variance
understatement does not merely inflate power at positive Δ, it manufactures
false SUCCESS decisions at Δ = 0. Directional honesty of the cluster path is
preserved: at Δ_true = −0.1 it returns NEGATIVE/INCONCLUSIVE, never SUCCESS
(P(SUCCESS) = 0.000 at every ρ × K cell simulated).

### Coverage

Under ρ = 0 the two paths agree closely (same estimand, independent members;
their widths match to within Monte Carlo noise — e.g., 0.127 vs 0.127 at
K = 72). In the degenerate cluster-size-1 case the module is bit-for-bit
identical to the frozen unit-level path by construction and by test. As ρ
grows the unit-level
path's coverage of the true Δ falls below the nominal 95% (e.g., ρ = 0.8:
coverage 0.675 at K = 72) while the cluster-robust path remains near
nominal (coverage 0.940), confirming the F0 pseudoreplication warning
quantitatively.

---

## 4. Decision memo — recommendation among the pre-registered options

The F0 study's option set for D2-0005, evaluated strictly on the pre-arming
OC evidence above (no outcome data exists; no threshold is moved):

1. **Retain D2-0005 as a pilot-sized / exploratory prospective experiment.**
   Viable and honest, but spends the entire experimental budget to produce an
   INCONCLUSIVE-dominated or exploratory-only result; it does not deliver the
   confirmatory decision the program needs at Δ_true = +0.2. Keep only as the
   disclosed fallback if the cluster requirement below is operationally
   infeasible.
2. **Increase genuinely independent units (clusters), holding the frozen
   unit-level analysis.** Rejected as insufficient on its own: under
   intracluster correlation the unit-level path is not merely low-powered, it
   is *invalid* — false-SUCCESS at Δ_true = 0 reaches 0.215 at ρ = 0.8 and
   coverage falls to 0.61–0.68 (§3). Adding units to an invalid analysis
   manufactures confident wrong answers.
3. **Revise the inferential method (cluster-robust bootstrap), holding the
   frozen 72-unit design.** Rejected as insufficient on its own: the method
   is valid at K = 72 (false-success ≤ 0.035, coverage ≈ nominal) but
   under-powered — P(SUCCESS) = 0.630–0.650 at Δ_true = +0.2, ρ = 0.5.

**RECOMMENDATION: options 2 + 3 jointly** — revise the inferential unit to
the cluster (cluster-robust bootstrap via
`ruthless_pipeline/certification/cluster_paired_arm_statistics.py`, same
frozen decision rule, seed, z, α, resample count, and width gate) **and**
increase genuinely independent units to a minimum of **K = 108 clusters**
(6 members each), the smallest simulated K with P(SUCCESS) ≥ 0.8 at
Δ_true = +0.2 under ρ = 0.5 (0.990 grid / 0.995 confirmation; sensitivity:
K ≥ 72 at ρ = 0.2, K ≥ 144 at ρ = 0.8). This is the only option combination
that is simultaneously valid (false-success controlled, coverage near
nominal) and adequately powered, and it is the combination drafted as
amendment A5 in §2(d). If K = 108 is operationally infeasible, fall back to
option 1 (exploratory declaration) — never to unit-level inference over
pseudoreplicates.

---

## 5. Reproduction

```
python scripts/design_analysis_d20005_cluster.py   # regenerates artifacts/ byte-identically
python -m pytest tests/test_cluster_paired_arm_statistics.py tests/test_design_analysis_d20005_cluster.py
```

Fixed constants: sim_seed 20261209; grid bootstrap resamples 1000
(confirmation 10000); bootstrap seed 20260907; z 1.959963984540054;
INCONCLUSIVE_WIDTH_MAX 0.20; min_clusters 8; 200 datasets per cell. No
timestamps, no `random` module state, no platform-dependent hashing anywhere
in the pipeline.

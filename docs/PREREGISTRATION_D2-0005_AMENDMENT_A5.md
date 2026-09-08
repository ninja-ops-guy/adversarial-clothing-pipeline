# PREREGISTRATION AMENDMENT A5 — RAC-PER-D2-0005 Cluster-Robust Redesign (FREEZE CANDIDATE)

> **STATUS: FREEZE CANDIDATE — NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT.**
> This document is the drafted amendment **A5** to `docs/PREREGISTRATION_D2-0005.md`,
> executing PATH (A) of `docs/D2-0005_GO_NOGO_MEMO.md` (sha256
> `f05e2d05029c7fe7c7303bf49534d58cddd1299a6351d0f498ed2045cad3ffbc`) and the DRAFT v2
> proposal `docs/DESIGN_AMENDMENT_D2-0005_PROPOSAL.md`. It is a NEW document; the frozen
> preregistration (amendments A1–A4) is NOT edited by this package. This freeze candidate
> **does NOT arm, execute, or trigger anything**: D2-0005 becomes effective ONLY after
> (1) human governance-lead approval, (2) this freeze, (3) the independent verifier step,
> (4) the outcome-free rehearsal (including the ICC ≤ 0.25 gate of clause A5.5), and
> (5) the boundary audit all pass, and the user signs the ARMING PACKET. Until then the
> header status above is the operative state and no clause below is in force.
>
> **Justification basis (mandatory disclosure):** justified SOLELY by pre-arming
> operating-characteristic studies (`docs/DESIGN_ANALYSIS_D2-0005.md` and
> `artifacts/design_analysis_d20005_cluster/results.json`, schema_version 2.0, sha256
> `5e8c78b1af395a67258960ac4d4f35e3e7cf20bfef381fd39f8d70c43a67d7d1`). **NO D2-0005
> outcome data exists** and none was used. No preregistered threshold is moved:
> z = 1.959963984540054, bootstrap seed 20260907, bootstrap resamples 10000, the 0.20
> interval-width gate, CVaR α = 0.5, candidate-pool seed 1337, and the §4 decision
> regions are all held fixed.
>
> Every clause below states the OLD preregistration text verbatim (guarded against drift
> by `tests/test_d20005_freeze_candidate.py`) followed by the NEW amended text.

---

## A5.1 — Model sets (header): restated and hash-pinned (no change to membership)

**OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
**Model sets:** surrogate `PERSON-SUR-v3` (6 models: yolov8n, fasterrcnn_mobilenet_v3_320, detr_resnet50, ssdlite320_mobilenet_v3, retinanet_resnet50_fpn_v2, fcos_resnet50_fpn); held-out `PERSON-HO-v3` (fasterrcnn_resnet50_fpn_v2, maskrcnn_resnet50_fpn_v2).
```

**NEW (A5):** Model sets are **unchanged**: surrogate `PERSON-SUR-v3` (6 models:
yolov8n, fasterrcnn_mobilenet_v3_320, detr_resnet50, ssdlite320_mobilenet_v3,
retinanet_resnet50_fpn_v2, fcos_resnet50_fpn); held-out `PERSON-HO-v3`
(fasterrcnn_resnet50_fpn_v2, maskrcnn_resnet50_fpn_v2). The frozen set files are
hash-pinned for this freeze in
`ruthless_pipeline/certification/config/d20005_freeze/model_sets.json` (schema
`d2-0005-freeze-model-sets` 1.0): `model_sets/PERSON-SUR-v3.json` sha256
`2f06c19e9e51f3f607b04b499760ab7f470f4b6e18f9c834013fb0a06a5d8876`,
`model_sets/PERSON-HO-v3.json` sha256
`ad1127659a5615871ff320056415dd3c8e8b6a27acef7c6a3bcc4a96e713495e`. The held-out set is
referenced by identity and hash only; this amendment neither requests nor implies any
held-out access.

---

## A5.2 — §3 "Primary comparison": cluster-robust analysis replaces unit-level analysis

**OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
**Primary comparison:** paired risk difference Δ = R_M − R_C on matched conditions (identical fixture, crops, sweep grid, **and the same underlying candidate pool** for both arms — the pairing is exact: each arm's selected winner comes from the identical candidate set, so the comparison isolates the objective with no sampling variability between pools), with Wilson score intervals for each marginal rate and a deterministic-seed bootstrap interval for the difference, via `ruthless_pipeline/certification/paired_arm_statistics.py` (`paired_arm_statistics`, `wilson_interval`, `bootstrap_paired_difference_interval`; bootstrap_resamples = 10000, bootstrap_seed = 20260907, z = 1.959963984540054) — AMENDED from `trial_statistics.py`, see §9. One-sided interpretation preregistered in favor of Arm C (H1).
```

**NEW (A5):** **Primary comparison:** paired risk difference Δ = R_M − R_C on matched
conditions, pooled over all cluster members (the pairing is unchanged: identical fixture,
crops, sweep grid, and the same shared 100-candidate pool for both arms), with Wilson
score intervals for each marginal rate (descriptive) and a deterministic hash-seeded
**cluster-bootstrap** interval for the difference, via
`ruthless_pipeline/certification/cluster_paired_arm_statistics.py`
(`cluster_paired_arm_statistics`; bootstrap_resamples = 10000, bootstrap_seed = 20260907,
z = 1.959963984540054 — all identical to the frozen parameters). **The inferential unit
is the independent base image.** All transformation views and fixture crops of one base
image, under BOTH arms, are members of that image's cluster and are declared
pseudoreplicates — never independent units. The bootstrap resamples clusters (images)
with replacement, carrying all members of every drawn cluster. The comparison **fails
closed** (raises rather than emitting a non-identifiable interval) below
`min_clusters = 8` (`DEFAULT_MIN_CLUSTERS = ABSOLUTE_MIN_CLUSTERS = 8`). The
intracluster-correlation / design-effect diagnostic (ρ̂, n_eff) is reported with every
primary result — **NA (null) at zero total variance, never 0**. The analysis
implementation is hash-pinned: sha256
`bad02b22a9061dd3baf273d92facff42c847f4da2c2e08ed891ac118f6094674` for
`ruthless_pipeline/certification/cluster_paired_arm_statistics.py`. Documented
divergence from the frozen unit-level path: the percentile lower-index off-by-one of
`paired_arm_statistics.py` is corrected in the new module ONLY; the frozen module is NOT
modified and the singleton-path divergence is pinned by
`tests/test_cluster_paired_arm_statistics.py`. One-sided interpretation remains
preregistered in favor of Arm C (H1). The frozen `paired_arm_statistics.py` path is
superseded for the primary comparison but remains the pinned reference implementation.

---

## A5.3 — §4 "Success criteria and decision regions": cluster-based sizing; regions restated in cluster terms

**OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
Let Δ = R_M − R_C with its 95% two-sided CI (equivalently, the preregistered one-sided 97.5% upper bound). Conditions-per-model = 3 brightness × 1 scale × 2 blur × 3 rotation = 18; with 2 held-out models and 2 fixture crops, the valid-trial count per arm is fixed by the protocol grid (up to 72 condition-model-crop trials before invalid-condition exclusion).
```


**OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
- **Success (H1 supported):** Δ > 0 with the CI excluding 0 in the preregistered direction (CI lower bound > 0), i.e., Arm C's held-out detection rate is significantly below Arm M's, one-sided.
- **Null (H0 not rejected; informative):** the CI includes 0 (either sign). Recorded and published as a closed-generation null datapoint.
- **Negative (direction reversed):** CI entirely below 0 — CVaR optimization transfers *worse*. Published as-is; this is a legitimate falsifying result, not a failed experiment.
- **Inconclusive region (preregistered):** if the risk-difference interval width exceeds `WILSON_WIDTH_MAX = 0.20` (matching the failure-taxonomy `STATISTICAL_INCONCLUSIVE` threshold) or valid-trial counts fall below the stopping-rule minimum (§6), the primary comparison is declared INCONCLUSIVE; the arm-level rates are still reported with their Wilson intervals, and the generation closes as inconclusive — never re-run silently.
```

**NEW (A5):** Let Δ = R_M − R_C with its two-sided cluster-bootstrap CI at the frozen
z = 1.959963984540054 (equivalently the preregistered one-sided 97.5% bound), computed
per A5.2. The design comprises **K ≥ 72 independent base images** (the inferential
units), each contributing its full member grid of 18 transformation views × 2 fixture
crops = **36 paired members per image** (K = 72 → 2592 paired member observations per
arm), per the multi-image fixture protocol of A5.6. Decision regions are **unchanged**,
restated against the cluster-bootstrap interval:

- **Success (H1 supported):** CI lower bound > 0 (unchanged region).
- **Null (H0 not rejected; informative):** the CI includes 0 (either sign); recorded and
  published as a closed-generation null datapoint.
- **Negative (direction reversed):** CI entirely below 0; published as-is.
- **Inconclusive (preregistered):** interval width exceeds `WILSON_WIDTH_MAX = 0.20`
  (unchanged gate), or the realized cluster count falls below the preregistered minimum
  (K < 72 planned; the analysis itself fails closed below `min_clusters = 8`), or
  valid-trial counts fall below the stopping-rule minimum.

**Sizing validity gate:** this sizing is valid only for realized ICC ≤ 0.25; the
rehearsal gate of A5.5 must confirm it BEFORE arming, else K must be raised by a further
pre-arming amendment (ICC ≈ 0.5 requires K ≈ 144, disclosed design-effect extrapolation).
**Distinguishability floor (disclosed):** confirmatory scope is limited to Δ ≥ 0.2 at
verified ICC ≤ 0.25. P(SUCCESS) = 0.700 at (Δ_true = +0.1, ICC = 0.25, K = 72) — below
the confirmatory bar — and P(SUCCESS) ≤ 0.070 at ICC = 0.5 for Δ_true = +0.2 at K = 72.
A SUCCESS supports "Δ > 0"; an INCONCLUSIVE at small true Δ is an expected design
limitation, not an anomaly. **Coverage claim (downgraded, A5.4).** False-success at
Δ_true = 0 is 0.030–0.035 at K = 72 (near the nominal one-sided 2.5%) and 0.000 at
Δ_true = −0.1 at every simulated cell; the small-K elevation (0.085 at K = 8) is beyond
Monte Carlo error and is mitigated by design sizing, not asserted away.

---

## A5.4 — Coverage claim downgrade (NEW clause; no OLD text exists)

There is no OLD clause: the frozen preregistration asserts a "95% two-sided CI" without a
calibrated-coverage statement. **NEW (A5):** **Nominal 0.95 coverage is NOT claimed.**
The calibrated claim written into this preregistration is: two-sided coverage
**≈ 0.90–0.95 at the recommended design point** (achieved 0.925–0.955 at K = 72 across
the simulated ICC range; 0.850–0.965 across the full Δ_true = +0.2 grid). This is a
mild, systematic anti-conservatism of the percentile cluster bootstrap, disclosed rather
than hidden. Fixing it properly (BCa or bootstrap-t cluster intervals) is a candidate
future pre-arming amendment and is NOT part of A5.

---

## A5.5 — §5 "Procedures": seeds restated; multi-image fixture protocol added; ICC rehearsal gate added

**OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
- **Seeds (fixed):** one shared seed 1337 for candidate generation, selection, and benchmark (as in `make_config` and `run_measured_benchmark.py`); bootstrap seed 20260907 (as in `paired_arm_statistics`, amended from `paired_trial_statistics` — see §9). There are no per-arm seeds: both arms draw from the identical pool, recorded in each candidate's `OptimizerConfig.seed` (= 1337) telemetry.
```

**NEW (A5):** Seeds are **unchanged and pinned**: one shared seed 1337 for candidate
generation, selection, and benchmark; bootstrap seed 20260907 (now the cluster-bootstrap
seed of A5.2). Additionally pinned for provenance: design-simulation seed 20261209 of
the pre-arming OC study (`scripts/design_analysis_d20005_cluster.py`, sha256
`ddaab35f4afe382ce096808b3b083a46420c01480397c82c13f99878a91b6737`). Machine-readable
pin: `ruthless_pipeline/certification/config/d20005_freeze/seeds.json` (schema
`d2-0005-freeze-seeds` 1.0).

**NEW (A5) — multi-image fixture protocol** (machine-readable pin:
`ruthless_pipeline/certification/config/d20005_freeze/fixture_protocol.json`, schema
`d2-0005-fixture-protocol` 1.0):

- The held-out evaluation fixture comprises **K ≥ 72 independent base images**, each
  content-pinned by **SHA-256 of the exact image bytes** in the frozen fixture manifest
  (planned path `fixtures/d20005_base_images/manifest.json`, schema
  `d2-0005-fixture-manifest` 1.0), exactly as `source-zidane.jpg` is pinned today.
- Per image: the existing frozen 18-transformation sweep × the existing 2 fixed crop
  specs of `run_measured_benchmark.prepare_fixture` = **36 paired members per image**,
  both arms scored on the SAME rendered view (pairing is within-member). Total design
  size at K = 72: **2592 paired member observations per arm**.
- **Independence criteria:** images are sourced independently of the candidate pipeline
  and of every surrogate/held-out model; no image may be selected, rejected, or weighted
  on the basis of any measured outcome; no two base images may be near-duplicates,
  crops, or transformed variants of one another; no base image may overlap the surrogate
  optimization or any prior-generation evaluation fixture.
- Image selection, crop specs, and the hash manifest are frozen BEFORE arming as part of
  executing A5; any change after freeze requires a new pre-arming amendment under the §7
  deviations policy.
- **Rehearsal ICC gate (hard gate):** before arming, the realized intracluster
  correlation is measured via the ρ̂ diagnostic
  (`cluster_paired_arm_statistics.intracluster_diagnostics`) on **outcome-free rehearsal
  data**; the design is armed only if **ICC ≤ 0.25 is confirmed**. If the realized ICC
  materially exceeds 0.25, K must be raised by a further pre-arming amendment (ICC ≈ 0.5
  → K ≈ 144, disclosed extrapolation) BEFORE arming. At zero total variance ρ̂ is
  reported NA, never 0.
- **Unmodeled-dependence disclosure:** cross-model same-image correlation and view-level
  ICC heterogeneity are NOT modeled in the sizing study; they are absorbed into the
  within-cluster member structure at analysis time and bounded by the rehearsal gate.
- **Provenance disclosure:** K = 72 is a disclosed grid pick from K ∈ {8, 12, 18, 24,
  36, 72}, the smallest simulated cluster count achieving P(SUCCESS) ≥ 0.8 at
  Δ_true = +0.2 under ICC = 0.25; the choice is conditioned on the ICC ≤ 0.25 assumption
  enforced by the gate above.

---

## A5.6 — §5 "Procedures": exclusion rules restated for the cluster design

**OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
- **Invalidation/exclusion rules:** a condition where the control/baseline is not detected is invalid and never counted as candidate success (`split_valid_invalid`); arms with `invalid_condition_fraction > 0.10` in selection are flagged per the selection script; held-out trials excluded only by the same control-undetected rule, reported via `invalid_condition_report`. Any run with a model-lock mismatch, missing preregistered hash, or pool-guard failure is invalid in full and documented, not patched.
```

**NEW (A5):** The frozen exclusion rules are **unchanged and extended to the cluster
design**: a condition where the control/baseline is not detected is invalid and never
counted as candidate success (`split_valid_invalid`); arms with
`invalid_condition_fraction > 0.10` in selection are flagged per the selection script;
held-out trials are excluded only by the same control-undetected rule, reported via
`invalid_condition_report`. Under the cluster design, exclusion operates at the
**member level within a cluster** (an excluded member is dropped from both arms of the
pair, preserving within-member pairing; a base image losing its entire 36-member grid is
dropped as a cluster and counted against the K ≥ 72 minimum and the fail-closed
`min_clusters = 8` floor). Any run with a model-lock mismatch, missing preregistered
hash, pool-guard failure, or fixture-manifest hash mismatch is invalid in full and
documented, not patched.

---

## A5.7 — §6 "Analysis plan": exact statistical calls replaced

**OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
- **Exact statistical calls (AMENDED — see §9):** the primary comparison uses `ruthless_pipeline/certification/paired_arm_statistics.py::paired_arm_statistics` over paired per-observation binary outcomes keyed by observation unit (`held-out model_id | transform_id | fixture_index`), with the exact preregistered parameters: primary Δ = R_M − R_C (one-sided toward Arm C, H1: Δ > 0); Wilson score intervals per arm rate at z = 1.959963984540054 (`statistics.wilson_interval`); paired interval for Δ via deterministic hash-seeded bootstrap over observation units with bootstrap_resamples = 10000 and bootstrap_seed = 20260907; discordant-pair counts (b = M-detected/C-not, c = C-detected/M-not) reported for condition-level behavior; decision regions per §4 with the interval declared INCONCLUSIVE when its width exceeds WILSON_WIDTH_MAX = 0.20. Exactly one primary comparison is performed; no multiplicity correction is applied (secondary endpoints remain descriptive, below). This module is used instead of `trial_statistics.paired_trial_statistics`, which assumes a physical matched control with valid-control rate 1.0 by construction and therefore does not apply to a digital two-arm ablation where both arm rates are estimated. Invalid-condition accounting (control/baseline-undetected conditions excluded) still follows `split_valid_invalid` / `invalid_condition_report` semantics upstream of pairing, per §5.
```

**NEW (A5):** The primary comparison uses
`ruthless_pipeline/certification/cluster_paired_arm_statistics.py::
cluster_paired_arm_statistics` over paired per-member binary outcomes grouped by cluster
key (the base image), with the exact preregistered parameters: Δ = R_M − R_C one-sided
toward Arm C (H1); Wilson z = 1.959963984540054 per arm rate (descriptive);
deterministic hash-seeded cluster bootstrap, resamples = 10000, seed = 20260907;
discordant-pair counts reported; decision regions per §4 (A5.3) with INCONCLUSIVE at
width > 0.20; fail-closed guard `min_clusters = 8`. The ρ̂/n_eff diagnostic is reported
with the primary result (NA at zero total variance). Invalid-condition accounting still
follows `split_valid_invalid` / `invalid_condition_report` semantics upstream of pairing
(A5.6). Exactly one primary comparison; no multiplicity correction; secondary endpoints
remain descriptive. The output record is the canonical JSON of
`cluster_paired_arm_statistics.to_canonical_json` (schema
`d2-0005-cluster-paired-arm-statistics` 1.0; planned artifact
`artifacts/d20005_primary_comparison/results.json`).

---

## A5.8 — Runtime lock and expected schemas (NEW clause; no OLD text exists)

**NEW (A5):** The runtime is locked by `benchmarks/runtime_lock.json` (schema_version
1.0; python 3.11, torch 2.14.0+cpu, torchvision 0.29.0+cpu, transformers 4.57.6,
ultralytics 8.4.142; sha256
`3c7ca4696a8066f3485e2141bab46570ab3265f591ffc87cd3a44795cd361186`), verified by
`scripts/verify_runtime_lock.py` as a hard gate before any model download or inference.
Every artifact the amended design produces carries a named schema id and
`schema_version`, enforced fail-closed by
`ruthless_pipeline/certification/schema_version.py::require_schema_version`:

| Artifact | Planned path | Schema id | schema_version |
|---|---|---|---|
| Freeze manifest (this package) | `docs/D2-0005_FREEZE_CANDIDATE.json` | `d2-0005-freeze-candidate` | 1.0 |
| Freeze seeds pin | `ruthless_pipeline/certification/config/d20005_freeze/seeds.json` | `d2-0005-freeze-seeds` | 1.0 |
| Freeze model-set pin | `ruthless_pipeline/certification/config/d20005_freeze/model_sets.json` | `d2-0005-freeze-model-sets` | 1.0 |
| Fixture protocol pin | `ruthless_pipeline/certification/config/d20005_freeze/fixture_protocol.json` | `d2-0005-fixture-protocol` | 1.0 |
| Fixture image manifest (rehearsal) | `fixtures/d20005_base_images/manifest.json` | `d2-0005-fixture-manifest` | 1.0 |
| Rehearsal ICC report | `artifacts/d20005_rehearsal_icc/results.json` | `d2-0005-rehearsal-icc` | 1.0 |
| Primary comparison result | `artifacts/d20005_primary_comparison/results.json` | `d2-0005-cluster-paired-arm-statistics` | 1.0 |
| Runtime lock | `benchmarks/runtime_lock.json` | `runtime-lock` | 1.0 |
| OC study evidence base | `artifacts/design_analysis_d20005_cluster/results.json` | `design-analysis-d20005-cluster` | 2.0 |
| Per-candidate telemetry | per-arm sealed telemetry records | `telemetry-contract` | 1.0 |

The full machine-readable enumeration with hashes lives in
`docs/D2-0005_FREEZE_CANDIDATE.json`.

---

## A5.9 — §9 amendment-log entry (to be appended on execution of A5)

> **A5 — Cluster-robust inferential unit, multi-image fixture, and cluster-count
> resizing (§3, §4, §5, §6).** The inferential unit is redefined as the independent base
> image (views/crops within an image declared pseudoreplicates); a multi-image fixture of
> K ≥ 72 SHA-256-pinned base images × 36 members each (2592 paired observations at
> K = 72) is specified; the primary interval becomes the deterministic cluster bootstrap
> of `cluster_paired_arm_statistics.py`; the design is resized to K ≥ 72 clusters gated
> on rehearsal-measured ICC ≤ 0.25; the coverage claim is downgraded to a calibrated
> ≈ 0.90–0.95 (nominal 0.95 NOT claimed); confirmatory scope is limited to Δ ≥ 0.2.
> Justified SOLELY by pre-arming OC studies; no D2-0005 outcome data exists. All
> preregistered thresholds unchanged (z = 1.959963984540054, seed 20260907, 10000
> resamples, 0.20 width gate, α = 0.5, decision regions, model sets, seeds). Once
> executed, the amended design is frozen.

---

## Addendum — Resolution of stale "D2-0004 still open" lines (amendment text, NOT edits to the frozen file)

The frozen preregistration predates the D2-0004 closure and carries three statements
that are now factually stale. They are resolved HERE, as amendment text; the frozen file
itself is not edited.

1. **OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
**Supersedes/depends on:** D2-0004 (RAC-PER-D2-0004, status READY_FOR_FRESH_HELDOUT_RUN) must close first; D2-0005 MUST NOT be opened, executed, or trigger-wired while D2-0004 is open.
```

   **Resolution (A5 addendum):** D2-0004 is **closed** (FAIL / RAC-D0, log-attested,
   immutable; `docs/D2-0004_CLOSURE_NOTE.md`). The precondition "D2-0004 must close
   first" is therefore SATISFIED as of this amendment. No D2-0004 outcome value entered
   any simulation parameter of the A5 evidence base (red-team F9 disclosure, proposal
   header); D2-0004 is cited for closure status only.

2. **OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
- D2-0005 execution requires D2-0004 closed, a new lock freeze under `model-lock-bootstrap`, and an explicit trigger arming in a later, separately reviewed change.
```

   **Resolution (A5 addendum):** "D2-0004 closed" is now met. The remaining
   requirements stand unchanged and are NOT met by this package: a new lock freeze under
   `model-lock-bootstrap` and an explicit trigger arming in a later, separately reviewed
   change (the ARMING PACKET) are still required. This freeze candidate performs neither.

3. **OLD (verbatim from `docs/PREREGISTRATION_D2-0005.md`):**

```old
(D2-0004 still open; generation skeleton `lock_status: PREREGISTERED`, trigger fields NOT armed; `generations/RAC-PER-D2-0005.json` untouched).
```

   **Resolution (A5 addendum):** the parenthetical's "(D2-0004 still open; ...)" is stale
   only as to D2-0004's status: amendments A1–A4 were made while D2-0004 was open, and A5
   is made after D2-0004 closed but still **before D2-0005 is armed or executed** — the
   generation skeleton remains `lock_status: PREREGISTERED`, trigger fields NOT armed,
   `generations/RAC-PER-D2-0005.json` untouched. The pre-arming legitimacy of the §7/§9
   mechanism is unaffected.

---

## Non-arming statement

This amendment is a FREEZE CANDIDATE with status **NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT**.
It arms nothing, executes nothing, and edits no frozen document. It takes effect only on
human governance-lead approval and execution through the §7/§9 mechanism, after the
independent verifier step, the outcome-free rehearsal (including the ICC ≤ 0.25 gate),
and the boundary audit pass and the user signs the ARMING PACKET. If K = 72 independent
base images is judged operationally infeasible, the legitimate fallback is the disclosed
pilot-sized/exploratory declaration (memo path B) — never unit-level inference over
pseudoreplicates.

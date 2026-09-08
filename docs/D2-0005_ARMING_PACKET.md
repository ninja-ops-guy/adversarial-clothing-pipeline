# D2-0005 ARMING PACKET (queue step 8 — FINAL)

> **PACKET STATUS: AWAITING_USER_DECISION — autonomous progress halted at this
> gate per queue step 8.** This packet synthesizes the full D2-0005 design,
> audit, disposition, and rehearsal chain into one decision artifact. It does
> **NOT** arm D2-0005, changes no threshold, seed, or preregistered parameter,
> and performs no execution. **Arming requires explicit user sign-off
> regardless of any other gate state.**

- HEAD at authoring: `e222c677106106d102df2ce8c3af1b33b45daa81`
- Freeze candidate manifest: `docs/D2-0005_FREEZE_CANDIDATE.json`, sha256
  `ae505bb0d57db1c98a04f7b7ef1259877040ce0e0c7968f6cdfe619864ab411c`,
  `keyed_to_commit` `67dd53fee37279ffb032e480053e165ebf6217fb`,
  `armed: false`, status `FREEZE_CANDIDATE_NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT`
- Manifest `required_gates`: `governance_lead_approval`,
  `independent_verification`, `rehearsal_icc_gate`, `boundary_audit`,
  `arming_packet_user_signoff`

---

## 1. DESIGN DECISION — GO/NO-GO memo and amendment A5

The GO/NO-GO memo (commit `67dd53f`, memo sha256
`f05e2d05029c7fe7c7303bf49534d58cddd1299a6351d0f498ed2045cad3ffbc`) chose
**PATH (A): amend the preregistration before evidence exists**. Every defect
was a pre-evidence design defect and every fix a pre-evidence correction; no
D2-0005 outcome data existed, so amendment was the legitimate, bias-free route
(same mechanism as amendments A1–A4). Path (B) (pilot-sized) is retained only
as the disclosed fallback if K = 72 proves operationally infeasible; path (C)
(stop/redesign) was rejected as unwarranted.

**Amendment A5** (sha256 `f2647f35b6475c2896408014a1760b4462e4ce4b0ac87803a6de92aaf3ceb51b`)
redefines the design:

- **Geometry:** K ≥ 72 SHA-256-pinned independent base images × 36 members
  per cluster (18 views × 2 crops) = **2592 paired observations** at the
  design point.
- **Inference:** deterministic cluster-robust paired bootstrap, module
  `ruthless_pipeline/certification/cluster_paired_arm_statistics.py` (sha256
  `bad02b22a9061dd3baf273d92facff42c847f4da2c2e08ed891ac118f6094674`);
  z = 1.959963984540054, bootstrap seed 20260907, 10000 resamples,
  width gate 0.20, min_clusters = 8 (absolute floor, cannot be lowered),
  CVaR α = 0.5, candidate pool seed 1337 — all unchanged from freeze.
- **Gates:** rehearsal-measured ICC ≤ 0.25 required before arming;
  confirmatory claims only for Δ ≥ 0.2; calibrated coverage ≈ 0.90–0.95
  (nominal 0.95 explicitly **NOT** claimed); false-success ≤ 0.035 at the
  design point (0.030–0.035 at Δ_true = 0, K = 72).
- **Power at design point:** P(SUCCESS) = 0.995 at Δ_true = +0.2, ICC = 0.25,
  K = 72 (10000-resample confirmation cell); width 0.163, coverage 0.930.
- Freeze candidate manifest (`ae505bb0…`, keyed to `67dd53f`, `armed: false`,
  5 required gates listed above).

## 2. AUDIT FINDINGS — three independent audits

### 2a. Red-team of Wave H (F1–F9)

Verdict: **"do not execute A5 as drafted; fix F1–F4 first."**

- **SERIOUS:** F1 ρ² miscalibration (labeled parameter ≠ realized ICC);
  F2 m = 6-vs-36 geometry (simulation at 6 members/cluster vs real 36);
  F3 K = 2 fixture (current fixture cannot support cluster-robust design;
  fails closed at min_clusters = 8); F4 coverage overclaim (nominal 0.95
  asserted; achieved 0.850–0.965 per cell).
- **MINOR (5):** distinguishability floor undisclosed (F5); K = 72
  grid-pick provenance (F6); ρ̂/n_eff NA at zero variance (F7); percentile
  off-by-one (F8); post-D2-0004 commissioning disclosure (F9).

### 2b. Independent freeze verification

Verdict: **VALID_WITH_NONBLOCKER_GAPS** — all 7 verification checks PASS
(manifest hash, keyed commit, frozen-surface integrity, pin recompute,
parameter lock, schema conformance, planned-output contract). 8 non-blocker
gaps (compact; authoritative enumeration in the verifier's step-7 report —
the gap table itself is not committed to the repo at HEAD):

1. Fixture image manifest `fixtures/d20005_base_images/manifest.json` does
   not exist yet (planned output, sha256 null).
2. Rehearsal ICC report artifact `artifacts/d20005_rehearsal_icc/results.json`
   not yet produced (null, by design).
3. Primary comparison result artifact not yet produced (null, by design).
4. Per-candidate telemetry records not yet produced (path null, by design).
5. PERSON-SUR-v3 / PERSON-HO-v3 are legacy unversioned JSONs pinned by hash
   only (`schema_version: null`).
6. Rehearsal exercised mock adapters for the real selection entry points
   (`select_surrogate_candidate.py` / `freeze_adaptive_candidate.py`), a
   documented substitution to avoid touching generation records.
7. Rehearsal used 8 synthetic clusters, not the real 72-image fixture
   geometry.
8. Manifest is keyed to `67dd53f` while the tree has since advanced (Wave H
   dispositions, rehearsal) — pin currency is a documentation note, not a
   mismatch; all pins re-verify byte-exact at HEAD.

None blocks arming; gaps 1–4 are planned outputs produced at defined stages.

### 2c. Boundary audit

Verdict: **BOUNDARIES_HOLD_WITH_CAVEATS** — boundaries 1–6 PROVEN:

1. HO-v3 isolation (held-out set never opened; hash-referenced only).
2. Freeze-before-access in the rehearsal state machine.
3. Arm equivalence (both arms through identical harness paths).
4. Telemetry non-influence (frozen_sha256 before outcomes; append-only).
5. Rerun fail-closed (bit-identical rerun; no divergent hashes).
6. No D2-0004-outcome leakage — the Δ-grid predates D2-0004 closure
   (`2ab3b4f` 2026-09-07 18:56 vs closure `c6fe509` 2026-09-08 05:17).

4 caveats:

- **(i)** Guardrail wording is literally inaccurate: post-closure additive
  schema guards (`0efb0c9`) and manuscript backlog prose edits occurred after
  the cited state — no semantic changes to any boundary.
- **(ii)** Freeze-before-access is procedural, not cryptographic, in the real
  `run_measured_benchmark.py`.
- **(iii)** Journal deletion loses tamper-evidence (mitigated: deterministic
  re-emit cannot diverge).
- **(iv)** Arm M pooled-rate vs Arm C per-surrogate CVaR ranking asymmetry —
  inherited frozen D2-0004 behavior, not introduced by D2-0005.

## 3. RESOLVED FINDINGS — disposition table F1–F9 (all FIX/ACCEPT, zero REJECT)

| # | Severity | Finding | Disposition |
|---|----------|---------|-------------|
| F1 | SERIOUS | ρ² miscalibration | FIX — ICC-true DGP; labeled parameter verified = realized pairwise ICC within ±0.02 per cell |
| F2 | SERIOUS | m = 6 vs 36 geometry | FIX — simulation rerun at real m = 36 (18 views × 2 crops) grid |
| F3 | SERIOUS | K = 2 fixture | FIX — multi-image fixture protocol spec (K ≥ 72, image-level clustering, SHA-256 pinning) |
| F4 | SERIOUS | Coverage overclaim | FIX — honest coverage: nominal 0.95 NOT claimed; 0.850–0.965 per cell; calibrated ≈ 0.90–0.95 at design point; small-K false-success 0.085 at K = 8 disclosed as beyond Monte Carlo error |
| F5 | MINOR | Distinguishability floor | FIX/ACCEPT — Δ ≥ 0.2 confirmatory floor disclosed in preregistration |
| F6 | MINOR | K = 72 grid pick | ACCEPT — disclosed as grid pick from {8, 12, 18, 24, 36, 72} conditioned on ICC ≤ 0.25; provenance travels with amendment |
| F7 | MINOR | ρ̂/n_eff at zero variance | FIX — NA-at-zero-variance (never 0); gate blocks on NA |
| F8 | MINOR | Percentile off-by-one | FIX — fixed in the new cluster module only; frozen `paired_arm_statistics.py` untouched; divergence pinned by tests |
| F9 | MINOR | Post-D2-0004 commissioning | ACCEPT — disclosed; no D2-0004 outcome value entered any simulation parameter |

**Determinism attested twice:** `results.json` sha256
`5e8c78b1af395a67258960ac4d4f35e3e7cf20bfef381fd39f8d70c43a67d7d1` identical
across two independent regenerations (run A / run B byte-parity confirmed).

## 4. REHEARSAL RESULTS (docs/D2-0005_REHEARSAL_REPORT.md, sha256 `10aa5179…`, at `e222c67`)

Outcome-free, **synthetic_pipeline_validation_only** rehearsal of BOTH arms
end-to-end (harness `rehearsal_d20005.py` + CLI + 21 pytest tests):

- Fixture: 8 synthetic hash-seeded 64×64 PNG "base images" pinned into a
  disposable fixture manifest; the real `fixtures/d20005_base_images/` path
  NOT touched. HO-v3 referenced by hash only, never opened. No generation
  records, no manuscript paths, no real data.
- Real pinned analysis module over 8 clusters × 36 members = 288 paired obs:
  decision `success`, realized ρ̂ ≈ 0.0070 on the synthetic main run.
- **6/6 failure injections fail-CLOSED:** (a) <8 clusters raises
  `ValueError`; (a′) min_clusters floor cannot be lowered; (b) sealed-evidence
  tamper detected by `verify_release`; (c) schema-version mismatch raises
  `SchemaVersionError`; (d/d′) crash + recovery: no double-emit, no partial
  promotion, recovered run byte-identical, summary hash `1e0daef8…` identical
  to clean run; (e/e′) RAC-P1 promotion of synthetic release REFUSED
  (`PromotionRefusedError`); (f) full/fresh rerun bit-identical (27 files,
  zero byte mismatches).
- **ICC gate (A5.5) exercised both directions:** blocks arming at ρ̂ = 1.0
  (design effect 36.0, n_eff 8.0); passes at ρ̂ = 0.0297 (n_eff 141.24);
  blocks on NA (zero total variance → null, never 0).
- Determinism: two independent runs, identical `summary_sha256`
  `1e0daef862e6fa734af9b4b8b537e0f3819f646485fcb55b443b6703c16e4d16`.
- **579 tests green** (558 baseline + 21 new, 0 failures), incl. freeze
  integrity and frozen-surface integrity tests.

## 5. EXACT COMMIT/HASH SET

- **HEAD:** `e222c677106106d102df2ce8c3af1b33b45daa81`
- **Freeze manifest:** `docs/D2-0005_FREEZE_CANDIDATE.json` sha256 `ae505bb0d57db1c98a04f7b7ef1259877040ce0e0c7968f6cdfe619864ab411c`,
  keyed_to_commit `67dd53fee37279ffb032e480053e165ebf6217fb`
- **Rehearsal report:** `docs/D2-0005_REHEARSAL_REPORT.md` sha256 `10aa517992e87eba9d2be3323e8cca2b9dc70a563176ce3217c4c45d05050374`

The 14 pins from the manifest (all recomputed byte-exact at HEAD by this
packet author):

| # | Path | sha256 |
|---|------|--------|
| 1 | docs/PREREGISTRATION_D2-0005.md (FROZEN A1–A4) | `5a26c0839f49d5bb8feedaa77027e9d778ac5ed40edd96651266f83b24e3a0a3` |
| 2 | docs/PREREGISTRATION_D2-0005_AMENDMENT_A5.md | `f2647f35b6475c2896408014a1760b4462e4ce4b0ac87803a6de92aaf3ceb51b` |
| 3 | docs/D2-0005_GO_NOGO_MEMO.md | `f05e2d05029c7fe7c7303bf49534d58cddd1299a6351d0f498ed2045cad3ffbc` |
| 4 | docs/DESIGN_AMENDMENT_D2-0005_PROPOSAL.md | `aad8b8128757f27d4b2bbf2e1fff0ecbc17532eec0d00cd9f327b6260737334c` |
| 5 | ruthless_pipeline/certification/cluster_paired_arm_statistics.py | `bad02b22a9061dd3baf273d92facff42c847f4da2c2e08ed891ac118f6094674` |
| 6 | scripts/design_analysis_d20005_cluster.py | `ddaab35f4afe382ce096808b3b083a46420c01480397c82c13f99878a91b6737` |
| 7 | ruthless_pipeline/certification/paired_arm_statistics.py (frozen, untouched) | `afce3df27ef03668400779f47510719c39c3bf7ec38a6fe66aaa402ab90a3132` |
| 8 | ruthless_pipeline/certification/config/d20005_freeze/seeds.json | `6dff892080af5c88ac5d2f7b1e09e79a9bd2bb209f5512d643abb434b2b01eb6` |
| 9 | ruthless_pipeline/certification/config/d20005_freeze/model_sets.json | `8d04ef8e2f2218a0bc6793ea5191e42634f6bd2d60d4bfb6f240a48e6d7cfbc6` |
| 10 | ruthless_pipeline/certification/config/d20005_freeze/fixture_protocol.json | `604fa9d861e2d29d12ee28381da9bc361837e7aa87e9b6baefa34d03bfdce457` |
| 11 | model_sets/PERSON-SUR-v3.json | `2f06c19e9e51f3f607b04b499760ab7f470f4b6e18f9c834013fb0a06a5d8876` |
| 12 | model_sets/PERSON-HO-v3.json | `ad1127659a5615871ff320056415dd3c8e8b6a27acef7c6a3bcc4a96e713495e` |
| 13 | benchmarks/runtime_lock.json | `3c7ca4696a8066f3485e2141bab46570ab3265f591ffc87cd3a44795cd361186` |
| 14 | artifacts/design_analysis_d20005_cluster/results.json | `5e8c78b1af395a67258960ac4d4f35e3e7cf20bfef381fd39f8d70c43a67d7d1` |

## 6. EXPECTED COMPUTE

Assumptions (stated explicitly — the repo logs no wall-clock profile for
D2-0004's n = 36 CI run; runtime lock is **CPU-only**: python 3.11,
torch 2.14.0+cpu, torchvision 0.29.0+cpu, transformers 4.57.6):

| Stage | Work | Estimate |
|-------|------|----------|
| Fixture freeze | source ≥ 72 independent base images, SHA-256 pin, generate 36 members each (2592 renders: 18 views × 2 crops) | ~0.5–1 CPU-h compute; dominated by human sourcing/review time |
| Arm C (surrogate selection) scoring | 2592 images × 6 PERSON-SUR-v3 models ≈ 15,600 CPU inferences @ ~1–3 s/img/model | ~4–13 CPU-h |
| Arm M + HO-v3 confirmation scoring | 2592 images × 2 PERSON-HO-v3 models ≈ 5,200 CPU inferences | ~1.5–4.5 CPU-h |
| Analysis | 10000-resample cluster bootstrap over 72 clusters (pinned module) | <0.5 CPU-h |
| Rehearsal ICC gate (on real fixture, pre-arming) | score fixture through surrogate stack + ρ̂ diagnostic | subsumed in Arm C scoring above |
| **Total** | | **~7–20 CPU-h; 0 GPU-h** (CPU-only lock) |

Scaling basis: D2-0004's n = 36 run is the only logged regime; n = 2592 is
72× that n, and inference cost scales linearly in images × models. Per-image
per-model latency of 1–3 s is an assumption for CPU ViT-class person
detectors at fixture resolution, not a measured value; treat the range, not
the midpoint. Storage: ~2592 images + telemetry + bootstrap artifacts, well
under a few GB. Fail-closed reruns are free of semantic risk (deterministic
re-emit proven) but each full rerun re-pays the scoring cost.

## 7. KNOWN LIMITATIONS

1. **8 non-blocker freeze-verification gaps** — listed in §2b (planned-output
   nulls 1–4 are by design; gaps 5–8 are documentation/operational notes).
2. **4 boundary-audit caveats** — listed in §2c: (i) literally inaccurate
   guardrail wording (no semantic change); (ii) procedural (not
   cryptographic) freeze-before-access in the real benchmark runner;
   (iii) journal deletion loses tamper-evidence (deterministic re-emit cannot
   diverge); (iv) Arm M pooled-rate vs Arm C per-surrogate CVaR ranking
   asymmetry (inherited frozen D2-0004 behavior).
3. **Distinguishability floor:** confirmatory claims only for Δ ≥ 0.2 at
   verified ICC ≤ 0.25; power at Δ = 0.1 is 0.700 — below the confirmatory
   bar; P(SUCCESS) = 0.000 at Δ_true = −0.1 everywhere simulated.
4. **ICC ≈ 0.5 regime:** needs K ≈ 144 (design-effect extrapolation,
   disclosed AS extrapolation, off the simulated grid; P(SUCCESS) = 0.070 at
   Δ = +0.2, K = 72).
5. **Coverage downgrade:** calibrated ≈ 0.90–0.95 at the design point
   (0.925–0.955 at K = 72 across simulated ICC); nominal 0.95 NOT claimed;
   small-K false-success elevation (0.085 at K = 8) disclosed.
6. **Unmodeled cross-model same-image correlation** and view-level ICC
   heterogeneity: must be measured at the rehearsal ICC gate and disclosed;
   design valid only if ICC ≤ 0.25 confirmed.
7. **Fixture image manifest does not yet exist** — it is a manifest
   `required_gates` item; the current real fixture (K = 2 from
   `source-zidane.jpg` × 2 crops) CANNOT support the design and fails closed.
8. **K = 72 grid-pick provenance:** selected from {8, 12, 18, 24, 36, 72}
   conditioned on ICC ≤ 0.25; disclosed, not derived from a continuous
   optimum.

## 8. READY_TO_ARM: **NO**

Justification — at least three required gates/preconditions are unmet:

1. **Fixture image manifest missing.** Manifest `required_gates` and planned
   outputs require `fixtures/d20005_base_images/manifest.json`
   (≥ 72 independent SHA-256-pinned base images). It does NOT exist; the
   fixture protocol is specified but not instantiated. **Action:** source and
   freeze the 72+ image manifest per the pinned fixture protocol
   (`fixture_protocol.json`), before any arming.
2. **Memo precondition §5.2 — rehearsal ICC gate on the REAL fixture.** The
   completed rehearsal was synthetic-only; realized ICC on the real
   multi-image fixture must be measured and confirm ICC ≤ 0.25 (else a
   further pre-arming amendment, e.g. K ≈ 144, is required first).
   **Action:** run the outcome-free ICC rehearsal on the frozen real fixture;
   emit `artifacts/d20005_rehearsal_icc/results.json`.
3. **Memo precondition §5.5 — run-B re-confirmation pre-execution.**
   Determinism is attested twice for the design-analysis artifact
   (`5e8c78b1…`) and the rehearsal harness (`1e0daef8…`), but the memo
   requires an independent regeneration re-confirmation immediately
   pre-execution as a hard check. **Action:** fresh-clone regenerate
   `results.json`; hard-compare sha256 against the pin; investigate any
   mismatch before proceeding.
4. **Governance sequence (precondition §5.6) incomplete:** governance-lead
   approval of A5 and final independent verification of the *armed-state*
   manifest (with fixture manifest in place) remain.
5. **User sign-off:** `arming_packet_user_signoff` is a manifest required
   gate; **arming requires user sign-off regardless** of all other gates.

Remaining-action list (ordered): (a) freeze fixture manifest → (b) real-fixture
ICC rehearsal gate → (c) governance-lead approval + final independent
verification → (d) pre-execution run-B determinism re-confirmation →
(e) user signs this packet → (f) only then arm.

## 9. Non-arming statement

This packet arms nothing. No threshold, seed, decision region, fixture, or
preregistered parameter is changed by its existence. Autonomous progress is
halted at this gate per queue step 8. D2-0005 remains **NOT ARMED**
(`armed: false`) pending the actions in §8 and explicit user decision.

# D2-0005 GO/NO-GO MEMO (queue step 4)

> **STATUS: GOVERNANCE MEMO — RECOMMENDATION ONLY. THIS MEMO DOES NOT ARM,
> AMEND, FREEZE, OR EXECUTE ANYTHING.** It changes no file other than itself,
> touches no preregistered threshold, and uses D2-0004 only by citing its
> closure status (closed FAIL/RAC-D0, log-attested, immutable; no outcome
> reuse).

## 1. Decision and rationale

**RECOMMENDATION: PATH (A) — amend the preregistration before evidence
exists**, executing the amendment drafted as A5 in
`docs/DESIGN_AMENDMENT_D2-0005_PROPOSAL.md` (DRAFT v2), subject to the
preconditions in §5.

Rationale: every defect found in the D2-0005 design is a **pre-evidence
design defect**, and every fix is a **pre-evidence design correction** —
no D2-0005 outcome data exists, so amending now is the legitimate,
bias-free route (the same §7/§9 mechanism amendments A1–A4 took). The
corrected design is simultaneously *valid* (cluster-robust inference with
false-success near nominal at the recommended K, replacing a unit-level
path whose coverage collapses to 0.32–0.49 under realistic clustering) and
*adequately powered* at the program's target effect (P(SUCCESS) = 0.995 at
Δ_true = +0.2, ICC = 0.25, K = 72). Path (B) (pilot-sized) spends the
experimental budget on a result that cannot answer the confirmatory
question and is correctly reserved as the disclosed fallback if the
K = 72 fixture is operationally infeasible. Path (C) (stop and redesign)
is not warranted: the residual limitations — mild bootstrap undercoverage,
the Δ ≥ 0.2 distinguishability floor, unmodeled cross-model correlation —
are **disclosed, quantified, and gated** (rehearsal ICC measurement),
not hidden; they bound what the design claims, they do not invalidate it.

## 2. Evidence basis

- **Wave H** delivered the cluster-robust paired analysis
  (`ruthless_pipeline/certification/cluster_paired_arm_statistics.py`) and
  the cluster-aware OC simulation
  (`scripts/design_analysis_d20005_cluster.py`,
  `artifacts/design_analysis_d20005_cluster/results.{json,md}`, schema 2.0),
  run at the real protocol geometry (m = 36 = 18 views × 2 crops) with the
  dependence axis corrected so the labeled parameter IS the realized
  pairwise ICC (verified within ±0.02 per cell).
- **Independent red-team (Wave H review, F1–F9):** 4 SERIOUS + 5 MINOR
  findings; verdict "do not execute A5 as drafted; fix F1–F4 first".
- **Author-side disposition (proposal §6):** ALL findings conceded — zero
  REJECT. Fixes landed: ICC-true DGP (F1), m = 36 geometry (F2),
  multi-image fixture protocol with image-level clustering (F3), honest
  coverage reporting — nominal 0.95 NOT achieved; 0.850–0.965 per cell;
  calibrated ≈ 0.90–0.95 at the design point; small-K false-success 0.085
  at K = 8 disclosed as beyond Monte Carlo error (F4), distinguishability
  floor disclosed (F5), K = 72 disclosed as a grid pick from
  {8, 12, 18, 24, 36, 72} (F6), ρ̂/n_eff reported NA at zero variance (F7),
  percentile off-by-one fixed in the new module only with the frozen
  `paired_arm_statistics.py` untouched and the divergence pinned by tests
  (F8), and post-D2-0004 commissioning disclosed with confirmation that no
  D2-0004 outcome value entered any simulation parameter (F9).
- **Determinism:** the artifact regenerates byte-identically; attested
  sha256 `5e8c78b1af395a67258960ac4d4f35e3e7cf20bfef381fd39f8d70c43a67d7d1`
  (run A; run B byte-parity verification of the full artifact was in flight
  at v2 finalization and must be confirmed before executing A5 — see §5).
- **Test state:** 549 tests pass.
- **Governing confirmation cells** (full preregistered 10000 bootstrap
  resamples, Δ_true = +0.2, ICC = 0.25, m = 36): K = 36 →
  P(SUCCESS) = 0.110, width 0.228 (width gate binds); K = 72 →
  P(SUCCESS) = 0.995, width 0.163, coverage 0.930.
- **D2-0004:** closed FAIL/RAC-D0, log-attested, immutable
  (`docs/D2-0004_CLOSURE_NOTE.md`). Cited for closure status only; no
  D2-0004 outcome value is reused anywhere in this decision.

## 3. Honest capability statement (corrected design: K = 72 × 36, gated on rehearsal-measured ICC ≤ 0.25)

**CAN** be distinguished confirmatorily:

- Δ ≥ +0.2 vs Δ ≤ 0 at verified ICC ≤ 0.25: P(SUCCESS) = 0.995 at
  Δ_true = +0.2, K = 72 (0.995 at the full 10000-resample confirmation);
  false-success at Δ_true = 0 is 0.030–0.035 at K = 72 (near the nominal
  one-sided 2.5%) and P(SUCCESS) = 0.000 at Δ_true = −0.1 at every
  simulated cell.

**CANNOT** be distinguished (disclosed floors, not anomalies):

- Δ ≈ +0.1 at ICC = 0.25: P(SUCCESS) = 0.700 at K = 72 — below the
  confirmatory bar.
- Anything at ICC ≈ 0.5 at K = 72: P(SUCCESS) = 0.070 at Δ_true = +0.2;
  matching power requires K ≈ 144 (design-effect extrapolation, disclosed
  AS extrapolation, off the simulated grid).
- Small-to-moderate effects (Δ ≈ 0.1) at realistic ICC: the program's only
  attested held-out regime (D2-0004, closed) sat at boundary rates with
  Δ ≈ 0; this design cannot detect effects in that neighborhood. A SUCCESS
  supports "Δ > 0"; an INCONCLUSIVE at small true Δ is an expected design
  limitation.
- Interval coverage is calibrated at ≈ 0.90–0.95 at the design point, NOT
  nominal 0.95 (0.925–0.955 achieved at K = 72 across the simulated ICC
  range).
- Cross-model same-image correlation and view-level ICC heterogeneity are
  unmodeled; the realized ICC must be measured on outcome-free rehearsal
  data and the design is valid only if ICC ≤ 0.25 is confirmed.

## 4. Cost / feasibility of each path

**(A) Amend before evidence exists (RECOMMENDED).** Cost: the A5
preregistration diff drafted in proposal §2(e) — redefining the inferential
unit as the base-image cluster, specifying a NEW multi-image fixture
protocol (K ≥ 72 independent SHA-256-pinned base images × 36 members =
2592 paired observations), switching the primary interval to the
deterministic cluster bootstrap, restating the success region in cluster
terms, and downgrading the coverage claim inside the preregistration
itself. All executed BEFORE any D2-0005 evidence exists — legitimate
precisely because no D2-0005 data exist; no preregistered threshold moves
(z = 1.959963984540054, seed 20260907, 10000 resamples, 0.20 width gate,
α = 0.5, decision regions all fixed). Feasibility risk: sourcing 72+
independent base images and freezing the hash manifest is real operational
work, and the fixture protocol is currently specified only at proposal
§2(b) level — the current real fixture (K = 2 clusters from
`source-zidane.jpg` × 2 crops) CANNOT support the design and the
cluster-robust analysis would fail closed (`min_clusters = 8`) on today's
data.

**(B) Declare D2-0005 pilot-sized (fallback).** Lower evidentiary bar and
cheaper now, but the result is NOT promotable to confirmatory status later;
it requires explicit demotion language in the preregistration and spends
the experimental budget on an INCONCLUSIVE-dominated or exploratory-only
answer. This is the F0 study's option (b2), kept as the disclosed fallback
if K = 72 images proves operationally infeasible — never as a route back
to unit-level inference over pseudoreplicates (that path is invalid:
coverage 0.32–0.49 at ICC ≥ 0.25).

**(C) Stop and redesign.** Cost: discard the current D2-0005 frame
entirely, including the frozen preregistration, the validated
cluster-robust module, and the attested OC evidence base — then rebuild
from scratch. Not warranted: the defects were design defects with
pre-evidence fixes now landed and independently reviewed; nothing in the
red-team findings or the disposition indicates the estimand, decision
regions, or program question are wrong, only that the original unit-count
and analysis were. Redesign would pay the full cost for no identified
gain over path (A).

## 5. Preconditions for executing path (A)

All of the following must complete BEFORE any arming step:

1. **Fixture protocol spec.** The multi-image fixture protocol (proposal
   §2(b)) must be expanded from proposal-level to a frozen specification:
   ≥ 72 independent base images, sourcing rules independent of the
   candidate pipeline and of any measured outcome, SHA-256 content-pinning
   manifest, crop specs, frozen before arming.
2. **Rehearsal ICC gate.** Realized ICC measured via the ρ̂ diagnostic on
   outcome-free rehearsal data; the design is armed only if ICC ≤ 0.25 is
   confirmed. If realized ICC materially exceeds 0.25, K must be raised by
   a further pre-arming amendment (ICC ≈ 0.5 → K ≈ 144) BEFORE arming.
3. **Coverage-claim downgrade in the preregistration itself.** The
   calibrated claim (two-sided coverage ≈ 0.90–0.95 at the design point,
   nominal 0.95 NOT achieved; small-K false-success elevation disclosed)
   must be written into the amended preregistration text, not left only in
   the proposal.
4. **Distinguishability floor disclosure in the preregistration.**
   Confirmatory scope limited to Δ ≥ 0.2 at verified ICC ≤ 0.25;
   P(SUCCESS) = 0.700 at Δ = 0.1 and the ICC ≈ 0.5 / K ≈ 144 requirement
   stated explicitly in the amended design.
5. **Determinism confirmation.** Verify `sha256(results.json)` ==
   `5e8c78b1af395a67258960ac4d4f35e3e7cf20bfef381fd39f8d70c43a67d7d1` on a
   fresh independent regeneration (run B full-artifact confirmation was in
   flight at v2 finalization); any mismatch invalidates the artifact and
   must be investigated before executing A5.
6. **Governance sequence.** Human governance-lead approval of A5; freeze;
   independent verification; rehearsal (incl. the ICC gate of item 2);
   boundary audit — per the remaining queue steps — all BEFORE arming.
7. **Provenance carried forward.** K = 72 remains a disclosed grid pick
   from {8, 12, 18, 24, 36, 72} conditioned on ICC ≤ 0.25; this disclosure
   travels with the amendment.

## 6. Non-arming statement

This memo does NOT arm D2-0005. It executes no amendment, edits no
preregistration, moves no threshold, and changes no fixture, seed, or
decision region. Arming requires the ARMING PACKET (queue step 8) and
explicit user sign-off, after the preconditions of §5 are met. If the
governance lead judges K = 72 independent base images operationally
infeasible, the fallback is path (B) — an explicit pilot-sized /
exploratory declaration with demotion language — never unit-level
inference over pseudoreplicates.

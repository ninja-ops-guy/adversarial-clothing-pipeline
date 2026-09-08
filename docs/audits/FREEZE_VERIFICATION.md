# Independent Verification — D2-0005 Freeze Candidate @ 6b8caaf

**Verdict: VALID_WITH_NONBLOCKER_GAPS** — all seven mandated checks PASS; no falsification succeeded.
Verifier: independent agent (non-author), verification-only, no edits, no pushes.

Repo: fresh clone, HEAD = `6b8caaf98c0e4f6aed3c401ae12d21bfec78e00e` (matches expected).

| # | Check | Verdict | Evidence |
|---|---|---|---|
| 1 | Hash integrity | **PASS** | Recomputed sha256 for all 13 pinned paths (4 governing docs, 3 analysis files, 6 frozen inputs) — every hash matches `D2-0005_FREEZE_CANDIDATE.json` exactly. Amendment/doc hashes match attested values (f2647f35…, ae505bb0…). `keyed_to_commit` 67dd53f is an ancestor of HEAD (`merge-base --is-ancestor` OK); `git show 67dd53f:<path>` sha256 for cluster_paired_arm_statistics.py, design_analysis script, frozen prereg, and results.json are all byte-identical to HEAD. |
| 2 | Verbatim-quote drift | **PASS** | Extracted all 10 ` ```old ` blocks; every one is an exact substring of `docs/PREREGISTRATION_D2-0005.md` (sha 5a26c083…). Zero drift. |
| 3 | Numeric consistency vs results.json (sha 5e8c78b1… verified) | **PASS** | K=72/ICC=0.25/Δ=+0.2: P(SUCCESS)=0.995 (grid AND 10000-resample confirmation cell); K=36 grid cell = 0.13 (confirmation cell 0.11 — claim says ≈0.130, matches grid; see Gap 3); coverage at K=72 across ICC at Δ=0.2 = {0.935, 0.925, 0.955} → "0.925–0.955"; full Δ=+0.2 grid min/max = 0.850/0.965; false-success at Δ=0, K=72 = 0.03/0.035/0.0 → "0.030–0.035"; Δ=−0.1 = 0.000 in all 18 cells; K=8 elevation 0.085; Δ=0.1/ICC=0.25/K=72 = 0.700; ICC=0.5/Δ=0.2/K=72 = 0.070; K=72 = smallest grid K with P≥0.8 at Δ=+0.2/ICC=0.25; 2592 = 72×36. ICC≈0.5→K≈144 is labeled "disclosed design-effect extrapolation" (outside simulated grid — see Gap 4). |
| 4 | Analysis-implementation soundness | **PASS** | `cluster_paired_arm_statistics.py` (bad02b22…): `DEFAULT_MIN_CLUSTERS = ABSOLUTE_MIN_CLUSTERS = 8`, fail-closed ValueError below min_clusters and on lowering below absolute; hash-seeded bootstrap via `_hash_draw(seed|resample|j)` shared with frozen path; defaults z=1.959963984540054 / resamples=10000 / seed=20260907 / width 0.20 match manifest; zero-variance ρ̂ → None/NA (lines 272–274); resamples whole clusters carrying all members (lines 196–204). seeds.json values (1337/20260907/20261209) match code: run_measured_benchmark.py:445 `seed=1337`, paired_arm defaults, SIM_SEED=20261209 in design script. CVaR α=0.5 matches objectives.py docstring. |
| 5 | Non-arming | **PASS** | `git diff --stat 67dd53f..6b8caaf`: exactly the 6 new files, 810 insertions, **0 deletions, 0 modifications**. `generations/RAC-PER-D2-0005.json` last touched at 4691edd (pre-freeze), still `lock_status: PREREGISTERED`; manuscript/ untouched; frozen prereg + paired_arm_statistics.py hashes unchanged; manifest `armed: false` with 5 required gates; no threshold changed. |
| 6 | Gap hunt | see below | |
| 7 | Tests | **PASS** | Full suite: **558 passed** (65.9s, PYTHONPATH=repo). `tests/test_d20005_freeze_candidate.py -v`: **9/9 passed**. |

## Gap list (all NON-BLOCKER)

1. Fixture image manifest deferred — but deferral is explicit, gated ("frozen BEFORE arming", schema+sha256 required, post-freeze change needs new amendment). Properly gated.
2. Rehearsal gate says ICC ≤ 0.25 "confirmed" (hard) but fallback triggers on "materially exceeds" — vague qualifier; gate itself is unambiguous.
3. K=36 power cited as ≈0.130 (1000-resample grid) vs 0.11 in the 10000-resample confirmation cell — amendment itself doesn't cite 0.130; only a cosmetic discrepancy in secondary evidence.
4. K≈144 for ICC≈0.5 is an extrapolation beyond the simulated grid (max K=72) — disclosed as such.
5. The three `d20005_freeze/*.json` pins are documentary: no production code consumes them; nothing fails if they drift (only the integrity test guards them).
6. New schema ids are "registered" only in a hardcoded dict inside the test file; `schema_version.py` is a generic guard with no id registry. Acceptable pre-arming (artifacts don't exist yet).
7. `run_measured_benchmark.py` (defines the 36-member geometry) is not individually hash-pinned in frozen_inputs — covered only implicitly by `keyed_to_commit` tree pin.
8. "Outcome-free rehearsal" ICC is computed from member deltas (arm outcomes) — what counts as "outcome-free" is not operationalized; presumed surrogate-side/pre-decision data.

No BLOCKER gaps found. No telemetry pre-freeze read path and no D2-0004-outcome tuning vector identified (F9 disclosure corroborated: simulation params are grid constants, no D2-0004 values). Nothing modified; verification-only.

# D2-0005 Non-Held-Out Rehearsal Report (queue step 6)

> **STATUS: REHEARSAL RECORD — synthetic_pipeline_validation_only.** This report
> documents an OUTCOME-FREE pipeline rehearsal of the D2-0005 freeze candidate
> (`docs/D2-0005_FREEZE_CANDIDATE.json`, status
> `FREEZE_CANDIDATE_NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT`; amendment draft
> `docs/PREREGISTRATION_D2-0005_AMENDMENT_A5.md`). **It does NOT arm D2-0005,**
> changes no threshold, touches no generation record, and does not satisfy or
> substitute for the independent-verifier, boundary-audit, governance-approval,
> or arming-packet-signoff gates. Every artifact produced by the rehearsal
> carries `evidence_class = "synthetic_pipeline_validation_only"` and
> `rac_evidence_eligible = false`, and promotion of any of them to RAC-P1 is
> structurally refused (see injection (e)).

## 1. What was exercised

Harness: `ruthless_pipeline/certification/rehearsal_d20005.py` (module) +
`scripts/rehearsal_d20005.py` (CLI driver) + `tests/test_d20005_rehearsal.py`
(21 repeatable pytest tests). Full chain over synthetic/disposable inputs for
BOTH amendment-A5 arms:

1. **Fixture:** 8 synthetic "base images" (hash-seeded 64×64 PNG arrays,
   generated — never photographic), SHA-256-pinned into a disposable fixture
   manifest (schema `d2-0005-fixture-manifest` 1.0). The planned real path
   `fixtures/d20005_base_images/manifest.json` was NOT created or touched.
2. **Surrogate-selection arm:** synthetic 100-candidate pool keyed to the
   frozen pool seed 1337; mock SHA-256-seeded surrogate scores over the six
   PERSON-SUR-v3 model names; CVaR (α = 0.5, the pinned `cvar_alpha`)
   minimization selects a winner. **Documented substitution:** the real
   selection entry points (`scripts/select_surrogate_candidate.py`,
   `scripts/freeze_adaptive_candidate.py`) were NOT executed because
   exercising them would touch generation records; the mock adapter preserves
   the selection semantics and frozen seeds.
3. **Freeze:** synthetic per-candidate telemetry record frozen and hashed
   (`frozen_sha256`) BEFORE mock held-out outcomes are drawn (append-only
   outcome discipline of the telemetry contract).
4. **Held-out-confirmation arm:** mock paired binary outcomes drawn from a
   hash-seeded generator keyed by the two PERSON-HO-v3 model NAMES ONLY.
   `model_sets/PERSON-HO-v3.json` (sha256 `ad1127659a…`) was referenced by
   identity/hash exactly as the freeze candidate does and **never opened for
   scoring; no held-out access of any kind occurred** (HO-v3 untouched).
5. **Cluster-robust paired analysis:** the REAL pinned module
   `ruthless_pipeline/certification/cluster_paired_arm_statistics.py`
   (sha256 `bad02b22a9…`) with the frozen parameters (z = 1.959963984540054,
   bootstrap seed 20260907, resamples 10000, width gate 0.20,
   min_clusters = 8) over 8 clusters × 36 members (2 mock models × 18
   transforms) = 288 paired observations. Result: decision `success`,
   realized ρ̂ ≈ 0.0070 on the synthetic main run.
6. **Evidence sealing:** hash-bound artifact (schema
   `d2-0005-cluster-paired-arm-statistics` 1.0) embedding the canonical JSON
   of `to_canonical_json` and its SHA-256.
7. **Publication-style release object:** content-addressed
   `MANIFEST.json` + `RELEASE.json` (content hash over canonical manifest
   JSON), frozen `ReleaseRevisionLog`, verified by the REAL
   `release_format.verify_release`.
8. **Manuscript export row:** the REAL exporter
   (`manuscript_export.paper5_arm_rows` / `paper5_arms_csv`) run on both
   rehearsal arms into a SCRATCH path (`export_synthetic/`); the harness
   hard-refuses any export path under `manuscript/`. **No file under
   `manuscript/` (including `manuscript/exports/`) was read or written.**

## 2. Failure-injection table (fail-CLOSED verification)

| # | Injection | Expected | Observed | Result |
|---|-----------|----------|----------|--------|
| a | Cluster-robust analysis with 7 clusters (< min_clusters = 8) | Raises `ValueError("…at least 8 clusters…")`, never degrades | `ValueError: cluster-robust comparison requires at least 8 clusters; got 7. Failing closed…` | PASS |
| a′ | `min_clusters` lowered below `ABSOLUTE_MIN_CLUSTERS` (4) | Raises, floor cannot be lowered | `ValueError: min_clusters may not be lowered below ABSOLUTE_MIN_CLUSTERS=8` | PASS |
| b | Sealed evidence tampered post-seal (decision field flipped in release copy) | Release verifier detects hash mismatch | `verify_release` → `ok=False`, `tampered=("sealed-evidence.json",)` | PASS |
| c | `schema_version` bumped to "2.0" / removed on the sealed artifact | `SchemaVersionError` | `SchemaVersionError` raised in both variants | PASS |
| d | Crash injected after stage `seal`, then recovery rerun | No double-emit; no partial-result promotion; recovered run byte-identical to a clean run | `RehearsalCrash` raised; journal held stages 1–5; no `release/` dir existed pre-recovery; recovery completed with unique stages and `summary_sha256` identical to the clean run (`1e0daef8…`) | PASS |
| d′ | Prior-stage artifact tampered before resume | Fail closed on resume | `ValueError: …hash-mismatched on resume; failing closed…` | PASS |
| e | Attempt to promote the synthetic release to RAC-P1 | Refused | `PromotionRefusedError: release 'RAC-EXP-2026-905' is labelled 'synthetic_pipeline_validation_only' … promotion to RAC-P1 is REFUSED` | PASS |
| e′ | Promotion attempt on a tampered release | Refused at verification step | `PromotionRefusedError: release verification failed (tampered=(…,)) …` | PASS |
| f | Full rerun after failure / fresh-directory rerun with identical inputs | No divergent hashes (determinism / fail-closed rerun semantics) | Two independent runs produced identical file sets (27 files) and byte-identical artifacts; `summary_sha256` equal (see §4) | PASS |

All injections are encoded as repeatable tests in
`tests/test_d20005_rehearsal.py` (21 tests, all passing).

## 3. Rehearsal ICC gate (amendment A5.5): gate exercisable in both directions

Synthetic ICC probes (ICC known by construction, K = 8 × 36 members each),
measured through the REAL pinned `intracluster_diagnostics` path:

| Probe | Construction | Realized ρ̂ | Design effect | n_eff | Gate (≤ 0.25) |
|-------|--------------|-----------|---------------|-------|----------------|
| Above gate | cluster-shared delta sign (maximal clustering) | 1.0 | 36.0 | 8.0 | **BLOCKS arming** (`gate_passed=false`) |
| Below gate | i.i.d. member deltas (no clustering) | 0.029689045159872533 | 2.039 | 141.24 | **passes** (`gate_passed=true`) |
| NA probe | zero total variance (all deltas identical) | NA (`null`, never 0) | NA | NA | **BLOCKS arming** (NA cannot arm) |

The gate therefore provably permits arming only when realized ICC ≤ 0.25 and
blocks both above-gate ICC and the zero-variance NA case (red-team finding
F7 semantics preserved).

## 4. Determinism evidence (two independent harness runs)

Run A and Run B (fresh output directories, identical inputs) produced
identical file sets (27 files) with **zero byte mismatches**;
`rehearsal-summary.json` `summary_sha256` identical across runs:

```
1e0daef862e6fa734af9b4b8b537e0f3819f646485fcb55b443b6703c16e4d16  (run A == run B)
```

Key harness artifact hashes (identical in both runs):

```
f47df376dd0e7d8564d5e2f64031ee466974ac1973c4445d830dde9fcc9a7611  sealed-evidence.json
83aa31db561f9fdea1bbfb9696319550864c4455fd866f1e76f0fb3c69ddfadf  release/RAC-EXP-2026-905/RELEASE.json
e7011e983f5c9d46fc5f54b0a259a29f50102b20eb8ddcecb90ca7d06cc67ec8  release/RAC-EXP-2026-905/MANIFEST.json
9f480f6d5bbf3a8d0dacabdc8663d4c403c21bb469d9cf265e42eb9cbde582e6  fixture-manifest.json
58e4797da16f410d1865e745de56d5accedbaa8c25657a5624f61fc18c87f180  export_synthetic/paper5_arms_rehearsal_synthetic.csv
2d2584bd1bbc2e3775f20888f6b1323af74eda5758579d8fe44d5193d17ca7c9  icc-gate-probes.json
07cff7195fe5a31f1bd9e577849ad1dbf570a1d455d0dc95f8bcc4a6bb7a6992  rehearsal-summary.json
```

## 5. Test results

`tests/test_d20005_rehearsal.py`: 21 tests, all passing. Full suite:
**579 passed** (558 baseline + 21 new), 0 failures, including the freeze
integrity tests `tests/test_d20005_freeze_candidate.py` and
`tests/test_frozen_surface_integrity.py` — the frozen surface is untouched.

## 6. Non-touch attestation

**No real data, models, or held-out anything was touched.** Specifically: no
generation records were read or written; no active-generation code paths were
edited or executed (mock adapters substituted, documented in the harness
module docstring); `model_sets/PERSON-HO-v3.json` was never opened (HO-v3
untouched — mock scores only); no real fixture images were read; nothing
under `manuscript/`, `fixtures/`, `generations/`, `releases/`, `artifacts/`,
or `.github/workflows/` was written; no threshold, seed, or preregistered
parameter was changed; D2-0004 was neither rerun nor re-optimized against.
D2-0005 remains **NOT ARMED**: this rehearsal satisfies only the
outcome-free rehearsal mechanics; the arming gates (governance approval,
independent verification, boundary audit, user sign-off) are untouched.

All rehearsal artifacts are and remain `synthetic_pipeline_validation_only`.

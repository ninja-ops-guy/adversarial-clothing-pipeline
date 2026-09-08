# Performance and Cost Note — Research Pipeline (Non-Inference Portions)

Measurements taken with `scripts/profile_pipeline.py` (`time.perf_counter`,
several repetitions, median reported) on a fresh anonymous clone at the commit
that introduced this file, on a shared CI-class container (Python 3.12, CPU
only, cold-ish filesystem). **No model weights were loaded and no inference
ran.** Numbers are envelopes, not benchmarks; absolute values move with the
machine, relative magnitudes are the point. Reproduce with:

```
PYTHONPATH=. python scripts/profile_pipeline.py --root . --report profile.json
```

## Measured timings (median)

| Segment | What it covers | Median | Repeats |
|---|---|---|---|
| Status ingestion | `read_d2_status(d2-latest-status.json)` — parse + legacy/packaging normalization | **~0.27 ms** | 200 |
| Release verification | `verify_release(releases/RAC-EXP-2026-001)` — re-hash every sealed file and compare to MANIFEST.json | **~4.4 ms** | 5 |
| Manuscript export inputs | parse of all `manuscript/evidence/**`, `manuscript/exports/*`, `manuscript/figures/*` JSON | **~5.5 ms** | 20 |
| Documentation linter | full `lint_repo()` scan (53 files, all 6 checks + allowlist) | **~0.11 s** | 5 |
| Rehearsal harness | `run_rehearsal()` end-to-end, both synthetic arms, all 7 stages incl. journal + hashing | **~39 ms** | 3 |
| Fast pytest segment | `test_doc_lint.py + test_release_format.py + test_schema_version_guard.py` (subprocess incl. startup) | **~7.1 s** | 1 |
| **Full test suite** | 608 tests | **~68–75 s** | 1 |

Slowest individual tests (from `pytest --durations=8`): d20006 readiness CLI
(~6.8 s), physical release export determinism (~4.6 s), doc-lint CLI
subprocess test (~4.2 s), paired-arm statistics end-to-end (~4.0 s). These
dominate the suite; everything else is sub-second.

## What dominates

1. **Inference, by orders of magnitude** — not measured here by design. Every
   non-inference segment above is milliseconds; the full test suite is
   ~70 s only because it subprocess-spawns CLIs and runs deterministic
   statistics/bootstrap loops. In a real measured run, surrogate + held-out
   detection inference over hundreds-to-thousands of conditions dwarfs all
   bookkeeping.
2. Within the non-inference budget, **subprocess/CLI startup** (Python
   interpreter + import graph) dominates, not compute: `read_d2_status` is
   0.27 ms but invoking the CLI that calls it costs ~1–2 s of interpreter
   startup. Status JSON parsing, release re-hashing, and JSON export are
   noise.
3. The **statistics bootstrap** (paired-arm / cluster modules, 10000
   resamples) is the only non-inference compute that scales with design size
   — still single-digit seconds at the frozen n.

## Safe caching opportunities (immutable inputs only)

- **Hash-verified caches only.** Any cache of an immutable input is safe iff
  the cached bytes are re-verified against a pinned sha256 before use. This is
  already the pattern for the zidane fixture (`source_sha256` in
  `scripts/run_measured_benchmark.py`: downloaded once per workspace, verified
  on every use) and for model weights (`benchmarks/model_manifest_v1.locked.json`
  + `tests/test_model_lock.py`).
- Candidates: pip/uv package caches keyed to `benchmarks/runtime_lock.json`
  pins (verified by `scripts/verify_runtime_lock.py` before use), HF weight
  caches keyed to the locked manifest hashes, and the fixture cache (already
  implemented).
- **Never cache:** anything derived from held-out outcomes, telemetry,
  journals, or status JSONs. Recomputation of these is milliseconds anyway
  (see table), so caching them buys nothing and risks T4/T6-class
  contamination (see `docs/THREAT_MODEL_RESEARCH_PIPELINE.md`).

## Expected envelope for a future D2-0005 run (K = 72 clusters × 36 conditions = 2592 paired observations per arm)

Stated assumptions:

- Inference cost per condition ≈ constant and equal to the D2-0004 per-condition
  cost (same protocol 1.2, same surrogate/held-out model sets PERSON-SUR-v3 /
  PERSON-HO-v3, same fixture pipeline). D2-0004 evaluated n=36 held-out
  conditions plus a 100-candidate surrogate sweep in one CI run on CPU.
- D2-0005 runs **two arms over one shared 100-candidate pool** (seed 1337) and
  a held-out evaluation of 2592 paired observations per arm — i.e. **72× the
  held-out inference volume of D2-0004**, twice (M and C), while the surrogate
  sweep cost is unchanged (one shared pool).
- Non-inference overhead (status write, bundle build+verify, release seal,
  export, lint): bounded by ~1 s total of compute + ~10–20 s of CLI startup,
  i.e. **< 1% of any realistic run** — negligible at any K.
- The deterministic statistics bootstrap at n=2592 is O(n · resamples);
  measured ~4 s class at n=36 → expect **single-digit minutes**, still noise
  next to inference.
- CI wall-clock envelope: if D2-0004's held-out+selection inference took T
  minutes, a first-order estimate for D2-0005 is ≈ T_selection + 2 × 72 ×
  T_heldout_per36 — dominated entirely by the 72× held-out term. On the same
  CPU-only runner class this argues for a multi-hour job with staged artifact
  uploads (already the pipeline's stage/journal design) rather than any change
  to the science.
- Monetary cost: on GitHub-hosted runners, Linux CPU minutes are effectively
  flat-rate for public repos; the binding constraint is wall-clock and the
  6-hour job timeout, not dollars. A self-hosted or larger runner is a
  scheduling decision, not a scientific one.

## Explicit statement

**No scientific shortcuts were taken or are proposed.** Every number above is
either measured by `scripts/profile_pipeline.py` on this checkout or an
explicitly labeled scaling assumption from measured D2-0004 parameters. No
threshold, gate, seed, preregistered constant, or frozen artifact was changed
to obtain these numbers; caching proposals are restricted to hash-verified
immutable inputs; the performance work does not touch inference semantics,
selection objectives, or evidence handling.

# D2-0004 Closure Note — Log-Attested (FAIL / RAC-D0)

**Status: CLOSED. Decision FAIL / evidence_state RAC-D0, retained permanently.**
This note is the canonical narrative for the closure of RAC-PER-D2-0004. It
changes no scientific content: the decision, protocol, model sets, and all
numbers below are exactly what the authorized CI run printed.

## 1. What happened

- First run 34147902820 failed at step 18 (protocol-loader `TypeError`, fixed
  by 7148202d). Its outcome was never observed; the one-shot boundary held.
- `docs/AMENDMENT_D2-0004_INFRA-001.md` authorized exactly ONE re-run with an
  unchanged scientific configuration under `benchmarks/runtime_lock.json`.
- The authorized re-run, **CI run 34175028944** (workflow_dispatch on main,
  source commit `b4fe0e5942b56b7fffb8de6f1cb3172744269f59`, 2026-09-08),
  completed all science steps:
  - Step 18 (measured held-out + full-benchmark inference): SUCCESS
  - Step 19 (build D2 evidence bundle): SUCCESS — bundle verified
  - Step 20 (schema/result validation): SUCCESS — status `measured_locked`
  - Step 21 (status write): SUCCESS — `d2-latest-status.json` = FAIL / RAC-D0
  - **Step 22 (build print-test kit): FAILED** — the Product Studio manifest
    schema guard still required `1.3` while the production manifest is `1.4`
    (`scripts/build_print_test_kit.js:55`). Fixed infrastructure-only at
    `5cdce1b`.
  - Steps 23–28 (artifact upload, publish): SKIPPED as a consequence.

## 2. Evidence basis and its limits

Because step 22 failed, the validated evidence bundle was **never archived**;
the workflow artifacts were never uploaded. Closure therefore rests on the
maintainer-downloaded run logs, transcribed byte-faithfully into
`manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json`.

Attested (printed in the logs, cross-checked between steps 18/19/20):

- candidate SHA-256: `9c8ae08de2106634e6a7f301d8d6e5933b0f561f3ea04e90e3c034c96c9e3803`
- decision: **FAIL**; evidence_state: **RAC-D0**; bundle_verified: true
- certificate_id: `RAC-PER-D2-0004-1.0.0-1.2`
- protocol: RAC-PERSON-DETECT 1.2; surrogates PERSON-SUR-v3; held-out PERSON-HO-v3
- held-out (n=36, valid_n=36, invalid_condition_fraction 0.0):
  baseline_detection_rate 1.0, candidate_detection_rate 1.0,
  baseline_mean 0.9947303864690993, candidate_mean 0.8959943834278319,
  mean_delta -0.0987360030412674
- verification_failures: []

Not attested (recorded as gaps, never reconstructed):

- candidate.png bytes (only its SHA-256)
- per-model held-out detection rates (only the PERSON-HO-v3 aggregate)
- surrogate-only split of the step-18 aggregate (only the full-benchmark
  aggregate over 144 rows is attested)
- surrogate-phase optimization telemetry (same D2-0004 gap documented for
  `--legacy-d20004`)
- `benchmark-results.json` `generated_at` timestamp (only the run date)

## 3. Governance statements

- The schema-guard fix `5cdce1b` is infrastructure remediation only. It did
  **not** authorize another scientific D2-0004 run, and none was performed.
- No held-out data was accessed beyond the single authorized run; no
  scientific parameter, threshold, candidate, or generation record was
  modified after the run.
- D2-0003's status file is preserved byte-identical at
  `manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json`
  (sha256 f55732d666ce0227747e0416485364cf2d0d871ac395e2b7ff29d54291f1b5d1).
- The sealed research release is `releases/RAC-EXP-2026-001/`
  (FAILURE.json classification, MANIFEST, REVISIONS).
- Paper 1's longitudinal export now carries D2-0004 as a closed row sourced
  exclusively from the log-attested evidence; unattested fields stay blank.

## 4. Consequence for the program

D2-0004 is a **retained negative**: the candidate did not suppress the
PERSON-HO-v3 held-out detectors (detection rate 1.0 → 1.0). This closes the
D2-0004 gate. D2-0005 remains **frozen and unarmed**; the next decision is
the pre-arming design question (cluster-aware amendment vs pilot/exploratory
declaration) per the F0 operating-characteristic study and the Wave H
cluster analysis — a decision memo, not an experiment launch.

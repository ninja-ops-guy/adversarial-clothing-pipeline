# Barrier 3 Completion Handoff

**Document ID:** BARRIER-3-COMPLETION-HANDOFF-001
**Wave:** RAC Parallel Swarm R1 (Lanes A–E)
**Date:** 2026-09-10
**Starting HEAD:** `f5fe07fdb655510e96cef1b7678e1df99192884f`

---

## 1. Scope

Five lanes executed against `ninja-ops-guy/adversarial-clothing-pipeline`:

- **Lane A — Barrier 3 integration** (P0)
- **Lane B — RAC-G preparation** (P1)
- **Lane C — production hardening guards** (P0)
- **Lane D — Print Alpha readiness** (P0)
- **Lane E — CI / E2E / reproducibility** (P1/P2)

Per the closing rule, parallel modification of the Barrier 3 surface stopped
when Lane A finished; the remainder of the wave ran as a single-threaded
closer pass (survey doc, verification, this handoff).

## 2. Lane A — Barrier 3 integration (CLOSED)

Survey first, per the execution order: `docs/BARRIER3_INTEGRATION_SURVEY.md`
classifies **CAN_COMPOSE_EXISTING_ENGINE = YES** — all six stages already had
deterministic, contract-validated entrypoints, so only a thin coordinator was
built:

- `ruthless_pipeline/integration/barrier3.py` — composes Optimization V3 →
  EOT → Detector Science → Pareto/Style → Printability → Physical Transfer.
  Single-process, seed-controlled (sha256 sub-seed chaining from
  `master_seed`), hash-pinned, replayable. No stage math reimplemented; the
  detector stage routes through the real `SyntheticDetectionAdapter` so the
  fabrication guard is exercised on the integrated path.
- `scripts/run_barrier3_integration.py` — runs the engine twice into isolated
  directories, verifies deterministic replay, writes the artifact package.
- `artifacts/barrier3/` — run-manifest, input-hashes, runtime-environment,
  six stage-artifacts, objective-telemetry, provenance, hashes.sha256,
  replay-report, barrier3-report. Every stage proves input source, input
  hash, configuration, seed, version, output hash, and upstream lineage.
  No silent stage skipping (enforced by `verify_provenance`).
- Deterministic replay: two equivalent runs compared across input hashes,
  config hash, seeds, stage outputs, telemetry, provenance, artifact hashes —
  **PASS**, zero mismatched artifacts. Only `runtime-environment.json` is
  excluded from scientific equivalence (documented in the report).
- Failure-injection gate on the integrated path: wrong input hash, corrupt
  checkpoint, invalid objective, NaN/Inf, invalid EOT distribution, unknown
  detector family, broken provenance, silent stage skip, candidate/control
  collision, stale production mapping, synthetic-presented-as-measured — all
  fail closed, covered by `tests/test_barrier3_integration.py` (21 tests).
- No held-out inference executed; D2-0005 not armed; evidence class forced
  `synthetic_pipeline_validation_only`.

**Gate report: `artifacts/barrier3/barrier3-report.json` —
artifact_integrity=PASS, provenance=PASS, deterministic_replay=PASS,
barrier3_closed=true.**

## 3. Lane C — production hardening (CLOSED)

Both strict XFAIL gaps resolved as implementation fixes (guard lands → XPASS
→ xfail marker removed → ordinary PASS). Tests were not removed or weakened;
the two fixtures were updated to call the production guard functions with the
injected fault as the sole violation, still expecting
`jsonschema.ValidationError`.

- **GAP 1 (candidate/control collision):**
  `validate_mapping_pairing()` in `scripts_print_alpha/validate_manifests.py`
  rejects any concrete `control_file == candidate_file`. Literal
  `PENDING_USER_ACTION == PENDING_USER_ACTION` is *unresolved*, not a proven
  collision, and remains allowed (readiness stays USER_ACTION_REQUIRED).
- **GAP 2 (stale production mapping):** mapping manifest now carries
  `source_manifest_ref` + `source_manifest_sha256` (pinned to the exact bytes
  of `sku-manifest.json`, `e4ed4754…`). `validate_mapping_source_pin()`
  recomputes the source hash and fails closed on any stale/missing/malformed
  pin. Both guards run in `validate_manifests.py` main() and in the order
  worksheet builder before any worksheet exists.
- New contract tests: `tests/print_alpha/test_mapping_guards.py` (8 tests).

## 4. Lane D — Print Alpha readiness (SOFTWARE-READY; USER ACTION stands)

New: `scripts_print_alpha/order_worksheet.py` consolidates the five
RAC-PRINT-ALPHA-001 manifests into a deterministic order worksheet
(`artifacts/print-alpha/order-worksheet.json`) binding all five manifest
hashes, carrying all 64 `PENDING_USER_ACTION` fields through verbatim, with
both Lane C guards firing before build. Tests:
`tests/print_alpha/test_order_worksheet.py` (7 tests).

Status: **USER_ACTION_REQUIRED** (unchanged, by design). UA-1..UA-8 remain
the only path to READY_TO_ORDER; no vendor values were fabricated (no
Printful tokens, SKU ids, template hashes, order numbers, fabric
measurements, vendor tolerances, or physical observations invented).

## 5. Lane B — RAC-G preparation (READY; verdict NOT_ISSUED)

`tools/rac_g_barrier3_audit_prep.py` prepares the independent audit surface
against a live Barrier 3 package, using the independent reference
implementations in `certification/numerical_verification.py` rather than the
production objective math where practical:

- mean/CVaR reference recomputation vs stage-3 aggregation — PREPARED_PASS
- Pareto dominance oracle (independent front recomputation) — PREPARED_PASS
- seed/replay verifier (own file hashing, no production verifier) — prepared
- EOT sample reproduction via the pinned seed chain — PREPARED_PASS
- hash/checkpoint tamper fixtures (byte-flip must be detected) — PREPARED_PASS
- provenance attack fixtures (broken edge, silent skip) — PREPARED_PASS
- detector-response fabrication guard — PREPARED_PASS
- synthetic→measured promotion attacks — PREPARED_PASS
- release replay verifier — PREPARED_PASS
- finite-difference checks — PREPARED_DEFERRED (the Barrier 3 synthetic path
  uses the finite-pool baseline optimizer; no gradient surface exists to
  differentiate. Applicable when a gradient-backend generation is audited.)

Inventory: `artifacts/rac-g/barrier3-audit-prep.json`.
Tests: `tests/test_rac_g_barrier3_audit_prep.py` (11 tests).
**Final verdict is hard-pinned NOT_ISSUED.** Per the RAC-G final rule, the
final independent audit begins only after this handoff is committed, pushed,
refetched, and byte-confirmed.

## 6. Lane E — CI / E2E / reproducibility

- **E1 (sharding):** `scripts/ci_shards.py` — deterministic sha256-based
  partition (`verify` proves complete/disjoint/no-shard-omitted; `run`
  executes a shard with junit parsing; `aggregate` requires every shard and
  reports exact pass/fail/error/skip/xfail/xpass). Tests:
  `tests/test_ci_shards.py` (7 tests). Verified live: 4 shards,
  1206 tests, partition complete and disjoint. CI workflow wiring is
  intentionally NOT pushed — `.github/workflows/` changes remain gated on the
  staged SEC-F review (`docs/WORKFLOW_SECURITY_REVIEW.md`, all four items
  STILL_REQUIRED).
- **E2 (subprocess environment):** 12 CLI entrypoints under `scripts/` and
  `scripts_print_alpha/` are now import-safe (self-bootstrap `sys.path`), so
  subprocess-spawning tests pass without `PYTHONPATH`. A latent conftest
  module-name collision (`from conftest import …` resolving to the wrong
  directory's conftest in mixed-directory runs) was fixed by packaging
  `tests/` and using explicit `tests.optimization.conftest` imports.
- **E3 (Playwright):** real defect fixed — `tests/e2e/capture-lab.spec.js`
  contained a literal `\n` escape inside code (syntax error). Executed with
  browser + app server + production-like static serving:
  - chromium-desktop: **48 passed, 0 failed, 1 skipped**
  - webkit-mobile: **47 passed, 0 failed, 2 skipped**
  - Playwright counts are reported separately from pytest, per the testing
    rule.
- **E4 (legacy hash manifest):** `SHA256SUMS.txt` formally DEPRECATED (stale
  since `1f42666`; two competing authorities prohibited). The deprecation
  notice names the authoritative systems: `benchmarks/frozen_surface_sha256.json`
  (frozen surface), `artifacts/barrier3/hashes.sha256` (integration package),
  `artifacts/print-alpha/package-manifest.json` (print package).
  `docs/THREAT_MODEL_RESEARCH_PIPELINE.md` updated to match.

## 7. Test accounting (exact, per the testing rule)

pytest (4 deterministic shards via `scripts/ci_shards.py`, aggregate
verified complete):

| metric | count |
|---|---|
| tests | 1206 |
| passed | 1204 |
| failed | 0 |
| errors | 0 |
| skipped | 2 (documented expected: torch-not-available guard path; pristine-checkout guard) |
| xfail | 0 (both former strict xfails are now ordinary PASS) |
| xpass | 0 |
| not executed | none |

Playwright (separate, per rule): 95 passed, 0 failed, 3 skipped
(chromium-desktop 48/0/1; webkit-mobile 47/0/2).

Environment note: the shard-0 collection initially surfaced the conftest
name collision (environment-independent repo fragility); it was fixed in
repo (E2), not worked around. A later full-suite re-verification surfaced
`tests/test_barrier3_rehearsal.py` failures that were environmental only
(the sandbox working copy was a tarball without `.git`; the rehearsal
module calls `git rev-parse HEAD`) — resolved by committing the working
copy, with zero repo changes. The committed provenance graph
(`artifacts/provenance/graph.json`) was regenerated so the pinned
artifact re-derives exactly over the enlarged tree
(`test_committed_graph_rederives_exactly` PASS); it is pushed as part of
the Lane A batch.

## 8. Push integrity record

- Temporary bad commit `d27c56ca479c8ae2ceef386ce2b0306d8710c47f` carried
  mangled (placeholder) bodies for three Lane C files; detected on push and
  immediately byte-fixed by `d4924fbdffd40842f57bfbdb09d9019014696ebf`.
  Post-fix refetch hash comparison confirmed byte-exact content
  (e.g. `scripts_print_alpha/validate_manifests.py` sha256
  `26aec8119119d35f3de5c2338879aa8a3891ef9b046167e407c24481260ebf0b`,
  local == remote). Classified PUSH_INTEGRITY_FAILURE, resolved; no
  scientific artifact was involved (verification tooling only).
- Every subsequent batch was refetched and sha256-compared file by file.
- During the Lane E batch, blob-SHA comparison flagged
  `scripts_print_alpha/export_trial_sheet.py`: the pushed (remote) bytes were
  correct, but the agent-side working copy had acquired a stray escape
  (`\\n` for `\n`) in a docstring line. The working copy was corrected to the
  verified remote bytes (both now blob `725b350d…`); no bad content ever
  reached the remote in this incident.

## 9. Scientific boundaries (re-read from authoritative files)

| Assertion | Value | Evidence |
|---|---|---|
| D2_0004_MODIFIED | false | `d2-latest-status.json` untouched (decision FAIL, RAC-D0); no diff to D2-0004 paths |
| D2_0005_ARMED | false | `generations/RAC-PER-D2-0005.json` lock_status PREREGISTERED; `docs/D2-0005_FREEZE_CANDIDATE.json` armed: false — untouched |
| NEW_HELDOUT_ACCESS | false | frozen surface suite green (shard totals above); Barrier 3 runs are synthetic-only |
| SCIENTIFIC_THRESHOLDS_CHANGED | false | no threshold/manifest/frozen-contract file modified |
| PHYSICAL_EFFICACY_CLAIMED | false | every new artifact carries `physical_efficacy_claimed=false`; schema const false enforced |
| FORCE_PUSH_USED | false | additive commits only |
| UNVERIFIED_PLACEHOLDER_CONTENT | false | every pushed file executed locally and hash-verified on refetch (see §8 for the one caught-and-fixed transit failure) |

WAVE_STATUS = CLEAN.

## 10. Desired end state

| Flag | Value |
|---|---|
| BARRIER_3_CLOSED | true |
| RAC_G_READY | true (verdict NOT_ISSUED until this handoff is byte-confirmed) |
| PRODUCTION_GUARDS_PASS | true |
| PRINT_ALPHA_SOFTWARE_READY | true (USER_ACTION_REQUIRED preserved) |
| SCIENTIFIC_BOUNDARIES_INTACT | true |

Control returns to the production/P1 gate: spend no physical-production money
until RAC-G issues PASS (or approved PASS_WITH_NONBLOCKING_GAPS) on top of
this handoff, and UA-1..UA-8 complete.

## 11. Remaining human/vendor actions (unchanged)

UA-1 Printful auth → UA-2 production template fetch → UA-3 template SHA-256
binding (re-pins the mapping source state) → UA-4 matched control/candidate
SKU → UA-5 order → UA-6 calibration target fabrication → UA-7 specimen
arrival checklist → UA-8 capture-lab intake. Plus: CI workflow wiring for
`ci_shards.py` after the SEC-F workflow review clears.

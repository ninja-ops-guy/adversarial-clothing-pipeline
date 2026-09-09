# Print Alpha Release Dry Run

<!-- doclint:allow check="broken-path" reason="references gitignored regenerable dry-run outputs under artifacts/print-alpha/ (release-package/, calibration-target/); produced deterministically by scripts_print_alpha/print_alpha_dry_run.py, sha256-bound in the committed dry-run-report.json" -->

**Document ID:** PRINT-ALPHA-DRY-RUN-001
**Applies to:** RAC-PRINT-ALPHA-001
**Runner:** `scripts_print_alpha/print_alpha_dry_run.py`
**Report:** `artifacts/print-alpha/dry-run-report.json`
**Package:** `artifacts/print-alpha/release-package/`

## Purpose

Exercise the complete print-alpha package-generation path end to end using only
currently permitted inputs, so that every software-controllable defect is found
**before** the first physical dollar is spent:

```
frozen artwork → production mapping → manifests → calibration reference
→ trial sheet → validation → release package
```

Hard evidence boundary — the dry run asserts on every run:

- `physical_test_executed = false` — no garment exists; nothing physical ran.
- `physical_efficacy_claimed = false` — no efficacy claim is created or implied.
- Every unresolved vendor/user field stays the literal `PENDING_USER_ACTION`.
  The dry run **preserves and enumerates** pending state; it never resolves it
  by estimation, and a `PENDING_USER_ACTION` never becomes `PASS`.

## How to run

```bash
PYTHONPATH=. python3 scripts_print_alpha/print_alpha_dry_run.py
# exit 0: no stage failed (PENDING stages are expected pre-order)
# exit 1: a stage FAILED — read the report's failed_stages
# exit 2 (--strict): no failures, but PENDING fields remain
PYTHONPATH=. python3 scripts_print_alpha/print_alpha_dry_run.py --strict
```

Determinism contract: same repo state → byte-identical
`dry-run-report.json` and `release-package/RELEASE_PACKAGE.json`
(no wall-clock values; canonical JSON). This is enforced by
`tests/print_alpha/test_print_alpha_dry_run.py`.

## Stages

| # | Stage | What it exercises | Failure meaning |
|---|---|---|---|
| 1 | `frozen_artwork` | The frozen pattern SHA-256 (`b07b617f…c261546`) is referenced identically by `production_alpha/SKU_MANIFEST.json`, `artwork-manifest.json`, and `print-alpha-manifest.json`; sealed `print-test-kit.zip` presence/hash recorded. Absence of the kit is **PENDING**, not hidden. | Hash drift between manifests |
| 2 | `production_mapping` | `mapping-manifest.json` placements exactly cover `template-manifest.json` panels; every file/hash slot is either `PENDING_USER_ACTION` or a real value — never empty/fabricated. | Structural break in the mapping contract |
| 3 | `manifests` | Runs the existing `scripts_print_alpha/validate_manifests.py` (frozen schema `schemas/print_alpha_manifest.schema.json` + fail-closed PENDING rule for the four supporting manifests). | Any schema/PENDING-rule violation |
| 4 | `calibration_reference` | Regenerates RAC-CALT-P1-0001 via `scripts/generate_calibration_target.py` twice and requires byte-identical PNG + manifest; the manifest passes the promotion guard (`validate_manifest`); fabrication status stays `PENDING_USER_ACTION`. | Nondeterministic generator or guard violation |
| 5 | `trial_sheet` | Re-exports the 108-row trial sheet in memory and requires byte identity with the committed `print-alpha/CAPTURE/trial-sheet.csv`. | Trial-sheet drift from the preregistered matrix |
| 6 | `pending_scan` | Enumerates every `PENDING_USER_ACTION` string in all five manifests with its JSON path (currently 64 fields). | — (inventory stage; PENDING while fields are open) |
| 7 | `release_package` | Assembles `artifacts/print-alpha/release-package/` — five manifests + production-alpha SKU manifest, trial sheet, QA/capture docs, calibration PNG + manifest — all SHA-256-addressed in `RELEASE_PACKAGE.json` with `release_ready = (pending fields == 0)`. | Packaging failure |

## Current result (at authoring HEAD)

`overall_status = PENDING_USER_ACTION` — expected and correct: all
software-controllable stages pass; the pending stages (`frozen_artwork` kit
presence, `production_mapping`, `pending_scan`) await the user actions in
`docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md` (UA-1…UA-5). `release_ready` flips to
`true` only when the pending-field count reaches zero through real vendor/physical
inputs.

## Simulated external dependencies

The readiness checker and package-integrity verifier are owned by a parallel
workstream and deliberately **not** created here. The dry run records the
intended call sites in the report under `simulated_external_tools`:

- scripts/check_print_alpha_readiness.py (planned, not yet in repo) — simulated
  by stages 3 + 6 (manifest validation + pending inventory).
- scripts/print_package_integrity.py (planned, not yet in repo) — simulated by
  stage 7 (SHA-256-addressed `RELEASE_PACKAGE.json`).

When those tools land, they slot in at the recorded invocation points; the dry
run's own checks remain as regression coverage.

## What the dry run does not do

- Does not contact any vendor API, download templates, or resolve any
  `PENDING_USER_ACTION` field.
- Does not print, fabricate, photograph, or measure anything.
- Does not modify D2-0004 evidence, D2-0005 design/arming state, or any frozen
  contract; it only reads repo state.
- Does not promote synthetic or generated artifacts to measured evidence.

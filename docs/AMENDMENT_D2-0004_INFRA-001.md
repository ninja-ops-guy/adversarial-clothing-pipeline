# AMENDMENT D2-0004-INFRA-001 — Infrastructure Re-run Authorization (NOT a scientific amendment)

**Status:** Active
**Scope:** Infrastructure only. This document changes no scientific parameter, threshold, model set, candidate policy, or boundary check.
**Applies to:** Generation `RAC-PER-D2-0004`, protocol `RAC-PERSON-DETECT-1.2`.

## 1. Failure record and true root cause

- CI run **34147902820** (generation `RAC-PER-D2-0004`) failed at **step 18, "Build D2 evidence bundle"** (`scripts/build_d2_bundle.py`), after held-out inference had completed at step 17. The step died in ~1 second, before any verification logic ran.
- **Confirmed root cause:** a protocol-loader crash, NOT a frozen-contract violation. `load_protocol()` constructs the frozen dataclass `CertificationProtocol`, which had no `generation_id` field; protocol 1.2 (added in commit `581ba5e`, the first protocol to carry the governance-required `generation_id`) therefore raised `TypeError: CertificationProtocol.__init__() got an unexpected keyword argument 'generation_id'`. Reproduced exactly; diagnosis staged at `staged/diag-step18/DIAGNOSIS.md`.
- **This defect is already fixed on main:** commit `7148202d` added the optional `generation_id` field to `ruthless_pipeline/certification/protocol.py` (byte-verified). The preregistered protocol was correct; the bug was in the loader.
- **Framework-version drift is REFUTED as the cause.** The runner resolved torchvision `0.29.0+cpu`, ultralytics `8.4.142`, transformers `4.57.6` — exactly the frozen manifest versions. Ultralytics 8.4.143 reached PyPI **19 minutes after** the runner's unpinned install finished; the match was pure luck, not a control.

## 2. Status of the prior step-17 output

Step 17's held-out inference was **not contract-violating**: the runtime matched the frozen software contract and both HO-v3 state-dict hashes reproduce equal to the frozen manifests. Nevertheless the job never completed, **no evidence bundle was built, and no outcome was published or observed by anyone**. The step-17 output was **never inspected** and **never used for candidate modification, selection, or any scientific decision**.

## 3. Authorization

Exactly **ONE (1) infrastructure re-run** of `RAC-PER-D2-0004` is authorized, under the loader fix on main (`7148202d`) and the pinned runtime defined by `benchmarks/runtime_lock.json`. Any further re-run requires a new amendment.

## 4. Unchanged scientific parameters

This amendment authorizes no change to any of the following, all of which remain exactly as preregistered:

- Candidate-selection policy (surrogate-only; `heldout_feedback_allowed: false`)
- Surrogate and held-out model sets (`PERSON-SUR-v3`, `PERSON-HO-v3`) and their frozen weight hashes
- Decision thresholds and all frozen preprocessing contracts
- Candidate pool (exactly 100 Product Studio candidates) and the reference-fidelity ranking
- Adaptive search parameters (top-k 8 → 4, frozen winner before held-out inference)
- Held-out boundary and all boundary validation steps

## 5. One-shot-boundary rationale

The one-shot boundary is intact because the experiment's outcome was **never observed**: step 18 crashed in the loader before building or verifying any evidence, nothing was published, and no held-out result was seen by any person or consumed by any selection process. The re-run is therefore the first completed execution of the preregistered experiment, not a repeated measurement of an observed outcome.

## 6. Permanent control preventing recurrence (hardening, not repair)

The version-drift bullet was dodged by 19 minutes of luck, not by a control. `benchmarks/runtime_lock.json` is now the single machine-readable source of truth for the runner runtime (python 3.11, torch 2.14.0+cpu, torchvision 0.29.0+cpu, ultralytics 8.4.142, transformers 4.57.6 — matching the frozen model manifests exactly). Both `model-lock-bootstrap.yml` and `measured-benchmark.yml` install the exact pinned strings from this lock and invoke `scripts/verify_runtime_lock.py` as a hard gate **before any model download or inference step**. The gate mirrors the frozen-contract comparison semantics in `verify_frozen_model_contract` (exact string equality, `+cpu` local specifier significant, no normalization) and exits non-zero on any mismatch, closing the luck window permanently. The frozen-contract check itself is unchanged and must never be weakened.

## 7. How to trigger the re-run (descriptive only — this document triggers nothing)

The re-run uses the existing, unchanged trigger mechanics of `.github/workflows/measured-benchmark.yml`:

- **Manual:** `workflow_dispatch` on the `Measured Detector Benchmark` workflow from the default branch.
- **Push:** a push to `main` touching `generations/RAC-PER-D2-0004.json`.

The workflow's own guards still apply: the preregistered detector lock must be frozen (`lock_status: PREREGISTERED` in `benchmarks/model_manifest.json`), and the run is blocked if published held-out evidence for this generation already exists. Do not modify the trigger paths; they remain scoped to `generations/RAC-PER-D2-0004.json` only.

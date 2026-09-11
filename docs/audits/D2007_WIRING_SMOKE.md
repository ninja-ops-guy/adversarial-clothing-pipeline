# D2-0007 Stage-0 Landmark-Free Wiring Smoke Test — Audit Note

**Status:** PASS. Relationship to the Stage-0 sequencing gate: the CI-executed
surrogate-scoring smoke gate is owned by a separate lane
(`ruthless_pipeline/patterns/d2007_smoke.py`; PASS receipt persisted and
test-guarded at `evidence/d2-0007/stage0-landmark-free-smoke-closure.json`).
This document covers the ADDITIVE provenance-completeness wiring lane
declared by the Stage-0 directive: both landmark-free generators, sourced
from `P0_GENERATORS` via `GeneratorRegistry`, routed through the exposure
ledger, observation-medium annotation, governed synthetic transfer record,
and provenance nodes/edges. It does not replace, re-run, or modify the
foreign gate.

**Artifacts:**
- Wiring module: `ruthless_pipeline/patterns/wiring.py`
- Entry point: `scripts/run_d2007_wiring_smoke.py`
- Tests: `tests/test_d2007_smoke_wiring.py`
- Committed summary: `artifacts/d2007_wiring_smoke/smoke_summary.json`
  - `summary_sha256`: `999f5a576af505459d21f980574301788886d4dd6a96fb7fe4ed25f8f684a77e`
  - file sha256: `231d7010e7c4454349b496216a3cb796e5a9f547abd424eff59553baf93f7c93`
  - exposure ledger sha256: `59235b06df03ebe1b3f0519f3c3a00ead70b194850ffc4965ffb91bc04e787ab`

## What was proven

Wiring and provenance only. `SaliencyEyeAttackGenerator` and
`FeatureCollageGenerator` were instantiated from `P0_GENERATORS` **via
`GeneratorRegistry`** (never by direct internal import) and run with fixed
smoke seeds `(70000001, 70000002)` — deliberately distinct from the
preregistered motif-screening seed schedule `[20270110, 20270111, 20270112]`
so the smoke test cannot contaminate screening inputs — and with **no
landmarks** in `GeneratorParams.mask_geometry`. FeatureCollage's eye-overlap
block is a `try/except MissingLandmarksError` enhancement; with no landmarks
supplied, its anchor-independent core is provably the path taken
(`landmark_free: true` recorded per candidate and asserted in tests).

Each `GeneratedPattern` was routed through the existing governed path:

1. `GeneratedPattern.to_candidate()` → governed candidate artifact,
   `claim_state: EXPLORATORY`, `physical_efficacy_claimed: false`,
   `evidence_class: digital_candidate`.
2. Candidate image → `detector_science.adapters.SyntheticDetectionAdapter`
   (capabilities-guarded evaluator-adapter surface) against a deterministic
   synthetic development fixture (`SMOKE-DEV-FIXTURE-v0`).
3. Exposure recorded in the NR-01 ledger
   (`governance.evaluation_exposure.EvaluationExposureLedger`) as a
   surrogate-surface exposure with `decision_influenced: false`.
4. Observation medium annotated via
   `certification.observation_medium.build_medium_annotation` as
   `image_composite` (synthetic; unknown-stays-unknown respected).
5. Governed transfer record via `physical_transfer.transfer_record.emit`
   with `synthetic_generator=True`, forcing evidence class
   `synthetic_pipeline_validation_only`.
6. Provenance nodes/edges per candidate recorded in the smoke summary using
   the `certification.provenance_graph` typing vocabulary.

Verdict PASS means: PATTERNS outputs became governed RAC candidates with
complete, regenerable provenance (generator name/version, seed, params hash,
pattern content hash, exposure records, medium annotations, provenance
nodes/edges). `verify_smoke_summary` regenerates every candidate from the
registry and fails closed on any tampered hash.

## What was NOT proven

- **No efficacy.** No detection rate moved; none was measured. The scoring
  surface is a deterministic synthetic fixture, explicitly
  hypothesis-screening infrastructure, never evidence. It is not
  PERSON-SUR-v3 and never touches PERSON-HO-v3.
- **No transfer, no held-out anything.** PERSON-HO-v3 is referenced by hash
  only (`benchmarks/frozen_surface_sha256.json`). No held-out access occurred.
- **No physical claims.** All media are synthetic `image_composite`; all
  transfer records are `synthetic_pipeline_validation_only`, never promotable.

## Boundary statements

- D2-0005: untouched, unarmed, unmodified (`d2_0005_touched: false`).
- D2-0004: no inference rerun, no post-hoc optimization against it.
- No threshold changes; no additional held-out access.
- D2-0007 steps 6/8/9 (bounded search, held-out evaluation, Alpha-002):
  declared-only, not implemented here.
- Smoke seeds are outside the preregistered screening seed schedule.
- Repo provenance graph (`artifacts/provenance/graph.json`): unchanged —
  this change adds no files under any walked path (generations/, model_sets/,
  schemas/, manuscript/evidence/, artifacts/ctm/), so no regeneration was
  required; `scripts/build_provenance_graph.py --verify` confirms the
  committed graph remains current.
- Frozen surface (`benchmarks/frozen_surface_sha256.json`): untouched; no new
  pins were needed for D2-0005/P1 files.

## Reproduction

```
PYTHONPATH=. python scripts/run_d2007_wiring_smoke.py           # run + write
PYTHONPATH=. python scripts/run_d2007_wiring_smoke.py --verify artifacts/d2007_wiring_smoke/smoke_summary.json
PYTHONPATH=. python -m pytest tests/test_d2007_smoke_wiring.py
```

Two runs over the same inputs produce byte-identical summary files.

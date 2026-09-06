# v2 prototype → v3 production-hardening migration

## Deliverable 1 — Enhanced NAP

Fixed:
- 512/513 tensor mismatch from even-kernel average pooling.
- missing/duplicated query-count ownership.
- black-box candidate replacement that detached the optimized tensor from the surrogate gradient path.
- silent fake Stable Diffusion and CLIP outputs.
- hard-coded output path and missing output-directory creation.
- unbounded metadata writes and lack of checkpoints.

Changed:
- real optional `diffusers` and `open_clip` adapters are lazy-loaded and fail loudly when unavailable.
- procedural prior is now an explicit CI/offline backend, not disguised as Stable Diffusion.
- black-box queries have one hard budget and finite-score validation.
- NPS is chunked for predictable memory use.
- optimizer uses Adam, gradient clipping, deterministic seeds, and atomic metadata output.

## Deliverable 2 — Neural deformation

Fixed:
- time conditioning dimension mismatch.
- training objective that optimized the deformation field toward zero rather than observed deformation.
- output-directory failures.

Changed:
- training now consumes explicit normalized source/target UV correspondences.
- the network predicts displacement plus uncertainty.
- fabric priors generate nonzero, material-specific analytic deformation fields.
- smoothness and magnitude regularization are explicit.
- save/load is supported.

The package deliberately does not pretend that random camera tensors are calibrated multi-view capture. Real capture must be converted to correspondences by a separate calibrated preprocessing stage.

## Deliverable 3 — Differentiable physics

Fixed:
- zero stretch and bend forces.
- no-op collisions/physics path being described as end-to-end differentiable cloth simulation.
- unstable first native integrator (now substepped symplectic Euler with damping).

Changed:
- added a working differentiable mass-spring cloth baseline with structural and bend springs.
- added differentiable dense UV displacement and texture rendering.
- added an optimization loop with real texture gradients.

This native solver is a validated software baseline for pipeline integration/CI, not a scientific replacement for HOOD or DiffCloth. External high-fidelity backends remain a separate integration gate.

## Deliverable 4 — Comparative benchmark

Added from scratch because no uploaded benchmark source file was present:
- surrogate vs held-out model split.
- lighting/scale/blur sweep.
- baseline vs candidate raw score deltas.
- thresholded detection rates.
- CSV and JSON reports.

## Verification performed during v3 hardening

- five Python test files are present in the repository; prior local verification passed.
- all four standalone entrypoints were exercised during the production-hardening pass.
- end-to-end smoke path exercised NAP → deformation → physics → benchmark.
- physics state remained finite in the baseline stability check.
- texture gradients propagated through the native physics renderer.
- source tree compiled locally during the hardening pass.

### Important CI update

The first GitHub Actions run after the v3 import did **not** reproduce a green release gate. Installation completed, but Ruff reported lint/import/style findings and the workflow stopped before pytest. The repository should therefore distinguish:

- **prior local functional verification**, from
- **current GitHub CI status**.

Do not state that CI is passing until a later workflow actually completes green.

## Still external / not claimed complete

- Stable Diffusion runtime was not exercised during the original hardening environment because `diffusers` was not installed.
- OpenCLIP runtime was not exercised because `open_clip_torch` was not installed.
- pretrained detector adapters and a frozen model manifest were not supplied in the original materials.
- calibrated multi-view garment capture data was not supplied.
- no physical printed garment validation has been run.
- no vendor-specific surveillance integration is included.

## Scene/evaluator integration

A differentiable garment-scene compositor and caller-supplied detection adapter close an important prototype gap: a raw textile texture should not be scored as though it were itself a surveillance-camera frame. Production experiments should compose the pattern into an authorized scene first, then pass that composed image to the evaluator.

For higher-fidelity experiments, replace the 2D mask compositor with calibrated UV/geometry information from the deformation/physics stages while retaining the same provenance-aware evaluator interface.

---

# Post-v3 repository additions — Pattern Lab

After the v3.0.0 production import, `main` gained a separate static browser application:

- `index.html` — Pattern Lab interface / Pages entrypoint.
- `styles.css` — Pattern Lab presentation.
- `core.js` — procedural pattern generation and browser simulation controls.
- `analysis.js` — analysis visualizations, history/gallery, exports, heuristic scoring, and quick-optimization UI.
- `.github/workflows/pages.yml` — GitHub Pages deployment workflow.

These additions were **not part of the original v3 production-hardening verification** and should be documented as a separate application layer.

## Pattern Lab claim boundary

The Pattern Lab currently contains two kinds of values:

1. deterministic/procedural image features and configuration data; and
2. UI-only heuristic/randomized scores.

The second category is not research evidence. In particular, model-named percentages in the browser are not produced by real model inference, and the current quick optimizer uses those UI values. Before Pattern Lab can become a measurement front end, it needs a bridge to frozen Python benchmark results plus explicit provenance.

## Recommended next migration step

Treat the next repository release as an **integration release**, not an efficacy release:

1. green CI;
2. unified experiment/config schema;
3. Pattern Lab → Python job bridge;
4. Python benchmark → Pattern Lab result import;
5. frozen detector manifest;
6. provenance shown beside every result;
7. physical-validation protocol only after the digital benchmark is reproducible.

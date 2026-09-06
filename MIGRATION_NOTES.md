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

## Verification performed

- `pytest`: 4/4 passing.
- all four standalone entrypoints execute successfully.
- end-to-end smoke path executes NAP → deformation → physics → benchmark.
- physics state remains finite through 40 simulation steps in the default stability check.
- texture gradients propagate through the native physics renderer.
- source tree compiles with `compileall`.

## Still external / not claimed complete

- Stable Diffusion runtime was not exercised in this environment because `diffusers` is not installed.
- OpenCLIP runtime was not exercised because `open_clip_torch` is not installed.
- pretrained detector adapters and weights were not supplied in the uploaded materials.
- calibrated multi-view garment capture data was not supplied.
- no physical printed garment validation has been run.
- no vendor-specific surveillance integration is included.

## Scene/evaluator integration

Added a differentiable garment-scene compositor and a caller-supplied torchvision detection adapter. This closes an important architecture gap in the prototype: a raw textile texture should not be scored as though it were itself a surveillance-camera frame. Production experiments can now compose the pattern into an authorized scene first, then pass that composed image to the evaluator.

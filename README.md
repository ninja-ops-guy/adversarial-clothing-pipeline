# Ruthless Adversarial Clothing Pipeline v3.0

Production-oriented research package for **machine-optimized fashion engineered to reduce reliable visual classification across diverse computer-vision systems** in owned or explicitly authorized lab environments.

## What changed from the v2 prototypes

- Removed silent random placeholders from production paths.
- Fixed the NAP 512/513 tensor mismatch by preserving spatial dimensions with odd kernels.
- Fixed query accounting: one authoritative budget counter with hard enforcement.
- Fixed NAP optimization so black-box candidate updates stay inside the same `nn.Parameter` and do not sever surrogate gradients.
- Added deterministic seeds, device validation, path creation, atomic metadata writes, checkpointing, and testable interfaces.
- Replaced fake CLIP/diffusion outputs with explicit optional adapters. If those backends are selected but dependencies/models are unavailable, the pipeline fails loudly.
- Reworked deformation training around real coordinate correspondences rather than minimizing displacement toward zero.
- Fixed time-conditioning input dimensions and added uncertainty prediction.
- Added a working differentiable native mass-spring cloth baseline so the physics path has real gradients instead of zero-force placeholders.
- Added the previously missing comparative benchmark with surrogate vs held-out splits and transformation sweeps.
- Added tests and runnable standalone wrappers for all four deliverables.

## Quick start

```bash
python -m pip install -e .
pytest
python -m examples.smoke_test
```

The four original-style entrypoints are also present:

```bash
python 01_enhanced_black_box_nap.py
python 02_neural_deformation_module.py
python 03_differentiable_physics_pipeline.py
python 04_comparative_benchmark.py
```

## Optional real generative backends

Stable Diffusion support is explicit:

```bash
pip install -e '.[generative]'
```

Then set `prior_backend="diffusers"` and point `diffusion_model_id` to an approved local model or set `diffusion_local_files_only=False` in an environment where model download is allowed.

CLIP aesthetic guidance:

```bash
pip install -e '.[aesthetic]'
```

Then set `aesthetic_backend="open_clip"`.

## Production boundary

The included black-box optimizer and benchmark accept generic evaluator callables; they do **not** contain vendor-specific surveillance integrations. Keep black-box testing limited to systems you own or have explicit authorization to evaluate. The benchmark intentionally reports only measured results from supplied evaluators and does not extrapolate those results to untested commercial systems.

## Remaining work before a physical product claim

1. Connect real open-model detector adapters and freeze a benchmark model/version manifest.
2. Collect actual garment deformation correspondences from calibrated multi-view video or optical-flow/keypoint preprocessing.
3. Replace the native cloth baseline with a validated HOOD/DiffCloth integration if research results justify it.
4. Calibrate digital-to-print color using measured fabric ICC/profile data rather than the approximate NPS palette.
5. Run a pre-registered physical protocol across pose, distance, camera angle, lighting, compression, and multiple garment sizes.
6. Report confidence intervals and held-out architecture results; do not market unmeasured transfer rates.

## Scene composition and model adapters

`GarmentTextureComposer` provides the missing camera-scene bridge: optimize/evaluate the texture only after it has been differentiably composited into an owned lab image using a garment mask. `TorchvisionDetectionEvaluator` wraps a caller-supplied torchvision detector without downloading or silently changing model weights, which keeps benchmark provenance reproducible.

For higher-fidelity experiments, replace the 2D mask compositor with UV maps from the neural-deformation/physics stages while keeping the same evaluator interface.

## Repository policy

This codebase is configured for a **private research repository by default**. Generated outputs, model weights, datasets, environment files, and credentials are git-ignored. See `RESPONSIBLE_USE.md`, `SECURITY.md`, and `PRODUCTION_READINESS.md` before connecting external models or running physical trials.

The current `LICENSE` is all-rights-reserved for internal/business development; it is intentionally not labeled MIT because MIT terms cannot simultaneously impose an "authorized use only" restriction. Replace the license only after choosing a publication/commercialization strategy.

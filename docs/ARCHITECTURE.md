# Architecture

**Reviewed against repository state:** 2026-09-06 (`main` baseline `a9e827e`)

The repository currently contains **two distinct execution planes** that must not be conflated in research reporting.

## 1. Browser exploration plane — Pattern Lab

```text
index.html
   |
   +--> styles.css
   +--> core.js
   |      +--> seeded procedural generators
   |      +--> palette/parameter controls
   |      +--> pose/fabric/warp/lighting UI simulation
   |
   +--> analysis.js
          +--> frequency/color visualizations
          +--> heuristic score displays
          +--> gallery/history
          +--> PNG/JSON export
```

The Pattern Lab is useful for candidate generation, visual review, parameter capture, and future orchestration. It is **not currently wired to the Python evaluator/benchmark stack**.

### Current Pattern Lab evidence boundary

- The eight browser generators are procedural design generators, not learned adversarial optimizers.
- The analysis panel does not execute YOLO, DETR, Faster R-CNN, SSD, or another detector.
- Several displayed metrics are randomized by the current front-end implementation.
- The model-named percentage display is a heuristic derived from image statistics, not model inference.
- “Quick optimize” searches UI seed candidates using those heuristic metrics.

Therefore, Pattern Lab scores are **DEMO/HEURISTIC** data only and must not enter benchmark tables, investor claims, product claims, papers, or technical leadership metrics as measured efficacy.

## 2. Python research plane

```text
texture prior / optimizer
        |
        v
neural deformation -----------+
        |                      |
        v                      |
differentiable cloth          |
        |                      |
        v                      |
garment scene composition <---+
        |
        v
evaluator adapters
        |
        v
held-out benchmark + reports
```

### Components

| Stage | Repository component | Current maturity |
|---|---|---|
| Pattern prior/optimization | `ruthless_pipeline/nap.py` | Production-hardened research baseline; optional real diffusion/OpenCLIP adapters |
| Deformation | `ruthless_pipeline/deformation.py` | Differentiable coordinate-correspondence field + uncertainty; calibrated capture still external |
| Physics | `ruthless_pipeline/physics.py` | Working differentiable mass-spring baseline; not a HOOD/DiffCloth replacement |
| Scene composition | `ruthless_pipeline/scene.py` | Differentiable garment-mask compositor |
| Evaluation | `ruthless_pipeline/evaluators.py` | Caller-supplied evaluator interfaces; real frozen model zoo not bundled |
| Benchmark | `ruthless_pipeline/benchmark.py` | Surrogate/held-out split + transformation sweeps + CSV/JSON reporting |

## 3. Evidence plane

Measured results should flow through a separate evidence contract:

```text
experiment definition
  -> frozen model manifest
  -> immutable preprocessing + thresholds
  -> seeds/transforms/splits
  -> raw outputs
  -> aggregate metrics + uncertainty
  -> artifact hashes
  -> claim review
```

A result is not “internally measured” unless the manifest and artifacts needed to reproduce it are retained.

## 4. Planned integration boundary

The clean future integration is:

```text
Pattern Lab candidate/config export
        |
        v
experiment job definition
        |
        v
Python optimizer / scene / evaluator stack
        |
        v
benchmark artifact bundle
        |
        v
Pattern Lab result import or dashboard view
```

Do not shortcut this by making browser heuristics look like detector outputs. When model-backed scoring is added, the UI should display provenance beside every metric: model ID/version, threshold, transform set, timestamp, experiment ID, and evidence label.

## Design rules

- **No raw-texture efficacy claims.** Evaluate composed scenes or physically meaningful renderings.
- **No hidden backends.** Diffusion, CLIP, detector, and high-fidelity physics backends must be explicitly selected and fail loudly when unavailable.
- **Reproducible provenance.** Record model identifiers/versions, seeds, transforms, thresholds, calibration data, and test splits.
- **Held-out evaluation.** Optimization/surrogate models must be separated from held-out reporting models.
- **Physical evidence boundary.** Digital and simulated results are not physical product-validation evidence.
- **UI evidence boundary.** Browser heuristic/demo scores are not benchmark results.
- **Authorized testing only.** External black-box interfaces are limited to owned or explicitly authorized systems.

## Versioning note

The Python package is currently `3.0.0`. The Pattern Lab JSON export identifies a front-end configuration schema as `2.0.0`. These versions describe different artifacts and should remain explicitly named until a unified repository release/version policy is adopted.

# Architecture

The production package separates pattern generation, physical deformation, scene composition, model evaluation, and benchmarking so each stage can be validated independently.

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

## Design rules

- **No raw-texture efficacy claims.** Detector evaluation should operate on composed camera scenes or physically meaningful renderings.
- **No hidden backends.** Diffusion/CLIP/high-fidelity physics integrations must be selected explicitly and fail loudly when unavailable.
- **Reproducible provenance.** Record model identifiers/versions, seeds, transforms, thresholds, and test splits.
- **Held-out evaluation.** Surrogate models used during optimization must be separated from held-out models used for reporting transfer.
- **Physical evidence boundary.** Digital and simulated results are not product-validation evidence.

# RAC Environment-Adaptive Patch Generation

This module is an original RAC implementation inspired by the research ideas in:

- Chaoqun Li, Zhuodong Liu, Huanqian Yan, Hang Su, **CapGen: An Environment-Adaptive Generator of Adversarial Patches**, arXiv:2412.07253 (2024).
- The external `SamSamhuns/yolov5_adversarial` repository was reviewed as a reference architecture only. Its AGPL-3.0 code is **not copied into this repository**.

## Why it matters to RAC

CAPGen's core result is useful for apparel: pattern structure and color can be treated separately. Their experiments report that the pattern component has a stronger effect on detector performance than the exact base colors. That suggests a product workflow where RAC first finds a strong structural pattern and then rapidly recolors it for different garments, collections, or environments.

## RAC implementation

`ruthless_pipeline.capgen` adds:

1. deterministic K-means environment palette extraction;
2. color-agnostic pattern-logit initialization from a seed texture;
3. palette-constrained differentiable rendering;
4. gradient optimization of a per-pixel color-allocation matrix;
5. EOT-style brightness, rotation, and scale transforms;
6. fast recoloring that preserves learned pattern allocation while replacing environment colors.

## Pipeline placement

```text
Conditional Textile Generator / NAP
              |
              v
       seed pattern structure
              |
              v
EnvironmentAdaptivePatchGenerator
  - extract environment palette
  - initialize pattern allocation
  - optimize on SURROGATE models only
  - EOT robustness
              |
              v
       candidate texture
              |
              v
existing deformation / scene / benchmark stack
              |
              v
        freeze candidate
              |
      === D2 boundary ===
              |
              v
       held-out model suite
```

Held-out detectors must never be supplied to the CapGen-style optimizer. Recoloring or optimization after seeing held-out results creates test-set leakage and invalidates D2.

## Fast environment adaptation

Once a high-performing allocation matrix has been learned, `recolor()` extracts a new environment palette and renders the same allocation with the new colors. This is the RAC equivalent of changing a collection palette without discarding the structural pattern.

## Evidence classification

Output from this module is a **candidate-generation artifact**, not certification evidence. The existing RAC benchmark/certification system remains authoritative for D1/D2/P1+ states.

## Commercial-code boundary

The external YOLOv5 adversarial repository is AGPL-3.0. RAC should not vendor or copy that code into the commercial core without legal review. The adapter boundary should remain generic: any owned/authorized detector runtime can provide differentiable surrogate scores through the `surrogate_fn` interface.

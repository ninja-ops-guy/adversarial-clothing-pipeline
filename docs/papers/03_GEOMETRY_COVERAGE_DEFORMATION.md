# Garment Geometry, Coverage, and Deformation in Physical Adversarial Apparel

**Manuscript status:** Pre-results draft  
**RAC paper:** 3

## Abstract

Physical adversarial apparel is simultaneously a texture-optimization and geometry problem. A pattern that is effective on a flat image may be distorted by perspective, non-rigid cloth deformation, body pose, seams, folds, occlusion, and limited garment coverage. This study decomposes those factors through two controlled ablations: a deformation-fidelity ladder (flat → affine → thin-plate spline → cloth simulation) and a fixed-area coverage/topology study across garment regions and coordinated garments. Optimization budget, model sets, and candidate area are held constant where the comparison requires it. The objective is to quantify which geometric approximations materially predict held-out and later physical performance. **Results are pending.**

## 1. Research questions

**RQ1:** How much robustness is gained as deformation modeling increases in physical fidelity?

**RQ2:** At fixed adversarial area, does placement/topology matter more than total area?

**RQ3:** Do coordinated regions across garments provide benefits not explained by coverage alone?

## 2. Deformation ladder

1. Flat digital texture.
2. Affine/perspective transforms.
3. Thin-plate-spline non-rigid deformation.
4. Differentiable cloth simulation.
5. Later: measured garment deformation distributions when calibrated capture exists.

All arms use equal candidate-generation budgets and the same surrogate/held-out discipline.

## 3. Coverage/topology study

Compare fixed-area placements on torso, shoulder, sleeve, leg, and coordinated multi-region configurations. Record visible adversarial area under each pose rather than assuming nominal printed area equals observed coverage.

## 4. Evaluation

Digital experiments precede physical validation. Physical sessions use matched garments and the same session-level statistical unit defined by RAC-P1. Report mean behavior, worst tested condition, and condition-specific failures.

## 5. Results

**RESULTS PENDING.**

## 6. Expected contribution

The study is designed to separate three explanations often collapsed into a single attack-success number: the pattern itself, the model of cloth deformation, and where/when the camera can actually see adversarial material.

## References

- Xu et al., *Adversarial T-shirt!*, ECCV 2020.
- Hu et al., *Adversarial Texture*, CVPR 2022.
- Huang et al., *AdvReal*, 2026.

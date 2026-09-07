# Manufacturing-Calibrated Optimization for Physical Adversarial Textiles

**Manuscript status:** Pre-results draft  
**Evidence state:** Methods / hypothesis only  
**RAC paper:** 2

## Abstract

A digital adversarial textile is not the signal observed by a deployed detector. Printing, substrate structure, garment deformation, optics, distance, resampling, exposure, and image-signal processing alter the optimized pattern before inference. RAC proposes to model this path as an empirically measured transfer function rather than relying only on generic expectation-over-transformation heuristics or static printable-color penalties. We define a calibration target containing color, geometry, registration, spatial-frequency, and RAC-specific motif structures; manufacture it using the same production process as the experimental garment; estimate a versioned digital→fabric→camera profile; and compare baseline, heuristic-EOT, measured-EOT, and measured-EOT plus frequency-survival optimization under equal budgets. The primary question is whether calibration learned from held-out target regions improves physical robustness without using held-out detector feedback. **Results are pending.**

## 1. Motivation

Prior physical apparel work models deformation and viewpoint, and AdvReal explicitly incorporates non-rigid surfaces, relighting, distance, and 2D/3D realism. REAP similarly demonstrates that realistic rendering choices materially affect evaluation. RAC extends this realism question toward manufacturing itself: can the print/substrate/camera chain be measured sufficiently well to improve optimization?

## 2. Hypotheses

- **H1:** A frozen print-camera profile predicts held-out calibration patches within preregistered color/geometric/frequency tolerances.
- **H2:** Measured-EOT yields better held-out physical performance than heuristic-EOT at equal optimization budget.
- **H3:** Constraining optimization toward spatial-frequency bands that survive print + distance + capture improves robustness relative to measured-EOT without that constraint.

## 3. Calibration target

The target includes at least 24 color patches, an 11-step neutral ramp, horizontal/vertical line pairs, multiscale checkerboards, frequency wedges, registration marks, physical rulers, high/low-frequency controls, and representative RAC motif fragments.

The target master, manufacturing process, substrate, provider template, camera configuration, and source commit are hash-bound before measurement.

## 4. Calibration estimation

Measurements estimate:

- digital RGB → observed RGB response;
- color error;
- geometric scale error;
- placement/registration error;
- blur / frequency attenuation by orientation and band;
- distance-dependent attenuation;
- repeatability across captures.

A calibration profile is accepted only after held-out target regions satisfy preregistered prediction tolerances. The profile is specific to the measured production/capture chain.

## 5. Experimental arms

| Arm | Optimization transform model |
| --- | --- |
| A | Minimal/baseline transforms |
| B | Heuristic EOT |
| C | Empirically measured EOT |
| D | Measured EOT + frequency-survival constraint |

Budgets, surrogate sets, candidate-selection rules, and held-out evaluation are held constant.

## 6. Physical evaluation

Matched control and candidate garments use the same SKU, size, substrate, manufacturing process, actor, camera, lighting, and session. Garment × actor × session is the primary statistical unit. Frames are nested observations.

## 7. Results

**RESULTS PENDING.**

## 8. Limitations

The learned calibration profile is not universal. Provider, substrate, fulfillment region, printer, garment construction, camera, software processing, and environment may all change the transfer function.

## References

- Xu et al., ECCV 2020.
- Hu et al., CVPR 2022.
- Hingun et al., ICCV 2023.
- Huang et al., Expert Systems with Applications 2026.

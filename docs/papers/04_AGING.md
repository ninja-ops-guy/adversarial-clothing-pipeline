# Aging of Adversarial Apparel: Physical Durability and Model Drift

**Manuscript status:** Pre-results draft  
**RAC paper:** 4

## Abstract

Adversarial apparel can age in two independent ways: the physical artifact changes through wear, laundering, abrasion, color shift, and deformation, while the machine-vision ecosystem changes through new model architectures, weights, preprocessing, and thresholds. RAC proposes a longitudinal design that freezes a physical garment and evaluates these axes separately. Physical aging is measured at W0, W1, W5, W10, and later preregistered states using the same manufacturing-bound artifact. Technological aging evaluates the same frozen physical artifact against later closed model generations without reprinting or re-optimizing it. This design distinguishes material degradation from model adaptation and turns product longevity into a measurable research question. **Results are pending.**

## 1. Research questions

- How quickly does adversarial effect change with laundering and wear?
- Which physical measurements—color shift, registration, frequency attenuation—best explain degradation?
- How quickly does a fixed garment lose or gain effectiveness as detector generations change?
- Are physical and technological aging independent, additive, or interacting?

## 2. Physical aging protocol

Freeze the W0 garment identity and manufacturing record. Evaluate the same garment at W0/W1/W5/W10. Record laundering process, detergent, temperature, drying method, color measurements, geometric measurements, and standardized photographs.

## 3. Technological aging protocol

Never alter the garment for the model-aging experiment. Evaluate the same physical artifact against later model generations under the same capture protocol. Once a model generation is observed, it is never described as unseen again.

## 4. Analysis

Model physical state and model generation as separate factors. Report condition-specific rates and uncertainty. Preserve all failures and avoid survivor bias from replacing degraded garments.

## 5. Results

**RESULTS PENDING.**

## 6. Significance

A privacy garment that works only when new is a different product from one whose effect persists after ordinary use. Likewise, a garment whose behavior changes rapidly with model generations has a measurable technological half-life. Both are more informative than a timeless efficacy claim.

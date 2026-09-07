# Robust Objectives and Surrogate Architecture Diversity for Adversarial Apparel

**Manuscript status:** Preregistration-aligned pre-results draft  
**RAC paper:** 5

## Abstract

Cross-model transfer is a central bottleneck in adversarial apparel. Optimizing the average surrogate loss may produce candidates that exploit a subset of models while leaving a weak worst-case model, whereas min-max or conditional-value-at-risk (CVaR) objectives explicitly emphasize difficult surrogate conditions. This paper specifies an equal-budget ablation comparing mean, worst-case/min-max, and CVaR objectives under the same candidate-generation, transformation, model-manifest, and held-out-evaluation rules. A second experiment removes one architecture family from the surrogate ensemble at a time to test whether surrogate diversity predicts transfer to a fresh held-out family. The D2-0005 generation is intended to instantiate the first objective comparison after D2-0004 closes. **No D2-0005 result is claimed in this draft.**

## 1. Motivation

Xu et al. extended adversarial T-shirt optimization to an ensemble setting using min-max optimization. RAC generalizes the underlying research question: under modern multi-architecture surrogate sets and a contamination-resistant held-out protocol, which robust objective produces the strongest worst-case transfer at equal optimization cost?

## 2. Primary D2-0005 question

Does worst-case/CVaR-oriented optimization reduce held-out detection rate relative to mean optimization when all other generation variables are frozen?

### Primary endpoint

Held-out candidate detection rate by arm, with paired risk difference under the preregistered comparison.

### Secondary endpoints

- held-out mean confidence;
- worst held-out model;
- surrogate/held-out transfer gap;
- transformation variance;
- candidate fidelity/printability tradeoff;
- optimization stability.

## 3. Experimental arms

At minimum:

- **Mean arm:** optimize average surrogate objective.
- **Worst-case arm:** optimize the hardest surrogate/model-condition objective.
- **CVaR arm:** optimize the upper-risk tail using a preregistered alpha.

All arms use the same surrogate set, fresh held-out set, seeds/pool size, EOT policy, candidate budget, threshold policy, and one-shot held-out rule.

## 4. Success and inconclusive regions

The preregistration must define before held-out access:

- the directional hypothesis;
- minimum effect considered practically meaningful;
- paired uncertainty procedure;
- success region;
- failure region;
- inconclusive region;
- treatment of invalid conditions;
- stopping rule.

The paper will report the preregistered decision even when it is FAIL or inconclusive.

## 5. Surrogate architecture ablation

After the objective experiment, run leave-one-architecture-family-out surrogate studies. The held-out architecture family for a given experiment must remain untouched until candidate freeze. Compare transfer loss when CNN, transformer, one-stage, or two-stage diversity is removed from the surrogate set.

## 6. Results

**RESULTS PENDING. D2-0005 is not yet an evaluated generation in this manuscript.**

## 7. Discussion

**DISCUSSION PENDING.**

The final discussion will separate improvements on surrogate models from genuine improvements on fresh held-out models and will explicitly report any objective that improves one while harming the other.

## References

- Xu, K. et al. *Adversarial T-shirt! Evading Person Detectors in A Physical World.* ECCV 2020.
- Hu, Z. et al. *Adversarial Texture for Fooling Person Detectors in the Physical World.* CVPR 2022.
- Hingun, N. et al. *REAP.* ICCV 2023.

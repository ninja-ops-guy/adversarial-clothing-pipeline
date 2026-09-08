# Prospective Prediction of Cross-Model Transfer in Adversarial Apparel

**Manuscript status:** Pre-results draft  
**Evidence state:** Methods / hypothesis only  
**RAC paper:** 1

## Abstract

Physical adversarial apparel research has demonstrated that printed patterns can affect person detectors under specific experimental conditions, but transfer from optimized surrogate models to previously unseen architectures remains difficult to predict. Existing work has addressed non-rigid deformation, multi-view texture coverage, and realistic rendering, while realistic benchmark work has also shown that simplified digital success can poorly predict performance under more realistic conditions. We propose a prospective, generation-based methodology for studying transfer rather than evaluating it retrospectively. Each RAC generation freezes candidate bytes, optimization telemetry, model manifests, thresholds, and transformation policy before a fresh held-out model generation is opened. Held-out outcomes are appended only after closure and cannot alter the frozen pre-held-out record. Across successive closed generations, we will test whether surrogate worst-case performance, cross-model disagreement, transformation variance, spectral properties, reference fidelity, printability, coverage, and camera/manufacturing margins predict held-out transfer better than surrogate mean alone. The contribution is a contamination-resistant longitudinal design for learning what predicts transfer in adversarial apparel. **Results are pending.**

## 1. Introduction

Adversarial apparel occupies an unusually difficult physical-adversarial setting: the optimized signal is printed on deformable material, worn on a moving human body, observed through a camera pipeline, and evaluated by models that may differ from those used during optimization. Xu et al. modeled non-rigid T-shirt deformation and reported both digital and physical attack results against person detection. Hu et al. later proposed full-garment expandable adversarial texture for multi-angle attacks. These works establish that apparel can be a meaningful physical attack surface under defined conditions, but they do not eliminate the transfer problem.

The gap between simplified digital optimization and realistic evaluation is broader than apparel. REAP found that attack success on simpler synthetic evaluations was poorly predictive of performance under more realistic rendering and image distributions. AdvReal further emphasizes non-rigid deformation, lighting, viewpoint, distance, and 2D/3D realism in physical adversarial evaluation.

RAC therefore treats transfer prediction itself as the research object. Instead of repeatedly asking whether a candidate transfers, we ask:

> **Which properties known before held-out access predict whether a frozen adversarial-apparel candidate will transfer to a fresh model generation?**

## 2. Research questions

**RQ1.** Does surrogate mean performance predict held-out transfer?

**RQ2.** Do worst-surrogate performance and cross-model disagreement improve prediction beyond surrogate mean?

**RQ3.** Do transformation variance and spectral properties add predictive value?

**RQ4.** After physical calibration exists, do camera/ISP and manufacturing-survival margins improve prospective prediction?

### Primary hypothesis

At least one preregistered pre-held-out feature—initially worst-surrogate performance, model disagreement, transformation variance, or spectral profile—will predict closed held-out transfer better than surrogate mean alone across multiple closed generations.

This is directional and falsifiable. Failure to outperform surrogate mean is a valid negative result.

## 3. Threat model and evidence boundary

The study concerns person-detection systems evaluated in owned or explicitly authorized research environments. It does not claim universal evasion of surveillance systems.

Candidate generation has access only to the declared surrogate set. The fresh held-out set is unavailable to optimization, ranking, mutation, or candidate selection. Once evaluated, that held-out generation is permanently considered observed for future research.

## 4. Prospective generation protocol

For each generation:

1. Freeze the generation protocol, surrogate set, fresh held-out set, thresholds, seeds, candidate pool policy, and success criteria.
2. Generate and rank candidates using surrogate information only.
3. Freeze the winning candidate and its SHA-256.
4. Freeze the pre-held-out telemetry record and its own hash.
5. Open the held-out generation once.
6. Append the held-out outcome without modifying the frozen telemetry.
7. Seal the experiment as a content-addressed RAC release.
8. Retain PASS, FAIL, and inconclusive generations.

## 5. Pre-held-out telemetry

The preregistered telemetry contract records:

- surrogate mean and worst performance;
- per-model performance and cross-model disagreement;
- transformation mean, worst case, and variance;
- spectral-band features;
- reference-fidelity score;
- printability measures;
- coverage/topology measures;
- optimizer objective and trajectory;
- candidate and source-commit hashes;
- calibration-profile reference when available.

Missing historical fields are represented as explicit null/unavailable values rather than reconstructed after held-out access.

## 6. Statistical analysis plan

The first analysis will remain interpretable because the number of closed generations will initially be small.

1. Establish surrogate mean as the baseline predictor.
2. Compare preregistered individual predictors against that baseline.
3. Report effect estimates and uncertainty rather than selecting a model solely by in-sample fit.
4. Add multivariable regularized models only after sufficient generations exist.
5. Perform leave-one-generation-out sensitivity analysis where sample size permits.
6. Preserve failed generations and missing telemetry.
7. Do not tune predictor definitions using the same held-out outcomes they are intended to predict.

A first serious predictor analysis requires at least three comparable closed generations, but this threshold is an analysis-start rule rather than a claim that three generations provide definitive statistical power.

## 7. Results

**RESULTS PENDING.**

D2-0003 is retained as a negative historical generation. D2-0004 closed on 2026-09-08 (FAIL / RAC-D0, log-attested) with its immutable release minted at `releases/RAC-EXP-2026-001/`; it may now be incorporated into the longitudinal dataset subject to its attestation gaps (`manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json` → `not_log_attested_gaps`).

## 8. Discussion

**DISCUSSION PENDING.**

The planned discussion will distinguish three possibilities: useful prospective predictors emerge; surrogate mean remains as good as richer telemetry; or transfer proves too unstable for the available features and sample size.

## 9. Reproducibility

Each included generation should resolve to a `RAC-EXP-YYYY-NNN` release containing the frozen protocol, candidate hashes, telemetry record, model manifests, benchmark outputs, failure classification when applicable, and release integrity manifest.

## 10. Ethics and limitations

RAC is motivated by public-interest privacy research and by understanding brittleness in computer-vision systems. The study is limited to named models, thresholds, fixtures, transformations, and later physical conditions. Results must not be generalized to arbitrary surveillance deployments.

## References

- Xu, K. et al. *Adversarial T-shirt! Evading Person Detectors in A Physical World.* ECCV 2020. https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/4383_ECCV_2020_paper.php
- Hu, Z. et al. *Adversarial Texture for Fooling Person Detectors in the Physical World.* CVPR 2022. https://openaccess.thecvf.com/content/CVPR2022/html/Hu_Adversarial_Texture_for_Fooling_Person_Detectors_in_the_Physical_World_CVPR_2022_paper.html
- Hingun, N. et al. *REAP: A Large-Scale Realistic Adversarial Patch Benchmark.* ICCV 2023. https://openaccess.thecvf.com/content/ICCV2023/html/Hingun_REAP_A_Large-Scale_Realistic_Adversarial_Patch_Benchmark_ICCV_2023_paper.html
- Huang, Y. et al. *AdvReal: Physical adversarial patch generation framework for security evaluation of object detection systems.* Expert Systems with Applications, 2026. DOI: 10.1016/j.eswa.2025.128967.

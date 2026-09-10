# RAC Research Paper Series — Pre-Results Build Plan

**Version:** 1.1.0  
**Rule:** Write methods before results. Never manufacture findings to complete a manuscript.

The RAC paper program now contains two **foundation papers** explaining the research system itself and five **experimental papers** whose results depend on closed RAC experiment releases.

## Foundation Paper 0 — RAC System Architecture

**Manuscript:** `papers/00_RAC_SYSTEM_ARCHITECTURE.md`

**Core question:** How should a physical adversarial research system separate exploration, optimization, certification and physical validation while preserving reproducibility and held-out boundaries?

Primary contributions:

- four-plane architecture;
- candidate-generation topology;
- surrogate/held-out trust boundary;
- provenance graph;
- digital-to-physical translation model;
- valid-failure versus invalid-experiment distinction;
- generalization from apparel to broader authorized physical-AI robustness studies.

This paper can describe implemented architecture before efficacy results exist. Physical performance remains **RESULTS PENDING**.

## Paper 1 — Predicting Cross-Model Transfer in Physical Adversarial Apparel

**Core question:** Which properties observable before held-out evaluation predict transfer to a fresh model generation?

Freeze per candidate before held-out access:

- surrogate mean / worst / disagreement;
- transform mean / worst / variance;
- spectral profile;
- camera/ISP margin when available;
- reference fidelity;
- printability;
- coverage/topology;
- objective and EOT configuration;
- artifact hash and source commit.

Append held-out outcome only after the generation closes. Minimum first analysis: three or more closed generations. Negative generations remain in the dataset.

## Paper 2 — Manufacturing-Calibrated Adversarial Textiles

**Core question:** Does measured digital→fabric→camera calibration improve physical robustness compared with generic EOT?

Arms:

A. baseline / minimal transforms  
B. heuristic EOT  
C. measured EOT  
D. measured EOT + physically survivable frequency constraint

Depends on the calibration target and first manufactured sample.

## Paper 3 — Garment Geometry, Coverage and Deformation

**Core question:** How much physical robustness is explained by texture, deformation fidelity and coverage topology?

Digital ladder:

flat → affine → TPS → cloth simulation

Coverage study:

fixed-area masks across torso / shoulder / sleeve / leg / coordinated-garment regions. Hold optimization budget constant.

## Paper 4 — Aging of Adversarial Apparel

Two independent axes:

- physical aging: W0 / W1 / W5 / W10 / later states;
- technological aging: fixed physical garment against later model generations.

Never reprint the garment when testing model aging; the physical artifact must remain fixed.

## Paper 5 — Objective and Surrogate Architecture Ablations

Compare equal-budget mean, min-max, CVaR and other preregistered objectives. Run leave-one-architecture-family-out surrogate experiments. Report both improvements and regressions.

## Foundation Paper 6 — Fail-Closed Evidence Certification for Physical-AI Experiments

**Manuscript:** `papers/06_FAIL_CLOSED_EVIDENCE_CERTIFICATION.md`

**Core question:** How can experimental AI infrastructure distinguish admissible evidence, valid negative results and invalid states while refusing silent provenance or numerical failures?

Primary contributions:

- fail-closed certification model;
- admissibility-before-performance ordering;
- failure-injection methodology;
- independent numerical verification;
- candidate/control pairing invariants;
- stale production-mapping detection;
- baseline preservation;
- sealed evidence releases.

This methods paper does not require a successful adversarial garment result.

## Common methodology requirements

Every experimental paper should include:

- threat model;
- evidence label;
- frozen model/threshold manifests;
- source commit;
- candidate hashes;
- matched controls where physically applicable;
- threshold curves where applicable;
- session-level statistical units for physical work;
- negative results;
- limitations against generalizing to arbitrary surveillance;
- reproducibility artifact inventory.

Foundation papers should additionally distinguish clearly between implemented software behavior and empirical efficacy.

## Immediate writing work

Complete now:

1. Introduction and literature positioning.
2. Research questions and hypotheses.
3. Methods / protocol.
4. Statistical analysis plan where applicable.
5. Reproducibility statement.
6. Ethics / public-interest framing.
7. Limitations.
8. Architecture and evidence-flow diagrams where applicable.

Leave Results, results-dependent Discussion and final empirical Conclusion explicitly marked **RESULTS PENDING** until experiments close.

## Publication discipline

A paper may say that a published study reported a result only when cited as an external observation. RAC-specific efficacy claims require RAC evidence. A D2/P1 FAIL is a result when the evidence contract is valid; an invalid experiment is a refusal, not a negative result.

These papers should be treated as research outputs of the RAC program, not marketing collateral.

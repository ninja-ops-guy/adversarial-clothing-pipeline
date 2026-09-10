# RAC Manuscript Workspace

**Status:** Pre-results manuscript series  
**Rule:** Methods may be completed before experiments. Results, Discussion and final Conclusions remain explicitly pending until the corresponding immutable RAC experiment releases exist.

## Literature foundation

- [Do Pattern Properties Predict Cross-Architecture Transfer in Physical Adversarial Textiles?](00_SYSTEMATIC_REVIEW.md) — structured 2017–2026 evidence review establishing the prospective property→transfer research gap, CAPGen baseline, Pattern Genome hypotheses, and replication requirements.

## Foundation papers

0. [RAC: A Reproducible Architecture for Physical Adversarial Textile Research](00_RAC_SYSTEM_ARCHITECTURE.md) — system topology, four-plane architecture, held-out trust boundary, provenance model and digital-to-physical research flow.
6. [Fail-Closed Evidence Certification for Physical-AI Experiments](06_FAIL_CLOSED_EVIDENCE_CERTIFICATION.md) — admissibility versus performance, refusal semantics, numerical verification, candidate/control integrity, stale-mapping detection and sealed evidence releases.

These two manuscripts explain **how the RAC research system works** independently from whether a particular adversarial garment succeeds.

## Experimental papers

1. [Prospective Cross-Model Transfer Prediction](01_TRANSFER_PREDICTION.md)
2. [Manufacturing-Calibrated Adversarial Textiles](02_MANUFACTURING_CALIBRATION.md)
3. [Garment Geometry, Coverage, and Deformation](03_GEOMETRY_COVERAGE_DEFORMATION.md)
4. [Physical and Technological Aging](04_AGING.md)
5. [Objective and Surrogate Architecture Ablations](05_OBJECTIVE_ABLATIONS.md)

## Suggested reading order

For a new technical reader:

1. `00_RAC_SYSTEM_ARCHITECTURE.md`
2. `../DIAGRAMS.md`
3. `../ARCHITECTURE.md`
4. `06_FAIL_CLOSED_EVIDENCE_CERTIFICATION.md`
5. `../CERTIFICATION_SYSTEM.md`
6. the experimental paper associated with the question being studied.

## Publication discipline

These manuscripts inherit the evidence rules in `PRODUCT_THESIS.md`, `PERPETUAL_IMPROVEMENT_MASTER.md`, `ENGINEERING_CONSTITUTION.md` and `RESEARCH_EVIDENCE_REGISTER.md`.

- External literature is described only under its reported conditions.
- RAC software capability is not RAC experimental evidence.
- D2/P1/M1 outcomes must come from frozen, hash-bound experiment releases.
- Negative results are retained.
- Held-out models may not be used to revise the candidate whose generation they evaluate.
- Physical claims require physical evidence.
- An invalid experiment is not reported as a negative result; certification must refuse it.

## Paper-state convention

Use explicit manuscript labels:

- **IMPLEMENTED METHOD** — supported by repository code or frozen protocol.
- **PUBLISHED OBSERVATION** — external evidence with citation.
- **RESULTS PENDING** — RAC outcome data not yet available.
- **INTERNALLY MEASURED** — allowed only when backed by a closed immutable RAC release.
- **LIMITATION** — bounded statement about what the present evidence cannot establish.

This keeps the paper series useful before physical trials without turning planned experiments into implied findings.

# Do Pattern Properties Predict Cross-Architecture Transfer in Physical Adversarial Textiles?

**Document type:** Systematic evidence review / literature foundation  
**Coverage:** 2017–2026  
**Status:** Literature-derived; RAC empirical property→transfer results remain **RESULTS PENDING**.

## Research question

Across published physical adversarial patch, camouflage-texture, and adversarial-garment research, which measurable pattern properties—spectral, topological, or colorimetric—have been tested as predictors of cross-architecture transfer, and what evidence shows that those properties generalize beyond the surrogate models used for optimization?

## Finding

The reviewed corpus did not identify a study that completes the chain:

**measured pattern property → quantitative transfer relationship → architecturally distinct held-out models → physical realization.**

The literature instead separates into three recurring forms:

1. **Transfer studies without property-level explanation.** Physical or digital transfer is measured, but the work does not identify which pattern characteristics predict success or failure.
2. **Property studies without transfer prediction.** Color, shape, entropy, heterogeneity, printability, or related characteristics are measured for fabrication, naturalness, attack geometry, or defense-side detection rather than as predictors of cross-architecture transfer.
3. **Partial bridge studies.** CAPGen is the closest identified prior art: it decomposes pattern structure from color and evaluates digital black-box transfer, but does not establish a parametric property→transfer map across physically realized, architecturally diverse held-out detectors.

Accordingly, RAC should treat its Pattern Genome and Heuristic Library as an **exploratory hypothesis-generation and measurement framework**, not as a confirmed transfer model.

## Scope and coding protocol

The review covers 20 representative works spanning the canonical adversarial-patch lineage, adversarial garments, vehicle camouflage, transfer-oriented ensemble attacks, and defense-side pattern-property measurement.

Each work is coded for:

- optimization surrogate(s);
- quantitative pattern-property analysis beyond attack success rate;
- evaluation on an architecture absent from the optimization loop;
- physical realization or physical-pipeline simulation;
- any reported quantitative property→transfer relationship.

“Transfer tested” requires a target architecture absent from optimization. “Property analysis” requires a quantitative or controlled-ablational treatment of a pattern characteristic rather than visual inspection.

## Evidence map

The corpus falls into four categories:

| Category | Count | Interpretation |
|---|---:|---|
| Transfer reported, no property analysis | 13 | Transfer is observed but not explained at the pattern-property level |
| Property analysis, no cross-architecture validation | 4 | Properties are measured for robustness, geometry, fabrication, or defense |
| Both, but partial | 1 | CAPGen bridges pattern/color decomposition and digital black-box transfer |
| Neither | 2 | Neither property analysis nor qualifying cross-architecture validation |

The load-bearing result is the absence of a paper reporting a statement of the form:

> **Property X predicts transfer by Y across Z architecturally distinct targets after physical realization.**

This is a literature-gap claim, not a RAC efficacy claim.

## Closest prior art: CAPGen

CAPGen is the most important baseline for RAC’s transfer-prediction work because it asks whether **pattern structure or color** contributes more to attack potency and includes a black-box transfer protocol.

RAC should extend that line of inquiry in three ways:

1. Replace the two-level pattern-vs-color factor with a **parametric Pattern Genome**.
2. Evaluate transfer on an **architecturally diverse held-out panel**, not only closely related detector families.
3. Test whether pre-held-out features predict **measured physical transfer deltas**, rather than only attack success on optimization/surrogate conditions.

Candidate genome families should initially include:

- spectral energy distribution and high-frequency ratio;
- dominant orientation;
- connected-component statistics;
- Euler characteristic / fragmentation;
- symmetry and motif repetition;
- CIELAB summary statistics and gamut descriptors;
- palette/color count;
- printability and minimum-feature-size measures.

These features are hypotheses. Their predictive validity must be established prospectively.

## Why this matters

Existing work demonstrates that physical adversarial patterns can behave differently across detector architectures. That creates the scientific question RAC should attack:

> **What measurable characteristics distinguish patterns that survive architecture changes and physical realization from patterns that merely overfit their surrogate ensemble?**

A cumulative property-level dataset would allow RAC to retain both successes and failures instead of discarding unsuccessful candidates. Over multiple preregistered sprints, this can turn candidate generation from repeated unconstrained search into evidence-guided exploration of a measured design space.

The expected scientific asset is therefore not merely a successful garment. It is a **transfer map** linking frozen pre-held-out pattern descriptors to later held-out and physical outcomes.

## Implications for the Pattern Genome

The Pattern Genome should be frozen before held-out evaluation and content-addressed alongside the candidate. A minimum record should bind:

- candidate SHA-256;
- genome schema/version;
- extractor source commit;
- runtime/environment hash;
- source experiment/generation;
- all finite feature values;
- evidence class;
- extraction timestamp.

The genome must not contain held-out outcomes. Outcomes are appended only after the relevant experimental boundary closes.

This separation permits prospective tests such as:

- Do spectral features predict held-out transfer after controlling for surrogate score?
- Does topology explain failures that surrogate mean cannot?
- Which features predict digital→physical degradation?
- Do transfer-predictive properties also make patterns easier for patch defenses to detect?
- Does the relationship replicate across later detector generations?

## Implications for the Heuristic Library

The Heuristic Library should be an append-only, cross-sprint registry joining:

**candidate → frozen genome → surrogate/transform telemetry → manufacturing profile → physical condition profile → held-out outcome → failure taxonomy.**

It should preserve negative results and distinguish at minimum:

- **SIMULATED** evidence;
- **INTERNALLY_MEASURED / MEASURED** evidence;
- physical condition profiles;
- model-family boundaries;
- superseded records without destructive overwrite.

The library must not promote a simulated association into a physical claim.

## Efficient experimental program

### Phase 1 — Instrument before optimizing harder

Implement the Pattern Genome and freeze it for every candidate that enters serious evaluation. Do this before accumulating P1 physical data so the first physical samples are prospectively characterized rather than retrospectively feature-mined.

### Phase 2 — Build the cumulative evidence store

Implement the Heuristic Library as an append-only content-addressed registry. Integrate the existing evidence classes, failure taxonomy, lineage contracts, and release machinery rather than creating a parallel trust system.

### Phase 3 — Add a transfer-screen experiment

For each candidate, compute a preregistered cross-surrogate robustness score and compare it against simpler baselines such as surrogate mean, worst-model score, disagreement, and CVaR. Do not assume a new score is superior; test whether it predicts later held-out outcomes.

### Phase 4 — Run a prospectively frozen Sprint 1

1. Generate a fixed candidate pool.
2. Freeze candidate identities and genomes.
3. Rank using surrogate-only information.
4. Downselect under frozen printability/manufacturing gates.
5. Manufacture the selected patterns plus matched controls.
6. Capture under a frozen physical condition matrix.
7. Evaluate on both surrogate and architecturally distinct held-out models.
8. Seal outcomes and append them to the library.
9. Retain failures.

### Phase 5 — Analyze prediction, not just attack rate

The primary scientific analysis should ask whether any frozen pre-held-out feature improves prediction of held-out/physical transfer over surrogate telemetry alone.

Start with interpretable statistics and regularized models. With a small corpus, avoid presenting a high-capacity predictor as evidence of generalization. Prefer effect sizes, uncertainty, leave-one-generation-out validation, and preregistered replication.

### Phase 6 — Replicate before claiming a transfer rule

Any discovered association should become a hypothesis for a later frozen generation. A property becomes a credible heuristic only after it predicts outcomes prospectively outside the data that suggested it.

## Critical methodological cautions

### Correlation is not mechanism

A genome feature can predict transfer without causing it. RAC should use “predictor” until an intervention or controlled ablation isolates a causal contribution.

### Do not hard-code speculative thresholds as facts

Values such as a high-frequency cutoff, color-count limit, or transfer-score threshold should be labeled engineering priors unless supported by manufacturing calibration or preregistered evidence. Thresholds discovered after observing outcomes require independent replication.

### Avoid pseudo-replication

Multiple frames of one garment/session are not necessarily independent experimental units. Physical papers should report session-, garment-, or condition-level structure explicitly.

### Preserve the held-out boundary

The Pattern Genome, ranking function, downselect, and candidate must be frozen before held-out access. Otherwise the library becomes a record of adaptive test-set optimization rather than transfer prediction.

### Defense-side symmetry

Properties associated with transfer may also be associated with adversarial-patch detectability. This is scientifically useful and should be measured rather than hidden.

## Positioning for the RAC paper series

The literature review supports a narrower and stronger contribution than “RAC finds better adversarial patterns.”

A defensible research framing is:

> **RAC prospectively measures whether pre-held-out properties of physically realizable adversarial textiles predict cross-architecture transfer, retains failures, and tests discovered associations in later frozen generations.**

This claim remains valuable whether the first predictors succeed or fail.

## Limitations

This review is a structured evidence review rather than a completed PRISMA-style systematic review. Exact quantitative values from individual papers should be verified against primary PDFs before final publication. Corpus coding should be independently checked before making priority or “first” claims in a peer-reviewed manuscript.

The review therefore supports the statement **“we did not identify prior work completing the property→physical cross-architecture transfer chain in the reviewed corpus”** more strongly than an absolute universal claim that no such work exists.

## Immediate implementation order

**Pattern Genome → Heuristic Library → prospective transfer-screen comparison → Sprint 1 with held-out architectures → property/outcome analysis → frozen replication.**

That sequence maximizes scientific information gained per manufactured sample while preserving RAC’s existing fail-closed evidence discipline.

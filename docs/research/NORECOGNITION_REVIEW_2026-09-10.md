# noRecognition review and RAC research integration

**Reviewed:** 2026-09-10  
**Status:** research review and proposed evaluation work; no new efficacy evidence  
**RAC source snapshot:** `2a8ea89d53e057f6e90fcb956ca1f9bc4bd8e1ea`  
**External repository snapshot:** `09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec`

## Decision

Incorporate the methodological lessons into RAC's evidence and reporting work. Prioritize the existing physical-validation critical path. Treat external outcomes as author-reported observations, requiring independent replication; do not import them into RAC performance totals.

This is a targeted review of the public README, persona documentation, license, current research/about pages, conference-slide text, and selected primary literature. It is not a reproduction, exhaustive source-code audit, or verification of the newer private research stack. Source publication versions differ, so historical and current numbers must remain separate.

## Addendum — learning from reported winners

**Added after user review, 2026-09-10. Implementation snapshot: `4d4719773cbcc6e4e61c23a7f79e22c288d8595a`.**

The original review underweighted positive findings. Reported winning candidates are useful research leads even when their generality remains uncertain. The next question is which capabilities RAC actually uses and which differences merit investigation.

### External leads

The [project's research narrative](https://sandbox.norecognition.org/about) reports multi-model winners, reuse of historical experiments, improved candidate ranking with persona context, and a transition from fixed recipes to a learned generator and reinforcement learning. These are architectural leads, not isolated causal demonstrations that each component produced the gains. The [current results](https://sandbox.norecognition.org/research) additionally make garment-specific outcomes visible. A successful garment/model combination remains informative even when it does not establish universal effectiveness.

### What RAC actually implements

This is a static review of code, configuration, workflow, and selected tests. Configured wiring is distinguished from a successful runtime measurement.

| Capability | Observed RAC implementation | Assessment |
| --- | --- | --- |
| Multi-model scoring | [model manifest](../../benchmarks/model_manifest.json) and [selection script](../../scripts/select_surrogate_candidate.py) configure six surrogate models and two separate held-out models for person detection. | Already wired into the configured selection workflow; this is not the same task panel as the external project. |
| Finite design families | [pool exporter](../../scripts/export_candidate_pool.js) enumerates style-profile families, variants, and seeds. The inspected manifest declares 100 candidates. | Current initial pool is procedural and predetermined. |
| Adaptation to environment | [adaptive script](../../scripts/adapt_surrogate_shortlist.py) extracts environment colors and evaluates a finite recoloring grid. | Already wired; does not train a persistent context-aware predictor. |
| Continuous optimization | [NAP](../../ruthless_pipeline/nap.py), [CAPGen-inspired module](../../ruthless_pipeline/capgen.py), and [optimizer namespace](../../ruthless_pipeline/optimization/optimizer.py) contain actual optimization implementations. | Present as components; it would be incorrect to describe the repository as only a procedural generator. |
| Which optimization path the workflow uses | [adaptive workflow](../../.github/workflows/adaptive-candidate.yml) invokes pool export, selection, and recoloring. | The inspected workflow does not invoke NAP training or CAPGen's gradient-based optimize method. Component availability is not workflow adoption. |
| Evolutionary search | [black-box backend](../../ruthless_pipeline/optimization/blackbox_backend.py) implements a seeded evolution strategy. | Partial conceptual overlap; not evidence of a learned, persistent breeding population or PPO policy. |
| Generative model prior | NAP offers an optional Diffusers image prior, with procedural initialization as the default. | An image prior exists; no learned generator trained on RAC experiment history was identified in the inspected workflow. |
| Active-learning label | NAP defines `ACTIVE_LEARNING`, but its optimization loop treats non-transfer modes through the same query-update branch. | The label does not establish a separate surrogate-fitting or uncertainty-learning system. |
| Context-aware prediction and historical learning | The inspected selection path stores results and provenance but contains no persistent predictor training stage. | Not established in this path. An evidence archive alone is not a learning system. |
| Cohort breadth | The inspected manifest explicitly uses a two-crop convenience fixture. | Useful for repeatable CI; not comparable to a broad wearer/garment research corpus. |
| Learned recipe composition | No sequence-trained recipe model was identified in the inspected generation/selection path. | Research candidate, not existing capability. |
| Garment rendering | [scene composer](../../ruthless_pipeline/scene.py) provides masked alpha composition and optional warped texture input. | A scene interface exists; its presence does not prove fidelity for every garment or material. |

The [NAP test](../../tests/test_nap.py) uses a synthetic image-mean objective. The [optimization integration tests](../../tests/optimization/test_optimization_integration.py) explicitly use synthetic fixtures. These demonstrate software behavior, not observed textile efficacy. No benchmark or training job was run for this review.

### Decisions to consider

1. **Prioritize a capability-to-evidence map.** For each existing approach, identify a retained result, exact entry point, dataset, and artifact. This will show whether a promising component has merely been written or has actually been evaluated.
2. **Prioritize cohort and context research.** RAC should investigate how garment, wearer, acquisition conditions, and existing visual features relate to observed outcomes. This is the strongest immediate conceptual gap in the inspected workflow. Environment recoloring only covers part of context.
3. **Consider retrospective predictive analysis.** Where enough comparable, independently usable observations exist, assess whether historical results contain predictive information beyond simple reference models. This establishes whether a learned representation is justified; it does not require adopting the external architecture.
4. **Keep learned generation and recipe-sequence models on the research shortlist.** They address representational limits that a finite pool does not address. They are not established upgrades until data sufficiency, prospective usefulness, and physical relevance are demonstrated.
5. **Defer choosing PPO or specialized hardware.** A reported winning system can contain many simultaneous changes. Current evidence does not isolate the learning algorithm from data, representation, rendering, or compute.
6. **Consider garment-specific hypotheses separately.** A useful result for one product need not work for every garment to deserve study. The present person-detection manifest should not be treated as evidence that face-recognition research is already implemented.

The practical correction is to give capability research an explicit place alongside evidence integrity. Preserve existing physical preparations while evaluating these research leads. The investigation should build on RAC's implemented components and keep adoption decisions tied to demonstrated usefulness.

**Scope:** documentation and static capability assessment only. No new training workflow, algorithm implementation, experiment execution, or efficacy claim is introduced.

---

## What the sources establish

### The public repository is historical

The [pinned README](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/README.md) declares the repository deprecated and points to the project website. It describes distributed evaluation, reproducible recipes, and multiple vision tasks. It does not establish that the public code reproduces the current website's results.

The [persona documentation](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/personas.md) describes six synthetic identities and controlled garment placements. Fixed fixtures improve repeatability; six generated identities cannot establish population representativeness, physical behavior, or demographic fairness. Repeated views of one identity are not independent participants.

### Current results have explicit limits

The [research page](https://sandbox.norecognition.org/research), reviewed on September 10, states that worn printed-fabric validation is pending, distinguishes printable from unconstrained digital conditions, and acknowledges selection on reused held-out identities. It distinguishes upstream detection failure from direct recognition failure. Its all-model coverage summary combines different garments, rather than demonstrating one universally effective garment.

There are also unresolved presentation inconsistencies: the gaiter table reports an F1 median of 58.3%, while nearby explanatory prose gives 87.5%; a curated F1 row pairs 86.0% with 8/10. These could reflect different subsets or stale text, but the page does not reconcile them. Do not repair or pool those figures by assumption.

**Interpretation:** useful methodological disclosures, with insufficient public evidence for a product-effectiveness claim or direct numerical comparison to RAC.

### Prediction quality is a different question from experimental evidence

The [about page](https://sandbox.norecognition.org/about) reports that broadly useful classifiers initially failed to rank elite candidates. It reports later gains after adding persona context, including historical outcome-derived features.

**Review inference, not an accusation:** the public narrative does not establish that every such feature was computed without evaluation-label leakage. RAC should require fold-local feature provenance before interpreting predictive correlations. Overall classification quality, ranking within a selected subset, and prospective accuracy answer different questions.


### User-supplied about-page snapshot

The supplied webarchive identifies its source as `https://sandbox.norecognition.org/about`. Archive SHA-256: `07f9794790950a636a5f0519fbe24e64d3e40d379b936378f5bef5d33d03149d`. It includes live-looking values alongside historical narrative. Its joint-success headline is 86.4%, while several individual-model rates are 0.0%. Those values cannot describe the same population and success event: a joint success rate cannot exceed any constituent success rate. Different run windows or denominators could explain the display, so classify this as unresolved scope rather than evidence of fabricated experiments. Preserve capture identity before comparing it with a newer page.

The archive also describes moving from fixed recipes to learned representations and reusing earlier experimental records. The transferable research questions are whether the representation limits what can be expressed, whether historical labels are comparable across versions, and whether complexity delivers prospective value. A larger search space does not establish physical realizability, and predictive association does not establish causal understanding. Preserve negative outcomes and source conditions when assembling any research corpus; count deduplicated observations separately from raw compute activity. These are research appraisal criteria, not an endorsement of the reported training architecture.

### Reuse boundary

The [pinned license](https://github.com/hevnsnt/norecognition/blob/09dbc4332fbb965991dfa0f5f8f1eaad1d0c12ec/LICENSE) is NRSAL v7.0. It expressly prohibits commercial use and includes provisions concerning generated outputs. Treat it as source-available with restrictions. This review imports no code, patterns, datasets, or outputs. Any later proposed reuse needs a separate permission review; the license's enforceability is not assessed here.

## Primary-literature cross-check

| Source | Review depth | Supported lesson | Limit |
| --- | --- | --- | --- |
| [Carlini et al., On Evaluating Adversarial Robustness, 2019](https://arxiv.org/html/1902.06705v2), sections 2.2 and 4.2 | Relevant full-text sections reviewed | Specify the evaluated capability, assumptions, baseline performance, and operating conditions. | A methodology paper does not validate either clothing project. |
| [Nakkiran and Błasiok, The Generic Holdout, 2018](https://arxiv.org/html/1809.05596v1), introduction and section 3 | Relevant full-text sections reviewed | Reusing evaluation feedback during adaptive research can invalidate naive holdout reasoning. Information exposure matters. | Its formal guarantees require its assumptions; a hidden label or an immutable hash alone supplies no such guarantee. |
| [Xu et al., Adversarial T-shirt, 2019 preprint](https://arxiv.org/abs/1910.11099) | Abstract only | Physical deformation and differences between digital and physical outcomes have prior research precedent. | Reading-queue entry only; no implementation choice or new numerical RAC claim rests on this abstract. |

The [conference slides](https://sandbox.norecognition.org/defcon-slides.pdf), especially slides 15 and 34 using zero-based PDF pages, provide additional task separation and evidence-scope context. Extracted slide text was reviewed; the talk video and demonstrations were not independently verified. A conference presentation is not equivalent to independent experimental replication.

## Reconciliation with RAC

Paths below were inspected at the RAC snapshot above. Schema or module presence is not a claim that every consumer enforces it.

| Concern | Existing RAC surface | Integration decision |
| --- | --- | --- |
| Identity and calibration separation | [cohort sealing](../../ruthless_pipeline/governance/seal.py), [sentinel governance](../../ruthless_pipeline/governance/sentinel.py) | Audit evaluation-access history and derived-feature lineage around these mechanisms. |
| Matched-property comparisons | [matched-null schema](../../schemas/ctm_matched_null_v1.schema.json), [CTM lessons](CTM_LESSONS_AND_SPEC_PROPOSALS.md) | Preserve existing controls; check that reports distinguish coverage controls from property-matched nulls. |
| Task-specific interpretation | [claim-scope schema](../../schemas/ctm_claim_scope_v1.schema.json) | Check downstream-skipped outcomes and shared-event counting in reports. |
| Citation provenance | [citation schema](../../schemas/ctm_citation_v1.schema.json) | Keep external observations and review depth explicit; do not label a page review as reproduction. |
| Physical claims | [project status](../PROJECT_STATUS.md), [technical roadmap](../RAC_TECHNICAL_ROADMAP.md) | Keep artifact, simulation, capture, and manufacturing evidence distinct. |
| Cumulative research planning | [CTM lessons](CTM_LESSONS_AND_SPEC_PROPOSALS.md), [governance roadmap](../experimental_governance/ROADMAP.md) | Add bounded acceptance checks; preserve frozen schemas and existing experiment gates. |

## Proposed acceptance checks

These are prospective requirements to audit and implement where missing, not claims of existing defects. Start by verifying each requirement against current code and tests. Reuse an existing implementation when it satisfies the requirement.

### NR-01 — Evaluation exposure and feature provenance

Maintain separate discovery, selection, and confirmation roles. Record which outputs from each cohort were available before each decision, including dashboard feedback and outcome-derived covariates. Fit preprocessing and historical summaries only on permitted data; bind their source cohorts and versions to the existing seal.

**Acceptance:** a fixture in which an evaluation result influences later candidate selection cannot produce an independent-confirmation label for that same cohort. A feature computed from prohibited outcome labels fails provenance review. Identity disjointness and calibration isolation remain necessary but distinct checks. Any multiple-testing or sequential policy must be declared before use.

**Basis:** Generic Holdout; RAC sealing and sentinel boundaries.

### NR-02 — Observation medium and production provenance

Every report should identify whether evidence came from image compositing, a display photographed by a camera, printed flat material, or worn fabric. Record the production profile, actual specimen and capture references where applicable. A simulated rendering operation needs a physical interpretation before its output supports a manufacturing assumption.

**Acceptance:** synthetic fixture evidence and photographed-display evidence cannot promote a worn-fabric claim. Unknown material or capture fields stay unknown. A change in rendering assumptions creates a versioned comparison rather than rewriting old results.

**Basis:** RAC's existing digital/physical evidence separation and production roadmap.

### NR-03 — Controls and interpretable comparisons

For future approved protocols, document the estimand for each control: ordinary garment, equivalent coverage, or matched visual property. Keep garment geometry and acquisition conditions paired where the protocol calls for pairing. A blank control addresses coverage; it does not isolate every visual property.

**Acceptance:** the report names the control and effect definition. Missing pairs, exclusions, and baseline-ineligible observations remain visible. Report uncertainty using the actual independent unit; repeated frames must not silently inflate participant counts. Existing frozen experiments require their normal amendment process.

**Basis:** RAC matched-null and swap-validity contracts.

### NR-04 — Stage outcomes and denominator integrity

Distinguish direct stage measurements, upstream-dependent outcomes, and stages that were not evaluated. A missing input to recognition is not a measured recognition score. Preserve end-to-end outcomes separately from conditional stage outcomes.

**Acceptance:** one upstream failure cannot be counted as two independent successes; a skipped stage cannot receive a fabricated numeric result. A multi-model summary identifies whether the same specimen, cohort, and conditions were shared. Confidence changes and discrete task outcomes retain separate fields.

**Basis:** RAC claim-scope contract and task-specific evaluation principles.

### NR-05 — Reports derived from one evidence snapshot

Generate tables, narrative summaries, and counts from the same versioned evidence view. Display numerator, denominator, eligibility rules, cohort, specimen, measurement medium, metric definition, and source version. Separate evaluations, independent participants, experimental runs, and retained observations.

**Acceptance:** inconsistent fractions and percentages fail a report check; differing aggregation methods require explicit labels. Selected-best results retain selection history. Median results improve description but do not erase selection bias. External observations never enter internal totals.

**Basis:** RAC evidence-register rules and the existing report-compilation architecture.

### NR-06 — Prediction audit before interpretation

If a prospective study evaluates a predictor, separate overall discrimination, calibration, and within-subset ranking. Include a simple reference model and prespecify the comparison. Outcome-derived covariates require documented permitted-data provenance.

**Acceptance:** an impressive overall score alone cannot support a ranking or mechanism claim. Unknown feature lineage marks the result uninterpretable for confirmation. This is an evaluation requirement, not a proposal to add or tune an optimizer.

**Basis:** RAC scalar typing, citation discipline, and independent-confirmation principles.

## Sequence and completion criteria

| Pass | Work | Exit | Priority |
| --- | --- | --- | --- |
| A | Audit NR-01, NR-04, NR-05 against present validators/exporters; implement only confirmed gaps. | Focused synthetic checks for reused evaluation feedback, skipped-stage accounting, and inconsistent summaries. | Before the next affected confirmatory report. |
| B | Reconcile NR-02 and NR-03 with the existing capture/readiness packet. | Evidence-medium labels and control estimands explicitly mapped to existing contracts. | Alongside physical readiness; preserve its critical path. |
| C | Evaluate NR-06 only when a predictor study is proposed; finish the physical-paper full-text review. | Prospective analysis plan and source-verification record. | Deferred; does not block specimen procurement or capture preparation. |

No scheduling promise or new gate closure is made here. These passes do not authorize experiment execution, purchases, new certification, or changes to frozen D2/CTM/governance artifacts.

## Review checklist

- [x] Follow deprecated repository to current research sources.
- [x] Identify source versions, review depth, and unresolved discrepancies.
- [x] Inspect existing RAC interfaces before proposing additions.
- [x] Record independent-implementation and evidence boundaries.
- [x] Add bounded work to the research roadmap.
- [ ] Audit all relevant runtime consumers and existing tests.
- [ ] Implement confirmed evaluation/reporting gaps.
- [ ] Verify the physical-paper full text before using it as a load-bearing source.
- [ ] Obtain prospective physical evidence under the approved RAC protocol.

**Recommendation:** RAC's next persuasive milestone remains a well-documented physical result, including an honest negative result. The useful research investment is making that result interpretable and independently checkable.

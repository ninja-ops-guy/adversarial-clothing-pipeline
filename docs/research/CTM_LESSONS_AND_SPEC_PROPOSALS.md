# CTM Lessons Learned & Spec Proposals — Program Hardening Register

**Status:** living register. **Scope:** CTM (Cumulative Transfer Map) subsystem within RAC. **Source:** eight rounds of adversarial review of the transfer-map research program (literature claim → map design → repo gap analysis → external challenges → vulnerability taxonomies → cascade analysis → survey stack → impact curation), each of which surfaced a distinct failure mode and each converted here into a mechanical guard.

Every spec below is additive, consistent with the frozen six-wave CTM build order, and designed to make the *class* of error a structural failure rather than a remembered caution. No spec modifies existing scientific content, thresholds, gate parameters, or D2-0004/D2-0005 artifacts.

---

## Part 1 — Lessons Learned

### L1. Universal negatives need corpus-bounded language, always

"Survives systematic verification" overstated what a 20-paper coded corpus can establish about a field-wide negative spanning 2017–2026. A near-miss (arXiv 2606.17711, adversarial Voronoi camouflage) surfaced in minutes of targeted searching. The claim itself survived — none of the newly found papers (Voronoi, MVPatch, AdvART) enters the property-analysis × cross-architecture-validation quadrant — but the epistemic wrapper was wrong. **Rule:** every negative claim carries its corpus scope in the sentence ("in a coded corpus of N papers…"), never bare universal quantification.

### L2. Factor-swap validity depends on the optimizer's constraint structure

The program's most important scientific lesson, learned by being wrong. Voronoi's "repainting with different palettes largely nullifies the effect" (arXiv 2606.17711 abstract, verbatim, primary-source verified) first read as an empirical contradiction with CAPGen's pattern-dominance finding. Correct reading: Voronoi optimizes seed locations under a *hard palette constraint* — repainting invalidates the optimization rather than measuring a property, while CAPGen varies color within the optimization neighborhood. A main-effect probe and an out-of-optimum swap answer different questions. **Generalized:** a decomposition experiment is interpretable only if the swapped factor's relationship to the optimization constraint set is recorded. The literature has no vocabulary for this; CTM supplies one (SPEC-1).

### L3. Epistemic classes must stay distinct at the sentence level

Voronoi's ≤0.17 is an optimization-perturbation tolerance; MVPatch's transferability score is an evaluation metric; a genome feature is a measured property. All are scalars; all are different kinds of thing. A tolerance cannot be a predictor; a metric cannot be a cause (SPEC-2).

### L4. Imposed structure is not measured structure — record both

The field *imposes* spectral structure constantly (total-variation loss is a low-pass constraint since Sharif 2016; TC-EGA toroidal cropping is a periodicity intervention in spatial language) while *measuring* it never. Genome extraction measures realized structure; optimizer-imposed constraints are a separate, unrecorded causal channel (SPEC-5).

### L5. Verification before amplification

A proposed paper framing ("resolve CAPGen vs. Voronoi") rested on a single abstract quote and collapsed under one primary-source check of the parameterization. A citation whose basis is abstract-only must be labeled as such; no framing decision may rest on it (SPEC-6).

### L6. Convergence on the near-miss space raises urgency, not doubt

Two independent groups (CAPGen; Voronoi) produced factorial pattern/color decompositions failing on the same two axes (digital-only, surrogate/single-family-bound). The gap is being actively colonized — which strengthens the case for publishing schema, null definitions, firewall, and promotion rules *before* results.

### L7. Mathematical novelty for textiles lives in the nuisance operators, not the loss

The mathematics specific to clothing is two objects: the deformation group and the rendering/coarsening operator. Everything genuinely new is a statement about what is invariant under those two operators. The field spent a decade making patterns robust *to* deformation; the open frontier is moving the adversarial signal into a subspace where deformation is not a threat (topological invariants under isotopy, near-fixed-points of coarsening, group-risk objectives over the transformation distribution). **Rule:** proposed attack innovations are classified by which nuisance operator they address; proposals addressing neither are out of scope.

### L8. A novelty claim is a lead to kill, not an assertion — including our own

Model discipline: falsification searches on one's own headline novelty claims before asserting them, with search depth reported honestly. Base-rate observation from this program: "nobody has done this" has been wrong in both directions.

### L9. Pre-registered kill-criteria are the cheapest scientific instrument available

Four candidate predictors (harmonic truncation order, description length, group-risk objective value, persistence statistics) are computable on published pattern images regressed against published transfer numbers — no fabrication, no training — with an explicit stopping rule: if none predicts transfer beyond a single luminance-spectrum scalar, the map is one row plus noise and the program should rescope. A platform that cannot be cheaply killed will be expensively killed (SPEC-7).

### L10. The channel confound: "transfer failure" is often a camera, not an architecture

Phan et al. (CVPR 2021): ISPs destroy, introduce, or amplify adversarial content non-linearly and per-vendor; CAP (NeurIPS 2024) makes it a min-max game over ISP parameters. In essentially every published physical study, camera hardware is confounded with architecture; a reported YOLO→SSD transfer failure may be the second camera's denoiser. Quantization, chroma subsampling, and H.264/HEVC rate control discard exactly the high-frequency content many attacks carry. A transfer cell without channel identity is an unidentifiable mixture (SPEC-10).

### L11. Exploit invariants of the task, not accidents of the architecture

Two independent vulnerability taxonomies derived the same split: high-transfer surfaces are properties of what the model was trained to do (thresholded box emission, texture/luminance reliance, temporal association); low-transfer surfaces are architectural accidents (NMS internals, anchor layout, token grids). Sharpest example: NMS is untrained and non-differentiable; NMS-free heads (DETR-family, YOLOv10+) have no such surface — a better mechanistic explanation of transfer breaks than family coding (SPEC-11).

### L12. An outcome-maximizing generator discovers the evaluation's weaknesses before the model's

The most reliably exploitable surface is the evaluation itself: arbitrary confidence thresholds (ASR is not comparable across papers), single-frame evaluation, surrogate-bound panels. This is Goodhart's law in adversarial-ML form and the deepest justification for the anti-optimization invariant: the invariant now has a stated adversary. Decision thresholds are part of target identity; threshold sweeps belong in the condition grid (SPEC-12).

### L13. The identity cascade: "detection" is one stage, and the corpus conflates stages

Deployed identification is a cascade (person detection → face detection → face recognition → Re-ID/gait fallback), each stage a different system with different surfaces and transfer behavior. FR results recapitulate the detection thread: margin attacks on cosine similarity, region-placement dominance (AdvHat), symmetry constraints raising ASR 65.4%→80.7% (GaP), ViTs more robust than CNNs with ViT transfer untested. A garment suppressing person detection while leaving the face visible is a partial win; scope statements must name the stage. The FR field's own consensus — "no two papers' physical conditions are comparable" — is independent cross-domain confirmation of CTM's premise (SPEC-13).

### L14. The survey layer exists to prevent foundation errors, not to be cited

Two of the program's prior errors were survey-catchable foundation errors (the "invisibility" framing; the unbounded universal negative — the 129-ref FR survey already tracks transferability as *the* open challenge). **Rule:** before corpus coding or novelty claims in an adjacent subfield, the most recent high-quality survey is read first and its taxonomy structures the corpus (SPEC-15).

### L15. Foundational papers are load-bearing in both directions

Sharif et al. 2016 anchors three independent threads (NPS colorimetry; foundational physical FR attack; the physical-realizability claim). Misread a foundational paper and every downstream claim inherits the misreading. **Rule:** the foundational set (Sharif 2016, Brown 2017, Athalye 2018, Demontis 2019) receives full-text verification before any claim rests on it (SPEC-6 hard precondition).

### L16. Success axes are orthogonal — and only one of them is CTM's

Scientific impact (Fawkes), physical effectiveness (Zhang et al. 2025 — one garment defeats nine defenses), public usability (Fawkes/Glaze apps), and policy impact (Gender Shades — corporate discontinuations and municipal bans with zero adversarial content) do not correlate. CTM's axis is measurement infrastructure (analogues: NIST FRVT, RobustBench), which accrues impact by being load-bearing for everyone else's claims. The paper must say so explicitly rather than implying attack-superiority framing (SPEC-18).

### L17. Public artifacts are a citation and correction engine, not a courtesy

Every high-follow-up entry ships something usable. Public code makes a result correctable and extensible by strangers — the mechanism behind both follow-up work and honest failure cascades (Hönig et al.'s Glaze break was possible because Glaze was available to break). AdvT-shirt-1K is the only physical, fabricated, multi-image dataset in the program's corpus — an external validation set for CTM's physical tier (SPEC-16). **Rule:** the registry is designed so that falsifying a CTM heuristic is a supported, schema-valid operation.

### L18. Brittleness is symmetric; defense-side brittleness is a measurement finding

Zhang et al. (nine defenses validated at patch scale collapse at garment scale — a spatial-extent × frequency, genome-expressible mechanism) plus the Glaze break: attacks and defenses are both more brittle than either side admits. Defense-failure modes are property-attributable measurements with the same cumulative structure as attack-transfer modes (SPEC-17).

---

## Part 2 — Spec Proposals (additive; wave-mapped)

### SPEC-1 — Factor-swap validity contract (CTM-A schema → CTM-C null registry → CTM-F pooling)

**Lesson:** L2. Every matched-null record carries:

```json
"swap_validity": {
  "varied_factor": "topology",
  "held_factors": ["color"],
  "held_factor_in_optimization_constraints": true,
  "swap_scope": "within_optimization_neighborhood | out_of_optimum | reoptimized",
  "constraint_set_ref": "sha256 of optimizer config",
  "interpretation_class": "main_effect_probe | interaction_probe | invalidation_test"
}
```

`interpretation_class` is derived, never user-asserted: `out_of_optimum` swaps can only label `invalidation_test`. CTM-F refuses to pool `invalidation_test` rows with `main_effect_probe` rows.

### SPEC-2 — Scalar-class typing (CTM-A enum → CTM-D tensor validation)

**Lesson:** L3. Required `scalar_class` enum — `pattern_feature | evaluation_metric | perturbation_tolerance | effect_size | covariate` — on every quantitative value entering the tensor and heuristic registry. Cross-class relational claims fail schema validation.

### SPEC-3 — Corpus-bounded-claim linter (extends `doc_lint.py`)

**Lesson:** L1. Universal-negative patterns ("no paper has", "nobody has measured", "the first") in `manuscript/` must co-occur with a corpus-scope qualifier and a citation to the corpus artifact. Violations fail lint unless allowlisted with stated reason.

### SPEC-4 — Living-corpus registry (`ctm_registry/literature/`)

**Lessons:** L1/L6. Versioned registry of near-miss and boundary papers (Voronoi 2606.17711, MVPatch, AdvART, CAPGen, Zhang 2510.17322, GaP, AdvHat as seeds), each with quadrant classification, failure axes, verification status, re-check date. Snapshot history makes gap-colonization a measurable trend; manuscript claims cite registry snapshots.

### SPEC-5 — Imposed-structure provenance (CTM-B adapter extension)

**Lesson:** L4. Candidate provenance gains an `optimizer_constraints` block (active regularizers, structural constraints — tileability, palette fixing, symmetry enforcement — with parameters). Genome schema itself stays frozen. CTM-F can then test "imposed vs. emergent structure" as a covariate.

### SPEC-6 — Citation verification status (extends citation/evidence matrix)

**Lesson:** L5/L15. Every citation carries `verification_status: abstract_only | full_text_verified | reproduced_internally`. The manuscript exporter refuses (fail-closed) to let a load-bearing claim cite an `abstract_only` source; foundational papers (L15) require `full_text_verified`.

### SPEC-7 — Retrospective property-mining kill-gate (pre-CTM-E; `cumulative_map/retro_mining/`)

**Lesson:** L9. Computes four cheap predictors (harmonic truncation retained-energy curves; description-length proxies, full-color and luminance-only; group-risk objective values under the registered transform sweep; persistence-diagram summaries) on published pattern images, regresses each against published cross-architecture transfer deltas with SPEC-2 multiple-testing discipline and a luminance-contrast control, and emits a sealed CONTINUE / STOP-RESCOPE report. The only CTM component designed to potentially end the program — which is why it goes first.

### SPEC-8 — Invariance-class genome v2 candidate register

**Lesson:** L7. Genome v1 stays frozen; a v2 candidate register lists invariance-class features (persistence-landscape norms, multi-scale energy-decay exponents, harmonic-order curves, description-length proxies), each with feature definition, invariance claim (deformation group / coarsening operator / both), computability cost, and SPEC-7 dependency. Prevents invariance enthusiasm from mutating the frozen schema prematurely.

### SPEC-9 — Defense-dual tracking (heuristic registry extension)

**Lesson:** L7/L18. Each heuristic entry gains `defense_dual: {principle, certification_form, status}`. When an attack-side heuristic is REJECTED or shows high heterogeneity, the defense dual is evaluated before archival.

### SPEC-10 — Camera/ISP identity as a first-class channel factor (CTM-A → CTM-C)

**Lessons:** L10/L12. Channel contract gains an ISP block (`camera_model, isp_pipeline_id, raw_available, codec {format, bitrate_class}, differentiable_isp_proxy_ref`). Rules: physical-tier transfer records without camera identity auto-classify CHANNEL-C; the digital tier offers ≥2 distinct ISP-proxy variants; cross-camera replication is a promotion precondition for PHYSICAL_REPLICATED.

### SPEC-11 — Mechanism-class tagging and head-class panel axis (CTM-A → CTM-C → CTM-F)

**Lesson:** L11. (a) `mechanism_class: task_invariant | training_data | pipeline_structure | physics | hardware | architecture_accident` required on heuristic entries; (b) `head_class: nms_based | nms_free` and `threshold_config_sha256` added to target identity; (c) CTM-F reports associations stratified by head class — accident-bound heuristics are labeled as such, with lower expected generality.

### SPEC-12 — Evaluation-surface audit block (CTM-D manifest)

**Lesson:** L12. Every experiment manifest records thresholds used (swept or fixed), frames-per-sample, firewall attestation, and a `goodhart_guard` field naming which evaluation choices candidate selection could have implicitly optimized against. Gives meta-analysis the covariates to test whether effects cluster by threshold choice rather than pattern property.

### SPEC-13 — Cascade-stage scope labels (CTM-A enum + manuscript linter rule)

**Lesson:** L13. `pipeline_stage: person_detection | face_detection | face_recognition | reid_tracking | fusion` on claim artifacts; claims using "invisibility"/"evasion"/"surveillance" without a stage label fail lint. FR boundary papers (GaP, AdvHat) enter the living corpus.

### SPEC-14 — FR-adjacency genome v2 candidates (SPEC-8 extension)

**Lessons:** L13/L15. Four register candidates with measured published effects: (1) landmark-relative placement descriptors (AdvHat: position/size dominate physical success); (2) symmetry-enforcement deltas (GaP: 65.4%→80.7% ASR) — also a matched-null axis for SPEC-1; (3) landmark-region energy density (DiffAM/PeopleTec); (4) similarity-margin outcomes for FR-adjacent targets — continuous margin shift, not binary threshold crossing. All gated on SPEC-7; all require full-text verification (L15) before promotion from candidate.

### SPEC-15 — Survey-seeded taxonomy bootstrap (SPEC-4 extension)

**Lesson:** L14. Registry category scheme seeded from survey taxonomies (Wang et al. Neurocomputing 2026 FR survey; ACM CSUR 2026 physical-world survey); each entry records its taxonomy node; new survey editions diff mechanically against registry coverage.

### SPEC-16 — AdvT-shirt-1K external-validation adapter (CTM-C; feeds SPEC-7)

**Lesson:** L17. Adapter ingesting the public 1000+ real-image physical dataset: genome extraction per image (v1 schema, external-artifact evidence class), dataset provenance/license in the corpus registry. Gives SPEC-7 a physical cohort alongside digital masters — a preview of fabrication-delta analysis on external data at zero fabrication cost.

### SPEC-17 — Defense-side tensor with brittleness metrics (CTM-D schema → CTM-C panel)

**Lesson:** L18. Defended model variants register as first-class panel members; cells record ASR-under-defense vs. undefended deltas and patch-scale vs. garment-scale success (the Zhang mechanism). "Which genome properties defeat which defense classes" becomes a queryable question with attack-side evidence discipline.

### SPEC-18 — Impact-axis declaration (manuscript front matter, fail-closed)

**Lesson:** L16. Required `positioning` block: which success axis the paper competes on (measurement infrastructure), which it disclaims (attack superiority — Zhang; policy — Gender Shades; consumer usability — Fawkes), naming the strongest existing result on each disclaimed axis. Exporter refuses if absent.

---

## Part 3 — Sequencing against the frozen wave order

| Spec | Wave | Effort | Blocking condition |
|---|---|---|---|
| SPEC-1 swap-validity contract | CTM-A → CTM-C → CTM-F | Small | Before matched-null construction (CTM-C close) |
| SPEC-2 scalar-class typing | CTM-A → CTM-D | Small | Before tensor ingestion |
| SPEC-3 claim linter | Any | Small | None |
| SPEC-4 living corpus | Any | Small + recurring | Before manuscript submission |
| SPEC-5 imposed-structure provenance | CTM-B | Small | Before Sprint 001 generation |
| SPEC-6 citation verification | Any | Small | Before next manuscript export |
| SPEC-7 retrospective mining | **Pre-CTM-E gate** | Days–weeks | Gates Sprint 001 fabrication budget and CTM-F justification |
| SPEC-8 v2 candidate register | CTM-A (format) | Small | Contents depend on SPEC-7 |
| SPEC-9 defense-dual field | CTM-F | Small | Before first heuristic promotion |
| SPEC-10 ISP/camera channel factor | CTM-A → CTM-C | Small schema; medium proxy integration | Before ANY physical-tier claim; ≥2 ISP proxies before camera-confounded interpretations |
| SPEC-11 mechanism/head-class tagging | CTM-A → CTM-C → CTM-F | Small | Before first attribution report |
| SPEC-12 evaluation-surface audit | CTM-D | Small | Before Sprint 001 manifest lock |
| SPEC-13 cascade-stage labels | CTM-A + linter | Small | Before next manuscript export |
| SPEC-14 FR-adjacency v2 candidates | SPEC-8 register | Small per feature | Frozen until SPEC-7 reports |
| SPEC-15 survey-seeded taxonomy | SPEC-4 bootstrap | Small | Before registry goes public |
| SPEC-16 AdvT-shirt-1K adapter | CTM-C; feeds SPEC-7 | Small | Before SPEC-7 report |
| SPEC-17 defense-side tensor | CTM-D → CTM-C | Small schema; panel expansion is the cost | Before any defense-related claim |
| SPEC-18 positioning block | Manuscript workspace | Trivial | Before next manuscript export |

**Program-level note:** SPECs 1, 2, and 5 gate Sprint 001's *interpretability*, not its executability — without them the sprint runs but its rows cannot support the level-3 controlled-effect claim the program exists to reach. SPEC-7 gates the program itself.

---

*Register compiled from eight adversarial-review rounds. Each lesson names the error instance it generalizes; each spec is designed so the error class becomes a mechanical failure rather than a remembered caution.*

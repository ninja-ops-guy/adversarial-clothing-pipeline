# Preregistration — RAC-PER-D2-0007: Motif Screening and Anchor-Abstracted Person-Detection Evasion

**Status:** PREREGISTERED — **NOT_ARMED** (frozen at commit time of this document; nothing in this generation is armed, executed, or trigger-wired).
**Generation:** RAC-PER-D2-0007 (fresh prospective lineage; hypothesis-screening generation).
**Arming:** **NOT_ARMED.** This document and `generations/RAC-PER-D2-0007.json` are a declaration only. No CI trigger is wired for D2-0007; arming requires a separate, reviewed change after the preregistered freeze and rehearsal gates.
**Lineage independence:** D2-0003 and D2-0004 remain immutable negative-result generations and are inputs to hypothesis formation only. D2-0005 is untouched: it stays PREREGISTERED/unarmed under its own frozen amendment A5 and is not modified, superseded, or depended upon by this generation. D2-0006 remains interpretation-policy only. RAC-PRINT-ALPHA-001 remains permanently bound to the D2-0003 specimen.
**Protocol:** `protocols/RAC-PERSON-DETECT-1.2.json` (RAC-PERSON-DETECT-1.2).
**Model sets:** development/surrogate only — `PERSON-SUR-v3` (6 models: yolov8n, fasterrcnn_mobilenet_v3_320, detr_resnet50, ssdlite320_mobilenet_v3, retinanet_resnet50_fpn_v2, fcos_resnet50_fpn). The held-out set `PERSON-HO-v3` is referenced **by hash-reference only** (`model_sets/PERSON-HO-v3.json`, sha256 pinned in `benchmarks/frozen_surface_sha256.json`: `ad1127659a5615871ff320056415dd3c8e8b6a27acef7c6a3bcc4a96e713495e`); it is never accessed, enumerated, or inferred against during any stage of this generation except the single terminal held-out evaluation (§8).
**Generation skeleton:** `generations/RAC-PER-D2-0007.json` (frozen, `lock_status: PREREGISTERED`, `armed: false`, `lock_inference_performed: false`, trigger fields present but NOT armed).

---

## 1. Purpose and hypotheses

D2-0003/D2-0004 established that the D2-0003 specimen class does not transfer to fresh held-out whole-person detector architectures. D2-0007 is a fresh prospective lineage that asks a narrower, screened question:

- **H1 (screening hypothesis, falsifiable):** within the frozen candidate-generation pool (§2), at least one motif family shows a **useful surrogate-only signal** against whole-person detection — defined exactly by the screening decision rule in §5 — sufficient to justify building a minimum viable anchor abstraction and governed optimization for that motif family only.
- **H0 (null):** no motif family in the frozen pool meets the screening decision rule. In this case **no adapter is built, no optimization is opened, and the generation closes as a screened-out null datapoint.**

**Motif screening is hypothesis screening, never evidence promotion.** Screening outcomes are computed exclusively on development/surrogate surfaces. A screening "signal" licenses only the *next engineering stage* (anchor abstraction, then governed optimization); it is not, and must never be reported as, evidence of held-out transfer, effectiveness, or evasion capability. If a face-derived motif (e.g., SaliencyEyeAttack-family compositions) shows no useful signal against whole-person detection on surrogate surfaces, **no adapter gets built** for it. Screening results carry the evidence label `target` (pre-execution hypotheses) and, once closed, `internally_measured` surrogate-only observations explicitly scoped "surrogate-only, hypothesis-screening, not transfer evidence."

---

## 2. Candidate-generation pool (frozen at preregistration)

The generator inventory below was taken from the repository at preregistration time (`ruthless_pipeline/patterns/__init__.py::P0_GENERATORS`). Every named generator either exists in the repo at freeze or is explicitly declared `EXTERNAL_NOT_YET_PRESENT` with an adapter gate; nothing is pretended to exist.

| Generator | Repo status at freeze | Anchor dependence | Screening role |
|---|---|---|---|
| `SaliencyEyeAttackGenerator` | PRESENT (`ruthless_pipeline/patterns/__init__.py`) | face-landmark-derived | in fixed screening set |
| `FeatureCollageGenerator` | PRESENT (`ruthless_pipeline/patterns/__init__.py`) | anchor-independent core (collage statistics not bound to any declared anchor capability) | in fixed screening set |
| `HyperfaceLikeGenerator` | PRESENT | face-landmark-derived | in fixed screening set |
| `DazzleSurgicalLinesGenerator` | PRESENT | face-landmark-derived | in fixed screening set |
| `KeyFeatureBlackoutGenerator` | PRESENT | face-landmark-derived | in fixed screening set |
| `AdversarialPatchGenerator` | PRESENT | landmark-anchored patch placement | in fixed screening set |
| `SwappedLandmarksGenerator` | PRESENT | face-landmark-derived | in fixed screening set |
| `LandmarkNoiseGenerator` | PRESENT | face-landmark-derived | in fixed screening set |

The fixed generator set for screening is exactly the `P0_GENERATORS` tuple above — i.e., `{SaliencyEyeAttack, anchor-independent FeatureCollage core, plus all other PATTERNS generators present in the repo at freeze}`. No generator may be added to or removed from the screening set after freeze except via a hash-committed amendment made before any screening execution.

**External generators:** any generator named in future discussion but not present in the repo at freeze is declared `EXTERNAL_NOT_YET_PRESENT` and is gated: it may enter the pool only through (a) a reviewed adapter implementation with unit tests, and (b) a hash-committed amendment to this preregistration, both completed **before** any screening execution that would include it. No external generator is in the frozen screening set.

---

## 3. Anchor capability vocabulary and provider governance

### 3.1 Capability vocabulary (declared, closed, not a pose framework)

The only anchor capabilities this generation may use are:

1. `torso_region` — coarse torso bounding region on the person crop.
2. `shoulder_axis` — the left-right shoulder line (two endpoints, one orientation).
3. `silhouette_mask` — binary person silhouette mask over the crop.
4. `panel_region` — a named garment-panel sub-region within `silhouette_mask`.
5. `bounding_region` (optional, generic) — an axis-aligned rectangle; used only when no more specific capability applies.

This vocabulary is intentionally small and declared. It is **not** a pose-estimation framework: no keypoint graph, no limb model, no identity or gaze information is introduced. Any capability beyond this list requires a hash-committed amendment before use.

### 3.2 Provider governance (preregistered)

Every anchor provider used at any stage must be declared in the preregistration/freeze record with: **provider identity** (name), **version/hash** (exact version string and content hash of the provider artifact or template), **configuration** (complete parameter set), **coordinate convention** (origin, axis directions, normalization, units — fixed per provider), **confidence handling** (threshold, fallback behavior on low confidence, and whether confidence is exposed downstream), and **permitted data exposure** (exactly which anchor outputs may cross stage boundaries — e.g., coordinates only, never source imagery). The additive machine-readable contract is `schemas/d2007_anchor_provider_v1.schema.json`; the schema is a declaration/validation surface only — **no provider implementation ships with this preregistration.**

### 3.3 Provenance classes (distinguishable, mandatory)

Every anchor carries exactly one provenance class:

- `template_derived` — anchors produced by a deterministic, declared template (fixed geometric rule from the crop/silhouette); fully reproducible from the freeze record.
- `model_derived` — anchors produced by a learned model (e.g., a segmentation or landmark model); the model identity, weights hash, and confidence handling must be declared, and the model is a governed surrogate-side dependency, never a held-out component.

Provenance class is recorded per anchor and per screening/optimization artifact so that template-derived and model-derived results are always distinguishable in analysis.

---

## 4. Design and sequencing (fixed order)

The stages run in this exact order; no stage may begin before the prior stage's frozen exit condition is met:

1. **Stage 0 — Landmark-free wiring smoke test (prerequisite, separately owned).** A landmark-free wiring smoke test validates that the D2-0007 pipeline path (fixture → surrogate scoring → telemetry) runs end-to-end without face landmarks. This stage is built and owned as a separate workstream; this preregistration depends only on its PASS as a gate.
2. **Stage 1 — Preregistered motif screening (§5).** Surrogate-only, under the frozen stopping rule. Output: per-generator screening outcomes and the set of surviving motifs (possibly empty).
3. **Stage 2 — Minimum viable anchor abstraction.** Built **only for surviving motifs**, using only the §3.1 vocabulary and §3.2 provider governance. If no motif survives, Stage 2 does not exist and the generation closes (§5, H0).
4. **Stage 3 — Governed optimization / EOT (§6).** Only over admitted candidates (≤ the frozen maximum), surrogate-only.
5. **Stage 4 — Preregistered selection (§6.4).** One winner per the fixed selection criteria.
6. **Stage 5 — Immutable freeze.** Candidate artifact, full configuration, seeds, anchor declarations, and telemetry are frozen and hashed before any held-out step.
7. **Stage 6 — ONE held-out evaluation (§8).** Single-shot; PASS or FAIL retained either way.
8. **Stage 7 — Optional RAC-PRINT-ALPHA-002**, only if the preregistered promotion condition (§9) is met. RAC-PRINT-ALPHA-001 stays the D2-0003 specimen permanently.

---

## 5. Motif screening stage and frozen stopping rule

### 5.1 Screening protocol

Each generator in the frozen set (§2) produces compositions on development/surrogate surfaces only (CI digital convenience fixture class as in prior generations; `PERSON-SUR-v3` scoring). Screening compares each composition's surrogate ensemble detection statistics against the unmodified control on the same fixture. The **screening decision rule** (fixed): a motif family "shows useful signal" iff its best composition reduces the mean per-surrogate detection rate over PERSON-SUR-v3 by at least **0.15 absolute** relative to the matched control, with the improvement present on at least **4 of 6** surrogates (no single-surrogate-only artifact), and `invalid_condition_fraction ≤ 0.10` under the standard control-undetected exclusion rule.

### 5.2 Frozen stopping rule for motif exploration (mandatory, machine-checkable)

The following values are explicit, fixed at preregistration, and machine-checkable against this document and the freeze record. They may not be tuned after any screening observation:

- **Generator set:** exactly the 8 generators in §2 (`P0_GENERATORS` at freeze).
- **Compositions-per-generator budget:** **8** compositions per generator (64 screening compositions total, upper bound).
- **Seeds (explicit integers):** **[20270110, 20270111, 20270112]** — screening composition *i* of generator *g* uses seed `20270110 + (i mod 3)` composed deterministically with the generator index; the full seed schedule is derivable from these three integers and is recorded in the freeze manifest.
- **Maximum candidates admitted to optimization:** **4** (surviving motifs ranked by the §5.1 rule; ties broken by lower worst-surrogate rate, then by generator order in §2, then by seed order).
- **No optional stopping / no extension:** if the budget is exhausted with no survivor, H0 stands and the generation closes; the budget may not be extended post-hoc. Early termination is permitted only on infrastructure failure (documented abort; one re-run from frozen inputs under amendment).

**Justification for values:** 8 generators × 8 compositions = 64 surrogate-only screening evaluations is large enough to cover each generator family with seed replication (3 seeds, ≥2 compositions per seed per generator) while keeping the multiple-comparison burden of screening small and explicit; admitting at most 4 candidates bounds optimization cost and prevents screening from becoming an unbounded search. These numbers are deliberately conservative given that screening is hypothesis screening only (§1).

---

## 6. Optimization objective, EOT/deformation, selection, printability

### 6.1 Objective

Minimize the **CVaR_0.5** (expected shortfall, worst 3 of 6) per-surrogate detection rate over PERSON-SUR-v3 — the Arm-C objective semantics preregistered for D2-0005, reused here verbatim so this generation stays comparable to the D2-0005 ablation without touching it. No α sweep (one-shot rule).

### 6.2 EOT / deformation configuration (fixed)

Expectation-over-transformation uses the RAC-PERSON-DETECT-1.2 transform grid: brightness {0.7, 1.0, 1.3} × blur {0, 0.8} × rotation {−20, 0, +20}, plus garment deformation dimensions sampled from the frozen `schemas/transformation_distribution.schema.json` garment group (stretch, wrinkle, fold, bend, partial_occlusion) at their declared default distributions, seed fixed per §5.2 seed schedule. The full EOT configuration is serialized into the freeze manifest before optimization opens.

### 6.3 Printability constraints (fixed)

Candidates must satisfy the repo's printability envelope inherited from the D2 print path: printable gamut mapping (perceptual), resolution loss ≤ 0.2 per the print/capture dimension group, and pattern energy bounded to the declared `panel_region`/`silhouette_mask` anchor regions so the motif is physically realizable on a garment panel. Candidates violating the envelope are ineligible at selection, not repaired post-hoc.

### 6.4 Selection criteria (fixed)

Exactly one winner: minimum CVaR_0.5 surrogate detection rate among admitted candidates satisfying eligibility (`invalid_condition_fraction ≤ 0.10`, printability envelope §6.3). Tie-break order: (1) lower worst-surrogate rate, (2) lower ensemble mean, (3) lower seed index. Selection boundary: **SURROGATE_ONLY**.

---

## 7. Model exposure rules

- Development and optimization observe **PERSON-SUR-v3 only**; all models observed in D2-0003/D2-0004 are surrogate-only in this generation.
- PERSON-HO-v3 is referenced by hash only (see header). No held-out weights are loaded, no held-out inference occurs, and no held-out metadata beyond the committed model-set file is read until Stage 6.
- `heldout_feedback_allowed: false` in the generation record; any tooling that computes candidate rankings must hard-fail on held-out input.
- Anchor providers (§3.2) declare permitted data exposure; provider outputs crossing stage boundaries are coordinates/masks only — never source imagery, never held-out-derived statistics.

---

## 8. Held-out evaluation protocol (single-shot)

- Exactly **one** held-out evaluation, on PERSON-HO-v3, per RAC-PERSON-DETECT-1.2, of the single frozen Stage-5 winner.
- **No iterative candidate replacement based on held-out observations.** The held-out result — PASS or FAIL — is retained either way and published as a closed-generation datapoint (`internally_measured`), including null and negative outcomes.
- PASS criterion (fixed): the frozen winner's held-out detection rate is strictly below the matched baseline/control detection rate with the protocol's Wilson interval excluding equality in the improvement direction; otherwise FAIL. Both outcomes are reported with intervals.
- Any lock mismatch, missing preregistered hash, or guard failure invalidates the run in full (documented, never patched); the generation then closes as invalid, not as a silent re-run.

---

## 9. Promotion condition for RAC-PRINT-ALPHA-002

A physical print test article RAC-PRINT-ALPHA-002 may be proposed **only if** Stage 6 returns PASS on the single held-out evaluation. The print article then derives exclusively from the frozen Stage-5 winner under the physical print protocol; any physical-trial extension requires its own preregistered stopping rule. If Stage 6 is FAIL, invalid, or never reached (screened-out H0), no print article is created. RAC-PRINT-ALPHA-001 remains the D2-0003 specimen permanently and is unaffected by this generation.

---

## 10. Freeze point and executable freeze enforcement

- **Freeze point:** this document, `generations/RAC-PER-D2-0007.json`, and `schemas/d2007_anchor_provider_v1.schema.json` are frozen at commit. The optimization-time freeze (Stage 5) additionally pins candidate bytes, EOT config, seed schedule, anchor provider declarations, and pre-held-out telemetry hashes.
- **Executable enforcement:** the artifact id `RAC-PER-D2-0007-PREREGISTRATION` is registered in `ruthless_pipeline/governance/constraints.py::FROZEN_D2_ARTIFACT_IDS` alongside D2-0003/0004/0005; `assert_frozen_d2_artifacts_unchanged` fails closed on any mutation. The generation record `generations/RAC-PER-D2-0007.json` is additionally covered by the frozen-surface manifest (`benchmarks/frozen_surface_sha256.json`, enforced by `tests/test_frozen_surface_integrity.py`). Dedicated tests pin the sha256 of this document and the generation record and reject any post-freeze mutation.

---

## 11. Evidence labels and deviations policy

All outputs carry the repo's six-label governance (`ruthless_pipeline/certification/experiment.py::EVIDENCE_LABELS`):

- Hypotheses and screening decision rules, pre-execution: **`target`**.
- Screening outcomes (surrogate-only, hypothesis-screening): **`internally_measured`**, always scoped "surrogate-only; not transfer evidence."
- The single held-out result: **`internally_measured`**.
- Any transfer claim beyond PERSON-HO-v3: **`external_replication_needed`**.
- Fixture/scenario framing: **`scenario_assumption`**.
- Mechanistic interpretations of why motifs did/did not signal: **`speculative_open`**.

**Screening is hypothesis screening, never evidence promotion** (§1): no screening result may be cited as effectiveness evidence in any release, manuscript, or claim registry.

**Deviations policy:** any deviation from this preregistration — generator set, budgets, seeds, stopping rule, anchor vocabulary, provider declarations, objective, EOT grid, selection criteria, held-out protocol — requires a documented, hash-committed amendment **before** the affected step is executed; if discovered after execution, the affected result is labeled `scenario_assumption` (or invalidated) and the deviation disclosed in the release. Deviations are never silent.

---

## 12. Operational constraints on this preregistration

- This document and `generations/RAC-PER-D2-0007.json` are a **document + frozen skeleton only**. D2-0007 is **NOT_ARMED**: no CI wiring is added for it; trigger fields are present but not armed, so committing the skeleton cannot fire any workflow.
- This preregistration **declares; it does not execute**: no surrogate runs, no held-out access, no anchor provider implementation, and no synthetic→measured relabeling are performed as part of this change.
- D2-0007 execution requires, in order: the Stage-0 smoke test PASS, a fresh lock freeze under the model-lock process, and an explicit trigger arming in a later, separately reviewed change.

---

## 13. Amendment log

No amendments yet. Pre-arming amendments are permitted only as documented, hash-committed entries recorded here; silent changes are not (§11).

# Perpetual Improvement Master Document
## Open Research Questions & Cutting-Edge Development Framework

**Document ID:** PIM-2026-09-06-001  
**Version:** 1.2.0  
**Date:** September 7, 2026  
**Classification:** Internal - Strategic  
**Review Cycle:** Quarterly  
**Owner:** Founder/CTO  
**Repository baseline reviewed:** `main` at `277cc0e`

---

## Executive Framework

This document establishes the perpetual improvement system for the Adversarial Fashion Venture while aligning research planning with the repository that actually exists today.

**Core principle:** Research is a permanent operating mode, but claims must move through an evidence pipeline before they become product language.

The repository currently supports serious software experimentation, but it does **not** yet support a physical garment efficacy claim. The highest-priority improvement is therefore not another speculative sensing modality; it is converting the current software and Pattern Lab into a reproducible evidence system.

---

# Part I — Current Repository Truth

## 1.1 Current software state

| Capability | Current state | Evidence label |
|---|---|---|
| Python research package | `ruthless_pipeline/`, package version `3.0.0` | Internally implemented software |
| Enhanced NAP path | Procedural prior + optional explicit diffusion/OpenCLIP adapters | Internally implemented; real generative runtime still needs reproducible exercise |
| Neural deformation | Coordinate-correspondence field + uncertainty + differentiable warp | Internally implemented software; calibrated capture not yet supplied |
| Differentiable physics | Native mass-spring cloth baseline | Internally implemented software; not equivalent to HOOD/DiffCloth validation |
| Scene composition | Differentiable garment-mask compositor | Internally implemented software |
| Comparative benchmark | Surrogate/held-out split + transform sweeps + CSV/JSON | Internally implemented harness; real frozen model zoo not yet locked |
| Pattern Lab | Static browser front end on repository root | Internally implemented design/experiment prototype |
| Pattern Lab generators | Eight procedural pattern families | Internally implemented design capability |
| Pattern Lab analysis | Frequency/color visualizations + heuristic model-named percentages | **Demo/heuristic only** |
| Pattern Lab summary metrics | Some values randomized by current JS | **Demo only; not evidence** |
| Pattern Lab quick optimization | Seed search driven by UI metrics | **Demo only; not a real model optimizer** |
| GitHub Pages | Deployment workflow present | Operational capability |
| GitHub CI | Not green at this review point | First v3 import run stopped at Ruff before pytest |
| Real detector ensemble | Not frozen/manifested | Open implementation gate |
| Calibrated physical garment data | Not present | Open experimental gate |
| Physical product validation | Not performed | No current product-efficacy claim |

## 1.2 Version boundary

- Python package: `3.0.0`.
- Pattern Lab JSON/config export currently identifies itself as `2.0.0`.
- Repository `main` contains post-v3 Pattern Lab and Pages commits.

Until versioning is unified, documents must specify whether a version refers to the **Python package**, **Pattern Lab schema**, or **repository release**.

---

# Part II — Evidence Governance

## 2.1 Required evidence labels

Every number, chart, roadmap metric, benchmark row, investor slide, product statement, and internal dashboard field must use one of these labels:

| Label | Definition | Allowed use |
|---|---|---|
| **Published observation** | Result reported by an external source | Literature review, with citation and test conditions |
| **External result — replication needed** | Relevant published result not reproduced internally | Research planning only |
| **Internally measured** | Produced by a frozen internal protocol with retained artifacts | Internal comparison; product claims only after claim review |
| **Target** | Desired future result | Roadmap only |
| **Scenario assumption** | Planning input / possible future condition | Strategy only; never presented as forecast fact |
| **Speculative/open** | Hypothesis or unanswered question | Research backlog |

### Rule

A percentage may not appear in a `Current performance` field unless it is **internally measured** or clearly presented as a **published external observation** under its original conditions.

## 2.2 Claim ladder

```text
hypothesis
  -> literature precedent
  -> reproducible digital experiment
  -> held-out architecture result
  -> calibrated simulated/scene result
  -> printed material result
  -> repeated physical result
  -> durability/environment result
  -> statistical uncertainty
  -> claim review
  -> product language
```

Skipping stages creates technical debt and marketing risk.

---

# Part III — Research Horizon Scanning

## 3.1 Surveillance / vision trajectory

Replace unsupported 2028/2030 adoption percentages with scenario monitoring.

| Trend | Observed 2026 research state | Planning treatment | Priority |
|---|---|---|---|
| Multimodal RGB + thermal | Physical adversarial clothing against RGB-T fusion is published | Replicate later under frozen owned-lab protocol | P2 |
| Vision transformers / foundation models | Task-agnostic feature-space attacks are published | Add held-out ViT/foundation backbone evaluation after baseline manifest exists | P1 |
| Self-supervised representations | Feature-space disruption is an active research direction | Reframe from “no classification head” to backbone/representation transfer | P1 |
| Edge deployment | Important product context, but repository currently lacks a representative hardware test matrix | Track after core benchmark is reproducible | P2 |
| Continual/online model change | Static patterns may age as models change | Treat as longitudinal transfer/version-drift study | P1 |
| LiDAR | Physical adversarial LiDAR research exists | Apparel relevance remains unproven; feasibility only | P3 |
| mmWave/radar | Adversarial radar research exists | Apparel-specific relevance remains speculative | P3 |
| Audio-visual fusion | Multi-sensor systems exist; apparel-only countermeasure thesis is immature | Monitor; do not divert core R&D yet | P3 |
| Quantum/neuromorphic sensing | Long-horizon technology watch | Scenario monitoring only | P3 |

## 3.2 Research frontier corrections

Do **not** maintain a single generic “SOTA transfer rate” table across unrelated papers. Attack success varies with:

- task and threat model;
- architecture;
- baseline confidence;
- transformation set;
- detector threshold;
- target class;
- digital vs physical setup;
- camera distance/resolution;
- garment coverage;
- white-box vs black-box access;
- transfer vs same-model evaluation.

Use condition-specific evidence rows instead.

---

# Part IV — Revised Open Research Question Database

## Category A — Reproducibility & Black-Box Evaluation

| ID | Research question | Status | Priority | Repository dependency |
|---|---|---|---|---|
| RQ-A-000 | Can the full GitHub CI pipeline run green and become a required merge gate? | Open | **P0** | Resolve Ruff findings; run pytest/smoke/package |
| RQ-A-001 | What frozen open-model manifest should define the first reproducible benchmark? | Open | **P0** | Evaluator adapters + version manifest |
| RQ-A-002 | Which ensemble diversity metric best predicts held-out transfer? | Open | P1 | Real model zoo + benchmark data |
| RQ-A-003 | What query budget produces the best performance/measurement-cost tradeoff? | Open | P1 | Query-efficient mode + multiple authorized targets |
| RQ-A-004 | Can transfer failure be predicted from surrogate disagreement and pattern statistics? | Open | P1 | Large result matrix |
| RQ-A-005 | Does adaptive surrogate weighting improve held-out results? | Open | P1 | Frozen model manifest |
| RQ-A-006 | How robust is the pipeline to adversarially trained or transformed-input detectors? | Open | P1 | Robust-model manifest |

### RQ-A-003 correction

There is no evidence for a universal “~200 query optimum.” Test a learning curve such as 0 / 25 / 50 / 100 / 200 / 500 authorized queries and report marginal improvement per query.

## Category B — Physical Robustness

| ID | Research question | Status | Priority | Validation method |
|---|---|---|---|---|
| RQ-B-001 | What is the pattern degradation curve versus effective pixels-on-garment and distance? | Open | **P0** | Fixed model/camera/pattern; sweep distance and effective spatial frequency |
| RQ-B-002 | What is the effect of pose and camera angle? | Open | **P0** | Pre-registered pose/azimuth/elevation matrix |
| RQ-B-003 | What is the effect of garment size, drape, and stretch? | Open | P1 | Multiple sizes/fabrics + calibrated deformation capture |
| RQ-B-004 | What is the wash durability curve? | Open | **P0** | Standards-aligned laundering + colorimetry + repeated CV benchmark |
| RQ-B-005 | How do compression, blur, exposure, and low light affect results? | Open | P1 | Frozen transform sweep then physical confirmation |
| RQ-B-006 | How do rain/fog/snow affect garment-specific efficacy? | Open | P2 | Environment-aware rendering followed by controlled physical trials |
| RQ-B-007 | Does 3D garment geometry provide robust benefit beyond 2D texture? | Open | P2 | Matched 2D vs geometry-aware optimization |

### Measurement rule for RQ-B-001

Do not report only “720p vs 8K.” Record:

- garment pixel width/height in the frame;
- physical pattern feature size;
- camera distance and focal length;
- crop/preprocessing size;
- detector input size;
- effective pixels per printed feature.

## Category C — Human Stealth & Design

| ID | Research question | Status | Priority | Validation method |
|---|---|---|---|---|
| RQ-H-001 | Does a naturalness constraint improve or reduce held-out transfer when coverage/frequency/budget are controlled? | Open | P1 | Matched A/B experiment |
| RQ-H-002 | What is the Pareto frontier between machine objective and human aesthetic rating? | Open | P1 | Blind human ratings + frozen model scores |
| RQ-H-003 | Which design families are most robust to manufacturing constraints? | Open | P1 | Pattern-family ablation |
| RQ-H-004 | How accurately do users understand efficacy and limitations? | Open | P1 | Comprehension study before product launch |
| RQ-H-005 | What claims create false confidence in wearers? | Open | **P0 product-safety** | Messaging study + legal review |

## Category D — Materials & Manufacturing

| ID | Research question | Status | Priority | Validation method |
|---|---|---|---|---|
| RQ-M-001 | Which printer/ink/fabric combinations preserve geometric and color fidelity? | Open | **P0** | ICC/profile, spectrophotometry, geometric registration |
| RQ-M-002 | Which fabric properties most affect CV results after deformation? | Open | P1 | Controlled textile ablation |
| RQ-M-003 | Can jacquard/knit structures match or exceed printed patterns? | Open | P2 | Matched pattern/material test |
| RQ-M-004 | Can automated QC verify pattern fidelity at line speed? | Open | P2 | Vision-based print inspection with calibration target |
| RQ-M-005 | Can recycled materials preserve the same measured performance envelope? | Open | P2 | Matched substrate trials |
| RQ-M-006 | How does laundering change color, geometry, and measured CV output over time? | Open | **P0** | Linked textile + model measurements |

## Category E — Foundation Models & Cross-Architecture Transfer

| ID | Research question | Status | Priority | Note |
|---|---|---|---|---|
| RQ-F-001 | Do physically constrained patterns transfer across CNN and transformer detector families? | Open | P1 | Must use held-out architectures |
| RQ-F-002 | Can feature-space objectives on vision foundation models improve downstream transfer? | Open | P1 | Prior task-agnostic attacks establish digital precedent |
| RQ-F-003 | Does optimizing against one backbone improve multiple downstream tasks after physical transforms? | Open | P2 | Requires careful task separation |
| RQ-F-004 | How quickly do patterns age as model versions change? | Open | P1 | Longitudinal benchmark/version registry |

## Category F — Cross-Modal / Multi-Spectral

| ID | Research question | Status | Priority | Correct framing |
|---|---|---|---|---|
| RQ-C-001 | Can published RGB-T clothing results be independently replicated under our manufacturing and held-out-fusion protocol? | Open | P2 | Existence is established externally; replication is the gap |
| RQ-C-002 | Which visible/thermal material properties remain stable after wear and laundering? | Open | P2 | Materials question |
| RQ-C-003 | Can a user-controllable thermal textile remain aesthetically and thermally safe? | Open | P2 | Published thermochromic precedent exists; safety/manufacturability remain open |
| RQ-C-004 | Is there any apparel-compatible LiDAR effect worth pursuing? | Open | P3 | Physical LiDAR attacks exist, but apparel transfer is not established |
| RQ-C-005 | Is there any apparel-compatible mmWave/radar effect worth pursuing? | Open | P3 | Radar adversarial research exists; garment thesis is speculative |
| RQ-C-006 | Does an apparel product meaningfully change audio-visual fusion performance? | Open | P3 | Monitor; avoid emitter-based product concepts without legal/safety review |

## Category G — Defensive Research

| ID | Research question | Status | Priority |
|---|---|---|---|
| RQ-D-001 | Can adversarial-pattern anomaly detectors identify our own candidate patterns? | Open | P1 |
| RQ-D-002 | Which transformations/ensembles most reduce our own measured effects? | Open | P1 |
| RQ-D-003 | Can we build a defense benchmark without weakening research integrity? | Open | P2 |
| RQ-D-004 | Can the same data support a responsible B2B robustness-evaluation product? | Open | P2 |

---

# Part V — Priority Matrix Aligned to Repo State

## P0 — Current blockers

1. **Green CI / reproducible repository baseline.**
2. **Freeze benchmark provenance and real open-model manifest.**
3. **Stop heuristic UI metrics from being confused with measured results.**
4. **Resolution/distance/angle physical protocol.**
5. **Print calibration and wash-durability protocol.**
6. **User-facing claim/comprehension controls before any commercial efficacy language.**

## P1 — Competitive research

- ensemble diversity vs transfer;
- query-efficiency learning curves;
- CNN ↔ transformer/foundation-model transfer;
- naturalness vs transfer matched experiments;
- calibrated deformation capture;
- model-version drift;
- defensive detection/countermeasure studies.

## P2 — Differentiation

- RGB-T independent replication;
- thermochromic or other controlled spectral materials;
- jacquard/knit structures;
- weather robustness;
- higher-fidelity cloth backend if it improves prediction of physical results.

## P3 — Horizon monitoring

- apparel-compatible LiDAR effects;
- mmWave/radar relevance;
- audio-visual fusion relevance;
- quantum sensing;
- neuromorphic sensing.

### Resource rule

Do not allocate fixed percentages to speculative P3 work while P0 evidence gates remain incomplete. Reallocate quarterly based on evidence and product stage.

---

# Part VI — Quarterly Research Review (Q-Cycle)

## Week 1 — Horizon scan

- Review new papers and official proceedings.
- Record source, date checked, task, threat model, digital/physical status, models, transformations, and limitations.
- Track detector/foundation-model releases relevant to the frozen manifest.
- Track textile/material methods and standards.
- Track regulatory/advertising guidance with primary sources.

**Output:** research brief + evidence-register diff.

## Week 2 — Gap analysis

- Compare published results with **internally measured** capability only.
- Identify 3–5 priority questions.
- Remove questions already answered by external literature and rewrite them as replication/generalization questions.
- Identify blocked dependencies and owners.

**Output:** gap memo.

## Week 3 — Roadmap update

- Update 12-month roadmap.
- Convert unsupported performance numbers into targets or remove them.
- Freeze protocols before experiments begin.
- Set go/no-go criteria.

**Output:** roadmap + protocol package.

## Week 4 — Knowledge transfer

- Update repository docs.
- Add experiment artifacts and hashes.
- Present findings with confidence/limitations.
- Update claim matrix and product language.

**Output:** knowledge-base/repository update.

---

# Part VII — Research Infrastructure

## 7.1 Near-term infrastructure actually required

| Capability | Current | Next target | Priority |
|---|---|---|---|
| GitHub CI | Present but not green | Green required merge gate | P0 |
| Model registry/manifest | Not frozen | Small reproducible open-model zoo first | P0 |
| Experiment artifact schema | Partial | IDs, configs, raw outputs, hashes, summaries | P0 |
| Pattern Lab → benchmark bridge | None | Job/config bridge | P1 |
| Benchmark → Pattern Lab results | None | Provenance-aware result import | P1 |
| Physical camera protocol | None | Owned/authorized calibrated lab setup | P0 |
| Print/fabric calibration | None | Initial printer/fabric profiles | P0 |
| Wash/durability lab access | None | Standards-aligned partner capability | P0/P1 |

## 7.2 Infrastructure to defer until justified

Do not buy a 20-camera commercial surveillance library, large on-prem GPU cluster, climate chamber, or specialized RF equipment solely because it appears in a long-range roadmap. First show that the core benchmark and first physical prototype produce reproducible information worth scaling.

---

# Part VIII — Data & Experiment Standards

Every experiment record should contain at minimum:

```text
experiment_id
repository_commit
package_version
pattern_config_hash
pattern_artifact_hash
model_id
model_version_or_weight_hash
preprocessing_version
thresholds
surrogate_or_heldout
camera_or_scene_id
transform_conditions
fabric/printer/ink identifiers (when physical)
seed
raw_outputs_location
aggregate_metrics
uncertainty/confidence_interval
operator/date
claim_status
```

Pattern Lab JSON exports can become the front end of this schema, but the current `2.0.0` UI export is not yet sufficient as a complete experiment record.

---

# Part IX — Success Metrics Reset

## 9.1 Current technical state

| Metric | Current | Label |
|---|---|---|
| Black-box transfer rate | **Unmeasured internally under a frozen real-model benchmark** | Open |
| Physical robustness | **Unmeasured internally** | Open |
| Cross-modal efficacy | **Not internally replicated** | External precedent exists |
| Query efficiency | Budget enforcement implemented; optimum unknown | Internally implemented + open research |
| Pattern library size | UI can generate/store candidates; no validated library count should be used as efficacy evidence | Operational |
| Products with validated efficacy claims | **0** | Internally known |

## 9.2 Targets

Targets may be ambitious, but they must remain in a **Target** column until measured. Do not use “70–80% current transfer,” “75% current robustness,” or similar planning values as baseline facts.

## 9.3 Better research productivity metrics

Track:

- reproducible experiments completed;
- held-out model coverage;
- physical conditions covered;
- percentage of claims with complete provenance;
- failed hypotheses documented;
- replication success/failure;
- artifact completeness;
- time from experiment completion to documentation update.

Paper/patent counts are secondary outcomes, not substitutes for reproducibility.

---

# Part X — Milestone Gates

| Gate | Target window | Criteria | Decision |
|---|---|---|---|
| **G0 — Repository integrity** | Immediate | Green CI; docs reflect current code; heuristic UI metrics labeled; reproducible build | Continue research integration |
| **G1 — Digital benchmark** | Q4 2026 | Frozen real-model manifest; held-out results; repeatable artifacts; no UI-only scores in evidence tables | Approve digital research baseline |
| **G2 — Physical pilot** | Q4 2026 / Q1 2027 | Print calibration + distance/angle/pose study + uncertainty | Decide whether first garment prototype merits expansion |
| **G3 — Durability** | Q1 2027 | Laundering/colorimetry + repeated frozen benchmark | Decide whether product-development durability gate is met |
| **G4 — Human factors** | Q1 2027 | Naturalness/stealth study + user understanding of limitations | Approve customer-facing design/claims direction |
| **G5 — Cross-modal replication** | After G1–G4 | Independent RGB-T result under our protocol | Decide whether multi-spectral product line is justified |

---

# Part XI — Research Output Classification

| Classification | Description | Examples | Distribution |
|---|---|---|---|
| **Core IP** | Potentially patentable implementation/material innovation | Novel optimization, calibration, textile structures | Internal + counsel |
| **Trade Secret** | Competitive implementation/data advantage | Model manifests, unpublished physical datasets, manufacturing calibration | Restricted |
| **Public Research** | Reproducible brand/recruiting contribution | Benchmark protocols, selected negative results, defensive findings | Public after review |
| **Defensive Publication** | Prior-art strategy | Non-core extensions | Public after counsel review |

Open-source release decisions must also account for the current all-rights-reserved repository license.

---

# Part XII — Regulatory & Claims Monitoring

This document is not legal advice. Maintain a counsel-reviewed register instead of categorical country conclusions.

## United States

The FTC has stated that false or unsubstantiated marketing claims about biometric-technology validity, reliability, accuracy, performance, fairness, or efficacy can be deceptive. Product language should therefore be tied to tested conditions and a retained substantiation file.

## European Union

The AI Act contains detailed restrictions and safeguards around certain real-time remote biometric identification uses in publicly accessible spaces. Do not summarize the EU as simply “strict” or “allowed/prohibited”; track the exact use case, actor, jurisdiction, provision, effective date, and counsel interpretation.

## United Kingdom

ICO biometric-recognition guidance is currently marked as under review following changes associated with the Data (Use and Access) Act. Treat UK conclusions as changeable and date-stamp every review.

## Required regulatory register fields

```text
jurisdiction
agency_or_authority
primary_source
provision_or_guidance
scope
product_implication
claim_implication
last_checked
counsel_status
owner
```

---

# Part XIII — Conference Tracking

Only official dates receive `CONFIRMED` status.

| Venue | Current official status checked 2026-09-06 | Priority |
|---|---|---|
| **CHI 2027** | **CONFIRMED:** paper deadline Sep 10, 2026 AoE | Human factors only if a mature study exists |
| **ICLR 2027** | **CONFIRMED:** abstract Sep 18, paper Sep 25, 2026 AoE | High for representation/foundation-model work |
| **USENIX Security 2027** | **CONFIRMED:** Cycle 2 registration Jan 19, paper Jan 26, 2027 AoE | High |
| **CVPR 2027** | Use official CFP when available/verified; otherwise `TBD` | High |
| **ICCV 2027** | `TBD` until official CFP verified | High |
| **IEEE S&P 2027** | `TBD` until official CFP verified | High |
| **ACM CCS 2027** | `TBD` until official CFP verified | Medium |

Do not extrapolate deadlines from prior years and present them as confirmed.

---

# Part XIV — Research Question Template

```text
ID:
Title:
Question:
Motivation:
Evidence status before starting:
Prior art / sources:
Hypothesis:
Protocol:
Frozen repository commit:
Model/data/material manifest:
Success criteria:
Failure criteria:
Risks / ethics / authorization:
Dependencies:
Owner:
Status:
Target date:
Actual date:
Result:
Confidence / uncertainty:
Replication status:
Impact on roadmap:
Claim impact:
Artifacts / hashes:
```

---

# Part XV — Immediate 30/60/90-Day Plan

## 0–30 days

- Make CI green.
- Lock repository versioning language.
- Label Pattern Lab heuristic fields visibly in code/UI in a future implementation change.
- Freeze first open-model benchmark manifest.
- Define experiment artifact schema.
- Run baseline/candidate benchmark with real evaluators in an owned/authorized lab.
- Create first print calibration target and physical protocol draft.

## 31–60 days

- Connect Pattern Lab configs to Python experiment jobs.
- Import provenance-aware benchmark results back into a dashboard.
- Run resolution/distance/angle/pose sweeps.
- Start fabric/printer/ink ablation.
- Start wash-durability pilot.
- Begin naturalness vs machine-performance matched study design.

## 61–90 days

- Repeat physical pilot on held-out model/camera conditions.
- Quantify model-version and architecture transfer.
- Decide whether higher-fidelity cloth simulation improves prediction enough to justify integration.
- Decide whether RGB-T replication belongs in the next quarter.
- Produce a claim-substantiation dossier for any statement intended for customers.

---

# Part XVI — Operating Principle

**The objective is not to maximize impressive percentages. It is to build a system that knows exactly what has been measured, what transfers, what fails, under which physical conditions, and how much confidence the evidence deserves.**

That is the durable competitive advantage: not a single pattern, but a repeatable research-to-textile-to-evidence loop.

---

# Part V-b — Computational Textile R&D Roadmap (35-Point Integration)

**Source:** Founder strategy memo, September 7, 2026.  
**Thesis:** Move from a sophisticated procedural design/benchmark platform to a **closed-loop computational textile R&D system**. The highest-value work is not more UI or more pattern families; it is better optimization, simulation, physical transfer, evidence quality, and manufacturing feedback.

Each item below is mapped against the live repository state at `main` (`277cc0e`) so roadmap language cannot drift ahead of implemented capability.

## Status legend

- **Implemented** — present and exercised on current main
- **Partial** — meaningful substrate exists; the full capability does not
- **Open** — not started in-repo

## A. Optimization & Generation

| # | Roadmap item | Repo status | PIM linkage |
|---|---|---|---|
| 1 | Multi-objective optimizer with Pareto frontier (transfer proxy, fidelity, printability, aesthetics, robustness, complexity) | **Open** — current surrogate selection uses a single sort key with reference fidelity as first tie-break | Extends RQ-A-002/005; **Top-5 build order #1** |
| 2 | Learned generative textile prior (latent/diffusion) alongside the deterministic procedural baseline | **Partial** — enhanced NAP path has optional diffusion/OpenCLIP adapters; no trained textile prior | RQ-H-002 |
| 3 | Garment-aware optimization from the start (panels, seams, occlusion) instead of the flat 4096 tile | **Open** — optimization target is still the flat tile; Product Studio has product-aware zones for design only | Feeds RQ-B-003/007 |
| 4 | Differentiable garment rendering inside the candidate loop (texture → drape → camera → detector) | **Partial** — neural deformation, mass-spring cloth, and differentiable compositor exist but are not in candidate evaluation | RQ-B-007 |
| 5 | Materially calibrated / higher-fidelity cloth solver | **Partial** — mass-spring baseline only; no material calibration | RQ-M-002; P2 cloth-backend decision |

## B. Robustness & Evaluation

| # | Roadmap item | Repo status | PIM linkage |
|---|---|---|---|
| 6 | Full EOT/robustness engine (distance, resolution, rotation, pose, deformation, lighting, exposure, blur, JPEG, occlusion, background, camera) with performance **surfaces** | **Partial** — protocol 1.2 sweeps brightness/blur/rotation/scale only | RQ-B-001/002/005; **Top-5 #3** |
| 7 | Versioned model zoo spanning one-stage, two-stage, transformer, segmentation families | **Partial** — SUR-v3 has 6 detectors across 5 families; no ViT/foundation backbones yet | RQ-A-002, RQ-F-001/002 |
| 8 | Automatic model-generation rotation (observed held-out → surrogate pool; fresh held-out provisioning) | **Partial** — D2-0004 executed this manually: HO-v2 models demoted to surrogate-only, HO-v3 frozen without inference, one-shot reuse block active | Now a standing rule; automate next |
| 9 | Statistical certification (bootstrap CIs, Wilson intervals, effect sizes, paired comparisons, preregistered stopping rules) | **Open** — D2 certification is threshold-based only | Upgrades G1–G5 gates |
| 10 | Serious authorized evaluation corpus (many subjects/scenes/garments/conditions, strict split hygiene) | **Open** — convenience fixture only | **Top-5 #2**; RQ-B series |
| 11 | Synthetic scene factory (thousands of reproducible garment scenes) | **Partial** — differentiable compositor exists; no scene factory | Feeds #10 |
| 12 | Environment-conditioned generation as first-class subsystem (scan → statistics → recolor → surrogate optimize → freeze) | **Partial** — reference-conditioning and CAPGen-inspired module exist; not closed-loop | RQ-B-006 |
| 13 | Beyond-RGB behavior (grayscale, low-light, IR-like, depth silhouettes) with claims scoped to tested sensors | **Open** | RQ-C series; claim-scope rule applies |

## C. Design Quality & Product Topology

| # | Roadmap item | Repo status | PIM linkage |
|---|---|---|---|
| 14 | Full Reference Fidelity system (style profiles, hero/suppression zones, composition analysis, deterministic sub-seeds, 0–100 scoring, Find Best Match) | **Implemented** on main — including monotonic Find Best Match after the 277cc0e fix; motif wiring through style-spec rendering restored same commit | **Top-5 #4** — now substantially complete |
| 15 | Learned perceptual/aesthetic scoring alongside deterministic fidelity, explicitly separate from detector efficacy | **Partial** — optional OpenCLIP adapter exists; not integrated into fidelity scorer | RQ-H-001/002 |
| 16 | Product-aware pattern topology (motifs crossing legs/pockets/seams; crown/brim continuity; mask exclusion zones) | **Partial** — product-aware zones and family profiles exist; topology-aware motif placement does not | Extends #14 |
| 17 | Seam-continuity as an optimization objective | **Partial** — Production Mapper warns on discontinuity and auto-maps; no objective-function search | Manufacturing feedback loop |
| 18 | Printer/fabric color calibration (printed target → measured profile → gamut-constrained optimization) | **Open** — printability is an uncalibrated proxy | RQ-M-001; **P0** |
| 19 | Physical digital-twin calibration loop (photograph sample → estimate transfer error → update rendering → re-optimize) | **Open** | **Top-5 #5**; RQ-M-001/004 |

## D. Physical Validation & Manufacturing Feedback

| # | Roadmap item | Repo status | PIM linkage |
|---|---|---|---|
| 20 | Automated physical P1 capture harness (camera/distance/angle/lighting/pose/size/fabric/wash metadata → immutable RAC bundles) | **Open** — print-test kit prepares artifacts; no capture harness | G2 gate; RAC-PHYSICAL-PRINT-TEST-1.0 |
| 21 | Durability as longitudinal experiment (W0/W1/W5/W10 degradation curve, not pass/fail) | **Open** | RQ-B-004, RQ-M-006; G3 gate |
| 22 | Manufacturing variance in robustness (scaling error, misregistration, color drift, seam displacement, stretch) | **Open** | Extends #17/18 |

## E. Evidence Infrastructure

| # | Roadmap item | Repo status | PIM linkage |
|---|---|---|---|
| 23 | Automatic experiment registry (IDs, SHAs, hashes, manifests, conditions, metrics, artifacts) | **Partial** — evidence bundles + generation markers exist; no unified registry | Part VIII schema |
| 24 | Content-addressed artifacts (hash = identity; one-pixel change → new artifact) | **Partial** — candidate PNGs, model states, and locks are SHA-256 bound; not yet universal | Extends D2 evidence binding |
| 25 | Lineage graphs (reference → generator → candidate → optimization → frozen master → D2 → print → P1 → wash → lot) | **Partial** — source candidate IDs, lock commits, and provenance fields survive; no queryable graph | Extends #23/24 |
| 26 | Adversarial evaluation of our own methodology (false-positive hunts: leakage, cherry-picked transforms, post-hoc thresholds, regeneration, hash mismatches) | **Partial** — contract tests enforce lock/boundary integrity and held-out isolation | RQ-D series; CI #32 |
| 27 | Challenge sets / failure archive evaluated per generation without contaminating certification sets | **Open** | Extends #8 rotation |
| 28 | Scaling-law tracking (candidates × surrogate diversity × EOT samples × scenes vs held-out transfer) | **Open** | RQ-A-002/004 |
| 29 | Ablation infrastructure (did adaptation/cloth/fidelity/surrogate-n actually help?) | **Open** | Publishable-research backbone; RQ-A-005, RQ-B-007, RQ-H-001 |
| 30 | Generation-centric research dashboard (D0→D2 lineage, Pareto fronts, per-model results, heatmaps, CIs, hashes, physical status) | **Open** — d2-latest-status.json is a single-generation status file only | Part IX metrics |

## F. Architecture & Process

| # | Roadmap item | Repo status | PIM linkage |
|---|---|---|---|
| 31 | Architectural separation into Design Studio / Research-Optimization / Certification-Manufacturing planes with explicit interfaces | **Open** — repo currently grows across all three | Prevents monolith drift |
| 32 | Scientifically aware CI (determinism, provenance leakage, model-set isolation, reproducibility, artifact identity, statistics, certificate integrity, generation boundaries) | **Partial** — contract tests cover locks, boundaries, held-out isolation, integrity; CI green since 277cc0e | G0 gate (now met) |
| 33 | Reproducible GPU experiment containers (pinned CUDA/PyTorch/models, container digests) | **Open** | Part VII |
| 34 | Dataset governance (versioning, provenance/permissions, sample hashes, contamination prevention, immutable splits) | **Partial** — model manifests and held-out isolation exist; dataset governance does not | Part VIII |
| 35 | Paper written alongside software; software auto-generates tables/ablations | **Open** | Conference tracking, Part XIII |

## Standing build order (founder memo, 2026-09-07)

1. **Multi-objective surrogate optimization + Pareto archive** (#1)
2. **Large authorized synthetic/digital scene corpus** (#10, #11)
3. **Garment-aware differentiable deformation/EOT loop** (#3, #4, #6)
4. **Reference Fidelity v1 + product-specific composition** (#14 — substantially implemented; #16 remainder)
5. **Calibrated print → photograph → physical P1 feedback loop** (#18, #19, #20)

## Interaction with P0 gates

The founder build order does **not** override the P0 evidence gates in Part V. Items #1–#5 proceed *on top of* the frozen-manifest / green-CI / one-shot-generation discipline established by D2-0004, not in place of it. Any optimizer, corpus, or calibration output that feeds a certification path must enter through the evidence labels in Part II and the generation-boundary rules now enforced by CI.

## Explicitly de-prioritized by the memo

Adding more UI features or pattern families without improvements to optimization, simulation, physical transfer, evidence quality, or manufacturing feedback. This supersedes any backlog item whose only effect is presentational.

---

## Document Control

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-09-06 | Initial perpetual-improvement framework |
| 1.1.0 | 2026-09-06 | Aligned to live repository state; reset unsupported baseline metrics; separated Pattern Lab heuristics from benchmark evidence; reprioritized research; corrected literature/conference framing |
| 1.2.0 | 2026-09-07 | Integrated 35-point computational-textile R&D roadmap with per-item repo-state mapping and founder build order; recorded Reference Fidelity v1 + motif/Find-Best-Match fixes as implemented at 277cc0e; CI green (G0 met) |

## Next Review

**Scheduled:** December 6, 2026  
**Required agenda:** CI/release health, frozen benchmark results, physical-pilot evidence, wash durability, human-factor study, RGB-T go/no-go, regulatory source refresh.

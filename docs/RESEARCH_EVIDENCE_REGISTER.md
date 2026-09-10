# Research Evidence Register

**Last reviewed:** 2026-09-06  
**Purpose:** Keep external research, internal measurements, targets, and open questions from being blended into one performance narrative.

This register is not a complete literature review. It records sources that materially change the current roadmap or correct statements in the Perpetual Improvement Master Document.

## Evidence labels

- **Published observation** — external source result under that source's conditions.
- **External result — replication needed** — relevant to the venture but not reproduced internally.
- **Internally measured** — produced by a frozen internal protocol with retained artifacts.
- **Target** — desired future result.
- **Scenario assumption** — planning input.
- **Speculative/open** — unanswered hypothesis.

---

## Computer vision / adversarial clothing

### RGB-T physical adversarial clothing exists as published research

**Status:** Published observation / replication needed  
**Source:** Xiaopei Zhu et al., *Physical Adversarial Clothing Evades Visible-Thermal Detectors via Non-Overlapping RGB-T Pattern*, CVPR 2026.  
**URL:** https://openaccess.thecvf.com/content/CVPR2026/html/Zhu_Physical_Adversarial_Clothing_Evades_Visible-Thermal_Detectors_via_Non-Overlapping_RGB-T_Pattern_CVPR_2026_paper.html

**What the source supports:** Physical adversarial clothing was evaluated against visible-thermal detection with different fusion architectures; the paper introduces non-overlapping visible/thermal pattern design and an ensemble method for transfer across unseen RGB-T detectors.

**What it does not establish for this repo:** Our own cross-modal efficacy, our manufacturing repeatability, or a universal success rate.

**Roadmap impact:** RQ-C-001 should be an independent replication/generalization question, not “can RGB-T clothing exist?”

### Thermally activated dual-modal clothing has physical precedent

**Status:** Published observation / replication needed  
**Source:** Jiahuan Long et al., *Thermally Activated Dual-Modal Adversarial Clothing against AI Surveillance Systems*, CVPR 2026.  
**URL:** https://openaccess.thecvf.com/content/CVPR2026/html/Long_Thermally_Activated_Dual-Modal_Adversarial_Clothing_against_AI_Surveillance_Systems_CVPR_2026_paper.html

**What the source supports:** Thermochromic dyes plus flexible heating were used to create a user-controlled visible/infrared adversarial wearable and physically evaluated under the paper's conditions.

**What it does not establish for this repo:** Product safety, wash durability, manufacturability, battery/heating reliability, or our own efficacy.

**Roadmap impact:** Temperature-adaptive adversarial textiles are no longer purely theoretical. Treat safety, materials durability, aesthetics, and independent replication as the open questions.

### Task-agnostic feature-space attacks against vision foundation models exist

**Status:** Published observation / replication needed  
**Source:** Brian Pulfer et al., *Task-Agnostic Attacks Against Vision Foundation Models*, CVPR Workshops 2025.  
**URL:** https://openaccess.thecvf.com/content/CVPR2025W/AdvML/html/Pulfer_Task-Agnostic_Attacks_Against_Vision_Foundation_Models_CVPRW_2025_paper.html

**What the source supports:** A task-agnostic adversarial objective can disrupt feature representations of vision foundation models and affect multiple downstream tasks; transfer between models is evaluated.

**Roadmap impact:** Replace “self-supervised detectors have no gradient surface via standard loss” with a more precise question: can physically constrained apparel patterns exploit feature-space objectives and transfer across unseen backbones/downstream tasks?

### Physical adversarial LiDAR research exists

**Status:** Published observation / relevance to apparel unproven  
**Source:** Ryunosuke Kobayashi et al., *Invisible but Detected: Physical Adversarial Shadow Attack and Defense on LiDAR Object Detection*, USENIX Security 2025.  
**URL:** https://www.usenix.org/conference/usenixsecurity25/presentation/kobayashi

**What the source supports:** Physical materials/geometry can alter LiDAR point-cloud behavior and affect object detection under the paper's setup; the work also evaluates a defense.

**What it does not support:** A textile-only or normal-apparel LiDAR evasion claim.

**Roadmap impact:** Keep LiDAR in feasibility monitoring until an apparel-compatible mechanism is demonstrated.

---

## Repository-specific evidence boundary

### Pattern Lab browser metrics are not detector results

**Status:** Internally observable implementation fact  
**Repository files:** `analysis.js`, `core.js`

The current browser implementation:

- computes model-named percentages from simple image statistics;
- generates several top-line scores from random values;
- uses the displayed transfer-rate field during “Quick optimize.”

Therefore those values are **DEMO/HEURISTIC**, not internally measured attack success, transfer, stealth, or printability.

### Python benchmark harness exists but a frozen real-model manifest does not

**Status:** Internally implemented software + open evidence gate  
**Repository files:** `ruthless_pipeline/benchmark.py`, `ruthless_pipeline/evaluators.py`, `ruthless_pipeline/scene.py`

The repository has the structure needed for surrogate/held-out evaluation, but product-relevant measurements require exact model/weight/preprocessing/threshold manifests and retained experiment artifacts.

---

## Claims / regulatory monitoring

### FTC substantiation risk for biometric-technology claims

**Status:** Official policy guidance  
**Source:** Federal Trade Commission, *Policy Statement on Biometric Information and Section 5 of the FTC Act* (2023).  
**URL:** https://www.ftc.gov/legal-library/browse/policy-statement-federal-trade-commission-biometric-information-section-5-federal-trade-commission

**Relevant point:** The FTC states that false or unsubstantiated claims relating to validity, reliability, accuracy, performance, fairness, or efficacy of biometric-information technologies can constitute deceptive practices. Real-world claims should be supported by testing that reflects how the technology is actually used.

**Venture implication:** Maintain a claim-substantiation file and tested-condition language for any efficacy statement.

### EU AI Act remote biometric identification is use-case specific

**Status:** Primary legal text; counsel interpretation required  
**Source:** Consolidated Regulation (EU) 2024/1689 text.  
**URL:** https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02024R1689-20260727

**Relevant point:** The Act contains detailed restrictions, exceptions, necessity/proportionality factors, and safeguards concerning certain real-time remote biometric identification in publicly accessible spaces for law enforcement.

**Venture implication:** Avoid simplistic “EU strict/prohibited” summaries. Maintain a jurisdiction/use-case legal register.

### UK biometric guidance is under review

**Status:** Official regulator guidance  
**Source:** UK Information Commissioner's Office biometric-recognition guidance.  
**URL:** https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/biometric-data-guidance-biometric-recognition/

**Relevant point:** ICO pages state that the guidance is under review following changes associated with the Data (Use and Access) Act.

**Venture implication:** Date-stamp UK legal guidance and avoid assuming static EU alignment.

---

## Conference dates — confirmed only from official sources

### CHI 2027

**Status:** Confirmed  
**Official URL:** https://chi2027.acm.org/authors/papers/  
**Paper deadline:** September 10, 2026, Anywhere on Earth.

### ICLR 2027

**Status:** Confirmed  
**Official URL:** https://iclr.cc/Conferences/2027/Dates  
**Abstract deadline:** September 18, 2026, AoE.  
**Paper deadline:** September 25, 2026, AoE.

### USENIX Security 2027 — Cycle 2

**Status:** Confirmed  
**Official URL:** https://www.usenix.org/conference/usenixsecurity27  
**Mandatory registration:** January 19, 2027.  
**Paper submission:** January 26, 2027.

For CVPR 2027, ICCV 2027, IEEE S&P 2027, and ACM CCS 2027, use `TBD` until a current official CFP is verified. Do not infer dates from prior years.

---

## Evidence-register maintenance rule

For each new source add:

```text
source_id
citation/title
official_or_primary_url
publication_date
reviewed_date
evidence_label
task/threat_model
digital_or_physical
models/sensors
conditions
reported_metric + definition
limitations
internal_replication_status
roadmap_impact
claim_impact
```

A paper's headline percentage should never be copied into an internal “current performance” dashboard without the source conditions and evidence label.


## External project review — noRecognition (2026-09-10)

**source_id:** EXT-NORECOGNITION-2026-09-10  
**citation/title:** noRecognition public repository and current research disclosures  
**official_or_primary_url:** [public repository](https://github.com/hevnsnt/norecognition), [research page](https://sandbox.norecognition.org/research)  
**publication_date:** mixed historical/live sources; see pinned versions in the review  
**reviewed_date:** 2026-09-10  
**evidence_label:** External result — replication needed  
**task/threat_model:** task-specific person detection, face detection, and recognition; protocols differ  
**digital_or_physical:** use each source's explicit observation medium  
**models/sensors:** source-specific; not mapped to RAC model identities by nickname  
**conditions:** mixed cohorts, garments, and source versions; not pooled  
**reported_metric + definition:** heterogeneous source metrics; no numeric result imported  
**limitations:** unresolved source inconsistencies and incomplete reproducibility of the current private stack  
**internal_replication_status:** not reproduced  
**roadmap_impact:** bounded evaluation/reporting audit, passes A–C  
**claim_impact:** no RAC efficacy or certification change

See the [detailed review, primary-literature checks, and acceptance criteria](research/NORECOGNITION_REVIEW_2026-09-10.md). This entry is prospective external-research integration; it does not refresh unrelated historical entries above.

# Paper 1 Backlog — Longitudinal D2 Program

> Fill-in protocol: see `README.md` in this directory. NO invented results.
> Every numeric placeholder is marked `[AWAITING: <source artifact>]`.

## 1. Working title and contribution claim

**Working title:** *A Preregistered Longitudinal Study of Cross-Architecture Transfer for Adversarial Clothing Patterns: The RAC D2 Generation Program (D2-0003–D2-0006)*

**Contribution claim (one paragraph):** This paper reports the first longitudinal, fully
preregistered research program on whether surrogate-ensemble optimization of adversarial
clothing patterns transfers to fresh, never-before-seen object-detector architectures.
Across a generation-based design in which every generation is preregistered before execution
and closed before the next is opened, we retain and publish a **negative result (D2-0003)**,
a second closed generation — also a retained negative (FAIL / RAC-D0) — with a canonical
content-addressed release **(D2-0004, protocol RAC-PERSON-DETECT-1.2, one authorized
infrastructure re-run under amendment D2-0004-INFRA-001; log-attested closure,
`releases/RAC-EXP-2026-001/`)**, a preregistered two-arm mean-vs-CVaR objective ablation **(D2-0005)**,
and a prospective **replication policy (D2-0006)** whose hypothesis form is selected
mechanically by a frozen decision tree keyed to D2-0005's preregistered decision regions.
The contribution is both empirical (per-generation sealed surrogate-vs-held-out evidence)
and methodological (a one-shot, fail-closed program structure in which null, negative, and
inconclusive generations are publishable datapoints and the experimental agenda itself is
not open to post-hoc revision).

## 2. Methods skeleton

### 2.1 Program structure and generation-based design
- Generation ladder D2-0003 (retained negative) → D2-0004 (closed 2026-09-08: FAIL / RAC-D0, log-attested; release `releases/RAC-EXP-2026-001/`) → D2-0005 (controlled ablation) → D2-0006 (replication, policy draft only) ← `docs/PREREGISTRATION_D2-0006_DRAFT.md` §4 table.
- One-shot rule and "never re-run silently" semantics ← `docs/PREREGISTRATION_D2-0006_DRAFT.md` §3; `docs/PREREGISTRATION_D2-0005.md` §1 (one-shot rule; publication commitment).
- Status per generation (closed / closing / PREREGISTERED / DRAFT) ← the four docs above, verbatim status lines.

### 2.2 Evaluation protocol (RAC-PERSON-DETECT lineage)
- Task, transform grid (brightness 0.7/1/1.3 × scale 1 × blur σ 0/0.8 × rotation −20/0/20°), decision criteria (min baseline 0.9, max candidate 0.5, min relative reduction 0.25, max invalid-condition fraction 0.10, confidence 0.95) ← `protocols/RAC-PERSON-DETECT-1.2.json`.
- Surrogate/held-out set split and the rule that all models observed in prior D2 runs are surrogate-only ← `protocols/RAC-PERSON-DETECT-1.2.json` notes.
- Protocol evolution 1.0 → 1.2 ← `protocols/RAC-PERSON-DETECT-1.0.json`, `-1.1.json`, `-1.2.json` (diff summary; sha recorded at freeze).

### 2.3 Model sets and frozen manifests
- Surrogate set definition (PERSON-SUR-v3: yolov8n, fasterrcnn_mobilenet_v3_320, detr_resnet50, ssdlite320_mobilenet_v3, retinanet_resnet50_fpn_v2, fcos_resnet50_fpn) ← `docs/PREREGISTRATION_D2-0005.md` header (model_sets/PERSON-SUR-v3.json sha [AWAITING: freeze commit]).
- Held-out set definition (PERSON-HO-v3: fasterrcnn_resnet50_fpn_v2, maskrcnn_resnet50_fpn_v2; state hashes bootstrapped without candidate inference, committed before D2 evaluation) ← `protocols/RAC-PERSON-DETECT-1.2.json` notes; manifest sha [AWAITING: model_sets/PERSON-HO-v3.json freeze].
- Runtime lock (python 3.11, torch 2.14.0+cpu, torchvision 0.29.0+cpu, ultralytics 8.4.142, transformers 4.57.6) ← `docs/AMENDMENT_D2-0004_INFRA-001.md` §6 (benchmarks/runtime_lock.json; NOT to be edited).

### 2.4 Telemetry contract and sealed pre-held-out evidence
- Pre-held-out telemetry frozen and hashed (`frozen_sha256()`) before any held-out inference; held-out outcome append-only ← `ruthless_pipeline/certification/telemetry_contract.py` docstring.
- Lineage binding (candidate → generation → optimization_telemetry → … → certificate), StageRef sha256 == frozen_sha256() ← `ruthless_pipeline/certification/experiment.py` docstring.
- Six-label evidence governance (internally_measured for closed D2 results; amendment A1) ← `docs/PREREGISTRATION_D2-0005.md` §9 A1; `ruthless_pipeline/certification/experiment.py` docstring.

### 2.5 D2-0003: the retained negative generation
- Negative-result record and failure classification ← D2-0003 closed release artifacts [AWAITING: RAC-EXP release id for D2-0003]; failure taxonomy categories ← `ruthless_pipeline/certification/failure_taxonomy.py` (CROSS_ARCHITECTURE_TRANSFER_FAILURE, SURROGATE_OVERFIT).

### 2.6 D2-0004: closure and infrastructure amendment
- Preregistered candidate-selection policy (surrogate-only, heldout_feedback_allowed: false; 100-candidate Product Studio pool; top-k 8→4; frozen winner before held-out inference) ← `docs/AMENDMENT_D2-0004_INFRA-001.md` §4.
- The single authorized infrastructure re-run (step-18 loader crash, root cause, 19-minute version-drift window, runtime_lock hard gate) ← `docs/AMENDMENT_D2-0004_INFRA-001.md` §§1, 3, 5, 6.
- Outcome numbers (held-out rates, verdict) ← `releases/RAC-EXP-2026-001/` plus the log-attested evidence record `manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json` (FAIL / RAC-D0, held-out 1.00 → 1.00, n=36; surrogate-only rate NOT attested — see `not_log_attested_gaps`; narrative: `docs/D2-0004_CLOSURE_NOTE.md`).

### 2.7 D2-0005 and D2-0006 as program continuations
- D2-0005 design summary (cross-reference Paper 5; gating rule "D2-0005 must not open while D2-0004 is open") ← `docs/PREREGISTRATION_D2-0005.md` header.
- D2-0006 interpretation-policy decision tree (§2.1–2.4) and what is frozen now vs decided later ← `docs/PREREGISTRATION_D2-0006_DRAFT.md` §§2–3.

### 2.8 Statistical analysis plan (program level)
- Minimum first analysis: three or more closed generations; negative generations remain in the dataset ← `docs/PAPER_SERIES.md` Paper 1.
- Per-generation Wilson intervals and sealed statistics; no cross-generation pooling that violates one-shot semantics ← `docs/PREREGISTRATION_D2-0005.md` §3 (Wilson z = 1.959963984540054).

### 2.9 Reproducibility and release format
- Content-addressed release bundle layout (experiment.json, MANIFEST.json, RELEASE.json, REVISIONS.json, FAILURE.json) ← `docs/RESEARCH_RELEASE_FORMAT.md`; `ruthless_pipeline/certification/release_format.py` docstring.
- Source commit, candidate hashes, frozen manifests per generation ← [AWAITING: per-generation release ids].

## 3. Figure caption drafts (F1–F4 scaffolds)

- **F1 — Surrogate-vs-held-out transfer scatter.** One point per closed D2 generation:
  frozen surrogate mean detection rate vs. sealed held-out mean detection rate. Filled
  strictly from sealed `TelemetryRecord`s (`pre.surrogate_mean_detection_rate`,
  `outcome.heldout_detection_rates`); records without attached outcomes are never plotted
  as estimates. Point coordinates: D2-0003 populated in the scaffold; D2-0004 **cannot be
  plotted on F1** — its surrogate mean detection rate is not log-attested
  (`not_log_attested_gaps` in `manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json`);
  further generations
  [AWAITING: D2-0005 release id], [AWAITING: D2-0006 release id]. Scaffold:
  `manuscript/figures/F1_transfer_scatter.json`.
- **F2 — Generation timeline.** Closure date vs. held-out mean detection rate, one series
  per generation, from `experiment.json` plus sealed telemetry `outcome.recorded_utc`.
  Dates/rates: D2-0003 (2026-09-07, 1.0) and D2-0004 (2026-09-08, 1.0) populated in the
  scaffold; further generations [AWAITING: closed release ids per generation]. Scaffold:
  `manuscript/figures/F2_generation_timeline.json`.
- **F3 — Architecture disagreement.** Per-candidate population variance, spread, and max
  pairwise delta of per-surrogate detection rates, recomputed inside
  `PreHeldOutTelemetry.validate()` so sealed values cannot drift. Values:
  [AWAITING: sealed pre-held-out telemetry per closed generation]. Scaffold:
  `manuscript/figures/F3_architecture_disagreement.json`.
- **F4 — Transformation robustness.** Heatmap of per-transform candidate detection rates
  per experiment over the RAC-PERSON-DETECT-1.2 transform grid; cells never imputed.
  Values: [AWAITING: sealed `transformation_rates` mappings per closed generation].
  Scaffold: `manuscript/figures/F4_transformation_robustness.json`.

## 4. Citation placeholder list

- [CITE: adversarial patches — foundational work on printable adversarial perturbations against image classifiers/detectors]
- [CITE: adversarial clothing / wearable adversarial patterns against person detectors]
- [CITE: physical-world adversarial examples — print-and-photograph robustness studies]
- [CITE: expectation-over-transformation (EOT) optimization for physical robustness]
- [CITE: object detection architectures — two-stage (Faster/Mask R-CNN), single-stage (YOLO, SSD, RetinaNet, FCOS), transformer (DETR)]
- [CITE: model ensembles and surrogate-model transfer in black-box adversarial attack literature]
- [CITE: cross-architecture / cross-model transfer failure of adversarial examples]
- [CITE: preregistration and registered reports methodology in experimental science]
- [CITE: one-shot / sequential preregistered experiment governance and replication programs]
- [CITE: publication of negative and null results; file-drawer problem]
- [CITE: content-addressed / reproducible research artifact standards (hash-pinned releases)]

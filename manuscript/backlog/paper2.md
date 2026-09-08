# Paper 2 Backlog — Physical P1 Garment Study

> Fill-in protocol: see `README.md` in this directory. NO invented results.
> Every numeric placeholder is marked `[AWAITING: <source artifact>]`.

## 1. Working title and contribution claim

**Working title:** *Physical Evaluation of a Preregistered Adversarial Garment: A Calibration-Gated, Stopping-Rule-Controlled Print-and-Photograph Study (RAC-P1)*

**Contribution claim (one paragraph):** This paper reports the physical (RAC-P1) evaluation
of the adversarial garment candidate produced by the preregistered digital pipeline,
conducted under a calibration-gated capture rig with a stopping rule frozen before the
first garment capture. The study uses a matched CONTROL/CANDIDATE paired-trial design over
a planned grid of 3 distances (1/3/5 m) × 3 yaw angles (−45/0/+45°) × 1 pitch × 1 locked
lighting variant × 2 poses × 8 repetitions (144 planned matched-pair trials, minimum 93
valid), with every capture session bracketed by a colorimetric calibration-target
measurement whose acceptance gates (mean ΔE2000 ≤ 6.0, scale error ≤ 2%, registration
error ≤ 3 mm) must pass before and after capture. Because the valid-trial semantics make
the physical control detection rate 1.0 by construction, the primary endpoint is a paired
risk difference with Wilson and deterministic-seed bootstrap intervals evaluated against a
preregistered interval-width stopping rule — a fail-closed physical evaluation in which
control-undetected conditions are invalid measurement conditions, never candidate successes.

## 2. Methods skeleton

### 2.1 Candidate garment and provenance
- Candidate identity and hash ← sealed candidate artifact from the D2 generation release [AWAITING: D2-0004 release id].
- Physical production SOP and golden-sample QA ← `docs/PRINTFUL_PRODUCTION_SOP.md`, `docs/PRODUCTION_ALPHA_SKU.md` (certificate stage artifact [AWAITING: sku/certificate stage refs]).

### 2.2 Preregistered stopping rule
- min_valid_trials = 93, max_valid_trials = 144, target_interval_width = 0.20, z = 1.959963984540054, require_interval_below_half ← `physical/p1/STOPPING_RULE.json`.
- Matched-pair semantics (control rate 1.0 by construction; Δ = 1 − candidate_rate via `trial_statistics._bootstrap_risk_difference_interval`) ← `physical/p1/STOPPING_RULE.json` derivation block; `ruthless_pipeline/certification/trial_statistics.py` docstring.
- Frozen-before-data commitment ← `physical/p1/STOPPING_RULE.json` ("must be committed before the first P1 garment capture and may not be edited after data collection begins").
- Invalid-condition rule ← `physical/p1/STOPPING_RULE.json` invalid_condition_rule; `ruthless_pipeline/certification/trial_statistics.py` (invalid-condition accounting).

### 2.3 Calibration rig and session gating
- Calibration target (RAC-CALT-P1-0001, 100 mm scale bar, same printer/substrate profile as garments) ← `physical/p1/CALIBRATION_MANIFEST.json` target block.
- Camera/lighting lock (manual mode, exposure lock, fixed ISO/aperture/shutter/WB, RAW capture, 15-minute warmup, ambient control) ← `physical/p1/CALIBRATION_MANIFEST.json` camera/lighting blocks [AWAITING: completed calibration session manifest — FILL-IN fields].
- Patch measurement procedure (fiducials, homography, rectification, CIELAB D65/2 sampling, PrintCameraProfile via `calibration_ingest`) ← `physical/p1/CALIBRATION_MANIFEST.json` patch_measurement_procedure; `ruthless_pipeline/certification/calibration_ingest.py` (`delta_e_2000`, CIEDE2000).
- Acceptance criteria (ΔE2000 ≤ 6.0, scale ≤ 2%, registration ≤ 3 mm; bracketing before/after; drift failure invalidates the session) ← `physical/p1/CALIBRATION_MANIFEST.json` acceptance_criteria.
- Capture angles (yaw −45/0/+45°, pitch 0°) and rig spec ← `physical/p1/CALIBRATION_MANIFEST.json` capture_angles; `physical/p1/CAMERA_LIGHTING_SETUP.md`; `docs/P1_CAPTURE_RIG_SPEC.md`.

### 2.4 Trial design and ingestion
- Session manifest and trial ingestion templates ← `physical/p1/SESSION_MANIFEST_TEMPLATE.json`, `physical/p1/PHYSICAL_TRIAL_INGESTION_TEMPLATE.json`.
- Naming convention and per-capture hashing ← `physical/p1/CAPTURE_NAMING_CONVENTION.md`.
- Evidence label: internally_measured; becomes RAC-P evidence only when bound into a session ExperimentArtifact with the physical_session stage ← `physical/p1/CALIBRATION_MANIFEST.json` evidence labels note.

### 2.5 Capture workflow (blinding)
- Capture Lab sequence Experiment → Calibration → Control → Candidate → Motion → Review → Seal; outcome blinding during capture ← `docs/CAPTURE_LAB.md` (cross-reference Paper 3 for full methodology).

### 2.6 Statistical analysis plan
- Paired control/candidate comparison, Wilson score intervals, deterministic-seed bootstrap paired difference, effect sizes (risk difference, Haldane-corrected odds ratio), minimum-sample planning ← `ruthless_pipeline/certification/trial_statistics.py` docstring.
- Primary endpoint values (candidate detection rate, Δ, intervals, stopping decision) ← [AWAITING: P1 physical session release id].
- Certification boundary: physical evidence is required for RAC-P1/P2/M1/M2 states; digital evidence may never satisfy a physical state ← `protocols/RAC-PERSON-DETECT-1.2.json` physical_required_for; `docs/CERTIFICATION_SYSTEM.md`.

### 2.7 Reproducibility
- Release bundle with physical_session stage and append-only certificate additions ← `docs/RESEARCH_RELEASE_FORMAT.md` §5; `ruthless_pipeline/certification/release_format.py` docstring.
- Source commit, rig checklist ← `physical/p1/RIG_MEASUREMENT_CHECKLIST.md` [AWAITING: session source commit].

## 3. Figure caption drafts

No F1–F8 scaffold is allocated to Paper 2 (per `manuscript/FIGURE_SPECIFICATIONS.md`,
scaffolds serve Papers 1 and 5). Paper-specific figure placeholders:

- **Fig P2-1 — Calibration acceptance over sessions.** Per-session mean ΔE2000, scale
  error %, and registration error (mm) against the three acceptance gates, before/after
  bracketing pairs. Values: [AWAITING: completed PrintCameraProfile artifacts
  RAC-PCP-* per session].
- **Fig P2-2 — Paired trial outcomes on the capture grid.** Candidate vs control
  detections across distance × yaw × pose cells, with invalid conditions shown explicitly
  (never counted as candidate successes). Values: [AWAITING: P1 physical session release id].
- **Fig P2-3 — Stopping-rule trajectory.** Wilson interval width of the paired risk
  difference vs accumulated valid trials, with the 0.20 target-width line and the 93/144
  valid-trial bounds. Values: [AWAITING: P1 physical session release id].

## 4. Citation placeholder list

- [CITE: physical-world adversarial examples — print-and-photograph evaluation methodology]
- [CITE: adversarial clothing / wearable patterns evaluated on real garments under viewpoint variation]
- [CITE: camera/ISP and colorimetric calibration for reproducible image capture (CIEDE2000, CIELAB)]
- [CITE: expectation-over-transformation and physically realizable perturbation constraints]
- [CITE: matched-pair / paired binary outcome statistics — Wilson intervals, bootstrap risk differences]
- [CITE: preregistered stopping rules and sequential analysis in experimental design]
- [CITE: invalid-condition / measurement-validity accounting in human-subject or pose-based capture studies]
- [CITE: object detection under distribution shift — viewpoint, distance, lighting variation]

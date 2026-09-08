# Paper 3 Backlog — Capture Lab Methodology

> Fill-in protocol: see `README.md` in this directory. NO invented results.
> Every numeric placeholder is marked `[AWAITING: <source artifact>]`.

## 1. Working title and contribution claim

**Working title:** *Capture Lab: A Blinded, Calibration-Gated Browser Workflow for Matched Control/Candidate Physical Adversarial-Garment Evaluation*

**Contribution claim (one paragraph):** We present Capture Lab, a sequential browser-based
workflow that operationalizes the RAC physical-evaluation SOP as a scientifically
constrained user interface: experiment binding → calibration gate → blinded matched
CONTROL/CANDIDATE capture (JPEG stills and short WebM motion) → review → cryptographic
seal. Detector outcomes are deliberately hidden from the operator during pair collection,
preventing pose/framing adaptation in response to live detector feedback; the browser never
fabricates detector output — frozen captures are analyzed by an authorized local model
runner against a frozen analysis manifest (model IDs, thresholds, preprocessing, identity
mode) and ingested into the Research OS as hash-addressed session evidence. The system
enforces an explicit recognition boundary (person/object detection only; identity matching
disabled by default and out of scope without a consent-based closed-set protocol), making
it a reusable methodology artifact for reproducible, blinded physical-world adversarial
evaluation.

## 2. Methods skeleton

### 2.1 System overview and design principles
- Sequential UX and scope list (live preview, frozen session manifest, evidence classes, matched capture, per-capture SHA-256, condition/arm ledger, calibration gate, frozen ensemble analysis contract, blinding, session export, seal gate) ← `docs/CAPTURE_LAB.md` Scope section.
- Evidence classes: printed-flat prototype / physical garment P1 / synthetic dry run ← `docs/CAPTURE_LAB.md`.

### 2.2 Scientific UX sequence and blinding
- Stage order Experiment → Calibration → Control → Candidate → Motion → Review → Seal ← `docs/CAPTURE_LAB.md` Scientific UX.
- Outcome blinding rationale (no live detector feedback to the operator) ← `docs/CAPTURE_LAB.md` Scientific UX.

### 2.3 Calibration gate integration
- Gate semantics: a session may start only if `PrintCameraProfile.acceptance()` passes; post-capture re-run, drift failure invalidates the session ← `physical/p1/CALIBRATION_MANIFEST.json` patch_measurement_procedure step 7 and acceptance_criteria.
- Calibration target and locked camera/lighting parameters ← `physical/p1/CALIBRATION_MANIFEST.json` (values [AWAITING: completed calibration session manifest]).

### 2.4 Frozen analysis contract and local analyzer boundary
- Frozen manifest fields (model IDs, thresholds, preprocessing, identity_mode) ← `docs/CAPTURE_LAB.md` Local analysis contract.
- Frame-level prediction schema (model/version, class, confidence, …) ← `docs/CAPTURE_LAB.md` Local analysis contract.
- "The browser deliberately does not fabricate detector output" — analysis hand-off ← `docs/CAPTURE_LAB.md`.

### 2.5 Recognition boundary and ethics
- Detection vs face detection vs identity matching; identity_mode: disabled default; consent-based closed-set requirement if ever added ← `docs/CAPTURE_LAB.md` Recognition boundary.

### 2.6 Session export, sealing, and Research OS ingestion
- Session export format, per-capture SHA-256, seal gate ← `docs/CAPTURE_LAB.md`.
- Ingestion as ExperimentArtifact physical_session stage with StageRef sha256 lineage ← `ruthless_pipeline/certification/experiment.py` docstring; `physical/p1/SESSION_MANIFEST_TEMPLATE.json`; `physical/p1/PHYSICAL_TRIAL_INGESTION_TEMPLATE.json`.
- Naming convention ← `physical/p1/CAPTURE_NAMING_CONVENTION.md`.

### 2.7 Relationship to the P1 study and certification states
- Capture Lab as the capture surface for the RAC-P1 stopping-rule study (cross-reference Paper 2) ← `physical/p1/STOPPING_RULE.json`; `docs/CERTIFICATION_SYSTEM.md` evidence states.
- Observation validity (valid/invalid/excluded; control-undetected invalid) ← `docs/CERTIFICATION_SYSTEM.md` Observation validity.

### 2.8 Limitations
- Single-rig, single-environment evaluation; identity research out of scope; internal verification framework, not accredited certification ← `docs/CERTIFICATION_SYSTEM.md` preamble; `docs/CAPTURE_LAB.md`.

## 3. Figure caption drafts

No F1–F8 scaffold is allocated to Paper 3. Paper-specific figure placeholders:

- **Fig P3-1 — Workflow state machine.** The seven-stage sequence with gate annotations
  (calibration gate before Control; seal gate at export) and the blinding window shaded.
  Diagram from `docs/CAPTURE_LAB.md` scope/sequence — no numeric data required.
- **Fig P3-2 — Evidence lineage of one captured session.** Capture files → SHA-256 ledger →
  local analyzer predictions → ExperimentArtifact physical_session StageRef → release
  bundle. Stage hashes: [AWAITING: first sealed Capture Lab session artifact].
- **Fig P3-3 — Calibration gate example.** Before/after bracketing ΔE2000 / scale /
  registration measurements against acceptance thresholds for one real session.
  Values: [AWAITING: completed PrintCameraProfile artifact RAC-PCP-*].

## 4. Citation placeholder list

- [CITE: blinding and outcome concealment in measurement protocols to prevent operator bias]
- [CITE: human-in-the-loop bias in interactive ML evaluation interfaces]
- [CITE: browser-based data collection platforms for vision experiments (webcam capture, in-browser UX)]
- [CITE: cryptographic sealing / hash chaining for evidence integrity in data collection pipelines]
- [CITE: physical-world adversarial example capture methodology — matched controls and condition ledgers]
- [CITE: ethical boundaries in person-detection research — recognition vs identification, consent-based protocols]
- [CITE: reproducible research tooling — frozen analysis manifests and literate/computable session records]

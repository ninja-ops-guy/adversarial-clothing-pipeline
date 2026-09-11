# RAC Capture Lab

**Version:** 1.4.0  
**Surface:** `capture-lab.html`  
**Primary execution path:** `docs/RESEARCH_WORKBENCH.md`

Capture Lab turns the P1/printed-prototype SOP into a sequential browser workflow and now hands sealed sessions directly to the RAC Research Workbench when the local runtime is connected.

## Scope

Implemented:

- camera permission and live preview;
- frozen session manifest;
- explicit evidence class: printed-flat prototype, physical garment P1, or synthetic dry run;
- matched CONTROL/CANDIDATE capture;
- JPEG still capture;
- short WebM motion capture;
- SHA-256 per capture;
- condition/arm ledger;
- calibration gate;
- frozen ensemble analysis contract;
- outcome blinding during capture;
- session export;
- seal gate;
- direct staging into the local Workbench workspace;
- responsive GitHub Pages UI.

The browser deliberately does **not** fabricate detector output. Frozen captures are analyzed by the authorized RAC research runtime and then ingested into the Research OS.

## Scientific UX

Sequence:

`Experiment → Calibration → Control → Candidate → Motion → Review → Seal`

Capture outcomes are hidden while collecting the pair. This prevents the operator from changing pose/framing in response to live detector feedback.

## Research Workbench behavior

When Capture Lab is opened through the local Workbench (`rac-platform --open` or `run-rac-platform.bat`):

1. the page detects the loopback research runtime;
2. the operator completes and seals the capture normally;
3. the sealed session is staged under `.rac-runtime/workspace/sessions/<session-id>/`;
4. original `control/` and `candidate/` relative paths are preserved;
5. only local workspace paths are remembered in browser local storage;
6. the Research Console can immediately validate, analyze, and ingest the session.

If the runtime is not connected, Capture Lab retains the existing browser-download fallback.

Raw capture data is intentionally excluded from git by `.gitignore`.

## Recognition boundary

Capture Lab distinguishes:

1. person/object detection;
2. face detection;
3. identity matching.

General stranger identification is outside this surface. If identity-matching research is later added, it must be a consent-based closed-set protocol with explicit enrollment and local-only reference data. The default analysis manifest has `identity_mode: disabled`.

## Local analysis contract

The model manifest text area freezes:

- model IDs;
- thresholds;
- preprocessing;
- identity mode;
- motion sampling when enabled.

The sealed session is then consumed by the existing frozen analyzer. The operator does not need to invoke it manually when using the Research Workbench.

The analyzer produces provenance-bearing predictions including:

- model/version;
- class;
- confidence;
- boxes;
- frame/timestamp;
- inference metadata.

Sequence aggregation and physical statistics happen downstream; frames remain nested observations.

## Paper prototypes

Use evidence class `printed_flat_prototype` for paper prints. These trials are useful for printer/camera/frequency-survival experiments but never automatically become RAC-P1 garment evidence.

## P1

Use `physical_garment_p1` only after the P1 preregistration, rig, calibration, matched SKU pair, model manifests, and stopping rule are frozen.

Control-undetected conditions remain INVALID downstream.

## Camera requirements

GitHub Pages and the local Workbench are browser surfaces. Modern browsers can expose `getUserMedia` after user permission. Device/browser support varies. The app fails visibly when camera permission is denied or unsupported.

## Frozen inference and motion analysis

The Workbench invokes `scripts/analyze_capture_session.py` behind the UI. The underlying runner remains authoritative and:

- requires a sealed session by default;
- verifies every capture hash;
- verifies model IDs, state hashes and thresholds against frozen benchmark/model manifests;
- loads only models named by the session analysis contract;
- runs real person-detection inference on captured stills;
- retains raw boxes, labels, scores and target-person scores;
- writes content-hashed `inference.json`;
- marks control-undetected model conditions invalid;
- keeps frame observations explicitly nested;
- refuses identity-matching mode.

Motion analysis remains implemented through `scripts/analyze_capture_motion.py` and `--include-motion`. FFmpeg/ffprobe are required on the machine running the Workbench. The frozen motion contract currently uses 2 fps, at most 120 frames per video, and sequence-level aggregation.

Capture Lab ships a SUR-v3 preset for ordinary authorized research and an HO-v3 preset visibly labeled fresh held-out. HO-v3 must not be used for optimization or candidate selection.

## Research OS ingestion

The Research Console invokes `scripts/ingest_capture_inference.py` behind the UI.

For each sealed matched session it:

1. verifies session/inference lineage;
2. requires capture integrity PASS;
3. enforces the calibration gate for `physical_garment_p1`;
4. applies the conservative P1 decision rule: **all frozen models must detect the control; any frozen model detecting the candidate counts as candidate detection**;
5. converts the result to `PhysicalTrial`;
6. runs paired statistics, invalid-condition accounting and the preregistered stopping rule;
7. appends the matched trial to the cumulative trial store when eligible;
8. can register physical-session lineage in the Research OS when real frozen candidate/generation hashes are supplied.

Use one cumulative trial store across the preregistered P1 experiment. Do not count video frames as trials.

## Current boundary

Capture Lab + Research Workbench now close the platform path for **local acquisition, sealed-session staging, frozen person-detection inference, temporal aggregation, P1 trial conversion, statistics and Research OS lineage operations**.

This still does not manufacture physical evidence. RAC-P1 requires the real garment, accepted calibration, preregistered conditions, and completed matched sessions.

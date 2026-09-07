# RAC Capture Lab

**Version:** 1.0.0  
**Surface:** `capture-lab.html`

Capture Lab turns the P1/printed-prototype SOP into a sequential browser workflow.

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
- responsive GitHub Pages UI.

The browser deliberately does **not** fabricate detector output. Frozen captures are analyzed by the authorized local model runner and then ingested into the Research OS.

## Scientific UX

Sequence:

`Experiment → Calibration → Control → Candidate → Motion → Review → Seal`

Capture outcomes are hidden while collecting the pair. This prevents the operator from changing pose/framing in response to live detector feedback.

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
- identity mode.

The exported session is intended for a local analyzer that produces frame-level predictions:

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

GitHub Pages is HTTPS, so modern browsers can expose `getUserMedia` after user permission. Device/browser support varies. The app fails visibly when camera permission is denied or unsupported.

## Next integration

The next backend layer should be an authorized local Capture Lab runner that:

- opens a sealed session;
- validates hashes;
- runs the frozen detector ensemble;
- writes `inference.json`;
- computes sequence summaries;
- emits PhysicalTrial-compatible records;
- refuses identity matching unless an explicit closed-set consent manifest exists;
- hands the sealed result to calibration/statistics/release tooling.

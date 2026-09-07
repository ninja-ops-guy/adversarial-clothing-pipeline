# RAC Capture Lab

**Version:** 1.2.0  
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

## Frozen local inference runner

Implemented in `scripts/analyze_capture_session.py`. The runner:

- requires a sealed session by default;
- verifies every capture hash;
- verifies model IDs, state hashes and thresholds against the frozen benchmark/model manifests;
- loads only the models named by the session analysis contract;
- runs real person-detection inference on captured stills;
- retains raw boxes, labels, scores and target-person scores;
- writes content-hashed `inference.json` with per-model control/candidate summaries;
- marks control-undetected model conditions invalid;
- keeps still/frame observations explicitly nested rather than treating them as independent trials;
- refuses any identity-matching mode.

Capture Lab ships a SUR-v3 preset for ordinary authorized research and an HO-v3 preset visibly labeled fresh held-out. HO-v3 must not be used for optimization or candidate selection.

Run locally after exporting a sealed session directory:

```bash
python scripts/analyze_capture_session.py RAC-CAP-...-session.json --output inference.json
```

Install the benchmark detector dependencies before first use. Model downloads/cache behavior follows the existing benchmark stack.

### Motion analysis

Implemented in `scripts/analyze_capture_motion.py` and integrated behind `--include-motion` in the main runner. Motion analysis requires `ffmpeg` and `ffprobe` on the local workstation. The session freezes a `motion_sampling` contract before analysis; current Capture Lab presets use 2 fps, at most 120 frames per video, and `sequence_fraction` aggregation.\n\nThe runner deterministically extracts frames, executes the same frozen person-detection ensemble, and records per sequence/model:\n\n- frame count;\n- detection fraction;\n- mean/max target confidence;\n- longest continuous detected run;\n- longest detection gap;\n- frozen aggregation rule.\n\nFrames remain nested within a video sequence. Sequence summaries, not raw frame count, are the appropriate inputs to later physical inference.\n\nRun both still and motion analysis with:\n\n```bash\npython scripts/analyze_capture_session.py RAC-CAP-...-session.json --include-motion --output inference.json\n```\n\nThe runner still refuses identity matching. Motion support is for person-detection research under the frozen authorized ensemble.

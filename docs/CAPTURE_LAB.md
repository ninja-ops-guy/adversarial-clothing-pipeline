# RAC Capture Lab

**Version:** 1.5.0  
**Surface:** `capture-lab.html`  
**Primary execution path:** `docs/RESEARCH_WORKBENCH.md`

Capture Lab is the browser instrument for preregistered capture. In the local Research Workbench it now binds real P1 work directly to the frozen 144-trial schedule and measured calibration brackets before handing sealed sessions to validation, inference, statistics, and Research OS ingestion.

## Scope

Implemented:

- camera permission and live preview;
- frozen session manifest;
- explicit evidence classes for printed-flat prototypes, physical garment P1, and synthetic dry runs;
- matched CONTROL/CANDIDATE still and motion capture;
- SHA-256 per capture and condition/arm ledger;
- direct frozen P1 schedule binding through the local runtime;
- locked P1 trial ID, distance, yaw, pitch, pose, lighting variant, and first-arm order;
- measured pre/post `PrintCameraProfile` intake for physical P1;
- 48-patch / scale / four-fiducial completeness checks;
- frozen ΔE2000 / scale / registration acceptance criteria;
- exact calibration-source text and SHA-256 preservation for Python re-validation;
- frozen detector ensemble analysis contract;
- outcome blinding during capture;
- session export and seal gate;
- direct staging into the private local Workbench workspace;
- responsive static/read-only GitHub Pages fallback.

The browser deliberately does **not** fabricate detector output or measured calibration evidence. Frozen captures and exact calibration sources are re-validated by the authorized RAC research runtime before a physical session may advance.

## Scientific UX

Sequence:

`Experiment → Calibration → Control → Candidate → Motion → Review → Seal`

For physical P1 the detailed gate is:

`next frozen trial → accepted PRE calibration → frozen capture → accepted POST calibration → seal → validate → analyze → ingest`

Capture outcomes remain hidden while collecting the pair so framing/pose cannot be adjusted in response to detector feedback.

## Frozen P1 schedule

Selecting `physical_garment_p1` requires the local Workbench runtime. **Load Next Frozen P1 Trial** queries the runtime's derivation of `RAC-P1-PAIRING-2026-001` and the cumulative local trial store. The next incomplete `RAC-P1-T-####` is loaded and the following values are locked into the session:

- schedule SHA-256;
- execution position and cell/repetition;
- trial ID;
- distance, yaw, and pitch;
- pose;
- lighting variant;
- frozen CONTROL/CANDIDATE first-arm order.

The schedule itself is not rewritten by Capture Lab. Validation independently re-derives it and refuses any drift.

## Measured calibration brackets

Physical P1 no longer uses the manual browser checkbox as its calibration authority. It requires measured pre- and post-capture `PrintCameraProfile` JSON inputs.

Each profile must contain:

- exactly 48 measured color patches;
- at least two scale observations;
- exactly `FID-TL`, `FID-TR`, `FID-BL`, and `FID-BR` registration measurements;
- the session camera ID and lighting ID;
- a timezone-aware `created_utc`;
- a valid RAC profile ID.

The frozen acceptance thresholds remain:

- mean ΔE2000 ≤ 6.0;
- absolute scale error ≤ 2.0%;
- maximum registration error ≤ 3.0 mm.

An accepted pre profile is required before a physical session can freeze. An accepted, distinct, later post profile is required before it can seal. Capture Lab retains the exact JSON source text and SHA-256 for each bracket. `scripts/validate_capture_session.py` then re-parses and re-evaluates those exact bytes through `p1_calibration_binding.py`; the browser calculation is operator feedback, not the final evidence authority.

Prototype/synthetic evidence classes retain a manual calibration acknowledgment because they are not eligible for the P1 cumulative store.

## Research Workbench behavior

When Capture Lab is opened through `rac-platform --open` or `run-rac-platform.bat`:

1. the page detects the loopback runtime;
2. physical P1 can load the next frozen schedule entry;
3. the operator completes measured pre calibration and matched capture;
4. the operator completes measured post calibration and freezes the ensemble analysis contract;
5. sealing stages the session under `.rac-runtime/workspace/sessions/<session-id>/` with the original `control/` and `candidate/` paths preserved;
6. Research Console enforces **Validate → Analyze → Ingest** for that staged session.

If the runtime is absent, physical P1 schedule execution remains unavailable. Prototype/static capture still retains the download fallback.

Raw capture data is intentionally excluded from git.

## Recognition boundary

Capture Lab's governed analysis surface is person/object detection. General stranger identification is outside this surface. Identity matching remains disabled by default; any future identity experiment would require a separate consent-based, closed-set protocol.

## Frozen analysis contract

The model manifest freezes model IDs, thresholds, preprocessing, identity mode, and motion sampling. The Workbench invokes `scripts/analyze_capture_session.py`; browser heuristics are never detector evidence.

The analyzer verifies capture hashes and frozen model identities/thresholds, runs the named person-detection ensemble, preserves provenance-bearing frame/sequence results, and keeps video frames nested rather than treating them as independent trials.

Motion analysis continues through the existing FFmpeg/ffprobe path. The current motion contract uses 2 fps, at most 120 frames per video, and sequence-level aggregation.

Capture Lab exposes SUR-v3 for ordinary authorized research and labels HO-v3 as fresh held-out. Held-out evaluation must not be used for optimization or candidate selection.

## Research OS ingestion

Research Console invokes `scripts/ingest_capture_inference.py` only after the staged session validation and frozen analysis steps have succeeded in the current platform workflow.

For a real P1 session the combined path preserves the frozen `RAC-P1-T-####` identity, verifies calibration/schedule/capture integrity, applies the conservative matched-control decision rule, updates cumulative paired statistics and the preregistered stopping rule, and appends an eligible trial only once.

Use one cumulative trial store across the preregistered P1 experiment. Video frames remain nested observations and are never counted as independent trials.

## Current boundary

Capture Lab + Research Workbench now provide the platform control plane for **frozen trial selection, calibration admission, local acquisition, sealed-session staging, detector inference, temporal aggregation, P1 trial conversion, cumulative statistics, and Research OS lineage operations**.

The platform does not manufacture the physical garment or calibration target and does not invent physical measurements. Those remain real-world experimental inputs; their measured data and all subsequent governed research operations are handled inside the platform workflow.

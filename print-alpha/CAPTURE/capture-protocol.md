# RAC-PRINT-ALPHA-001 — Capture Protocol

Condensed operational protocol for capturing the matched control/candidate
print-alpha garments. This document **summarizes** the authoritative sources;
where anything appears to conflict, the sources win:

- `docs/P1_CAPTURE_RIG_SPEC.md` — rig, session hierarchy, validity rules
- `physical/p1/CAMERA_LIGHTING_SETUP.md` — locked camera/lighting sheet
- `physical/p1/STOPPING_RULE.json` — preregistered stopping/invalidity rule
- `ruthless_pipeline/physical_protocol.py::capture_rows` — trial matrix (108 rows)

## Evidence boundary

`physical_efficacy_claimed = false`; `evidence_class = experimental_print_specimen`.
Capture produces manufacturing-specimen measurement data only.

## 1. Trial matrix (108 matched rows)

The preregistered grid (exported byte-deterministically to
`print-alpha/CAPTURE/trial-sheet.csv` by `scripts_print_alpha/export_trial_sheet.py`):

- distance: 2, 5, 8 m
- yaw: 0°, +30°, −30° (pitch locked at 0°)
- pose: standing, walking
- lighting: indoor-even, daylight-even
- repeats: R1, R2, R3
- wash state: W0 (garments never laundered before/during capture)

3 × 3 × 2 × 2 × 3 = **108 trials**, each producing one `__control.jpg` and one
`__candidate.jpg` under `captures/`. Trial IDs are deterministic:
`D{dist:02d}_Y{yaw:+03d}_P0_{POSE}_{LIGHTING}__R{repeat}`.

## 2. Session rules (from P1_CAPTURE_RIG_SPEC.md)

- Primary statistical unit: garment × actor × session; frames are nested
  observations, not independent trials.
- Matched control and candidate use the same product, size, substrate,
  manufacturing process, actor, session, path, camera, and lighting state.
- Camera positions and actor marks are taped; settings are locked after the
  calibration exposure and never changed mid-session. Any threshold/camera
  change after observing candidate results is a **new experiment**.
- Calibration target RAC-CALT-P1-0001 is captured in-frame or bracketed at
  session start and end; lighting drift > 5% invalidates the session.

## 3. Validity and stopping (from STOPPING_RULE.json)

- Invalid measurement conditions (see `invalid-condition-rules.json`) are
  excluded from `valid_trials` and reported via `invalid_condition_report`.
- **Control-undetected trials are invalid measurement conditions, never
  candidate successes.**
- Planned bounds: min 93 / max 144 valid trials, target interval width 0.20
  (z = 1.959963984540054). The stopping rule file is frozen before the first
  capture and may not be edited after data collection begins.

## 4. File naming

Per `physical/p1/CAPTURE_NAMING_CONVENTION.md`; session metadata per
`physical/p1/SESSION_MANIFEST_TEMPLATE.json`; ingestion per
`physical/p1/PHYSICAL_TRIAL_INGESTION_TEMPLATE.json`.

# P1 Pre-Session Rig Measurement Checklist

Complete every item before the first garment capture of a session. Any FAIL
stops the session until corrected. Initial each line.

## Rig geometry

- [ ] PASS / FAIL — Camera-to-garment distance measured with a tape/laser and matches the session manifest value.
- [ ] PASS / FAIL — Camera height measured and matches the setup sheet.
- [ ] PASS / FAIL — Garment plane parallel to sensor plane (fiducial left/right scale agreement within 2%).
- [ ] PASS / FAIL — Floor/board yaw marks for -45 / 0 / +45 deg verified with an angle gauge.

## Calibration target

- [ ] PASS / FAIL — Printed target `RAC-CALT-P1-0001` verified: the 100 mm scale bar measures 100.0 +/- 0.5 mm with a ruler.
- [ ] PASS / FAIL — All four fiducials are visible and unobstructed in the calibration frame.
- [ ] PASS / FAIL — Scale bar fully inside the frame, not clipped at any session distance.
- [ ] PASS / FAIL — `calibration-target-manifest.json` SHA-256 matches the PNG used on the day.

## Lighting

- [ ] PASS / FAIL — Fixtures at taped positions; nothing moved since lock-in.
- [ ] PASS / FAIL — >= 15 min warm-up completed.
- [ ] PASS / FAIL — Color temperature matches the setup sheet (all fixtures identical).
- [ ] PASS / FAIL — Ambient light at garment plane within the setup-sheet bound (blackout intact).
- [ ] PASS / FAIL — Light-meter reading at garment centre recorded (pre-session baseline).

## Camera

- [ ] PASS / FAIL — Manual mode; exposure locked; auto WB off.
- [ ] PASS / FAIL — ISO / aperture / shutter / Kelvin match the setup sheet.
- [ ] PASS / FAIL — RAW capture enabled and storage verified.

## Calibration acceptance (calibration_ingest thresholds)

- [ ] PASS / FAIL — Bracketing calibration capture ingested into a `PrintCameraProfile`; mean Delta-E 2000 <= 6.0.
- [ ] PASS / FAIL — Scale error <= 2% on every scale measurement.
- [ ] PASS / FAIL — Max fiducial registration error <= 3 mm.
- [ ] PASS / FAIL — Profile id assigned (`RAC-PCP-<version>-<seq>`) and recorded in the session manifest.

## Session paperwork

- [ ] PASS / FAIL — Session manifest (SESSION_MANIFEST_TEMPLATE.json) filled: session_id, date, operator, SKUs (candidate / control / reserves), environment.
- [ ] PASS / FAIL — Capture naming convention loaded; first filename dry-checked against the grammar in CAPTURE_NAMING_CONVENTION.md.

Operator: `____________`  Date (UTC): `____________`  Session id: `____________`

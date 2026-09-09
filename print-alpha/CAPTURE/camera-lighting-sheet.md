# RAC-PRINT-ALPHA-001 — Camera & Lighting Sheet (summary)

Operational summary of the locked rig sheet. **Authoritative sources:**
`physical/p1/CAMERA_LIGHTING_SETUP.md` (per-rig FILL-IN values) and
`docs/P1_CAPTURE_RIG_SPEC.md` (rig geometry and lighting states). This sheet
adds nothing new and never overrides them.

## Camera (locked once, recorded in session manifest)

| Parameter | Rule |
|---|---|
| Mode | Manual (M); auto WB prohibited |
| ISO / aperture / shutter / WB | Fixed per rig sheet FILL-IN values; locked after calibration exposure for the whole session |
| Focal length | Fixed; no zoom changes mid-session |
| Format | RAW + JPEG/PNG export; RAW retained as primary evidence |
| Camera height | Fixed (rig sheet FILL-IN); distance grid uses marked floor positions, not camera moves, unless rail-mounted |

## Lighting

| Parameter | Rule |
|---|---|
| Fixtures | Fixed count/model; positions taped, (x, y, z) mm recorded relative to garment-plane origin |
| Color temperature | Single temperature across all fixtures (recommend ~5000 K) |
| Warm-up | ≥ 15 min before calibration capture |
| Ambient | Windowless room or blackout fabric; ambient lux at garment plane recorded |
| Stability | Meter at garment centre before first and after last capture; drift > 5% invalidates the session |
| Named states | Per rig spec: L1 bright diffuse, L2 lower controlled, optional L3 directional; protocol grid uses `indoor-even` and `daylight-even` |

## Background & mounting

- Matte, spectrally neutral 18% gray seamless backdrop extending beyond the
  garment silhouette at every capture angle; no reflective surfaces in frame.
- Garment flat on rigid matte board (or torso form for worn trials — record
  which); smoothed centre-out, no tension wrinkles; hem clips only, outside
  capture area.
- Garment plane parallel to sensor plane, verified via calibration-target
  fiducials (left/right scale agreement within the 2% acceptance bound).
- Orientation mark (garment top) aligned to the taped rig axis.

## Lock discipline

All settings are set once, locked, and copied verbatim into the session
manifest. Changing any locked parameter after seeing candidate results starts
a new experiment (`docs/P1_CAPTURE_RIG_SPEC.md`).

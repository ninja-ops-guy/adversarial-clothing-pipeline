# P1 Camera & Lighting Setup Sheet

Fixed rig for the P1 physical experiment. Everything on this sheet is set
once, locked, and recorded in the session manifest. Fields marked `FILL-IN`
are physical parameters that must be measured on the actual rig before the
first session; no design decision remains after they are filled.

## Camera

| Parameter | Value |
|---|---|
| Camera body | `FILL-IN: camera model` |
| Lens / focal length | `FILL-IN: fixed focal length (no zoom changes mid-session)` |
| Camera height above floor | `FILL-IN: m` |
| Camera-to-garment distance | `FILL-IN: m (session distance grid 1.0 / 3.0 / 5.0 m uses marked floor positions, not camera moves, unless the rig is rail-mounted)` |
| Mode | Manual (M) |
| ISO | `FILL-IN: fixed` |
| Aperture | `FILL-IN: fixed` |
| Shutter | `FILL-IN: fixed` |
| White balance | `FILL-IN: fixed Kelvin; auto WB prohibited` |
| Exposure lock | **Required.** Settings are locked after the calibration exposure and not touched for the rest of the session. |
| Format | RAW + JPEG/PNG export; RAW retained as primary evidence |

## Lighting

| Parameter | Value |
|---|---|
| Fixtures | `FILL-IN: count + model` |
| Positions | `FILL-IN: (x, y, z) mm per fixture relative to garment-plane origin; positions are taped and must not move` |
| Color temperature | `FILL-IN: K (recommend 5000 K D50-ish; single temperature across all fixtures)` |
| Warm-up | >= 15 min before calibration capture |
| Ambient | Windowless room or blackout fabric; ambient lux at garment plane `FILL-IN` |
| Stability check | Meter reading at garment centre before first and after last capture; drift > 5% invalidates the session |

## Background

Matte, spectrally neutral mid-gray (18%) seamless backdrop extending beyond
the garment silhouette in every capture angle. No printed patterns, no
reflective surfaces in frame.

## Garment mounting / flattening

1. Garment on a flat, rigid, matte board (or torso form for worn trials —
record which in the session manifest).
2. Smooth from centre outward; no tension wrinkles across the printed
region. Use low-tack clips at the hem only, outside the capture area.
3. Garment plane parallel to the sensor plane (check with the calibration
target fiducials: left/right scale must agree within the 2% scale
acceptance bound).
4. Orientation mark (top of garment) aligned to the taped rig axis so the
yaw grid (-45 / 0 / +45 deg) is reproducible by rotating the board on
taped angle marks.

## Lock-in rule

Any change to a locked parameter (exposure, light position, distance,
background) starts a **new session_id** and requires a new bracketing
calibration.

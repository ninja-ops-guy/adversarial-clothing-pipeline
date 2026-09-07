# RAC Print / Camera Calibration Target Specification

**Version:** 1.0.0  
**Purpose:** Pre-build the E7 manufacturing-calibration artifact before the first Production Alpha garment arrives.  
**Evidence boundary:** Calibration infrastructure only. No adversarial efficacy or RAC-P claim is created by this target.

## Objective

Measure the transformation between a frozen digital master and the image recovered after the actual print/substrate/camera process. The resulting profile is intended to replace guessed print/camera transforms with empirically measured parameters in future generations.

## Target contents

The master target MUST contain:

1. 24 or more color patches spanning dark neutrals, cream/gray, saturated accents, and the canonical RAC palette.
2. 11-step neutral ramp from black to white.
3. Horizontal and vertical line pairs at multiple spatial periods.
4. Checkerboards at 2, 4, 8, 16, 32 and 64 px cell sizes.
5. Sinusoidal or bar-pattern frequency wedges in both axes.
6. Geometric registration marks at corners and center.
7. 100 mm and 200 mm rulers for scale recovery.
8. RAC-specific motif crops: eye/anatomy, botanical, glitch/static, and high-contrast signal structures.
9. A high-frequency randomized patch and a low-frequency control patch.
10. Human-readable target ID, version, and SHA-256 prefix outside measurement regions.

## Frozen production record

Before ordering, record:

- calibration_target_id
- master PNG SHA-256
- source commit
- POD provider
- product / variant ID
- substrate and color
- print process
- nominal DPI / provider guidance
- template version and SHA-256
- fulfillment region if controllable
- date ordered

## Capture protocol

Capture the unprinted digital master and printed target under the same analysis pipeline. For the physical target record camera ID, lens, distance, yaw/pitch, lighting ID, exposure/white-balance mode, native image dimensions, and whether any automatic enhancement is enabled.

At minimum collect:

- perpendicular close capture for color/registration;
- 1 m, 3 m, and 5 m captures for frequency survival;
- repeated captures under at least two controlled lighting levels;
- rawest available camera output plus the normal deployment-style processed image when practical.

## Derived measurements

Produce a versioned `print_camera_profile.json` containing:

- per-patch digital RGB and observed camera RGB;
- color error summary;
- geometric scale error;
- placement / registration error;
- estimated blur or frequency attenuation by band and orientation;
- camera-distance attenuation curves;
- confidence / repeatability statistics across repeated captures;
- all source artifact hashes.

Do not describe the profile as universal. It is specific to the measured manufacturing and capture chain.

## Acceptance gate

The calibration pipeline is ready for use in optimization only when:

1. target bytes and production metadata are frozen;
2. captures pass geometry and exposure validity checks;
3. repeated measurements produce finite, reproducible parameters;
4. held-out calibration patches are predicted within preregistered tolerance;
5. the profile is versioned and hash-bound to the exact target/manufacturing process.

## Integration

Future EOT code should consume the calibration profile as a declared transformation source. Generic EOT remains a comparison arm. A measured-EOT candidate must record the calibration profile hash in its candidate manifest.

This work belongs to E7 and enables E6 frequency-survival experiments. It does not modify or contaminate RAC-PER-D2-0004.

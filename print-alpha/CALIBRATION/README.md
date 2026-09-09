# print-alpha/CALIBRATION — calibration target placement

This directory receives the physical print / camera **calibration target**
**RAC-CALT-P1-0001** materials used alongside every RAC-PRINT-ALPHA-001
capture session.

## Source of truth

- Target specification: `docs/CALIBRATION_TARGET_SPEC.md` (24+ color patches,
  11-step neutral ramp, line pairs, checkerboards 2–64 px, frequency wedges,
  registration fiducials, 100/200 mm rulers, RAC motif crops, human-readable
  target ID + SHA-256 prefix).
- Session acceptance machinery: `physical/p1/CALIBRATION_MANIFEST.json`
  (max mean ΔE00 6.0 for the print→camera chain; 2% scale acceptance bound).
- Purpose: measure the transformation frozen-digital-master →
  print/substrate/camera → observed image, replacing guessed print/camera
  transforms with measured parameters (calibration feedback model, currently
  `SCAFFOLD_ONLY` until measured captures via UA-3).

## Evidence boundary

- `physical_efficacy_claimed = false`
- `evidence_class = experimental_print_specimen`

Calibration infrastructure only. Per `docs/CALIBRATION_TARGET_SPEC.md`, no
adversarial-efficacy or RAC-P claim is created by this target.

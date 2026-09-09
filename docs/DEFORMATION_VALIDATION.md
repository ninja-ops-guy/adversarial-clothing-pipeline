# Deformation Tier Validation (RAC-E, Wave 4)

Status: synthetic-only. `evidence_class = synthetic_pipeline_validation_only`.
No physical-world efficacy is claimed or implied anywhere in this document.

## Tier definitions

| Tier | Model | Implementation | Status |
|------|-------|----------------|--------|
| T0 | Explicit affine / projective warp | `T0ExplicitWarp` — pure numpy inverse-mapping + bilinear resample | OK |
| T1 | Neural deformation field | `T1NeuralDeformation` — lazy adapter over `ruthless_pipeline.deformation.NeuralDeformationModule` (torch imported inside the method; `TierUnavailableError` when torch is absent) | OK (synthetic fit only) |
| T2 | Native differentiable mass-spring cloth | `T2ClothPhysics` — lazy adapter over `ruthless_pipeline.physics.NativeDifferentiableCloth`; same torch guard | OK (synthetic baseline) |
| T3 | Empirically calibrated correction field | `T3EmpiricallyCalibrated` — **SCAFFOLD_ONLY**; construction without measured calibration data raises `CalibratedDataRequiredError` (fail-closed) | BLOCKED on measured data (UA-3/UA-4) |

All tiers share one interface: `name`, `cost_estimate`,
`apply(uv, texture, params) -> warped`, deterministic. Determinism for T1 is
enforced with a seeded torch generator (fabric-prior sample) plus fixed MLP
evaluation; T0/T2 are deterministic by construction.

## Validation methodology

Synthetic fixtures only: a known texture and uv grid, an identity affine
reference warp (`reference_warp`, exact inverse-mapping), and per-tier
metrics from `run_tier_benchmark`:

- **cost**: mean wall-clock seconds per `apply` (first T1 call includes the
  one-time lazy synthetic fit).
- **determinism**: bitwise equality of two repeat runs (`np.array_equal`).
- **fidelity**: MSE / PSNR vs the reference warp. For T0 this is exact (0
  MSE, identity reproduced bitwise). For T1/T2 the reference is the identity
  warp, so the value measures *departure from identity of the tier's own
  deformation field*, not correctness against a physical ground truth —
  no physical ground truth exists yet.
- **predictive_value**: always `null` with a note. Predicting physical
  detector observations requires a detector loop plus measured captures;
  this is future work and is never fabricated.

## Current results (synthetic benchmark, 64×64 fixture, CPU)

| Tier | Status | Cost (s, mean) | Deterministic (bitwise) | MSE vs reference | PSNR (dB) |
|------|--------|----------------|--------------------------|------------------|-----------|
| T0 | OK | ~9.2e-4 | yes | 0.0 | inf |
| T1 | OK | ~49.2 (one-time fit) | yes | 1.11e-4 | 39.5 |
| T2 | OK | ~2.2e-2 | yes | 1.68e-13 | 127.7 |

Numbers reproduced by `tests/physical_transfer/test_deformation_tiers.py`
(`test_tier_benchmark_determinism_and_keys`); exact timing varies by host.
T1 without torch: `TierUnavailableError` (tested guard path); T2 likewise.

## Limitations

- All fidelity numbers are against a *synthetic* reference. Nothing here
  validates against printed fabric.
- T1 is fit on `synthetic_observation(seed=0)` — a stand-in observation, not
  measured cloth behavior.
- T2 is the small native mass-spring baseline, not a validated HOOD/DiffCloth
  integration (see `ruthless_pipeline/physics.py` docstring).
- T3 does not exist as a runnable tier: any construction without measured
  calibration data fails closed.
- Printability components (`printability.py`) use documented proxies
  (RGB-cube gamut distance, erosion-lifespan min feature, FFT radial energy);
  the gamut distance is NOT a calibrated ΔE00.

## Physical validation plan

1. UA-3 measured captures → populate versioned production profiles with
   `source='measured'` (`production_profiles.py`); assumed values stay
   `assumed_documented` with mandatory rationale.
2. UA-4 vendor measurements → enable `digital_to_camera_discrepancy` and
   MTF-based high-frequency survivability with measured cutoffs; until then
   these components return `None` + `MEASUREMENT_UNAVAILABLE` and totals are
   renormalized with `partial=True`.
3. Measured calibration targets (docs/CALIBRATION_TARGET_SPEC.md) → fit T3
   correction field; only then does T3 leave SCAFFOLD_ONLY.
4. Detector loop + physical transfer records
   (`transfer_record.py`, frozen schema) → replace the `predictive_value`
   placeholder with real predictive-value metrics. Records from synthetic
   generators are forced to `synthetic_pipeline_validation_only`;
   `measured_physical_capture` requires a `measured_evidence_ref`
   (schema + builder-level guard).

## T3 gating on measured data

`T3EmpiricallyCalibrated()` raises `CalibratedDataRequiredError` unless
constructed with a measured calibration payload. When such data exists, T3
fits an additive uv-correction field on top of a base tier (default T0).
Until UA-3/UA-4 deliver measured captures, T3 remains a fail-closed stub by
design.

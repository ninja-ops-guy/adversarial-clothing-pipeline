# RAC-P1 Capture Rig and Dry-Run Specification

**Version:** 1.0.0  
**Purpose:** Make the physical experiment executable before the first garment arrives.  
**Primary statistical unit:** garment × actor × session. Frames are nested observations, not independent trials.

## Goal

The day a control/candidate pair arrives should be a capture day, not a protocol-design day. This specification defines the rig, metadata, validity rules, synthetic dry run, and handoff into RAC statistical tooling.

## Rig

Mark fixed camera positions at 1 m, 3 m, 5 m and 8 m where space permits. Mark actor center, yaw positions (0°, ±45°, ±90°), and a repeatable walking/rotation path. Use fixed camera height and document lens / field of view.

Lighting should have stable named states. At minimum:

- L1: bright diffuse;
- L2: lower controlled illumination;
- optional L3: directional / high-contrast.

Do not change thresholds or camera settings after observing candidate results unless the protocol explicitly defines that change as a new experiment.

## Session hierarchy

```text
experiment
  actor
    garment_pair
      session
        condition
          sequence
            frames
```

The matched control and candidate should use the same product, size, substrate, manufacturing process, actor, session, path, camera and lighting state.

## Required metadata

Every session records:

- experiment_id
- protocol_version
- actor_id (pseudonymous)
- control garment artifact / SKU hash
- candidate garment artifact / SKU hash
- camera_id and configuration
- lighting_id
- distance_m
- yaw_deg / pitch_deg
- pose or motion sequence
- wash_state
- session timestamp
- threshold/model manifest IDs
- capture artifact hashes

## Validity

A condition is valid only when the matched control is detected according to the preregistered control criterion. A control-undetected condition is INVALID, never candidate success.

Record invalid conditions with reason codes. Never delete them.

## Capture sequence

For each condition:

1. capture matched control sequence;
2. capture matched candidate sequence;
3. retain complete video / burst;
4. derive frame-level telemetry;
5. aggregate at session level;
6. feed valid matched observations into `trial_statistics.py`.

Use sequence-level measures in addition to frame summaries so occasional favorable frames cannot masquerade as persistent physical performance.

## Synthetic dry run

Before physical garments exist, run the entire pipeline with synthetic data clearly labeled:

`evidence_class = synthetic_pipeline_validation_only`

The dry run must exercise:

capture manifest → ingestion → validity → statistics → plots/report → evidence bundle → certificate refusal / non-physical status.

Synthetic data MUST NOT enter RAC-P evidence or product claims.

## Statistical handoff

Use the existing `ruthless_pipeline.certification.trial_statistics` module for:

- invalid-condition accounting;
- paired control/candidate rates;
- Wilson intervals;
- bootstrap risk-difference interval;
- preregistered stopping rule.

The stopping rule must be frozen before real P1 capture.

## P1 readiness gate

P1 capture may begin when:

- rig geometry is marked and documented;
- camera and lighting IDs are frozen;
- control/candidate SKU identities are frozen;
- session schema validates;
- synthetic dry run completes end-to-end;
- statistical stopping rule is preregistered;
- evidence bundling rejects synthetic/invalid promotion.

This work is independent of and must not alter D2-0004.

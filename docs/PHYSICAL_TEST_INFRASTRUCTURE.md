# Physical Test Infrastructure (v1.0.0 draft)

**Status:** DRAFT — must be frozen and hash-bound before any capture begins.
**Scope deliverables:** (A) Calibration Target, (B) P1 Capture Rig Protocol.
**Deadline constraint:** Both deliverables must be READY BEFORE physical sample garments arrive.

---

## 1. Purpose & Scope

This document specifies the physical infrastructure required to execute phase P1
(first physical capture) of RAC adversarial-garment trials against person-detector
models, and freezes every parameter that governance requires to be fixed prior to
data collection.

**What this document freezes:**

- The calibration target design and its acceptance measurements (§2).
- The P1 capture rig: camera identities, distances, angles, poses, lighting,
  backgrounds, garment states, and the metadata capture form (§3).
- The experimental-unit definition and anti-pseudoreplication rules (§4).
- Invalid-condition accounting rules (§5).
- The preregistration block that must be committed (with SHA-256) before any
  capture (§6).

**What this document explicitly does NOT claim:**

- No claim of physical adversarial efficacy. Efficacy is asserted only after P1
  completes under the preregistered stopping rule and the trial_statistics
  module reports a paired control-vs-candidate effect with Wilson CIs.
- No claim about durability across wash states. W0/W1/W5/W10 belong to the later
  durability cohort; P1 captures W0 only (§3.6).
- No claim of detector generality beyond the preregistered detector set
  (detector list is external to this document; OPEN, see §7).
- No guarantee that the candidate pattern transfers from digital evaluation to
  print; the calibration target exists precisely to quantify print-vs-file
  deviation before that question is asked.

---

## 2. Calibration Target

**Task:** fabricate and characterize before garments arrive. The target
quantifies the print-and-capture pipeline so that garment-level measurements can
be expressed as deviations from a known physical reference.

### 2.1 Board specification

Rigid matte board, A1 (594 × 841 mm), printed via the same sublimation process
and provider as the candidate garment panels where feasible; otherwise a
photo-grade matte inkjet reference is used and the discrepancy is recorded as a
known limitation. Contents:

| Element | Spec | Yields |
|---|---|---|
| Color swatches | 24-patch color-checker layout (6×4 grid), reference Lab values per patch | Color shift ΔE per patch (CIEDE2000) |
| Grayscale ramp | 11 steps, 0–100% reflectance, equal L* spacing | Tonal linearity, gamma error |
| Line-pair targets | Steps at 0.5, 1, 1.5, 2, 3, 4, 6 lp/mm, chosen so that 150 DPI file ≈ 3 lp/mm and 300 DPI file ≈ 6 lp/mm native; both horizontal and vertical | Line-resolution cutoff of the print + capture chain |
| Geometric rulers | 50 cm and 20 cm ruled edges, cm graduations, verified against a certified ruler | Scale error (px/cm) per distance |
| Registration marks | Crosshair marks at all four corners + center, known spacing (±0.5 mm) | Placement/registration error, keystone distortion |
| Motif patches | 3 representative patches (≥8×8 cm) extracted from the candidate adversarial pattern at final print scale | Motif-level color/fidelity drift vs. source file |
| Seam-crossing elements | Two line/gradient features printed across a physical fold seam in the board | Distortion introduced by seams/garment construction |
| Metadata panel | Printed: target ID, version, print date, printer/process, SHA-256 of the generating file | Hash-binding of physical target to source artifact |

Target ID format: `RAC-CALT-<version>-<seq>` (e.g., `RAC-CALT-1.0.0-001`).

### 2.2 Capture of the target

The target is photographed with the **same rig as garments** (§3): same two
cameras, same tripod positions, same distances (2 m / 4 m / 8 m), same lighting
conditions (§3.4), mounted flat and frontoparallel at the actor position.

### 2.3 Measurements produced

For each camera × distance × lighting cell:

1. **Color shift:** mean and max ΔE (CIEDE2000) across the 24 patches vs.
   reference Lab values.
2. **Scale error:** measured px/cm vs. nominal, per ruler; percent error.
3. **Line-resolution cutoff:** highest lp/mm step at which line pairs remain
   separable (contrast ≥ 20% Michelson) — defines the finest printable motif
   feature that survives the pipeline.
4. **Placement/registration error:** corner-mark displacement in mm vs. nominal
   geometry; keystone angle.

These values are recorded in a `calibration_report.json`, SHA-256 hashed, and
attached as an evidence label to all subsequent P1 trials. **Acceptance
thresholds are OPEN** (must be set before P1 freeze; candidate defaults:
mean ΔE ≤ 6, scale error ≤ 2%, registration error ≤ 3 mm).

---

## 3. P1 Capture Rig Protocol

### 3.1 Cameras (frozen identities)

Exactly two cameras are permitted. Each has a frozen `camera_id` string that
appears verbatim in every `PhysicalTrial.metadata.camera_id`:

| camera_id | Type | Role |
|---|---|---|
| `CAM-PHONE-MAIN-01` | Phone main (rear) camera | Primary capture |
| `CAM-WEBCAM-FIXED-01` | Fixed webcam | Secondary/fixed viewpoint |

No other imaging device may produce trial evidence. Device model, firmware/app
version, resolution, frame rate, and fixed exposure/white-balance settings are
recorded once in the rig manifest and frozen. **Exact device models are OPEN**
pending hardware availability (§7), but once entered in the manifest they are
frozen.

### 3.2 Geometry (frozen)

| Parameter | Frozen values |
|---|---|
| Distances (`distance_m`) | 2.0, 4.0, 8.0 (tape-measured, marked on floor) |
| Yaw (`yaw_deg`) | 0, 45, 90, 135, 180 (floor markers at actor position) |
| Pitch (`pitch_deg`) | 0 (camera at torso height); ±15 as secondary set — **OPEN whether ±15 enters P1 or is deferred** |
| Tripod positions | One fixed position per camera × distance; position IDs `TP-<cam>-<dist>` |
| Actor mark | Single floor cross; rotation in place for yaw; walk lane for walk-cycle |

### 3.3 Backgrounds

Two named backgrounds, frozen:

- `BG-INDOOR-PLAIN-01` — uniform indoor wall, measured reflectance recorded.
- `BG-OUTDOOR-URBAN-01` — fixed outdoor location, photographed and documented.

### 3.4 Lighting conditions (`lighting_id`)

| lighting_id | Description | Lux range (recorded per session) |
|---|---|---|
| `LUX-INDOOR-OFFICE` | Office ceiling lighting | measured, target 300–700 lx |
| `LUX-OUTDOOR-OVERCAST` | Overcast daylight | measured |
| `LUX-OUTDOOR-DIRECT-SUN` | Direct sunlight | measured |
| `LUX-DUSK` | Civil dusk | measured |

A lux meter reading at the actor position is logged per session into
`metadata.lux`. No session may run outside its condition's preregistered lux
band; bands are finalized in the preregistration block (§6).

### 3.5 Actor poses (`pose`)

Frozen pose set:

- `standing-front`, `standing-back`, `standing-left`, `standing-right`
  (static stills at each yaw/distance)
- `walk-cycle` (video along the marked walk lane, toward and across camera)
- `rotation-360` (continuous in-place 360° video at each distance)

### 3.6 Garment states

P1 captures `wash_state = W0` (unwashed) only. W1/W5/W10 belong to the
durability cohort and are out of scope for P1. Control and candidate garments
must be matched pairs: same POD provider, same base garment, same size, same
print process; candidate differs only in the printed pattern.

### 3.7 Video protocol

Because sequence-level detection — not per-frame detection — is the evidence
unit (§4), each session captures:

1. One `rotation-360` video per distance (≥10 s, constant frame rate).
2. Two `walk-cycle` traversals per distance (toward camera; lateral across).
3. Static stills for each pose × yaw cell.

Control and candidate are captured in the **same session, same actor, same
lighting**, alternating order (A/B then B/A) to cancel drift.

### 3.8 Metadata capture form

Every capture produces one JSON record per trial conforming to the
`PhysicalTrial` schema:

```json
{
  "trial_id": "P1-<session>-<cond>-<rep>",
  "condition_id": "<distance>x<yaw>x<pitch>x<pose>x<lighting>x<bg>x<wash>",
  "control_detected": true,
  "candidate_detected": false,
  "camera_id": "CAM-PHONE-MAIN-01",
  "distance_m": 4.0,
  "yaw_deg": 45,
  "pitch_deg": 0,
  "pose": "walk-cycle",
  "lighting_id": "LUX-OUTDOOR-OVERCAST",
  "wash_state": "W0",
  "metadata": {
    "session_id": "SES-<actor>-<date>-<seq>",
    "actor_id": "ACT-01",
    "lux": 1200,
    "garment_pair_id": "PAIR-01",
    "calibration_report_sha256": "<hex>",
    "video_sha256": "<hex>",
    "rig_id": "RIG-P1-1.0.0"
  }
}
```

All artifacts (raw video, stills, metadata JSON) are SHA-256 hashed at capture
time; hashes are appended to an append-only evidence log with evidence labels
(`raw`, `calibration`, `derived`).

---

## 4. Experimental Unit & Anti-Pseudoreplication Rules

### 4.1 Unit hierarchy

```
trial outcome (control/candidate detection pair)
  └── session  = garment × actor × session   ← EXPERIMENTAL UNIT
        └── frames / sequence windows        ← nested, never independent
```

**The experimental unit is garment × actor × session, NOT the video frame.**
Frame-level pseudoreplication is banned: frames within a session share actor,
garment, lighting, and camera state, and must never be counted as independent
observations. A session's outcome is a **sequence-level** aggregate (e.g.,
"detected in ≥ k of n windows", with k/n frozen in the preregistration block).

### 4.2 Minimum counts (P1)

| Quantity | Frozen value |
|---|---|
| Actors | ≥ 2 (actor IDs frozen) |
| Sessions per actor per condition | ≥ 3 (OPEN pending pilot feasibility) |
| Garment pairs | ≥ 1 matched control/candidate pair |

### 4.3 Analysis

- Primary: paired control-vs-candidate detection rate difference per condition,
  95% Wilson confidence intervals (per trial_statistics module).
- Uncertainty: **clustered bootstrap resampling at the session level**
  (sessions resampled with replacement; all frames/windows within a resampled
  session move together). Never bootstrap frames.
- Multiplicity: per-condition claims only; no pooled claim unless preregistered.

### 4.4 Preregistered stopping rule

- Minimum valid trials per condition: 20; maximum: 100.
- Stop early only if the Wilson interval half-width ≤ 0.20 (target interval
  width 0.20) at 95% confidence, evaluated no more than once per 10 new valid
  trials (one-shot evaluation schedule, frozen).
- Otherwise continue to the maximum and report the interval as-is.

---

## 5. Invalid-Condition Accounting

1. A trial in which the **control garment is not detected** is **invalid**:
   the pipeline failed at baseline, so the trial carries no information about
   the candidate.
2. An invalid trial is **counted and reported per condition** (numerator,
   denominator, fraction) — it is never silently dropped and **never counted as
   a candidate success**. Candidate-undetected with control-detected is a valid
   trial outcome; candidate-undetected with control-undetected is invalid.
3. **Flagging threshold:** if the invalid fraction for a condition exceeds
   **0.10**, the entire condition is flagged and excluded from efficacy claims
   pending root-cause review (e.g., lighting out of band, garment mismatch).
4. Invalid trials still count toward session bookkeeping and are retained in
   the hash-bound evidence log with label `invalid`.

---

## 6. Preregistration Checklist

All fields below must be frozen and committed **before any capture begins**.
One-shot rule: after freeze, parameters change only via a new versioned
preregistration with a new hash; P1 evidence is bound to exactly one hash.

```json
{
  "rig_id": "RIG-P1-1.0.0",
  "camera_ids": ["CAM-PHONE-MAIN-01", "CAM-WEBCAM-FIXED-01"],
  "distances_m": [2.0, 4.0, 8.0],
  "yaws_deg": [0, 45, 90, 135, 180],
  "pitches_deg": [0],
  "poses": ["standing-front", "standing-back", "standing-left",
            "standing-right", "walk-cycle", "rotation-360"],
  "lighting_ids": ["LUX-INDOOR-OFFICE", "LUX-OUTDOOR-OVERCAST",
                   "LUX-OUTDOOR-DIRECT-SUN", "LUX-DUSK"],
  "backgrounds": ["BG-INDOOR-PLAIN-01", "BG-OUTDOOR-URBAN-01"],
  "actor_ids": ["ACT-01", "ACT-02"],
  "session_plan": {
    "sessions_per_actor_per_condition": 3,
    "capture_order": "AB-then-BA",
    "wash_states": ["W0"]
  },
  "sequence_aggregation": {"detected_windows_k": null, "of_n_windows": null,
                           "note": "OPEN — frozen before capture"},
  "thresholds": {
    "detector_score_threshold": null,
    "note": "OPEN — must match frozen detector config"
  },
  "stopping_rule": {"min_valid_trials": 20, "max_valid_trials": 100,
                    "wilson_target_width": 0.20, "confidence": 0.95,
                    "evaluation_every_n_valid": 10},
  "invalid_rules": {"control_undetected": "invalid",
                    "invalid_fraction_flag_threshold": 0.10},
  "calibration_report_sha256": "<hex>",
  "preregistration_sha256": "<hex-of-this-block-excluding-this-field>"
}
```

Checklist: every field non-null and hash committed; calibration report complete
(§2.3); rig manifest complete; garment pair provenance recorded; evidence log
initialized.

---

## 7. Open Items

| Item | Owner | Needed by |
|---|---|---|
| Physical capture space (indoor + outdoor BG-OUTDOOR-URBAN-01 site) | external | P1 start |
| Actors (≥2, consent + IDs) | external | P1 start |
| Camera hardware (phone + fixed webcam; model/firmware manifest) | external | rig freeze |
| Printed calibration target (fabrication per §2.1) | external | rig freeze |
| Calibration acceptance thresholds (§2.3 defaults to confirm) | internal | prereg freeze |
| Pitch set for P1 (0 only vs. ±15) | internal | prereg freeze |
| Sequence-aggregation k/n and detector score threshold | internal | prereg freeze |
| Sessions-per-actor count (pilot feasibility) | internal | prereg freeze |
| Detector set/version manifest | external to this doc | prereg freeze |

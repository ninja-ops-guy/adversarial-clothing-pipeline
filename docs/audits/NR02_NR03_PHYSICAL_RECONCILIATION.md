# NR-02 / NR-03 Physical Reconciliation (Pass B)

Scope: reconcile the observation-medium / production-provenance requirement
(NR-02) and the controls / interpretable-comparisons requirement (NR-03) with
the EXISTING capture/readiness packet. This is reconciliation and mapping, not
redesign: the physical-readiness critical path (frozen contracts, frozen
pairing, frozen preregistrations) is preserved unchanged.

Boundary compliance: no D2-0004 / D2-0005 modification (amendment docs
unchanged); no arming; no held-out access; no synthetic→measured promotion;
frozen schemas frozen (additive extensions only); no PENDING_USER_ACTION
resolution.

## NR-02 — observation medium and production provenance

### (a) Evidence-medium inventory (how current artifacts identify medium)

| Artifact / lane | Medium identification today | Where |
|---|---|---|
| Physical Transfer Record | `evidence_class` ∈ {`synthetic_pipeline_validation_only`, `measured_physical_capture`}; distinguishes synthetic vs measured, **not** the physical medium (composite / display-photo / flat print / worn fabric) | `schemas/physical_transfer_record.schema.json`, `ruthless_pipeline/physical_transfer/transfer_record.py` |
| Evidence-class registry (frozen + additive ext) | `synthetic_pipeline_validation_only`, `generated_digital_reference`, `log_attested`, `scenario_assumption`, `experimental_print_specimen`, `derived_digital_measurement`; specimen vs digital, no worn/flat/display split | `ruthless_pipeline/evidence_classes_ext.py`, `schemas/evidence_class.schema.json` |
| Calibration ingest | PrintCameraProfile (ΔE2000, scale, resolution, registration) — calibrates a camera/print chain; carries no medium field | `ruthless_pipeline/certification/calibration_ingest.py` |
| Physical capture rehearsal | Every artifact labelled `synthetic_pipeline_validation_only`; `synthetic_frame: True` on Capture Lab records; mock detector marked `mock: true`, model id `MOCK-DETECTOR-SYNTHETIC-NOT-A-MODEL` | `ruthless_pipeline/certification/physical_capture_rehearsal.py` |
| Production profiles | `source` ∈ {`vendor_spec`, `measured`, `assumed_documented`} with mandatory rationale for assumed; immutable versions | `ruthless_pipeline/physical_transfer/production_profiles.py` |
| P1 pairing contract / capture schedule | Grid + matched-pair rule documented; `evidence_class: synthetic_pipeline_validation_only` until bound to a real session | `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`, `ruthless_pipeline/certification/p1_pairing_schedule.py` |

Finding: the composite / display-photographed-by-camera / printed-flat /
worn-fabric distinction has **no field anywhere** — confirmed gap (NR-02b).

### (b) Field mapping and additive gap fix

| NR-02 requirement | Existing contract / field | Status | Gap + fix |
|---|---|---|---|
| Synthetic vs measured evidence distinction | `evidence_class` enum + builder guards (`synthetic_generator` forces synthetic; measured requires `measured_evidence_ref`) | Present | None |
| Measured claims need provenance ref | `measured_evidence_ref` (schema `allOf` + builder guard) | Present | None |
| Production profile provenance | `profile_id`, `version`, `vendor`, `source`, `created`, `sha256`; assumed requires rationale | Present | None |
| Specimen/capture references | `garment_sku`, `capture_id`, `camera`, `lighting`, `pose`, `view`, artifact sha256 fields | Present | None |
| Observation medium (composite / display-photo / flat print / worn fabric) | **none** | **Gap** | Additive sidecar annotation registry `ruthless_pipeline/certification/observation_medium.py` (`ext_schema_version` 1.0; frozen schemas untouched); default `unknown`, unknown stays unknown |
| Rendering-assumption change → versioned comparison, no rewrite | ProfileStore versions immutable (`ProfileVersionError` on overwrite); sha256 integrity | Present for profiles; **gap** for medium annotations | `compare_rendering_assumptions()` creates a versioned comparison record; old annotations never rewritten (append-only supersession by hash) |

### (c) Acceptance fixtures (tests/test_observation_medium.py)

- Synthetic fixture evidence (`image_composite` / synthetic evidence class)
  cannot promote a worn-fabric claim — `PromotionRefusedError`, reusing the
  existing machinery from `physical_capture_rehearsal` (extended, not forked).
- Photographed-display evidence cannot promote a worn-fabric claim even with
  a measured evidence class.
- Unknown material/capture fields stay unknown (`normalize_medium(None) ==
  "unknown"`; typos fail closed with KeyError, never coerced).
- Rendering-assumption changes produce a versioned comparison record binding
  both annotation hashes; the old annotation is verified byte-unchanged;
  supersession must be explicit and same-subject.

## NR-03 — controls and interpretable comparisons

### (a) Control estimands (documentation only; frozen experiments NOT amended)

| Protocol | Control | Estimand (effect definition) |
|---|---|---|
| D2-0005 amendment A5 control arm | Arm M (mean-objective selection from the shared 100-candidate pool, seed 1337) | **Matched visual property** — Δ = R_M − R_C of held-out detection rates where the arms differ ONLY in the Stage-B surrogate objective; pairing is exact at candidate and condition level. This is a digital ablation estimand (objective effect at final selection given a shared mean-screened pool), NOT a garment-coverage estimand. Documented here only; D2-0005 is frozen and NOT amended by this audit. |
| P1 capture protocol | Matched control garment (same blank, same print process, non-adversarial flat mid-gray sRGB(128,128,128) fill per SKU_MANIFEST control rule) | **Equivalent coverage** — same garment geometry, substrate, placements, session, and acquisition conditions; the pair differs only in printed artwork. A flat-gray control addresses coverage/geometry; it does NOT isolate every visual property (color/texture differ), consistent with `docs/research/NORECOGNITION_REVIEW_2026-09-10.md`. |
| Print Alpha matched control/candidate | `PA-HOODIE-CTRL-001` vs `PA-HOODIE-CAND-001` (same product_id 388, variant, batch, vendor) | **Equivalent coverage** — matched-pair admissibility per `print-alpha/QA/garment-pairing-checklist.md`; control artwork is the unmodified base texture, marked `scenario_assumption` if no sealed base texture exists. |

An **ordinary-garment** estimand (unprinted/off-the-shelf garment) is not the
preregistered control in any of the three lanes; it remains a distinct
estimand available only to future protocols.

### (b) Pairing verification

- Pairing contract `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`
  (contract `RAC-P1-PAIRING-2026-001`, frozen) pins the 144-trial schedule:
  3 distances × 3 yaw × 1 pitch × 1 locked lighting × 2 poses × 8 reps, 2
  captures per trial (one control + one candidate of the same grid cell,
  session, variant/size — pair differs ONLY in printed artwork).
- `ruthless_pipeline/certification/p1_pairing_schedule.py` deterministically
  re-derives grid, cell order, and within-trial arm order from the frozen
  SHA-256 seed (no random module, no wall clock); schedule hash pinned in the
  contract (`schedule_sha256`).
- Geometry and acquisition conditions stay paired by construction: one trial
  = one matched pair sharing cell/session; reserve-garment substitution
  re-runs the pairing checklist before capture.
- Rehearsal lane honors the same pairing (control/candidate captures per
  trial id, shared geometry fields) in
  `physical_capture_rehearsal.build_synthetic_trials`.

Status: pairing contract present and enforced; no gap.

### (c) Reporting / uncertainty acceptance status

| NR-03 requirement | Existing machinery | Status |
|---|---|---|
| Report names the control and effect definition | `report_compiler` emits `control_detection_rate`, per-condition control/candidate rates, and "Paired risk difference (control minus candidate detection rate ...)"; invalid-condition narrative explicit | Present |
| Missing pairs / exclusions / baseline-ineligible observations stay visible | `invalid_condition_report`, `split_valid_invalid`, control-undetected ⇒ invalid measurement condition, never candidate success; invalid-fraction flag at 0.10 surfaced in rehearsal summary (`flagged_invalid_conditions`) | Present |
| Uncertainty uses the actual independent unit (no silent frame-count inflation) | Unit-level path `paired_arm_statistics.py` (preregistered for D2-0005); cluster-robust path `cluster_paired_arm_statistics.py` resamples CLUSTERS (base images) so transformed views/crops of one base image are not counted as independent; fail-closed below a minimum cluster count | Present (cluster path is a PROPOSED amendment path only; frozen preregistration unchanged) |
| Frozen experiments keep the normal amendment process | This audit documents estimands only; no amendment to D2-0005 | Respected |

## Additive changes landed by this reconciliation

- `ruthless_pipeline/certification/observation_medium.py` — additive,
  versioned (`ext_schema_version` 1.0) observation-medium annotation registry
  and promotion guard; reuses `PromotionRefusedError` from
  `certification.physical_capture_rehearsal`.
- `tests/test_observation_medium.py` — 13 acceptance fixtures covering
  NR-02(c).
- This document.

No frozen schema, frozen contract, preregistration, amendment, or readiness
artifact was modified.

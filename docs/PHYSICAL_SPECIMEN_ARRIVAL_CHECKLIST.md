# Physical Specimen Arrival Checklist — RAC-PRINT-ALPHA-001

**Document ID:** PSA-CHECKLIST-001
**Purpose:** from the moment the Printful package arrives to the start of trial
ingestion, without any further software-design session. Execute sections in
order. Every section lists its authoritative repo source; where this checklist
and a source appear to conflict, **the source wins**.

**Evidence boundary:** `physical_efficacy_claimed = false`;
`evidence_class = experimental_print_specimen`. This checklist produces
manufacturing-specimen measurements only. Invalid conditions are recorded as
invalid and are **never** counted as candidate success. All garments stay wash
state **W0** — no laundering before or during capture.

**Prerequisites before the package arrives:** UA-6 done (physical calibration
target RAC-CALT-P1-0001 printed at 100% scale, scale bar verified at 100 mm);
capture rig available per `docs/P1_CAPTURE_RIG_SPEC.md`. See
`docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md` for the full UA sequence.

---

## Section 1 — Package inspection (before opening anything)

Source: `print-alpha/QA/chain-of-custody.md` §2/§4.

- [ ] Photograph the sealed shipping package from all sides (photo log event
      `package_received`): label, tracking number, package condition.
- [ ] Record: date/time (ISO 8601 with timezone), receiver name, carrier,
      tracking number, number of packages.
- [ ] Note any visible damage, moisture, or tampering. Damage does not
      automatically invalidate units — it is recorded, and affected units go
      through Section 4 defect inspection like everything else.
- [ ] Open the package; photograph contents before removing anything
      (event `package_opened`).

## Section 2 — Garment identification

Source: `production_alpha/SKU_MANIFEST.json`, `print-alpha/QA/chain-of-custody.md` §1.

- [ ] Lay out all units. Expected (per the order record): candidate
      `PA-HOODIE-CAND-001`, control `PA-HOODIE-CTRL-001`, plus any reserve
      articles ordered (`reserve_candidate`, `reserve_control`, fallback tees).
- [ ] Count units vs the order record; note discrepancies immediately.
- [ ] Identify which physical unit is which **before attaching any label**:
      the candidate carries the mapped frozen pattern; the control carries the
      base/flat-fill design. They must be visually distinct — if they are not,
      STOP: a mix-up here would invalidate the entire experiment; escalate and
      re-verify against the sealed artwork files.
- [ ] Attach a tamper-evident tag to each unit: specimen ID (SKU ID), role
      (candidate / control / reserve_*), wash state `W0`, pairing group
      `RAC-PRINT-ALPHA-001`. Tags never reference expected outcomes.

## Section 3 — SKU verification (against the manifest)

Source: `production_alpha/RECEIPT_QA_FORM.md` §A.

Per unit, verify against `production_alpha/SKU_MANIFEST.json`:

- [ ] SKU ID / role matches the tag and the manifest.
- [ ] Printful product_id matches (hoodie units: 388; fallback tees: 257).
- [ ] Variant / size / color match the manifest — **identical on candidate and
      control** (matched-pair rule).
- [ ] Printful order ID / line item recorded per unit.
- [ ] Wash state is W0.
- [ ] Any mismatch → unit is quarantined (segregated storage, logged), not
      silently accepted.

## Section 4 — Print defect inspection (receipt QA)

Source: `production_alpha/RECEIPT_QA_FORM.md` §B–§D (one form per unit, same day
as delivery).

- [ ] **Registration:** lay flat; measure per-placement artwork offset vs the
      template/seam reference with ruler or caliper; each placement must be
      ≤ 3.0 mm. Check seam continuity across every cut-sew seam
      (> 3.0 mm visible discontinuity → FAIL).
- [ ] **Scale/placement:** measure known features vs template dimensions.
- [ ] **Fabric distortion:** lay flat; compare panel dimensions vs template;
      note stretch/warp.
- [ ] **Defect classification:** classify any defects per the form's §D table
      (class, location, size, photo).
- [ ] Failures trigger re-order or vendor escalation — never silent acceptance.
      A failed unit does not enter capture; a reserve unit is activated only
      with a logged reserve activation (`production_alpha/ORDER_WORKSHEET.md`).

## Section 5 — Calibration target capture

Sources: `physical/p1/CALIBRATION_MANIFEST.json`,
`production_alpha/RECEIPT_QA_FORM.md` §C.

- [ ] Place RAC-CALT-P1-0001 flat, in-frame or bracketed, under the locked
      session rig; capture the calibration exposure **before** any garment
      capture.
- [ ] Rectify via target fiducials; verify scale via the 100 mm bar.
- [ ] Confirm session acceptance: max mean ΔE00 6.0 for the print→camera chain
      (per CALIBRATION_MANIFEST.json). If calibration fails, STOP — no garment
      capture until the rig passes.
- [ ] Perform the receipt ΔE00 spot-check on each garment (≥ 3 flat regions per
      unit, per the form's §C); flag for review if any patch exceeds 6.0.

## Section 6 — Control/candidate labeling and pairing

Source: `print-alpha/QA/garment-pairing-checklist.md`.

- [ ] Complete every pairing check: SKU match, substrate match, size/variant
      match, print-technology match. The pair is admissible for capture only if
      **all** checks pass.
- [ ] Record the pairing verdict (admissible / not admissible) in writing.
- [ ] Filenames distinguish roles only by the preregistered suffix
      (`__control` / `__candidate`); labels carry no outcome information.

## Section 7 — Camera configuration (locked)

Sources: `physical/p1/CAMERA_LIGHTING_SETUP.md`,
`print-alpha/CAPTURE/camera-lighting-sheet.md`, `docs/P1_CAPTURE_RIG_SPEC.md`.

- [ ] Fixed camera identity; record the real camera identifier in the session
      manifest (`physical/p1/SESSION_MANIFEST_TEMPLATE.json`).
- [ ] RAW capture, manual exposure/focus/white balance; settings locked after
      the calibration exposure and **never changed mid-session**.
- [ ] Camera positions taped; distances marked at 2 m, 5 m, 8 m.
- [ ] Record device/app processing in the session manifest and keep it fixed
      across all matched pairs.

## Section 8 — Lighting

Sources: `physical/p1/CAMERA_LIGHTING_SETUP.md`, capture protocol §2.

- [ ] Two locked lighting states only: `indoor-even` and `daylight-even`.
- [ ] Lighting state per trial must match the trial sheet; any lighting change
      outside the two locked states invalidates the affected trials (record as
      invalid — see Section 10).

## Section 9 — Pose / view schedule (108 matched trials)

Sources: `print-alpha/CAPTURE/trial-sheet.csv`,
`print-alpha/CAPTURE/capture-protocol.md` §1,
`physical/p1/CAPTURE_NAMING_CONVENTION.md`.

- [ ] Execute all 108 rows of the trial sheet: distances 2/5/8 m × yaw
      0°/+30°/−30° (pitch 0°) × pose standing/walking × lighting
      indoor-even/daylight-even × repeats R1–R3, all W0.
- [ ] Each row produces exactly `captures/<trial_id>__control.jpg` and
      `captures/<trial_id>__candidate.jpg` with the sheet's exact names.
- [ ] Same actor, session, path, camera, and lighting state for each matched
      control/candidate pair; actor marks taped.
- [ ] Tick rows off the printed trial sheet in real time; never reconstruct
      coverage from memory afterwards.

## Section 10 — Invalid-condition recording

Sources: `print-alpha/CAPTURE/invalid-condition-rules.json`,
`physical/p1/STOPPING_RULE.json`, `docs/P1_CAPTURE_RIG_SPEC.md`.

- [ ] Any protocol violation (camera/lighting/settings change, wrong distance
      or yaw, garment state change, control not reliably detectable, occlusion,
      mislabeled file) → mark the affected trial(s) **invalid** with the rule
      ID from invalid-condition-rules.json.
- [ ] Invalid trials are recorded, never deleted, and never counted as
      candidate success.
- [ ] No threshold, camera, or lighting changes after seeing any result.

## Section 11 — Trial ingestion

Sources: `physical/p1/PHYSICAL_TRIAL_INGESTION_TEMPLATE.json`,
`scripts/evaluate_physical_trial.py`.

- [ ] Complete the session manifest from the template (camera id, processing,
      lighting states, actor, calibration reference, timestamps).
- [ ] Hash every RAW capture file (SHA-256) into the ingestion record.
- [ ] Ingest per the ingestion template; then the frozen evaluation path is
      `scripts/evaluate_physical_trial.py` with the trial manifest, captures,
      and model manifest.
- [ ] Evaluation output is labeled with its true evidence class; physical
      results are reported against the preregistered rule only.

## Section 12 — Chain of custody (continuous, Sections 1–11)

Source: `print-alpha/QA/chain-of-custody.md`.

- [ ] Every custody event (receipt, opening, tagging, QA, storage move,
      capture, reserve activation) is photo-logged with photo_id, specimen_id,
      event, ISO 8601 timestamp, actor, file ref, and SHA-256.
- [ ] Storage: active pair flat, unfolded, inert packaging, dark,
      climate-stable; reserves stored identically but segregated; location IDs
      recorded.
- [ ] Custody log is append-only; corrections are new entries, never edits.

---

## Completion definition

Physical testing can begin when: Sections 1–6 are complete with a **pair
admissible** verdict, Section 5 calibration has passed, and Sections 7–8 are
locked. Sections 9–11 then execute in one session block. Section 12 runs
throughout. No step in this checklist requires new software or new design
decisions; every referenced template, rule, and tolerance already exists in the
repository paths cited above.

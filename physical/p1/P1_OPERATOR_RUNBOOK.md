# P1 Operator Runbook — Specimen Arrival to Sealed Evidence (No Improvisation)

**Document ID:** P1-RUNBOOK-001
**Status:** FROZEN for P1 no-spend readiness. Hash-pinned in
`physical/p1/P1_READINESS_FREEZE.json`.
**Scope:** the complete physical P1 workflow once garments exist. Every step
references its authoritative source; where this runbook and a source appear
to conflict, **the source wins**. Nothing here is executed until UA-1..UA-8
are complete with real vendor/fabrication/garment/measurement values.

**Evidence boundary (applies to every step):**
`physical_efficacy_claimed = false`; evidence produced by P1 capture is
`internally_measured` only after validated ingestion; the synthetic rehearsal
of this runbook is `synthetic_pipeline_validation_only` and is never RAC
evidence. D2-0005 stays PREREGISTERED/unarmed; held-out model sets stay
untouched; no threshold changes.

**Refusal rule (global):** any step that cannot be completed as written ends
in a recorded REFUSAL or INVALID condition — never in an improvised
substitute, never in a silently defaulted field, never in a retried capture
outside the schedule.

---

## Phase 0 — Prerequisites (all must already be true)

- UA-1..UA-6 complete per `docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md`
  (token, template bound, SKU pair selected, order placed, calibration target
  fabricated and scale-verified at 100 mm).
- All `PENDING_USER_ACTION` fields in `print-alpha/MANIFESTS/*.json` and
  `production_alpha/SKU_MANIFEST.json` resolved to real values.
- Capture rig assembled per `docs/P1_CAPTURE_RIG_SPEC.md` and measured per
  `physical/p1/RIG_MEASUREMENT_CHECKLIST.md`.

## Phase 1 — Specimen arrival and receipt QA (UA-7)

Source: `docs/PHYSICAL_SPECIMEN_ARRIVAL_CHECKLIST.md` (sections 1–6),
`production_alpha/RECEIPT_QA_FORM.md`, `print-alpha/QA/garment-pairing-checklist.md`,
`print-alpha/QA/chain-of-custody.md`.

1. Package inspection and photo log (`package_received`, `package_opened`).
2. Garment identification against `production_alpha/SKU_MANIFEST.json`.
3. Per-unit receipt QA: registration ≤ 3.0 mm per placement, seam continuity,
   fabric distortion, defect classification. All units stay wash state W0.
4. ΔE00 spot-check with RAC-CALT-P1-0001 in-frame (form §C).
5. Pairing checks: SKU, substrate, size/variant, print technology match.
6. Custody log opened; storage location recorded.

**Failure behavior:** a failed unit is recorded, quarantined, and replaced
only per the reserve rule in
`physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`. Never silent acceptance.

## Phase 2 — Session setup and calibration acceptance

Sources: `physical/p1/CAMERA_LIGHTING_SETUP.md`,
`physical/p1/CALIBRATION_MANIFEST.json`,
`docs/CALIBRATION_TARGET_SPEC.md`.

1. Configure camera/lighting/distance/height/background/mounting exactly as
   the session manifest requires (`physical/p1/SESSION_MANIFEST_TEMPLATE.json`).
2. Run the bracketing calibration; record `profile_id`
   (`RAC-PCP-<version>-<seq>`).
3. Acceptance thresholds (frozen, unchangeable at session time):
   max mean ΔE00 ≤ 6.0; scale error ≤ 2.0%; registration error ≤ 3.0 mm.

**Failure behavior:** calibration acceptance failure → the session does not
start. Adjust rig, re-calibrate, or abort the session with a recorded
refusal. No threshold relaxation.

## Phase 3 — Capture execution (UA-8)

Sources: `physical/p1/P1_CAPTURE_SCHEDULE.json` (frozen 144-trial schedule),
`physical/p1/CAPTURE_NAMING_CONVENTION.md`,
`physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`.

1. Execute trials in the frozen execution order; within each trial capture
   arms in the recorded `first_arm` order.
2. Name every file per the naming convention; record each capture's SHA-256
   at capture time in the session manifest.
3. Record environment fields (temperature, humidity, lux, meter baseline)
   per session.
4. An invalid condition (e.g. control undetected) is recorded as invalid —
   never retried into a "success", never counted as candidate success.

**Failure behavior:** any deviation from the schedule (missed cell, wrong
order, substituted garment) → the affected trials are invalid; the session
manifest records the deviation. No on-site re-randomization.

## Phase 4 — Session validation and ingestion

Sources: `scripts/validate_capture_session.py`,
`scripts/ingest_capture_inference.py`,
`schemas/physical_transfer_record.schema.json`.

1. `validate_capture_session.py` must pass: schema version, required fields,
   per-capture SHA-256 hash-chain verification, calibration association.
2. Ingest via `ingest_capture_inference.py`; the promotion gate refuses any
   synthetic-labelled payload and any physical payload without
   `calibration_pass: true`.
3. Trials enter the cumulative store exactly once (replay of an existing
   trial ID is a contract violation).

## Phase 5 — Sealed evidence packaging

Sources: `scripts/build_p1_bundle.py`,
`ruthless_pipeline/certification/release_format.py`,
`docs/RESEARCH_RELEASE_FORMAT.md`.

1. Stopping-rule evaluation over the full trial store
   (`physical/p1/STOPPING_RULE.json`; min 93 / max 144 valid trials).
2. Bundle build: every artifact hash-bound (SHA-256), provenance-linked,
   schema-versioned.
3. `verify_release` must pass before the package is sealed.
4. The sealed package records the five boundary assertions:
   `D2_0004_MODIFIED=false`, `D2_0005_ARMED=false`,
   `NEW_HELDOUT_ACCESS=false`, `SCIENTIFIC_THRESHOLDS_CHANGED=false`,
   `PHYSICAL_EFFICACY_CLAIMED=false` (efficacy is asserted only by the
   preregistered P1 analysis itself, never by packaging).

## Rehearsal

This entire runbook is rehearsed synthetically and deterministically by
`scripts/rehearse_physical_capture.py` and `scripts/p1_full_chain_dry_run.py`
(receipt → calibration → capture → ingestion → stopping rule → sealed
release, byte-identical on re-run). The readiness gate
(`tools/p1_no_spend_readiness_gate.py`) re-executes that rehearsal and its
failure-injection battery and refuses readiness if any step improvises.

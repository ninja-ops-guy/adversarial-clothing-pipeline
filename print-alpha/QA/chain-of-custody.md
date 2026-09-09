# RAC-PRINT-ALPHA-001 — Chain of Custody

Custody standard for all print-alpha specimens (candidate, control, reserves)
and the calibration target RAC-CALT-P1-0001. Complements
`production_alpha/RECEIPT_QA_FORM.md` §F and the session manifest fields in
`physical/p1/SESSION_MANIFEST_TEMPLATE.json`.

Evidence boundary: `physical_efficacy_claimed = false`;
`evidence_class = experimental_print_specimen`.

## 1. Specimen labeling

- Each unit carries a tamper-evident tag with: specimen ID (SKU ID from
  `production_alpha/SKU_MANIFEST.json`), role (candidate / control /
  reserve_candidate / reserve_control), wash state (W0 until protocol says
  otherwise), and pairing group (`RAC-PRINT-ALPHA-001`).
- Tags never reference expected experimental outcome; labels identify
  manufacturing specimens only.
- The calibration target is labeled `RAC-CALT-P1-0001` with version and
  SHA-256 prefix per `docs/CALIBRATION_TARGET_SPEC.md`.

## 2. Photo log

Every custody event is photo-documented. Photo log fields:

| Field | Content |
|---|---|
| photo_id | sequential, e.g. `PA001-PH-0007` |
| specimen_id | SKU ID of the unit photographed |
| event | custody event (see §4) |
| timestamp | ISO 8601 with timezone |
| actor | person performing the event |
| file_ref | RAW file path per `physical/p1/CAPTURE_NAMING_CONVENTION.md` |
| sha256 | hash of the RAW file |
| notes | package condition, visible defects, tag state |

## 3. Storage

- Active pair: flat, unfolded, inert packaging, dark, climate-stable; location
  ID recorded. Reserve units stored identically but segregated.
- Quarantine (rejected units): sealed, unaltered, never laundered, retained
  for vendor claim (see receipt QA §E).
- No specimen is laundered before/during the W0 capture campaign
  (`physical/p1/STOPPING_RULE.json` wash-state semantics).

## 4. Handoff log fields

Every transfer of a specimen is recorded with:

| Field | Content |
|---|---|
| event_id | sequential |
| event_type | delivered / opened / inspected / stored / transferred_to_rig / returned_from_rig / quarantined / reserve_activated / transferred_to_archive |
| specimen_id | SKU ID |
| timestamp | ISO 8601 with timezone |
| from_actor / to_actor | custody handoff parties |
| from_location / to_location | location IDs |
| condition_on_transfer | tag intact? visible state; photo_id reference |
| authorization | session lead initials |

## 5. Integrity rules

- A break in the custody log invalidates the affected specimen's session data
  (logged as an invalid measurement condition, never silently dropped).
- Custody records are append-only; corrections are new rows referencing the
  corrected event_id.

# RAC-PRINT-ALPHA-001 — Receipt QA (condensed)

Condensed from `production_alpha/RECEIPT_QA_FORM.md` — that form remains the
authoritative per-unit inspection record. One form per garment unit, completed
on delivery day, before any laundering (all units W0).

Evidence boundary: `physical_efficacy_claimed = false`;
`evidence_class = experimental_print_specimen`.

## A. Unit identity (vs `production_alpha/SKU_MANIFEST.json`)

Verify: SKU ID · role (candidate / control / reserve) · Printful product_id ·
variant / size / color · order ID / line item · artwork identity (visual match
to sealed artwork; candidate ≠ control) · wash state = W0.

## B. Print registration (tolerance ≤ 3.0 mm)

Per placement (front, back, sleeve_left, sleeve_right, pocket, hood,
label_panel, label_inside): measure offset between printed artwork
boundary/fiducial and the panel/seam reference from template geometry.
Panel-to-panel continuity across cut-sew seams: discontinuity > 3.0 mm → FAIL.

## C. Color ΔE spot-check (vs RAC-CALT-P1-0001)

Photograph garment + calibration target under the locked P1 rig (RAW, manual);
rectify via fiducials; convert sRGB → CIELAB D65/2 exactly per
`physical/p1/CALIBRATION_MANIFEST.json` patch_measurement_procedure; sample
≥ 3 flat regions; compute ΔE00 vs intended artwork color after the session
PrintCameraProfile correction. Flag for review if any single patch ΔE00 > 6.0
(screening flag only; final acceptance is session-level
PrintCameraProfile.acceptance()).

## D. Defect classes

| Class | Definition | Action |
|---|---|---|
| D0 none | no observable defect | proceed |
| D1 cosmetic | no artwork/measurement impact | proceed, note |
| D2 print defect | artwork-affecting, within tolerance | flag; session lead decides |
| D3 rejection | identity mismatch, registration > 3.0 mm, missing/misplaced panel, wrong size/product, fabric damage, confirmed color flag | REJECT; quarantine; activate reserve per `production_alpha/ORDER_WORKSHEET.md` |

## E. Acceptance

ACCEPT → unit enters active matched pair (or reserve storage).
REJECT → quarantine; do not launder or alter; retain for vendor claim;
activate reserve; open reprint question in `production_alpha/VENDOR_QUESTIONS.md`.

## F. Chain of custody

Record: delivered/received (package condition) → opened → inspected → stored
(active / reserve / quarantine, location ID) → transferred to session rig.
See `print-alpha/QA/chain-of-custody.md`.

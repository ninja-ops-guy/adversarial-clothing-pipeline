# RECEIPT_QA_FORM.md — Production Alpha on-arrival inspection form

One form per garment unit. Complete on the day of delivery, before any laundering (all units must be W0). Acceptance thresholds follow the calibration contract: registration error ≤ 3.0 mm and color spot-check vs calibration target RAC-CALT-P1-0001 (physical/p1/CALIBRATION_MANIFEST.json; session acceptance max_mean_delta_e_2000 6.0 applies to the print→camera chain — this form's spot-check is a receipt screen, not a new scientific threshold).

## A. Unit identity (vs SKU_MANIFEST.json)
| Field | Expected (from manifest) | Observed | Pass? |
|---|---|---|---|
| SKU ID | ____________ | ____________ | ☐ |
| Role (candidate / control / reserve) | ____________ | ____________ | ☐ |
| Printful product_id | ____________ | ____________ | ☐ |
| Variant / size / color | ____________ | ____________ | ☐ |
| Printful order ID / line item | ____________ | ____________ | ☐ |
| Artwork identity (visual match to sealed artwork; candidate ≠ control) | ____________ | ____________ | ☐ |
| Wash state (must be W0) | W0 | ____________ | ☐ |

## B. Print registration check (tolerance ≤ 3.0 mm)
Procedure: lay garment flat; for each placement in the manifest, measure the offset between the printed artwork boundary/fiducial feature and the panel/seam reference defined by the template geometry, using a ruler or caliper (mm).
| Placement | Measured offset (mm) | ≤ 3.0 mm? |
|---|---|---|
| front | ______ | ☐ |
| back | ______ | ☐ |
| sleeve_left | ______ | ☐ |
| sleeve_right | ______ | ☐ |
| pocket (hoodie) | ______ | ☐ |
| hood (hoodie) | ______ | ☐ |
| label_panel / label_inside (hoodie) | ______ | ☐ |

Also check panel-to-panel continuity across cut-sew seams: any visible artwork discontinuity > 3.0 mm at a seam → FAIL.

## C. Color ΔE spot-check (vs RAC-CALT-P1-0001 procedure)
Procedure:
1. Photograph the garment under the locked P1 session rig (fixed camera, fixed lighting, RAW, manual settings) together with the calibration target RAC-CALT-P1-0001 in-frame or bracketed.
2. Rectify via target fiducials; convert sampled sRGB to CIELAB D65/2 exactly as in CALIBRATION_MANIFEST.json patch_measurement_procedure.
3. Sample ≥ 3 flat regions of the garment print; compute ΔE00 of each sample against the corresponding intended artwork color (from the sealed upload file) after the session PrintCameraProfile correction.
4. Record: mean ΔE00 ______, max ΔE00 ______, sample count ______.
Screen rule: flag for review if any single patch ΔE00 exceeds the session acceptance bound (6.0). This is a screening flag only; final color acceptance is determined by the session-level PrintCameraProfile.acceptance().

## D. Defect classification
| Class | Definition | Examples | Action |
|---|---|---|---|
| D0 — none | no observable defect | — | proceed |
| D1 — cosmetic | does not affect printed artwork or measurement | loose thread, minor packaging crease | proceed, note in log |
| D2 — print defect | artwork-affecting defect within tolerance limits | small ink spot outside critical pattern region | flag; session lead decides |
| D3 — rejection | identity mismatch, registration > 3.0 mm, panel missing/misplaced, wrong size/product, fabric damage, color flag confirmed | wrong variant, seam discontinuity > 3.0 mm | REJECT; activate reserve per ORDER_WORKSHEET.md |

Observed defects (class, location, photo reference): ____________

## E. Acceptance decision
- [ ] ACCEPT — unit enters active matched pair (or reserve storage)
- [ ] REJECT — quarantine unit; do not launder or alter; retain for vendor claim; activate reserve; open reprint question in VENDOR_QUESTIONS.md
Inspector: ____________  Date: ____________  Signature: ____________

## F. Chain of custody
| Event | Date/time | Actor | Location | Notes |
|---|---|---|---|---|
| Delivered / package received | ______ | ______ | ______ | package condition: ______ |
| Package opened | ______ | ______ | ______ | |
| Inspection performed (this form) | ______ | ______ | ______ | |
| Stored (location ID) | ______ | ______ | ______ | active / reserve / quarantine |
| Transferred to session rig | ______ | ______ | ______ | |
| Returned to storage | ______ | ______ | ______ | wash state: ______ |

Photo log (package, label, garment front/back, defects): ____________

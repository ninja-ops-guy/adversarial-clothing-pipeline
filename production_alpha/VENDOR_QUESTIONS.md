# VENDOR_QUESTIONS.md — open questions for Printful (Production Alpha)

Status values: OPEN / ANSWERED (record answer + date + source). Items needing a logged-in account, token, or support ticket are marked USER ACTION REQUIRED.

| # | Question | Why it matters | Status |
|---|----------|----------------|--------|
| Q1 | What is the guaranteed print placement tolerance (mm) for CUT-SEW all-over sublimation on product 388, per panel and across seams? Public docs describe the process but publish no tolerance (accessed 2026-09-08). | Receipt QA uses ≤ 3.0 mm registration per the calibration contract; need to know whether Printful's spec is looser, and what they consider a misprint. | OPEN — USER ACTION REQUIRED (Printful support ticket / account) |
| Q2 | How are uploaded files color-managed: expected ICC profile (sRGB assumed), any per-substrate conversion, and typical color accuracy (ΔE) for sublimation on the recycled hoodie fabric? | RECEIPT_QA_FORM.md ΔE spot-check compares delivered print to sealed artwork; need the vendor's intended color pipeline to interpret deviations. | OPEN — USER ACTION REQUIRED (Printful support) |
| Q3 | Is fabric batch consistency guaranteed across units of product 388 ordered in one batch (base whiteness, fabric weight, recycled blend ratio)? Can all 4 hoodie units (pair + reserves) be confirmed from the same fabric batch? | Matched-pair validity: control and candidate must differ only in artwork; a fabric batch difference is a confound. | OPEN — USER ACTION REQUIRED (Printful support; may only be confirmable at order time) |
| Q4 | What is the reprint/refund policy and turnaround for a unit rejected at receipt for misregistration or print defect, and can a reprint reuse the identical uploaded files (byte-identical) without re-processing? | Reserve plan hedges a missed W1/W5 window; need to know whether a reprint is a full manufacturing cycle and whether artwork bytes stay identical. | OPEN — USER ACTION REQUIRED (Printful support / account) |
| Q5 | Do the v2 catalog-product IDs for products 388/257 equal the v1 IDs, and which variant namespace is authoritative for ordering? (Unauthenticated v2 calls returned 401 on 2026-09-08.) | SKU_MANIFEST.json variant IDs must be the order-authoritative namespace. | OPEN — USER ACTION REQUIRED (Printful API token): run TEMPLATE_INGESTION_CHECKLIST.md Step T3 |
| Q6 | Do the printfiles/templates responses for 388 include all 8 placements (incl. pocket, hood, label panels) with per-variant geometry, and at what dpi? | Panel geometry must be filled per SKU before artwork mapping. | OPEN — USER ACTION REQUIRED (Printful API token): run Steps T1/T4 |
| Q7 | Are mockup-generator template ZIPs available for products 388/257 from the product page, and are they byte-stable over time (versioned)? | Template archive must be hashed; byte instability would invalidate template_archive_sha256 between download and upload. | OPEN — partially answerable without auth (product page), confirm with USER ACTION REQUIRED (Printful account) |
| Q8 | Will live stock for the chosen variant be available across US/EU/EU_LV regions at order time, and does Printful ever substitute blanks on stockout without notice? | Substitution would break garment identity vs the manifest; reserve tees hedge this. | OPEN — USER ACTION REQUIRED (Printful account): re-check availability at order time per ORDER_CHECKLIST.md Step 7 |
| Q9 | Does Printful apply any automatic scaling, centering, or repositioning of uploaded files on AOP products beyond the template geometry? | Any vendor-side transform changes the effective print and must be recorded per RAC-PHYSICAL-PRINT-TEST-1.0 ("provider-side scaling or positioning changes"). | OPEN — USER ACTION REQUIRED (Printful support) |
| Q10 | Can Printful confirm production facility for our order (US vs EU) and whether facility choice affects color/placement output for the same product? | Facility is a potential confound between primary pair and reserves if split across facilities. | OPEN — USER ACTION REQUIRED (Printful account) |

## Log
| Date | Question | Answer summary | Source |
|------|----------|----------------|--------|
| | | | |

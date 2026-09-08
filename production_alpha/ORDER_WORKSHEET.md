# ORDER_WORKSHEET.md — Production Alpha matched control/candidate order worksheet

The agent never places orders or pays. All ordering steps are USER ACTION REQUIRED (Printful account). Cost fields are intentionally blank — fill at order time from the Printful quote.

## Order line items

| # | SKU | Role | Product | Variant/Size | Qty | Unit cost | Line total |
|---|-----|------|---------|--------------|-----|-----------|------------|
| 1 | PA-HOODIE-CAND-001 | candidate (primary) | 388 AOP Recycled Unisex Hoodie | PENDING_USER_SIZE_SELECTION | 1 | ______ | ______ |
| 2 | PA-HOODIE-CTRL-001 | control (primary) | 388 AOP Recycled Unisex Hoodie | same as line 1 | 1 | ______ | ______ |
| 3 | PA-HOODIE-CAND-R01 | reserve candidate | 388 | same as line 1 | 1 | ______ | ______ |
| 4 | PA-HOODIE-CTRL-R01 | reserve control | 388 | same as line 1 | 1 | ______ | ______ |
| 5 | PA-TEE-CAND-R01 | reserve fallback candidate | 257 AOP Men's Crew Neck Tee | PENDING_USER_SIZE_SELECTION | 1 | ______ | ______ |
| 6 | PA-TEE-CTRL-R01 | reserve fallback control | 257 | same as line 5 | 1 | ______ | ______ |

Subtotal: ______  Shipping: ______  Tax/VAT: ______  **Order total: ______**

## Pre-order verification (must all pass; mirrors ORDER_CHECKLIST.md Step 7)
- [ ] SKU_MANIFEST.json has no PENDING_TEMPLATE_DOWNLOAD / PENDING_USER_SIZE_SELECTION fields for ordered SKUs
- [ ] candidate ≠ control artwork hashes; identical product/variant/size/placements per pair
- [ ] template_archive_sha256 matches downloaded files
- [ ] all variants in_stock at order time (re-run availability check)
- [ ] USER ACTION REQUIRED (Printful account): place manual order in Printful Dashboard with lines 1–6

## Shipping & timeline (record actuals)
| Field | Value |
|---|---|
| Shipping address | ______ |
| Shipping method / region (US / EU / EU_LV) | ______ |
| Order date | ______ |
| Printful estimated production time | ______ |
| Estimated delivery date | ______ |
| Actual delivery date | ______ |
| Tracking number(s) | ______ |
| Printful order ID(s) | ______ |

## Reserve-unit plan
- **Quantities:** 1 extra of each primary garment (reserve candidate hoodie, reserve control hoodie) + 1 candidate tee + 1 control tee as fallback-product hedge against hoodie-SKU stockouts (per ORDER_CHECKLIST.md §W1/W5 contingency).
- **Purpose:** if a primary garment arrives damaged, misprinted, or substituted, swap in the identical reserve immediately — reprinting would take a full manufacturing cycle and could miss the fixed W1/W5 physical-session windows.
- **Storage:** reserves remain sealed in original packaging, flat, dry, dark, room temperature; do not unfold or handle except for the receipt QA identity check; store separately from the primary pair and label box "RESERVE — DO NOT OPEN UNLESS PRIMARY REJECTED".
- **Wash-state tracking:** ALL garments (primary and reserve) are wash state **W0** (never laundered) at receipt and must remain W0 through the physical capture matrix (protocols/RAC-PHYSICAL-PRINT-TEST-1.0 specifies W0 before laundering). Record wash state per SKU in the session manifest; any laundering creates a new wash state (W1, ...) and must be logged with date and method.
- **Consumption rule:** a reserve, once substituted for a rejected primary, becomes the active unit of that role; the rejected unit is quarantined (see RECEIPT_QA_FORM.md) and never re-enters the active pair.

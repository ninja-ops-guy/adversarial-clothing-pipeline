# Production Alpha SKU Manifest (v1.0.0 draft)

Status: DRAFT — pending external inputs marked OPEN / PENDING-API-FETCH below.
Scope: defines the first physical production decision ("Production Alpha") for the RAC
(Ruthless Adversarial Clothing) research repo. This document specifies what is ordered,
from whom, and how its identity is recorded. It makes no efficacy claims (see §8 Precedence).

## 1. Decision summary

Production Alpha commits to ordering a matched pair of garments from Printful: the
candidate and the control are both the All-Over Print Unisex Crew Neck T-Shirt (AOP
cut-and-sew category), white-base 100% polyester sublimation knit, size M, produced via
cut-and-sew dye sublimation (Printful API technique key `SUBLIMATION`). The candidate
carries the frozen adversarial tile mapped through the vendor's per-panel template; the
control is the identical variant printed with a solid-fill template, placed in the same
order under identical order conditions. Provider, garment, color, size, and print method
are fixed by this document; integer `product_id` / `variant_id` values are
PENDING-API-FETCH and must be resolved live against the Printful API before any order.

## 2. Vendor comparison outcome

Hard requirements (all five must hold):

1. Downloadable per-product PSD template ZIPs with guide layers, bleed, and safe zones.
2. 150–300 DPI, sRGB artwork pipeline.
3. True cut-and-sew sublimation all-over print (not cut-from-printed-roll approximations).
4. Single-unit ordering (no MOQ) for iteration.
5. Stable integer product_id/variant_id exposed via a public REST API for manifest binding.

| Vendor | Req 1 templates | Req 2 DPI/sRGB | Req 3 cut-and-sew sub | Req 4 MOQ=1 | Req 5 API IDs | Outcome |
|---|---|---|---|---|---|---|
| Printful | Yes (per-product PSD ZIPs) | Yes (150–300 DPI sRGB) | Yes | Yes | Yes (developers.printful.com) | **SELECTED** |
| Subliminator | Best-in-class per-panel templates | Yes | Yes | Yes | No public API for stable manifest IDs | Runner-up |
| Printify | Varies by print provider; not uniform | Varies | Varies by provider | Yes | API exists, but garment/provider geometry not stable per-SKU | Rejected |
| Others (AOP dropship printers surveyed) | Incomplete or no guide-layer PSDs | Unverified | Unverified | Mixed | No | Rejected |

Printful is the only vendor satisfying all five hard requirements simultaneously.
Subliminator is retained as runner-up solely on template quality; its lack of a public
API for stable manifest IDs is disqualifying under evidence governance.

Garment rationale: tee over hoodie — fewer panels/seams, flatter under the camera capture
rig, cheaper per iteration. Polyester sublimation over cotton DTG — dye-in-fiber, matte
finish, holds high-frequency pattern detail.

## 3. The golden digital SKU manifest

Example (values shown are illustrative placeholders; hash and ID fields are populated at
freeze time):

```json
{
  "manifest_version": "1.0.0",
  "generation_id": "RAC-PER-D2-0004",
  "provider": {
    "name": "Printful",
    "product_id": "PENDING-API-FETCH",
    "variant_id": "PENDING-API-FETCH",
    "technique": "SUBLIMATION",
    "fulfillment_region": "OPEN"
  },
  "garment": {
    "model": "All-Over Print Unisex Crew Neck T-Shirt",
    "color": "white-base",
    "material": "100% polyester sublimation knit",
    "size": "M"
  },
  "artwork": {
    "candidate_sha256": "<computed at freeze time>",
    "frozen_tile_sha256": "<computed at freeze time>"
  },
  "template": {
    "source_url": "<product page > File guidelines tab > template ZIP URL>",
    "template_version_or_date": "<download date or vendor version string>",
    "template_zip_sha256": "<computed at download>",
    "panel_geometry": {
      "front":  { "dims_px": [0, 0], "bleed_mm": 0, "safe_area_mm": 0, "dpi": 0 },
      "back":   { "dims_px": [0, 0], "bleed_mm": 0, "safe_area_mm": 0, "dpi": 0 },
      "sleeve_l": { "dims_px": [0, 0], "bleed_mm": 0, "safe_area_mm": 0, "dpi": 0 },
      "sleeve_r": { "dims_px": [0, 0], "bleed_mm": 0, "safe_area_mm": 0, "dpi": 0 }
    }
  },
  "mapping": {
    "mapper_version": "<Production Mapper version tag>",
    "mapping_sha256": "<computed at freeze time>",
    "panel_hashes": ["<per-panel output sha256>"]
  },
  "order": {
    "order_ids": ["<candidate order id>", "<control order id>"],
    "pair": { "candidate": true, "control": true },
    "order_conditions": "<date, shipping speed, fulfillment region, account>"
  },
  "timestamps": {
    "manifest_created_utc": "<ISO-8601>",
    "artwork_frozen_utc": "<ISO-8601>",
    "order_placed_utc": "<ISO-8601>"
  },
  "manifest_sha256": "<computed at freeze time>"
}
```

Field definitions:

| Field | Meaning |
|---|---|
| manifest_version | Schema version of this manifest (semver). |
| generation_id | Pattern generation lineage ID. D2-0004 closed FAIL / RAC-D0 on 2026-09-08 (log-attested; `docs/D2-0004_CLOSURE_NOTE.md`); the operative Production Alpha manifest (`production_alpha/SKU_MANIFEST.json`) uses the sealed RAC-PER-D2-0003 print-kit candidate. |
| provider.name | Vendor legal/display name. |
| provider.product_id | Printful integer product ID. PENDING-API-FETCH; fetch live via `GET /products`. Do not invent. |
| provider.variant_id | Printful integer variant ID for the size-M white-base tee. PENDING-API-FETCH. |
| provider.technique | Printful technique key; fixed `SUBLIMATION`. |
| provider.fulfillment_region | Region the order is pinned to for batch consistency; OPEN pending vendor answer. |
| garment.* | Physical garment identity: model, color, material, size. |
| artwork.candidate_sha256 | SHA-256 of the final mapped candidate artwork package, at freeze time. |
| artwork.frozen_tile_sha256 | SHA-256 of the frozen adversarial tile pre-mapping, at freeze time. |
| template.source_url | URL from which the template ZIP was downloaded (product page → "File guidelines" tab). |
| template.template_version_or_date | Vendor version string if present, else download date (ISO-8601). |
| template.template_zip_sha256 | SHA-256 of the downloaded template ZIP, recorded at download. |
| template.panel_geometry | Per-panel geometry extracted from the template: pixel dims, bleed, safe area, DPI. |
| mapping.mapper_version | Version tag of the repo Production Mapper used for the panel pack. |
| mapping.mapping_sha256 | Hash over the mapper profile + inputs, binding geometry to this run. |
| mapping.panel_hashes | SHA-256 of each exported per-panel print file. |
| order.order_ids | Printful order IDs for the candidate/control pair. |
| order.pair | Flags identifying the candidate and control members of the matched pair. |
| order.order_conditions | Free-text record of date, shipping speed, region, account used. |
| timestamps.* | UTC ISO-8601 timestamps for manifest creation, artwork freeze, order placement. |
| manifest_sha256 | SHA-256 over the serialized manifest with this field empty; seals the record. |

All hash fields are computed at freeze time and are immutable thereafter. Any change
requires a new manifest_version.

## 4. Template-to-Production-Mapper integration plan

The repo contains Production Mapper code (see `product-studio.js` / production mapper
modules) that currently operates on generic panel geometry. For this SKU, generic
geometry is retired in favor of real vendor template geometry. Data flow:

1. Download the Printful template ZIP for the AOP tee (product page → "File guidelines"
   tab). Record URL, download date, and template ZIP SHA-256 (manifest §3).
2. Extract per-panel geometry from the PSD guide layers: pixel dimensions, bleed, safe
   area, DPI for front, back, left/right sleeves, collar if present.
3. Emit a geometry JSON profile in the mapper's profile format.
4. Register the profile as the mapper profile for this SKU; remove/fence generic
   geometry so it cannot be selected for this manifest.
5. Run the frozen adversarial tile through the mapper → per-panel pack export
   (print-ready files at template DPI, sRGB).
6. Hash binding: compute per-panel SHA-256, mapping_sha256, and write all hashes into
   the manifest. The manifest, not the files in flight, is the source of truth.

## 5. Ordering plan — matched pair protocol

- Same provider (Printful), same garment model/color/material/size, same print process
  (cut-and-sew sublimation), same order conditions, placed in a single order where the
  API permits.
- Candidate: per-panel pack from §4. Control: identical variant printed with a
  solid-fill template (single flat color), same order.
- Record fulfillment region for both items; if the vendor cannot guarantee same-region
  fulfillment, record actual regions and flag for batch-consistency risk.
- Record order IDs, timestamps, and conditions in the manifest.

## 6. Manufacturing QA on arrival (pre-efficacy)

Tolerances are OPEN pending vendor answers (§7). Each check must produce a recorded
measurement before any efficacy testing.

| Check | Measurement method | Acceptance note |
|---|---|---|
| Color shift vs digital twin | Photograph under the calibrated capture rig; compare against digital twin swatches in sRGB; report ΔE per region | Tolerance OPEN |
| Scale error | Measure known tile features on fabric vs template dims with calibrated ruler/photogrammetry; report % deviation | Tolerance OPEN |
| Placement | Measure anchor-point offsets per panel against template coordinates (mm) | Tolerance OPEN |
| Registration | Measure cross-panel alignment at seams; report max misregistration (mm) | Tolerance OPEN (vendor numeric tolerance requested) |
| Seam continuity | Visual + photographic check of pattern continuity across each seam | Documented pass/fail with photos |
| Fabric distortion | Lay flat; measure panel dimensions vs template; note stretch/warp | Tolerance OPEN |

QA applies to both candidate and control. Failures trigger re-order or vendor escalation,
not silent acceptance.

## 7. Open Items (external)

1. Printful account creation + API key provisioning.
2. Template ZIP download for the AOP tee; record URL + download date + SHA-256.
3. Live fetch of integer `product_id` / `variant_id` via `GET /products` (PENDING-API-FETCH).
4. Vendor questions outstanding:
   a. Effective on-fabric print resolution.
   b. Numeric panel-registration tolerance.
   c. Template versioning policy.
   d. Fulfillment-region pinning for batch consistency.
   e. Whether unprinted blanks of the identical garment are sold (useful for rig calibration).
5. Shipping address and budget approval.

## 8. Precedence

This document defers to PRODUCT_THESIS: no efficacy claim is made or implied here; this
is a production identity and QA specification only. It also defers to the Production
Completion Checklist for what constitutes "done" for a production run. Where any
statement in this document conflicts with those documents, those documents win.

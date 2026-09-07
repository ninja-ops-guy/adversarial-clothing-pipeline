# Printful Production Alpha SOP

**Version:** 1.0.0  
**Purpose:** Convert a frozen RAC textile into the first matched physical control/candidate pair without breaking provenance.

> Provider UI/API details can change. Record the exact provider pages, API responses, template bytes, IDs, and dates used for the actual order.

## 1. Current SKU decision

Target:

- Printful all-over-print unisex crew-neck tee;
- white-base 100% polyester;
- size M;
- cut-and-sew dye sublimation;
- candidate and control matched on every available production variable.

This is the Production Alpha research SKU, not a universal commercial recommendation.

## 2. Account/API setup

Before downloading/ordering:

- create/authorize Printful account;
- create API access appropriate for catalog/product lookup;
- store credentials outside source control;
- record API/account setup date;
- fetch exact product and variant metadata;
- save raw JSON response as an experiment/vendor artifact.

Never place credentials in the repo.

## 3. Resolve exact identifiers

Record:

- product_id;
- variant_id;
- product name;
- size;
- color/base;
- material composition;
- print technique;
- catalog URL/API endpoint;
- retrieval timestamp.

If the product has changed from the preregistered Production Alpha choice, stop and update the SKU decision before ordering.

## 4. Acquire template

Download the exact provider template ZIP/PSD/PNG package for the selected product.

Immediately preserve:

- original filename;
- raw ZIP bytes;
- SHA-256;
- source URL/page;
- retrieval date;
- provider product ID;
- any version/date embedded in the template;
- included instructions.

Do not edit the original vendor archive.

## 5. Encode template for RAC

Create the RAC adapter JSON from the provider geometry.

For each panel capture:

- panel ID/name;
- canvas dimensions;
- panel x/y/width/height;
- bleed;
- safe margin;
- rotation;
- continuity group;
- seam relationships;
- DPI;
- units;
- provider source reference;
- template version.

Validate against the vendor-template guard.

## 6. Map frozen candidate

Load the exact frozen Product Studio design into Production Mapper.

Verify:

- candidate master SHA-256;
- family/product/seed;
- template SHA-256;
- mapping SHA-256;
- each panel SHA-256;
- continuity validation;
- bleed/safe-area status.

Export the panel pack. Do not regenerate the design during mapping.

## 7. Create matched control

The control must use the same:

- provider;
- product;
- variant;
- size;
- base/substrate;
- print process;
- template;
- fulfillment/order window.

Only the experimental artwork should differ.

Use the preregistered solid/control design and hash it exactly like the candidate.

## 8. Golden SKU manifest

Freeze a manifest containing:

- RAC experiment ID;
- candidate ID;
- provider;
- product_id;
- variant_id;
- product name;
- size;
- material;
- process;
- candidate master SHA;
- control master SHA;
- template SHA;
- mapping SHA;
- panel hashes;
- source commit;
- order date;
- order ID after submission;
- fulfillment region when known;
- notes/deviations.

## 9. Pre-order QA

Before checkout/API order:

- compare control/candidate SKU metadata;
- verify dimensions;
- verify panel coverage;
- inspect seams/continuity;
- verify no unintended scaling/cropping;
- verify safe/bleed areas;
- verify candidate/control manifests;
- verify hashes;
- archive provider preview/mockup if available.

## 10. Place matched order

Prefer candidate and control in the same order to reduce production variability.

If budget permits, order reserve units for calibration/durability/replacement so later work is not delayed by another manufacturing cycle.

Record order ID immediately.

## 11. Receipt SOP

On arrival:

1. photograph unopened package;
2. photograph labels/SKU identifiers;
3. photograph control and candidate front/back/details under fixed light;
4. inspect size/material/construction;
5. record obvious defects;
6. assign physical artifact IDs;
7. record receipt date;
8. record fulfillment origin if available;
9. hash digital receipt/photograph records;
10. stop if candidate/control are materially mismatched.

## 12. Questions to resolve with provider

Document answers, including source/date:

- effective on-fabric print resolution;
- expected panel registration tolerance;
- template-version/change policy;
- fulfillment-region consistency/pinning;
- whether repeat orders may use materially different production equipment/processes.

Unknown answers remain UNKNOWN; do not infer them.

## 13. Handoff

After receipt:

Production Alpha → calibration target/capture → P1 matched experiment → immutable RAC release.

Ordering a garment does not create RAC-P evidence.

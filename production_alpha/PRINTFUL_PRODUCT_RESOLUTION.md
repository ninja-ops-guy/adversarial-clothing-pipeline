# PRINTFUL_PRODUCT_RESOLUTION.md — Production Alpha (Wave F, Track B)

Access date for all sources: 2026-09-08
Evidence labels: published_observation (verified live against Printful public endpoints) / scenario_assumption / UNVERIFIED.

## 1. Chosen garment (primary candidate)

**All-Over Print Recycled Unisex Hoodie** — Printful catalog product_id **388** (v1 catalog namespace).
Rationale: matches `primary_product: "hoodie"` in `/mnt/agents/acp/print-test-kit-status.json` (candidate RAC-PER-D2-0003 sealed print-kit); hoodie offers large continuous panels (front/back/hood) for a full-coverage adversarial texture, sublimation print ("ink becomes part of the fabric") resists cracking/peeling.

Secondary candidate (cheaper, faster, fallback): **All-Over Print Men's Crew Neck T-Shirt**, product_id **257**.

## 2. Resolution table

| Field | Product 388 (hoodie, PRIMARY) | Product 257 (tee, fallback) | Verification status |
|---|---|---|---|
| product_id (v1) | 388 | 257 | VERIFIED — live `GET https://api.printful.com/products/388` and `/257`, HTTP 200, no auth (published_observation) |
| Title | All-Over Print Recycled Unisex Hoodie | All-Over Print Men's Crew Neck T-Shirt | VERIFIED (same source) |
| Print technique | CUT-SEW, "All-over synthetic" (sublimation, is_default) | CUT-SEW, "All-over synthetic" (sublimation, is_default) | VERIFIED (techniques field, same source) |
| is_discontinued | false | false | VERIFIED (same source) |
| variant_ids (v1) + sizes | 2XS:18730, XS:10869, S:10870, M:10871, L:10872, XL:10873, 2XL:10874, 3XL:10875, 4XL:18731, 5XL:18732, 6XL:18733 (all White) | XS:8850, S:8851, M:8852, L:8853, XL:8854, 2XL:8855 (all White) | VERIFIED (variants array, same source) |
| Stock status | all variants in_stock in EU / EU_LV / US regions | all variants in_stock in EU / EU_LV / US regions | VERIFIED as of 2026-09-08; re-check at order time |
| Placements / file slots | front, back, sleeve_left, sleeve_right, pocket, hood, label_panel, label_inside, mockup | front (default), back, sleeve_left, sleeve_right, mockup | VERIFIED (files field, same source) |
| Printfile/template archive | UNVERIFIED — `GET https://api.printful.com/mockup-generator/printfiles/388` returned HTTP 401 without token | UNVERIFIED — `GET .../printfiles/257` returned HTTP 401 | NOT verifiable without auth; see §3 |
| v2 catalog_product_id mapping | UNVERIFIED — `GET https://api.printful.com/v2/catalog-products/388` returned "This endpoint requires Oauth authentication!" | same | Requires user API token; see §3 |
| Panel geometry (mm) | UNVERIFIED | UNVERIFIED | Obtained from printfiles response after auth (width/height/dpi per variant) |

## 3. Exact API calls the user must run (with Printful API token)

```
# 0. Create token: Printful Dashboard -> Settings -> API (or developer.printful.com). Store as $PF_TOKEN.

# 1. Confirm v2 catalog product + variants (v2 IDs are the authoritative order namespace):
curl -s -H "Authorization: Bearer $PF_TOKEN" \
  https://api.printful.com/v2/catalog-products/388 | jq .
curl -s -H "Authorization: Bearer $PF_TOKEN" \
  https://api.printful.com/v2/catalog-products/388/catalog-variants | jq '.data[] | {id, size, color}'
# Cross-check v1 product 388 == v2 catalog-product 388 (IDs are expected to match, but this is UNVERIFIED).

# 2. Retrieve printfiles (panel geometry, per variant):
curl -s -H "Authorization: Bearer $PF_TOKEN" \
  https://api.printful.com/mockup-generator/printfiles/388 | jq .
# Response contains printfiles[] {printfile_id,width,height,dpi,fill_mode} and
# variant_printfiles[] mapping variant_id -> placements. Px -> mm: mm = px / dpi * 25.4 (dpi is 150 in Printful examples).

# 3. Layout templates (template archive / panel images):
curl -s -H "Authorization: Bearer $PF_TOKEN" \
  https://api.printful.com/mockup-generator/templates/388 | jq .

# 4. Repeat 1–3 for fallback product 257.
```

## 4. Control garment (matched pair)

Control = the SAME catalog product and SAME size variant as the candidate, printed with the unmodified base design (see ORDER_CHECKLIST.md §Control rule). No separate product_id is needed; the control uses identical variant_ids with `control_texture_sha256` instead of the adversarial texture.

## 5. Source URLs (all accessed 2026-09-08)

- https://api.printful.com/products (v1 catalog list, unauthenticated, HTTP 200)
- https://api.printful.com/products/388, https://api.printful.com/products/257 (unauthenticated, HTTP 200)
- https://api.printful.com/mockup-generator/printfiles/388 (HTTP 401 without token — auth required)
- https://api.printful.com/v2/catalog-products/388 (HTTP 401 — OAuth required)
- https://developers.printful.com/docs/ (v1 Catalog API, Product Templates API, Mockup Generator API: `/mockup-generator/printfiles/{id}`, `/mockup-generator/templates/{id}`)
- https://developers.printful.com/docs/v2-beta/ (Catalog v2: `GET /v2/catalog-products/{id}/catalog-variants`, OAuth required)
- https://help.printful.com/hc/en-us/articles/10293184543260-What-should-I-know-about-Printful-s-API-v2 (API v2 open beta)
- https://www.printful.com/blog/how-to-make-custom-all-over-print-shirts (AOP technique, cut-and-sew panels, file guidance)
- https://www.printful.com/blog/best-quality-tshirts-for-printing (AOP Men's Crew Neck T-Shirt: from $25.95, XS–2XL, White, 95% polyester / 5% elastane, sublimation)

UNVERIFIED items and what verifies them: v2 ID mapping, printfile dimensions, template ZIP contents, live stock at order time — all verified by running the §3 calls with a valid token.

# TEMPLATE_INGESTION_CHECKLIST.md — Printful template archive acquisition & hashing

Purpose: acquire the **untouched** Printful template/printfile data for products 388 (hoodie, primary) and 257 (tee, fallback), hash it, and record the hashes + panel geometry into `SKU_MANIFEST.json`. Do not modify, resize, recompress, or re-save any downloaded template artifact before hashing.

## Step T0 — Authentication (USER ACTION REQUIRED (Printful API token))
1. USER ACTION REQUIRED (Printful API token): create a private token — Printful Dashboard → Settings → Stores → API (or https://developers.printful.com).
2. USER ACTION REQUIRED (Printful API token): `export PF_TOKEN=...`
3. Sanity check:
   ```
   curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/oauth/scopes
   ```
   Expect HTTP 200.

## Step T1 — Download printfiles + templates (untouched bytes)
USER ACTION REQUIRED (Printful API token) for every call in this step (endpoints returned HTTP 401 unauthenticated on 2026-09-08).
```
mkdir -p template_archive
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/mockup-generator/printfiles/388 -o template_archive/printfiles_388.json
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/mockup-generator/templates/388  -o template_archive/templates_388.json
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/mockup-generator/printfiles/257 -o template_archive/printfiles_257.json
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/mockup-generator/templates/257  -o template_archive/templates_257.json
```
- If the product page offers a downloadable template ZIP, prefer the ZIP: download it untouched and use it in place of (or in addition to) the JSON responses. Record exactly which artifacts were acquired.
- [ ] Verify each response is valid JSON (or a ZIP), not an error body: check for `"error"` keys and HTTP status.

## Step T2 — Hash the archive (agent or user; no auth)
```
cd template_archive && sha256sum printfiles_388.json templates_388.json printfiles_257.json templates_257.json | tee SHA256SUMS.txt
```
- [ ] Record each hash into `SKU_MANIFEST.json → template_archive_sha256` for the affected SKUs (per-SKU field), replacing the `PENDING_TEMPLATE_DOWNLOAD` placeholders. Never invent or estimate a hash; if an artifact was not downloaded, its placeholder stays.

## Step T3 — Confirm v2 catalog identity (USER ACTION REQUIRED (Printful API token))
```
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/v2/catalog-products/388
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/v2/catalog-products/388/catalog-variants
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/v2/catalog-products/257
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/v2/catalog-products/257/catalog-variants
```
- [ ] Titles match PRINTFUL_PRODUCT_RESOLUTION.md §2; v2 IDs equal v1 IDs 388/257 (else record the mapping in the manifest).
- [ ] Variant sizes/colors match the v1 variant maps in the manifest; resolve the chosen order size to a variant_id.

## Step T4 — Panel geometry extraction & verification
1. From `printfiles_388.json`: locate `variant_printfiles` for the chosen variant_id; for each placement (front, back, sleeve_left, sleeve_right, pocket, hood, label_panel, label_inside) take the printfile `width`, `height`, `dpi`.
2. Convert: `mm = px / dpi * 25.4`. Fill `panel_geometry.<placement>.width_mm / height_mm / dpi` per SKU.
3. Repeat for product 257 (front, back, sleeve_left, sleeve_right).
- [ ] All panel_geometry values non-null; no `PENDING_TEMPLATE_DOWNLOAD` remains for the SKUs being ordered.
- [ ] Sanity: front panel width plausible for the chosen size (hoodie chest width); front/back heights equal within template tolerance; dpi consistent across placements.
- [ ] Placements available in the printfiles response match the manifest placement list exactly; any missing placement is flagged in VENDOR_QUESTIONS.md before ordering.

## Step T5 — Artwork mapping & hashing
1. Verify the sealed print kit: `sha256sum print-test-kit.zip` must equal `b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548`; inner pattern must equal `b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546` (candidate RAC-PER-D2-0003).
2. Tile the frozen pattern onto each verified panel rectangle at the template dpi (no regeneration, no retuning, identical tiling origin/scale for candidate and control).
3. Produce the control artwork per the control rule in SKU_MANIFEST.json.
4. `sha256sum` each final per-placement upload file; record as per-SKU `artwork_sha256`.
- [ ] candidate artwork_sha256 ≠ control artwork_sha256.
- [ ] All `PENDING_TEMPLATE_DOWNLOAD` artwork placeholders resolved for ordered SKUs.

## Step T6 — Final manifest audit
- [ ] `unverified_fields` emptied; evidence_label upgraded per ORDER_CHECKLIST.md Step 7.
- [ ] Manifest remains canonical JSON (sorted keys, 2-space indent, trailing newline).

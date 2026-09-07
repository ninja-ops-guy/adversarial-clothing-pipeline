# ORDER_CHECKLIST.md — Production Alpha matched-pair order (user-executed)

The agent never places orders or pays. Execute steps in order; record outputs into `SKU_MANIFEST_DRAFT.json`.

## Step 0 — Account & API token
1. Log in to your Printful account (or create one at https://www.printful.com).
2. Create a private API token: Printful Dashboard → Settings → Stores → API (or https://developers.printful.com). Export it: `export PF_TOKEN=...`.
3. Sanity check: `curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/oauth/scopes` returns 200.

## Step 1 — Verify product/variant IDs (v2 authoritative namespace)
Run the §3 calls in PRINTFUL_PRODUCT_RESOLUTION.md:
```
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/v2/catalog-products/388
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/v2/catalog-products/388/catalog-variants
```
- [ ] Confirm v2 catalog-product 388 exists and title = "All-Over Print Recycled Unisex Hoodie".
- [ ] Pick the order size; record its variant_id into both garment_pair entries (candidate and control use the SAME size/variant_id).
- [ ] If v2 ID ≠ v1 ID 388, update the manifest and note the mapping.

## Step 2 — Template/printfile archive download + hash
```
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/mockup-generator/printfiles/388 -o printfiles_388.json
curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/mockup-generator/templates/388 -o templates_388.json
sha256sum printfiles_388.json templates_388.json   # record into manifest template_archive_sha256
```
- [ ] Hashes recorded. (If Printful offers a downloadable template ZIP from the product page, prefer that and hash the ZIP instead.)

## Step 3 — Panel-geometry extraction
From `printfiles_388.json`: for the chosen variant_id, take each placement's printfile `width`/`height`/`dpi` and convert: `mm = px / dpi * 25.4`. Fill `panel_geometry` in the manifest for: front, back, sleeve_left, sleeve_right, pocket, hood, label_panel, label_inside.
- [ ] All panel_geometry values non-null.

## Step 4 — Texture mapping (candidate)
Candidate texture comes from the sealed print-kit of the closed D2 generation:
`/mnt/agents/acp/print-test-kit-status.json` → kit `print-test-kit.zip`, candidate `RAC-PER-D2-0003`,
expected pattern_sha256 `b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546`.
1. Locate/obtain `print-test-kit.zip`; verify `sha256sum` equals `b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548` (status in repo says `ready_for_print_and_physical_test: true`; note D2 decision is FAIL — this physical test is the governance-required physical evidence step).
2. Tile/map the frozen pattern (do NOT regenerate or re-tune it) onto each verified panel rectangle from Step 3 at the template dpi.
3. `sha256sum` the final per-placement upload files; record the canonical hash as `texture_sha256`.

## Step 5 — Matched control generation rule
Control = identical catalog product (388), identical variant_id/size, identical placement set and panel geometry, printed with the **unmodified base design**: the same frozen D2 generation's pre-modification base texture (the pattern the adversarial perturbation was applied to), with no adversarial layers, no retuning, same color profile, same dpi, same tiling origin and scale as the candidate mapping. If no pre-modification base texture is sealed in the repo, use a flat mid-gray (sRGB 128,128,128) full-coverage fill as the control design and mark it `scenario_assumption` in the manifest. Record `control_texture_sha256`.

## Step 6 — Reserves (order now if budget permits)
Per user directive, add the 4 reserve line items from `SKU_MANIFEST_DRAFT.json → reserve_articles`:
1× reserve candidate (product 388, same size), 1× reserve control (product 388, same size), 1× fallback candidate tee (product 257, size→variant from 8850–8855), 1× fallback control tee (product 257, same size).

## Step 7 — Final pre-order verification checklist
- [ ] candidate `texture_sha256` recomputed and equal to manifest value
- [ ] `control_texture_sha256` recomputed and equal to manifest value
- [ ] candidate ≠ control texture hashes (they must differ)
- [ ] candidate and control share identical product_id, variant_id, size, placement set
- [ ] template_archive_sha256 matches the downloaded printfile/template files
- [ ] all variants in_stock (re-run availability check)
- [ ] manifest `evidence_label` upgraded from `scenario_assumption` to `internally_measured` for verified fields; `unverified_fields` empty
- [ ] order totals reviewed; ONLY THEN place order in Printful Dashboard (manual order) with the 2 primary + up to 4 reserve items

## W1/W5 delivery-window contingency
Physical waves W1 and W5 have fixed detection/photo-session windows. If the primary pair arrives damaged, misprinted, or out-of-stock substitutions occur, reprinting takes a full manufacturing cycle (production + shipping) that can miss the window. The reserve articles ordered in Step 6 are pre-positioned so a failed primary garment can be swapped immediately without initiating a new Printful production cycle. Fallback tee reserves (product 257) additionally hedge against hoodie-SKU stockouts.

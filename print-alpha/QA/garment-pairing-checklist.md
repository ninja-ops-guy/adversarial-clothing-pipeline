# RAC-PRINT-ALPHA-001 — Garment Pairing Checklist

Matched-pair verification for the control/candidate print-alpha garments. A
pair is admissible for capture only when **every** check below passes. Source
rule: `production_alpha/SKU_MANIFEST.json` → `control_rule` and the
matched-pair semantics in `docs/P1_CAPTURE_RIG_SPEC.md` (same product, size,
substrate, manufacturing process, actor, session, path, camera, lighting).

Evidence boundary: `physical_efficacy_claimed = false`;
`evidence_class = experimental_print_specimen`.

## 1. SKU match

- [ ] Control SKU ID is `PA-HOODIE-CTRL-001`; candidate SKU ID is `PA-HOODIE-CAND-001` (per `production_alpha/SKU_MANIFEST.json`).
- [ ] Both units are Printful **product_id 388** (All-Over Print Recycled Unisex Hoodie), color White.
- [ ] Neither unit is a reserve article unless a reserve activation is logged (per `production_alpha/ORDER_WORKSHEET.md`).

## 2. Material / substrate match

- [ ] Both units are the same fabric/substrate (CUT-SEW all-over synthetic, sublimation) from the same product line.
- [ ] Fabric hand/weight visually and tactilely consistent between units; no substituted blanks.

## 3. Size / variant match

- [ ] `variant_id` identical on both units (matched-pair rule: SAME variant_id and size as candidate; resolved from the v1 variant map once user size selection completes — currently `PENDING_USER_ACTION`, UA-1).
- [ ] Physical size labels on both garments identical and matching the manifest size.

## 4. Print technology match

- [ ] Both units printed with the same print technology (sublimation cut-sew); vendor value recorded identically for both (currently `PENDING_USER_ACTION`, UA-1/UA-4).
- [ ] Same placements on both units: front, back, sleeve_left, sleeve_right, pocket, hood, label_panel, label_inside.
- [ ] Same panel geometry, dpi, tiling origin and scale (verified against template geometry; registration ≤ 3.0 mm per receipt QA).

## 5. Vendor / batch match

- [ ] Same printer vendor and facility for both units (`PENDING_USER_ACTION` until vendor-confirmed, UA-4).
- [ ] Same manufacturing batch, or batch difference explicitly logged in the session manifest (`PENDING_USER_ACTION` until order confirmation, UA-2).
- [ ] Same Printful order (preferred) or linked order IDs recorded on both receipt QA forms.

## 6. Artwork identity

- [ ] Candidate artwork is byte-identical to the sealed per-placement upload files (artwork_sha256 in `print-alpha/MANIFESTS/artwork-manifest.json`); expected pattern sha256 `b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546`.
- [ ] Control artwork is the unmodified base texture per the SKU_MANIFEST control rule (flat mid-gray sRGB(128,128,128) fill marked `scenario_assumption` if no sealed base texture exists).
- [ ] Candidate ≠ control on visual inspection (anti-swap check).

## Sign-off

Pairing verified by: ____________  Date: ____________
Any unresolved `PENDING_USER_ACTION` field blocks capture (fail-closed).

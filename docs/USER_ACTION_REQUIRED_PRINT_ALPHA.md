# USER ACTION REQUIRED — Print Alpha Consolidated Packet

**Document ID:** UAR-PRINT-ALPHA-001
**Applies to:** RAC-PRINT-ALPHA-001 (matched control/candidate print run)
**Audience:** the human operator. **No repository-architecture knowledge is required.**
Every action below lists exactly what to do, what to keep, and where it goes.

**Evidence boundary (applies to every action):**
`physical_efficacy_claimed = false`; `evidence_class = experimental_print_specimen`.
Nothing in this packet tests, measures, or claims adversarial efficacy. Fields that
cannot be resolved yet stay as the literal string `PENDING_USER_ACTION` and are never
filled in with guesses. A `PENDING_USER_ACTION` status never becomes `PASS` without the
named physical input.

**How to use this packet:** execute UA-1 through UA-8 in order. Do not skip ahead:
each action's output is the next action's input. If any step cannot be completed,
stop and leave the corresponding repo field as `PENDING_USER_ACTION`.

---

## UA-1 — Printful account + API access

**Exact steps**
1. Create or log in to a Printful account at https://www.printful.com.
2. Create a private API token: Printful Dashboard → Settings → Stores → API
   (or via https://developers.printful.com).
3. Store the token as an environment variable on your own machine:
   `export PF_TOKEN=<token>`. Do **not** paste the token into any repo file.
4. Sanity check: `curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/oauth/scopes`
   must return HTTP 200.

- **WHY_REQUIRED:** every vendor fact (product IDs, variant IDs, template files,
  panel geometry) must be fetched from the live Printful API; the repo fail-closed
  rule forbids inventing them. The token is the only credential needed.
- **INPUT:** a Printful account; payment method (used later at UA-5).
- **EXPECTED_OUTPUT:** a working `PF_TOKEN` that returns HTTP 200 on the scopes call.
- **WHERE_TO_STORE_OUTPUT:** nowhere in the repo — the token stays on your machine.
  Record only "token verified, date" in `production_alpha/ORDER_WORKSHEET.md`.
- **WHAT_GATE_IT_UNBLOCKS:** UA-2 (template download) and UA-4 (SKU/variant resolution).

---

## UA-2 — Obtain the exact garment production template

**Exact steps** (product: Printful catalog product **388**, All-Over Print Recycled
Unisex Hoodie, color White, cut-and-sew sublimation)
1. `curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/mockup-generator/printfiles/388 -o printfiles_388.json`
2. `curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/mockup-generator/templates/388 -o templates_388.json`
3. If the product page offers a downloadable template ZIP (product page →
   "File guidelines" tab), download that ZIP too and prefer it as the archive of record.
4. Keep the downloaded file(s) unchanged — do not re-save or convert them.

- **WHY_REQUIRED:** this is the single biggest external production blocker
  (`docs/PRODUCTION_COMPLETION_CHECKLIST.md` step 3). All panel dimensions, DPI,
  bleed, and safe areas must come from the real vendor template; guessed geometry
  is forbidden.
- **INPUT:** UA-1 token.
- **EXPECTED_OUTPUT:** `printfiles_388.json`, `templates_388.json`, and/or the
  template ZIP, byte-exact as downloaded.
- **WHERE_TO_STORE_OUTPUT:** `production_alpha/` (as referenced by
  `production_alpha/TEMPLATE_INGESTION_CHECKLIST.md`); the SHA-256 goes into
  `print-alpha/MANIFESTS/template-manifest.json` at UA-3.
- **WHAT_GATE_IT_UNBLOCKS:** UA-3 (hash + mapping bind) and all per-placement
  artwork export.

---

## UA-3 — Record template SHA-256 and bind the production mapping

**Exact steps**
1. `sha256sum printfiles_388.json templates_388.json` (or the template ZIP).
2. Record the hash(es), download URL, and download date into
   `print-alpha/MANIFESTS/template-manifest.json` (`template_archive_sha256`) and
   `production_alpha/SKU_MANIFEST.json` (`template.*` fields), replacing
   `PENDING_USER_ACTION`.
3. Extract per-panel geometry for the chosen variant (front, back, sleeve_left,
   sleeve_right, pocket, hood, label_panel, label_inside): take each placement's
   `width`/`height`/`dpi` from `printfiles_388.json` and convert with
   `mm = px / dpi * 25.4`. Fill `panel_geometry` in both manifests.
4. Tile the frozen pattern (SHA-256
   `b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546` — never
   regenerate or retune it) onto each panel rectangle at template DPI.
5. `sha256sum` each per-placement upload file and record the hashes in
   `print-alpha/MANIFESTS/artwork-manifest.json` and `mapping-manifest.json`.

- **WHY_REQUIRED:** the manifest — not files in flight — is the source of truth.
  Hash binding makes the template, geometry, and artwork immutable and auditable.
- **INPUT:** UA-2 files; the sealed print-test kit
  (`print-test-kit.zip`, SHA-256 `b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548`).
- **EXPECTED_OUTPUT:** all `PENDING_USER_ACTION` geometry/hash fields in
  `print-alpha/MANIFESTS/template-manifest.json`, `artwork-manifest.json`, and
  `mapping-manifest.json` replaced by real 64-hex values; per-placement upload PNGs.
- **WHERE_TO_STORE_OUTPUT:** manifests in `print-alpha/MANIFESTS/`; upload files in
  `print-alpha/CANDIDATE/` and `print-alpha/CONTROL/`.
- **WHAT_GATE_IT_UNBLOCKS:** UA-5 (order) and the Production Alpha gate
  ("provider-accepted panel pack").

---

## UA-4 — Select the matched control/candidate SKU

**Exact steps**
1. `curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/v2/catalog-products/388`
   — confirm the title is "All-Over Print Recycled Unisex Hoodie".
2. `curl -s -H "Authorization: Bearer $PF_TOKEN" https://api.printful.com/v2/catalog-products/388/catalog-variants`
   — pick your order size and note its integer `variant_id`.
3. Record the **same** `variant_id` and size on both garments in
   `print-alpha/MANIFESTS/sku-manifest.json` (candidate `PA-HOODIE-CAND-001`,
   control `PA-HOODIE-CTRL-001`) and in `production_alpha/SKU_MANIFEST.json`.
4. Control design rule: identical product/variant/size/placements/geometry printed
   with the unmodified pre-modification base texture; if no sealed base texture
   exists, use a flat mid-gray sRGB(128,128,128) full-coverage fill and keep the
   `scenario_assumption` evidence label.

- **WHY_REQUIRED:** the control pairing is mandatory, not optional
  (`docs/PRODUCTION_COMPLETION_CHECKLIST.md` step 7). The experiment is only valid
  if control and candidate differ **only** in the printed artwork.
- **INPUT:** UA-1 token; your size choice.
- **EXPECTED_OUTPUT:** one integer `variant_id` + size recorded identically on both
  SKUs; control fill decision recorded.
- **WHERE_TO_STORE_OUTPUT:** `print-alpha/MANIFESTS/sku-manifest.json` and
  `production_alpha/SKU_MANIFEST.json` (`garment_pair[].variant_id`, `size`).
- **WHAT_GATE_IT_UNBLOCKS:** UA-5 (order placement).

---

## UA-5 — Order the matched garments

**Exact steps** (follow `production_alpha/ORDER_CHECKLIST.md` — the agent never
places orders or pays)
1. Complete the Step 7 pre-order verification in `production_alpha/ORDER_CHECKLIST.md`
   (candidate and control texture hashes recomputed and equal to manifest values;
   candidate ≠ control; variant IDs identical).
2. Place one Printful order containing: 1× candidate (product 388), 1× control
   (product 388, same variant), and — if budget permits — the 4 reserve line items
   listed in `production_alpha/SKU_MANIFEST_DRAFT.json → reserve_articles`
   (1× reserve candidate 388, 1× reserve control 388, 1× fallback candidate tee
   product 257, 1× fallback control tee 257, same size).
3. Same shipping speed and fulfillment region for all line items.
4. Record order IDs, date, region, and conditions.

- **WHY_REQUIRED:** everything between Production Alpha and Production Beta depends
  on real physical objects; code cannot close this.
- **INPUT:** UA-3 hashes, UA-4 variant, shipping address, budget approval.
- **EXPECTED_OUTPUT:** Printful order ID(s) for the matched pair (and reserves).
- **WHERE_TO_STORE_OUTPUT:** `production_alpha/SKU_MANIFEST.json → order.order_ids`,
  `order.order_conditions`, `timestamps.order_placed_utc`; worksheet notes in
  `production_alpha/ORDER_WORKSHEET.md`.
- **WHAT_GATE_IT_UNBLOCKS:** UA-7 (receipt QA), UA-8 (capture), and the
  Production Alpha gate ("ordered sample").

---

## UA-6 — Fabricate the calibration target (RAC-CALT-P1-0001)

**Exact steps**
1. The digital target is already generated deterministically by
   `scripts/generate_calibration_target.py`; its manifest
   (`calibration-target-manifest.json`) binds the target ID, per-patch sRGB/Lab
   reference values, fiducial coordinates, the 100 mm scale bar, and the PNG
   SHA-256. Re-generation is byte-identical, so the file you already have is the
   authoritative reference — do not edit it.
2. Print `RAC-CALT-P1-0001.png` at **100% scale, 300 dpi**, on matte paper (or have
   it fabricated on a rigid matte board). Verify with a ruler that the printed
   scale bar measures exactly **100 mm**; if not, reprint — scaling is forbidden.
3. Label the printed target `RAC-CALT-P1-0001` with the SHA-256 prefix from the
   manifest.

- **WHY_REQUIRED:** the calibration target is the physical anchor that converts
  "photograph of a shirt" into measured color/scale/geometry data; without it,
  receipt QA (UA-7) and the capture session (UA-8) produce unusable images.
- **INPUT:** the generated PNG + manifest (output of
  `scripts/generate_calibration_target.py`); a 300-dpi-capable printer; a ruler.
- **EXPECTED_OUTPUT:** one physical calibration target whose scale bar measures
  100 mm, labeled with target ID and hash prefix.
- **WHERE_TO_STORE_OUTPUT:** the physical target lives with the capture rig; the
  digital reference stays at `print-alpha/CALIBRATION/` (see its README) and
  `physical/p1/CALIBRATION_MANIFEST.json`.
- **WHAT_GATE_IT_UNBLOCKS:** UA-7 color spot-checks and UA-8 session calibration
  acceptance (max mean ΔE00 6.0 for the print→camera chain).

---

## UA-7 — Receipt QA on arrival

**Exact steps** (one form per garment, on delivery day, before any laundering —
all units must stay wash state W0)
1. Fill `production_alpha/RECEIPT_QA_FORM.md` per unit: identity vs manifest,
   print registration (≤ 3.0 mm per placement), seam continuity, fabric distortion,
   defect classification.
2. Photograph each garment with the RAC-CALT-P1-0001 target in-frame; do the ΔE00
   spot-check per the form's §C procedure.
3. Apply the pairing checks in `print-alpha/QA/garment-pairing-checklist.md`
   (SKU, substrate, size/variant, print technology match).
4. Start the custody log in `print-alpha/QA/chain-of-custody.md` (tags, photo log,
   storage location).
5. Failures trigger re-order or vendor escalation — never silent acceptance.

- **WHY_REQUIRED:** receipt QA is a manufacturing measurement gate that must pass
  before any efficacy testing; it catches wrong garments, misprints, and
  mismatched pairs while a re-order is still cheap.
- **INPUT:** delivered garments (UA-5); printed calibration target (UA-6);
  the manifest values from UA-3/UA-4.
- **EXPECTED_OUTPUT:** one completed receipt-QA form per unit + a pairing verdict
  (pair admissible / not admissible) + custody-log entries with photos and hashes.
- **WHERE_TO_STORE_OUTPUT:** completed forms and photo log under `print-alpha/QA/`;
  verdicts noted in `production_alpha/SKU_MANIFEST.json` QA fields.
- **WHAT_GATE_IT_UNBLOCKS:** UA-8 (P1 capture session) and the Production Beta gate
  ("physical sample received + verified").

---

## UA-8 — P1 capture session

**Exact steps**
1. Set up the rig per `docs/P1_CAPTURE_RIG_SPEC.md` and lock camera + lighting per
   `physical/p1/CAMERA_LIGHTING_SETUP.md`; tape camera positions and actor marks.
2. Run the session calibration exposure with RAC-CALT-P1-0001; confirm the session
   acceptance bound (max mean ΔE00 6.0) before any garment capture.
3. Capture all **108 matched rows** from `print-alpha/CAPTURE/trial-sheet.csv`
   (distances 2/5/8 m × yaw 0/±30° × pose standing/walking × lighting
   indoor-even/daylight-even × 3 repeats, wash state W0), saving files with the
   exact names in the sheet (`captures/<trial_id>__control.jpg` /
   `__candidate.jpg`), following `print-alpha/CAPTURE/capture-protocol.md`.
4. Record the session manifest from `physical/p1/SESSION_MANIFEST_TEMPLATE.json`;
   record any invalid condition per
   `print-alpha/CAPTURE/invalid-condition-rules.json` — invalid conditions are
   marked invalid, never counted as candidate success.
5. Ingest with the trial-ingestion template
   (`physical/p1/PHYSICAL_TRIAL_INGESTION_TEMPLATE.json`); keep RAW files and
   hashes per `physical/p1/CAPTURE_NAMING_CONVENTION.md`.

- **WHY_REQUIRED:** this is the preregistered physical P1 measurement — the only
  path from a printed garment to measured physical evidence. Camera settings and
  thresholds are locked after calibration and never changed mid-session.
- **INPUT:** QA-passed matched pair (UA-7), calibration target (UA-6), locked rig,
  the trial sheet.
- **EXPECTED_OUTPUT:** 108 × 2 capture files with preregistered names, a completed
  session manifest, an invalid-conditions record (possibly empty), and ingested
  trial records.
- **WHERE_TO_STORE_OUTPUT:** captures under the session's `captures/` directory per
  the naming convention; session manifest and ingestion records under
  `physical/p1/` and `print-alpha/CAPTURE/`.
- **WHAT_GATE_IT_UNBLOCKS:** physical P1 evaluation
  (`scripts/evaluate_physical_trial.py`), the physical response surface, and the
  Production Beta gate ("matched control/candidate P1 experiment"). Note: a
  physical PASS/FAIL is decided by the preregistered rule only — no threshold
  changes after seeing results.

---

## Cross-reference: earlier UA register

`docs/RAC_WORLD_CLASS_GAP_ANALYSIS.md` §17 and `docs/RAC_PARALLEL_SWARM_HANDOFF.md`
use an older UA-1..UA-5 numbering. Mapping to this packet: old UA-1 ≈ UA-1+UA-2,
old UA-2 ≈ UA-5, old UA-3 ≈ UA-8, old UA-4 ≈ vendor questions
(`production_alpha/VENDOR_QUESTIONS.md`, runs in parallel with UA-2), old UA-5
(D2-0005 arming) is **out of scope for this packet** and is a governance decision
only. The `user_action_refs` values inside `print-alpha/MANIFESTS/*.json` follow
the older numbering and are left unchanged for compatibility.

## Standing rules

- No efficacy claim is created by any action in this packet.
- `PENDING_USER_ACTION` fields are resolved only by the named physical/vendor
  input — never by estimation.
- Any deviation from a step is recorded in writing in the same file the step
  writes to; silent deviation is a protocol violation.

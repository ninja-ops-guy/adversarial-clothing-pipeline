# RAC User Action — Next Steps to Physical P1

**Document ID:** RAC-USER-ACTION-NEXT-001  
**Audience:** Mike / human operator  
**Status:** CURRENT OPERATOR CHECKLIST  
**Purpose:** Give one executable, dependency-ordered path from current software readiness to admissible physical P1 evidence.

> **Authority:** this is a navigation/operator guide. Frozen contracts and hash-pinned artifacts outrank it. `docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md` is retained as historical provenance and contains a superseded 108-row plan. **Do not execute that plan.** P1 authority is `physical/p1/P1_OPERATOR_RUNBOOK.md` + `physical/p1/P1_CAPTURE_SCHEDULE.json` + `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`, currently **144 trials**.

> **Scientific boundary:** none of these steps establishes physical efficacy by itself. Keep `physical_efficacy_claimed=false`. D2-0004 remains CLOSED/NEGATIVE/immutable. D2-0005 remains PREREGISTERED/NOT ARMED unless a separate governance action explicitly changes it.

## 0. Preflight — do this before touching vendor data

From the repository root:

```bash
python3 tools/p1_no_spend_readiness_gate.py
```

Require `P1_NO_SPEND_READINESS=PASS`. If it fails, stop and repair the software/evidence state before collecting vendor values.

Also confirm these files exist:

```text
physical/p1/UA_VALUES_TEMPLATE.json
physical/p1/P1_OPERATOR_RUNBOOK.md
physical/p1/P1_CAPTURE_SCHEDULE.json
physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json
physical/p1/P1_READINESS_FREEZE.json
tools/p1_bind_ua_values.py
```

**Done when:** the baseline gate passes and the authoritative P1 surfaces are present.

---

## 1. Create/verify Printful API access

Use Printful's Developer Portal to create a **Private Token**. A store-scoped token is simplest if you have a Manual order platform/API store. An account-level token is also valid, but endpoints that need store context may require `X-PF-Store-Id`.

Keep the token outside the repository.

### macOS/Linux/Git Bash

```bash
export PF_TOKEN='REDACTED'
curl --fail-with-body -sS \
  -H "Authorization: Bearer $PF_TOKEN" \
  https://api.printful.com/oauth/scopes
```

### PowerShell

```powershell
$env:PF_TOKEN = 'REDACTED'
Invoke-RestMethod -Headers @{Authorization="Bearer $env:PF_TOKEN"} `
  -Uri 'https://api.printful.com/oauth/scopes'
```

Never paste the token into `UA_VALUES_TEMPLATE.json`, a manifest, shell history you plan to commit, screenshots, or issue text.

**Done when:** the scopes request returns successfully.

---

## 2. Capture a live vendor snapshot — no spend

The current production plan uses:

- primary hoodie: Printful catalog product **388**, All-Over Print Recycled Unisex Hoodie;
- reserve/fallback tee metadata: Printful catalog product **257**, All-Over Print Men's Crew Neck T-Shirt.

The tee metadata is required by the current binder even if you choose not to purchase a reserve tee. Do not confuse **binder-required metadata** with **required procurement**.

Create a local working directory that is not used for secrets:

```bash
mkdir -p vendor_snapshot
```

Capture the exact API responses you rely on. For the AOP hoodie, explicitly request the cut-and-sew technique rather than relying on a default technique:

```bash
curl --fail-with-body -sS -H "Authorization: Bearer $PF_TOKEN" \
  'https://api.printful.com/mockup-generator/printfiles/388?technique=CUT-SEW' \
  -o vendor_snapshot/hoodie-388-printfiles.json

curl --fail-with-body -sS -H "Authorization: Bearer $PF_TOKEN" \
  'https://api.printful.com/mockup-generator/templates/388?technique=CUT-SEW' \
  -o vendor_snapshot/hoodie-388-templates.json

curl --fail-with-body -sS -H "Authorization: Bearer $PF_TOKEN" \
  'https://api.printful.com/mockup-generator/printfiles/257?technique=CUT-SEW' \
  -o vendor_snapshot/tee-257-printfiles.json

curl --fail-with-body -sS -H "Authorization: Bearer $PF_TOKEN" \
  'https://api.printful.com/mockup-generator/templates/257?technique=CUT-SEW' \
  -o vendor_snapshot/tee-257-templates.json
```

If Printful rejects `CUT-SEW` for a product, **do not substitute another technique silently**. Inspect the live catalog/product response and reconcile the technique before continuing.

If you use an account-level token and Printful reports missing store context, add the documented `X-PF-Store-Id` header. Do not invent a store ID.

### Important distinction: metadata snapshot vs production template archive

The API JSON above is **vendor metadata**, not automatically the downloadable production template archive. If Printful's File Guidelines/Design Maker provides an actual template ZIP/PNG/PSD archive, download and preserve that exact file as the production-template artifact. Do not rename a JSON response to `.zip` or bind a metadata hash as an archive hash merely to satisfy the schema.

If no downloadable archive is available for a required binder field, stop and treat it as a contract/tooling reconciliation item rather than fabricating a value.

**Done when:** you have byte-exact vendor metadata for both products and, where the binder requires an archive, the actual vendor template artifact.

---

## 3. Hash every authoritative vendor file

### macOS/Linux/Git Bash

```bash
sha256sum vendor_snapshot/*
```

On macOS without `sha256sum`:

```bash
shasum -a 256 vendor_snapshot/*
```

### PowerShell

```powershell
Get-ChildItem vendor_snapshot | Get-FileHash -Algorithm SHA256
```

Record the acquisition date, source endpoint/page, product ID, technique, and SHA-256. Preserve the original bytes.

**Done when:** every vendor artifact used downstream has a reproducible SHA-256.

---

## 4. Resolve live variants and manufacturing context

Choose one size supported by the primary hoodie and the binder-required tee metadata. Resolve the **live** variant IDs rather than trusting the embedded reference map blindly.

Record:

- selected size;
- hoodie variant ID;
- tee variant ID;
- printer/vendor = Printful;
- actual print technique from the live vendor response;
- selling/fulfillment region used for the order;
- vendor snapshot date.

The binder contains a v1 variant map. If live Printful data disagrees with it, **stop for review**. Do not use `--allow-variant-map-drift` merely to get a green result; use that override only after documenting why the vendor mapping changed and verifying the selected product/size manually.

Printful has documented 2026 AOP fabric changes. Because material/fulfillment changes can become experimental confounders, record the fulfillment/manufacturing region and any vendor-disclosed fabric substitution or material change on the actual order/receipt. Candidate and control must be fulfilled as a matched pair as far as practical.

**Done when:** live size/variant/technique/region facts are known and no unresolved drift exists.

---

## 5. Derive panel geometry from vendor data

Populate only geometry supported by the vendor's live print-file/template data:

**Hoodie:** `back`, `front`, `hood`, `label_inside`, `label_panel`, `pocket`, `sleeve_left`, `sleeve_right`.

**Tee:** `back`, `front`, `sleeve_left`, `sleeve_right`.

For each required placement record:

- width/height in the source units;
- DPI/minimum DPI where supplied;
- conversion to `width_mm` / `height_mm` if the binder requires millimetres;
- source printfile/template ID.

For pixel dimensions at a known DPI:

```text
millimetres = pixels / dpi × 25.4
```

Do not infer a missing placement from a visually similar placement. Do not treat mockup canvas dimensions as print-area dimensions. If a required binder placement does not exist for the live variant/technique, stop: that is a schema-vendor mismatch to fix in code before binding.

**Done when:** every binder-required geometry field is traceable to a live vendor field.

---

## 6. Export the exact production artwork

Use the resolved live geometry to produce the exact candidate and matched-control files that will be uploaded to Printful.

Pairing rule: candidate/control should differ in **artwork**, not product, size, variant, substrate, technique, fulfillment conditions, or other avoidable variables.

Do not regenerate or retune a frozen candidate merely because the vendor template is inconvenient. Template fitting is a production mapping operation; scientific design changes require their own governed path.

Hash every final upload file and the assembled article packages. The current intake requires article hashes for:

```text
PA-HOODIE-CAND-001
PA-HOODIE-CTRL-001
PA-HOODIE-CAND-R01
PA-HOODIE-CTRL-R01
PA-TEE-CAND-R01
PA-TEE-CTRL-R01
```

The reserve hashes are binder-required even if reserve garments are not purchased in the first order.

**Done when:** the exact bytes you intend to upload are frozen, named, and hashed; candidate/control hashes differ where required.

---

## 7. Fill a working copy of the UA intake

Do not edit the template as scratch state.

### macOS/Linux/Git Bash

```bash
cp physical/p1/UA_VALUES_TEMPLATE.json my_ua_values.json
```

### PowerShell

```powershell
Copy-Item physical/p1/UA_VALUES_TEMPLATE.json my_ua_values.json
```

Replace every `PENDING_USER_ACTION` leaf with a real, source-backed value. Never put the API token in this file.

Before binding, manually verify:

- all SHA-256 values are lowercase 64-hex;
- all geometry values are positive;
- filenames refer to the exact files you hashed;
- hoodie/tee variants correspond to the selected size;
- candidate/control artwork is not accidentally identical;
- no `TBD`, `FIXME`, placeholder, or guessed value remains.

**Stop if any required value is unknown.**

---

## 8. Validate without writing

```bash
python3 tools/p1_bind_ua_values.py --values my_ua_values.json --check-only
```

Require success. If it refuses, fix the **source value or genuine contract mismatch**. Do not weaken the binder, frozen schedule, pairing contract, stopping rule, thresholds, D2 state, or readiness logic merely to make it pass.

**Done when:** check-only succeeds with zero writes required to protected scientific surfaces.

---

## 9. Bind atomically, then verify the receipt and readiness

Run:

```bash
python3 tools/p1_bind_ua_values.py --values my_ua_values.json
```

The binder should emit:

```text
artifacts/p1-readiness/ua-binding-receipt.json
```

It is designed to re-pin the allowed readiness surface and invoke the readiness verification as part of the controlled transition. After it succeeds, run the readiness gate explicitly once more for operator confirmation:

```bash
python3 tools/p1_no_spend_readiness_gate.py
```

Require PASS. Verify the 144-trial schedule and pairing contract hashes did not change unexpectedly.

Successful binding does **not** authorize spend and does **not** arm D2-0005.

**Done when:** binder succeeds, receipt exists, readiness is PASS, protected state is intact.

---

## 10. Human procurement go/no-go

Before paying, verify all of the following:

- bound hashes match the files you will upload;
- candidate/control use the same hoodie product, size and variant;
- print technique matches;
- fulfillment region/conditions are matched as far as the vendor allows;
- candidate/control artwork is intentionally different;
- no vendor substitution is known that would break the pair;
- readiness is PASS;
- you accept the cost.

At minimum order:

- 1 × primary candidate hoodie;
- 1 × matched control hoodie.

Reserve hoodie/tee units are optional procurement unless the current production plan explicitly promotes them; their metadata may still be required by the binder.

Record order ID, order date, line-item variant IDs, fulfillment region, uploaded artwork hashes, and any vendor warnings/substitutions.

**Done when:** a traceable matched pair is in production.

---

## 11. Prepare calibration and rig while the garments ship

Use the repository's deterministic calibration target. Print/fabricate it exactly as specified by its manifest/runbook; verify the physical scale bar with a ruler. Do not crop, stretch, recolor, or rescale it to fit a page.

Stage and read:

```text
physical/p1/P1_OPERATOR_RUNBOOK.md
physical/p1/P1_CAPTURE_SCHEDULE.json
physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json
physical/p1/CAMERA_LIGHTING_SETUP.md
physical/p1/P1_READINESS_FREEZE.json
```

Prepare storage, camera, lighting, actor marks, naming workflow, custody labels, and enough capacity to retain original captures and hashes.

Do **not** collect experimental trials yet.

---

## 12. Receipt QA — before efficacy capture

When the garments arrive, keep them at the required initial wash state and verify:

- order/SKU/variant identity;
- candidate/control pairing;
- material and disclosed manufacturing/fulfillment origin;
- print placement/registration;
- seams and continuity;
- visible defects or substitutions;
- chain of custody.

Photograph/measure using the repository's receipt-QA procedure and calibration target. A mismatched or materially defective pair is **not** something to average away later: stop, document, and reorder/escalate.

**Done when:** the pair is explicitly QA-admissible.

---

## 13. Calibration acceptance — before the first P1 trial

Set up the locked rig exactly as the P1 runbook requires. Perform the calibration exposure/acceptance procedure first.

If calibration fails, correct the rig/environment and repeat calibration. Do not change a scientific acceptance threshold because the session failed it.

**Done when:** the session is calibration-accepted under the frozen rule.

---

## 14. Execute the authoritative 144-trial P1 schedule

Execute:

```text
physical/p1/P1_CAPTURE_SCHEDULE.json
```

Follow the frozen order/pairing/randomization and `P1_OPERATOR_RUNBOOK.md`. Preserve original files, exact filenames, session metadata, invalid-condition records, and hashes.

Never:

- use the old 108-row planning sheet;
- improvise a replacement trial outside the runbook;
- change thresholds after seeing outcomes;
- arm D2-0005 as part of P1;
- rewrite D2-0004;
- access new held-out data outside the approved process;
- count invalid trials as favorable outcomes;
- label synthetic/rehearsal data as measured physical evidence.

**Done when:** all required P1 trial dispositions are accounted for under the frozen stopping/invalid-condition rules.

---

## 15. Ingest, seal, then analyze

After capture:

1. complete the session and ingestion records;
2. validate expected files and hashes;
3. preserve invalid-condition records and raw captures;
4. seal the physical evidence package using the repository workflow;
5. only then run the preregistered physical analysis;
6. report PASS, FAIL, negative, or inconclusive results as produced by the frozen rules.

No post-hoc threshold changes.

---

## Short operator card

```text
[ ] Baseline P1 no-spend gate PASS
[ ] Printful private token works; token is not in repo
[ ] Live product 388 + 257 vendor metadata captured
[ ] Actual production template artifacts captured where required
[ ] Vendor files SHA-256 hashed
[ ] Live size/variant/technique/region verified
[ ] Required panel geometry source-backed
[ ] Final candidate/control upload bytes frozen + hashed
[ ] my_ua_values.json complete; no placeholders/secrets
[ ] binder --check-only PASS
[ ] atomic binder PASS + receipt exists
[ ] explicit readiness recheck PASS
[ ] protected state unchanged
[ ] human spend authorization
[ ] matched candidate/control hoodies ordered
[ ] calibration target + rig ready
[ ] receipt QA PASS
[ ] calibration acceptance PASS
[ ] authoritative 144-trial P1 executed
[ ] evidence ingested + sealed
[ ] preregistered analysis run without threshold changes
```

## Non-negotiable stop conditions

Stop and investigate if:

- a UA value would have to be guessed;
- a vendor API response/product/placement/variant disagrees with the binder contract;
- an actual production-template artifact cannot be obtained for a field that requires one;
- binder check-only or binding refuses;
- readiness is not PASS;
- a hash no longer matches the file being used;
- candidate/control identity or fulfillment is materially mismatched;
- receipt QA fails;
- calibration fails;
- the frozen 144-trial schedule/pairing contract changes unexpectedly;
- D2-0004 changes;
- D2-0005 becomes armed without separate explicit governance authorization;
- a scientific threshold changes after outcome access;
- unauthorized held-out access appears;
- synthetic/rehearsal evidence is being promoted as measured physical evidence.

## Protected-state checkpoint

Before procurement and again immediately before P1 execution confirm:

```text
D2-0004 = CLOSED / NEGATIVE / immutable
D2-0005 = PREREGISTERED / NOT ARMED
physical_efficacy_claimed = false
authoritative P1 schedule = 144 trials
readiness gate = PASS
spend authorization = separate human decision
```

If any checkpoint is false or ambiguous, stop before spending or collecting outcome data.
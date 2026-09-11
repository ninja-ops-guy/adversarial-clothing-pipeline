# P1 Production Launch — RAC-PRINT-ALPHA-001

This is the shortest production path from the frozen Alpha-001 digital specimen to a valid physical P1 matched-pair trial.

## Current scientific identity

- Release: `RAC-PRINT-ALPHA-001`
- Candidate lineage: `RAC-PER-D2-0003`
- Expected frozen pattern SHA-256: `b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546`
- Expected sealed print-test-kit SHA-256: `b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548`
- Primary garment: Printful product `388`, All-Over Print Recycled Unisex Hoodie
- Fallback/reserve garment: Printful product `257`, All-Over Print Men's Crew Neck T-Shirt
- Evidence boundary: `physical_efficacy_claimed=false` until the preregistered physical P1 evaluation is actually executed.

D2-0007 is not a physical-test candidate. It closed at Stage 1 with zero survivors and does not authorize an Alpha-002/P1B lineage.

## What is already complete

The software-side P1 protocol, capture schedule, pairing/randomization contract, stopping rule, calibration contract, receipt QA, custody rules, ingestion path, synthetic rehearsal, and no-spend readiness machinery are already implemented and fail closed.

Do not redesign these surfaces merely to begin manufacturing. Real vendor/specimen values are the remaining inputs.

## Production command path

### 1. Obtain a Printful API token

Create the token in Printful and keep it only in the local environment:

```bash
export PF_TOKEN='<secret>'
```

Never commit or paste the token into JSON, logs, issues, receipts, or manifests.

### 2. Run vendor intake

Pick one size available on both product 388 and the fallback tee. Example only:

```bash
python tools/prepare_print_alpha_production.py intake \
  --fetch \
  --size M \
  --output-dir production_alpha/vendor_intake
```

The tool downloads the live product, printfile, and template responses for products 388 and 257. It:

- selects the exact White variant for the chosen size;
- requires every preregistered placement to exist;
- joins `variant_printfiles` to the exact Printful `printfile_id` dimensions;
- converts px/DPI to millimeters;
- stores untouched response bytes under `production_alpha/vendor_intake/raw/`;
- creates deterministic `printful-source-388.zip` and `printful-source-257.zip` archives;
- writes `vendor-intake.json` with hashes and geometry;
- does **not** authorize spend or place an order.

If responses were downloaded separately, use the offline mode instead:

```bash
python tools/prepare_print_alpha_production.py intake \
  --raw-dir template_archive \
  --size M \
  --output-dir production_alpha/vendor_intake
```

The raw directory must contain:

- `products_388.json`
- `printfiles_388.json`
- `templates_388.json`
- `products_257.json`
- `printfiles_257.json`
- `templates_257.json`

### 3. Recover the exact frozen Alpha-001 source bytes

Preferred input is the original `print-test-kit.zip`. The production tool requires the exact historical kit hash and exact inner pattern hash before it will render anything.

```bash
sha256sum /secure/path/print-test-kit.zip
# must equal b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548
```

If only the exact frozen `pattern_tile_4096.png` is available, it may be supplied directly, but its SHA-256 must equal the frozen pattern hash above. Do not regenerate, tune, or visually recreate Alpha-001.

### 4. Build exact panel artwork and UA values

Preferred sealed-kit path:

```bash
python tools/prepare_print_alpha_production.py build \
  --intake production_alpha/vendor_intake/vendor-intake.json \
  --print-test-kit /secure/path/print-test-kit.zip \
  --recorded-by '<operator>'
```

Pattern-only recovery path:

```bash
python tools/prepare_print_alpha_production.py build \
  --intake production_alpha/vendor_intake/vendor-intake.json \
  --candidate-pattern /secure/path/pattern_tile_4096.png \
  --recorded-by '<operator>'
```

This stage:

- refuses any candidate source whose hash differs from Alpha-001;
- tiles the frozen candidate without regeneration or retuning;
- writes exact-size primary hoodie files to `print-alpha/CANDIDATE/*.png`;
- writes matched flat-mid-gray control files to `print-alpha/CONTROL/*.png` under the existing scenario-assumption control rule;
- prepares fallback tee panel artifacts under `production_alpha/vendor_intake/tee-panels/`;
- builds deterministic role/product artwork archives;
- writes `production_alpha/vendor_intake/ua-values.generated.json`;
- validates that generated values satisfy the real P1 UA binder contract;
- writes `production-prep-receipt.json`;
- still does **not** authorize spend or place an order.

### 5. Review and bind

Always run the fail-closed dry check first:

```bash
python tools/p1_bind_ua_values.py \
  --values production_alpha/vendor_intake/ua-values.generated.json \
  --check-only
```

Only after reviewing the exact variant, geometry, panel files, and hashes:

```bash
python tools/p1_bind_ua_values.py \
  --values production_alpha/vendor_intake/ua-values.generated.json
```

The binder updates only its allowlisted P1 vendor/manufacturing manifests, re-pins the P1 readiness freeze, and writes a binding receipt. It does not touch D2 scientific surfaces, the P1 schedule, the stopping rule, or held-out data.

### 6. Run the manufacturing readiness gate

```bash
python scripts/check_print_alpha_readiness.py --check-only
python tools/p1_no_spend_readiness_gate.py
```

At this point the expected state is `READY_TO_ORDER` / P1 readiness PASS, assuming all generated bytes and hashes remain intact.

### 7. Human-only spend gate

The operator—not RAC automation—places the matched order after completing `production_alpha/ORDER_CHECKLIST.md`.

Order at minimum:

- 1× `PA-HOODIE-CAND-001`
- 1× `PA-HOODIE-CTRL-001`
- same product, color, size, variant, fulfillment conditions, substrate, and print technology
- candidate/control differ only in artwork

Reserves may be ordered if budget permits.

### 8. Fabricate calibration target while garments are in transit

Produce `RAC-CALT-P1-0001` at 100% scale / 300 DPI and verify the printed 100 mm scale bar physically measures 100 mm. Do not scale-to-fit.

### 9. Receipt QA and custody

When garments arrive, do **not** start efficacy captures immediately.

First complete:

- `production_alpha/RECEIPT_QA_FORM.md`
- `print-alpha/QA/garment-pairing-checklist.md`
- `print-alpha/QA/chain-of-custody.md`
- calibration-target-in-frame documentation

Any mismatch, registration failure, custody break, or pair mismatch blocks capture rather than becoming a candidate success.

### 10. Run P1 capture

After receipt QA passes, execute `physical/p1/P1_OPERATOR_RUNBOOK.md` and the frozen capture schedule. Preserve RAW captures and exact filenames. Invalid conditions are recorded under the frozen invalid-condition/stopping rules; thresholds are not changed after seeing results.

## Production blockers that cannot be solved by repository code

The remaining external inputs are intentionally explicit:

1. a valid Printful token long enough to retrieve current template/printfile data;
2. operator size selection;
3. recovery of the exact Alpha-001 sealed kit or exact frozen pattern bytes;
4. payment/order placement;
5. fabrication of the calibration target;
6. physical receipt QA;
7. the actual P1 capture session.

Everything else in the vendor-to-panel-art handoff should now be automated or fail closed.

# P1 Production Release Gate

For real `RAC-PRINT-ALPHA-001` manufacturing, use
`tools/p1_production_release.py` as the operator entry point. It wraps the lower-level
`tools/prepare_print_alpha_production.py` helper with additional evidence-integrity
checks and is the preferred path before binding any UA values.

## 1. Vendor intake

Keep the Printful token in the local environment only. Pick the actual garment size;
do not copy the example blindly.

```bash
export PF_TOKEN='<secret>'
python tools/p1_production_release.py intake \
  --fetch \
  --size M \
  --output-dir production_alpha/vendor_intake
```

The release gate refuses:

- wrong Printful product IDs or titles;
- no exact White variant for the selected size;
- missing required placements;
- unexpected non-mockup placements that have not been reviewed;
- malformed/error API responses.

It writes untouched raw responses, deterministic source archives, panel geometry, and
a self-hashed `vendor-intake.json`. No order is placed and no spend is authorized.

Offline mode is supported with previously downloaded untouched responses:

```bash
python tools/p1_production_release.py intake \
  --raw-dir template_archive \
  --size M \
  --output-dir production_alpha/vendor_intake
```

## 2. Build the exact Alpha-001 production art

Preferred path — original sealed kit:

```bash
python tools/p1_production_release.py build \
  --intake production_alpha/vendor_intake/vendor-intake.json \
  --print-test-kit /secure/path/print-test-kit.zip \
  --recorded-by '<operator>'
```

Recovery path — only if the exact frozen pattern bytes are available:

```bash
python tools/p1_production_release.py build \
  --intake production_alpha/vendor_intake/vendor-intake.json \
  --candidate-pattern /secure/path/pattern_tile_4096.png \
  --recorded-by '<operator>'
```

Before rendering, this command re-derives the intake self-hash and verifies every raw
response and deterministic vendor-source archive byte-for-byte. The Alpha-001 kit and
pattern SHA-256 pins are then enforced by the underlying preparation helper.

After rendering it verifies the vendor evidence a second time, so a concurrent
mutation cannot silently enter the build receipt.

## 3. Bind only after review

```bash
python tools/p1_bind_ua_values.py \
  --values production_alpha/vendor_intake/ua-values.generated.json \
  --check-only
```

Review the selected variants, source hashes, panel dimensions, and generated artwork.
Only then run the binder without `--check-only`.

## 4. Manufacturing and capture boundary

This release gate deliberately stops before purchasing anything. The human operator
still owns the spend/order decision, physical calibration-target fabrication, receipt
QA, custody, and the P1 capture session. None of those steps may be inferred from a
software PASS.

D2-0007 remains closed as a screened-out null and is not a P1 candidate. Alpha-001
remains bound to `RAC-PER-D2-0003`.

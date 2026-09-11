# Production Alpha SKU Manifest / Decision

**Version:** 1.1.0  
**Updated:** 2026-09-11  
**Status:** CURRENT PRODUCTION DECISION — live vendor values remain runtime-bound until intake/binding completes.  
**Scope:** identifies the first matched physical Production Alpha test article. It makes no efficacy claim.

## 1. Decision summary

Production Alpha is `RAC-PRINT-ALPHA-001`, scientifically bound to the retained `RAC-PER-D2-0003` lineage.

Primary garment:

- provider: Printful;
- product ID: `388`;
- product: **All-Over Print Recycled Unisex Hoodie**;
- color/base: exact White variant resolved from live vendor data;
- size: selected by the operator from live supported variants rather than frozen blindly in this document;
- process/placements: accepted only from the exact live Printful product/printfile/template relationships validated by the production release gate;
- candidate/control: matched on every practical production variable except experimental artwork.

Fallback/reserve metadata surface:

- Printful product `257`, All-Over Print Men's Crew Neck T-Shirt.

Product 257 remains useful to the current vendor/binder contract but is not the primary first-order SKU unless a separately reviewed change promotes it.

## 2. Frozen candidate identity

The exact Alpha-001 digital source was recovered from historical GitHub Actions run `34078238095` and verified against the frozen pins.

```text
print-test-kit.zip
b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548

print-test-kit/design/pattern_tile_4096.png
b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546
```

Recovery provenance is recorded in `evidence/p1/alpha001-source-recovery.json`.

This source must not be regenerated, retuned, or rebound to D2-0007 or another lineage while retaining the Alpha-001 identity.

## 3. Why the hoodie is the current primary SKU

The original planning document selected a crew-neck tee to simplify early production. Subsequent repository work resolved and productionized Printful product `388` as the primary Alpha-001 surface, with exact live intake/build support and product `257` retained as fallback/reserve metadata.

The current decision therefore follows the implemented and governed production path rather than preserving the earlier planning choice solely for convenience.

## 4. Live vendor identity is runtime-bound

Do not hard-code a stale variant ID or size in this document.

The actual order identity must be derived by:

```bash
python tools/p1_production_release.py intake \
  --fetch \
  --size <chosen-size> \
  --output-dir production_alpha/vendor_intake
```

The release gate must confirm:

- product `388` identity/title;
- exact White variant for the chosen size;
- required production placements;
- no unreviewed unexpected production placement;
- valid product/printfile/template relationships;
- untouched vendor response hashes;
- deterministic vendor-source archive hashes.

If Printful's live catalog no longer satisfies the contract, stop and review the SKU decision rather than inventing IDs or geometry.

## 5. Exact production artwork

After successful intake:

```bash
python tools/p1_production_release.py build \
  --intake production_alpha/vendor_intake/vendor-intake.json \
  --print-test-kit /secure/path/print-test-kit.zip \
  --recorded-by '<operator>'
```

This build:

- verifies the live vendor intake before rendering;
- verifies the exact Alpha-001 source hashes;
- derives exact-size candidate/control panel artwork from the validated vendor geometry;
- creates deterministic artwork archives;
- produces binder-ready real-value inputs;
- re-verifies vendor evidence after rendering.

No spend is authorized by this process.

## 6. Golden digital SKU record

The final bound production record must identify at minimum:

```json
{
  "release_id": "RAC-PRINT-ALPHA-001",
  "generation_id": "RAC-PER-D2-0003",
  "provider": "Printful",
  "product_id": 388,
  "variant_id": "<resolved-live>",
  "size": "<operator-selected>",
  "color": "White",
  "print_technique": "<resolved-and-validated-live>",
  "frozen_pattern_sha256": "b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546",
  "sealed_kit_sha256": "b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548",
  "vendor_intake_sha256": "<generated>",
  "panel_artwork_sha256": "<generated-per-placement>",
  "candidate_control_pairing": "MATCHED_EXCEPT_ARTWORK",
  "order_id": "<record-after-human-purchase>",
  "fulfillment_region": "<record-when-known>"
}
```

The repository's actual manifests/binder schemas remain authoritative; this example communicates the identity that must be preserved, not a competing schema.

## 7. Matched-pair ordering rule

Candidate and control must match on every practical production variable:

- provider;
- product `388`;
- live variant;
- size;
- substrate/material;
- print technique;
- order window;
- intended fulfillment/manufacturing conditions when controllable.

Only the experimental artwork differs intentionally.

Minimum first order:

```text
1 × PA-HOODIE-CAND-001
1 × PA-HOODIE-CTRL-001
```

Prefer the two arms in the same order to reduce avoidable manufacturing variation.

## 8. Pre-order authority

Before purchase:

1. review generated product/variant/size/placement geometry;
2. verify candidate/control artwork and archive hashes;
3. run `tools/p1_bind_ua_values.py --check-only`;
4. bind only after the dry check passes;
5. run `tools/p1_no_spend_readiness_gate.py`;
6. require readiness PASS;
7. make a separate human spend decision.

A software PASS never authorizes purchase by itself.

## 9. Receipt QA and physical handoff

When the matched garments arrive:

- reconcile SKU/order/variant identity;
- verify candidate/control pairing;
- record material and manufacturing/fulfillment facts where available;
- inspect registration, placement, seams, continuity and defects;
- preserve chain of custody;
- block P1 if the pair is materially mismatched or outside acceptance rules.

After receipt QA and calibration acceptance, execute the authoritative frozen P1 package:

```text
physical/p1/P1_OPERATOR_RUNBOOK.md
physical/p1/P1_CAPTURE_SCHEDULE.json        # 144 frozen trials
physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json
physical/p1/P1_READINESS_FREEZE.json
```

The older 108-row planning sheet is not execution authority.

## 10. Open external items

The remaining unresolved production facts are intentionally runtime/physical rather than guessed in this document:

- actual chosen size;
- live Printful variant ID and current placement geometry;
- current vendor print-technique details as returned by the governed intake;
- fulfillment/manufacturing region when known;
- order/payment details;
- received-specimen QA measurements.

## 11. Evidence boundary and precedence

This is a production identity specification, not an efficacy claim. Alpha-001 derives from a retained negative D2-0003 result and is being manufactured to measure the digital-to-physical behavior under a controlled matched trial.

Precedence:

1. frozen/hash-pinned scientific and P1 execution contracts;
2. generated/verified production intake and binding receipts;
3. `docs/CURRENT_PROGRAM_STATE.md`;
4. this SKU narrative.

If this narrative conflicts with the live fail-closed production release/binder or a frozen P1 contract, the stricter artifact wins and production stops for review.

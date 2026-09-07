# RAC Physical Print Test 1.0

**Status:** preregistered procedure for future physical evidence  
**Evidence boundary:** no physical claim exists until this procedure is actually executed on a printed garment.

## Required artifacts before printing

- `design/pattern_tile_4096.png`
- `design/product_studio_manifest.json`
- `export-verification.json`
- `benchmark-results.json`
- `d2-latest-status.json`
- SHA-256 values recorded in `print-test-manifest.json`

Do not resize, re-compress, recolor, sharpen, denoise, or otherwise alter the master tile after the print-test kit is sealed. Any changed artwork is a new candidate and requires a new digital evidence chain.

## Print specimen

Use one candidate garment and one matched control garment with the same provider, product, size, fabric, print process, and base color whenever possible. The control must not contain the candidate adversarial artwork. Record provider order/product identifiers, garment size, fabric description, print method, order date, received date, and any provider-side scaling or positioning changes.

## Camera capture matrix

Capture matched control/candidate images under the same conditions. Use a fixed camera position and fixed exposure/processing settings where the device permits it.

| Variable | Required values |
|---|---|
| Distance | 2 m, 5 m, 8 m |
| Yaw | 0°, +30°, -30° |
| Pitch | 0° |
| Pose | standing, walking |
| Lighting | indoor-even, daylight-even |
| Repeats | 3 per condition |
| Wash state | W0 before laundering |

This produces 108 control/candidate pairs. Each pair uses the same `condition_id` and repeat number.

Recommended file naming:

`<condition_id>__r<repeat>__control.jpg`  
`<condition_id>__r<repeat>__candidate.jpg`

Example condition ID: `D05_Y+30_P0_STANDING_DAYLIGHT`.

## Baseline qualification

A physical condition is valid only when the matched control is detected at the frozen model's decision threshold. Conditions with an undetected control are excluded from candidate-rate aggregation and recorded as invalid; they are never counted as candidate success.

## Frozen evaluation

Evaluate the captured image pairs with the model manifest committed with the print-test kit. Do not change model weights, thresholds, preprocessing, or model-set membership after seeing candidate results.

Use:

```bash
python scripts/evaluate_physical_trial.py \
  --trial-manifest physical_trial/manifest.json \
  --captures physical_trial/captures \
  --model-manifest benchmarks/model_manifest.json \
  --output physical-results.json
```

## P1 decision boundary

The physical result is measured evidence only. RAC-P1 eligibility still requires the certification layer to validate the evidence chain and protocol criteria. Digital benchmark performance does not imply physical success.

## After initial test

If W0 passes, repeat the frozen capture matrix after laundering/durability states under a separately recorded wash protocol for RAC-P2 work. Manufacturing certification remains a separate RAC-M evidence process.

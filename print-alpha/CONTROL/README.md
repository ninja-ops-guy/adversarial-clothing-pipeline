# print-alpha/CONTROL — control artwork placement

This directory receives the **control** print artwork for RAC-PRINT-ALPHA-001:
the **unmodified base texture**, printed on a garment identical in product,
variant, size, placements, panel geometry, dpi, tiling origin and scale to the
candidate (the matched-pair rule).

## Source of truth

- Control rule: `production_alpha/SKU_MANIFEST.json` → `control_rule`:
  identical product/variant/size/placements/geometry as the candidate, printed
  with the unmodified pre-modification base texture. If no sealed base texture
  exists in the repo, use flat mid-gray sRGB(128,128,128) full-coverage fill
  and mark `scenario_assumption`.
- Control SKU: `PA-HOODIE-CTRL-001` (same `variant_id` and size as
  `PA-HOODIE-CAND-001`; both currently `PENDING_USER_ACTION` pending user size
  selection and UA-1 template download).
- Per-placement control upload files are hashed and recorded in
  `print-alpha/MANIFESTS/artwork-manifest.json` after template download (UA-1).

## Evidence boundary

- `physical_efficacy_claimed = false`
- `evidence_class = experimental_print_specimen`

The control garment is the reference arm of a matched-pair manufacturing
specimen set. Nothing in this directory asserts physical-world efficacy.

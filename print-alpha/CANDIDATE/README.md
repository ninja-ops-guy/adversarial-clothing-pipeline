# print-alpha/CANDIDATE — candidate artwork placement

This directory receives the **candidate** print artwork for RAC-PRINT-ALPHA-001:
the frozen master pattern from generation candidate **RAC-PER-D2-0003**, tiled
onto verified panel rectangles at template dpi, one upload file per placement
(front, back, sleeve_left, sleeve_right, pocket, hood, label_panel,
label_inside — see `production_alpha/SKU_MANIFEST.json`).

## Source of truth

- Frozen pattern sha256 (expected): `b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546`
  per `production_alpha/SKU_MANIFEST.json` → `candidate_source.expected_pattern_sha256`.
- Print test kit `print-test-kit.zip` sha256: `b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548`.
- **No regeneration or retuning is permitted.** Per-placement upload files are
  hashed and recorded as `artwork_sha256` in
  `print-alpha/MANIFESTS/artwork-manifest.json` once templates are downloaded
  (user action **UA-1**; see `production_alpha/TEMPLATE_INGESTION_CHECKLIST.md`).
- Until UA-1 completes, every vendor/template-derived field remains the literal
  `PENDING_USER_ACTION` (fail-closed; values are never fabricated).

## Evidence boundary

- `physical_efficacy_claimed = false`
- `evidence_class = experimental_print_specimen`

Files placed here are manufacturing specimens for the matched-pair physical
experiment only. Nothing in this directory is, or becomes, evidence of
physical-world adversarial efficacy.

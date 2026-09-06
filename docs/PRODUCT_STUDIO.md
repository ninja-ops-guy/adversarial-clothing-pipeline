# RAC Product Studio

## Purpose

The repository now has two linked apparel surfaces:

- `product-studio.html` — deterministic procedural apparel design and technical mockups.
- `production-studio.html` — vendor-template ingestion, seam-aware panel mapping, artifact hashing, panel-pack export, and batch seed ranking.

The end-to-end flow is now:

1. select a deterministic design family and seed;
2. render a repeat tile and technical garment mockup;
3. persist the Product Studio design state;
4. open the Production Mapper;
5. load a normalized preview template or import an exact vendor template JSON;
6. map the design independently across cut panels;
7. validate continuity-group transforms;
8. export exact-size panel PNGs, a ZIP panel pack, mapping JSON, and a hash-bound manifest;
9. optionally generate and rank a batch of candidate seeds for collection development.

## Implemented design families

- **Machine Static** — dark ground, grayscale block interference, micro-grain, electric-blue and signal-yellow accents.
- **Ghost Hound** — the same technical grammar with fragmented eye/figurative motifs.
- **Broken Human** — displaced eye and rib-like collage cues over distressed block structure.
- **Error Garden** — floral forms, muted greens/pinks, distressed digital artifacts and signal accents.

Changing the seed creates a new deterministic variation inside the same family.

## Implemented Product Studio mockups

The canvas renderer supports:

- hoodie — front/back;
- beanie — front/side/back/slouch;
- cargo pants — front/back/side;
- balaclava/mask — front/side/back;
- oversized shirt — front/back.

The reference-board renderer uses the supplied visual direction: large industrial product title, off-white technical sheet, multiple garment views, textile-detail crop, pattern-strategy copy, restrained technical typography and signal-color accents.

## Production Mapper

### Vendor-template contract

`templates/vendor-template.schema.json` defines the supported adapter contract. A template records:

- provider and product identifiers;
- template version and source;
- DPI and canvas dimensions;
- exact panel rectangles;
- bleed and safe margins;
- required/optional panel status;
- continuity groups;
- optional seam relationships.

The included `templates/generic-aop-hoodie-preview.json` is deliberately marked `vendor_ready: false`. It is normalized preview geometry only and must not be represented as a provider production template.

Imported templates may set `vendor_ready: true`; the resulting manifest records this as an imported template claim, not as independent RAC verification of the provider source.

### Seam-aware panel mapper

Every panel has independent:

- X/Y pattern offset;
- pattern scale;
- rotation.

Panels may share a `continuity_group`. The mapper reports inconsistent transforms within a continuity group and provides an **Auto-Map Continuity Groups** action that copies a common transform across related panels.

Bleed and safe-area guides are drawn in the mapper preview when provided by the template.

### Panel-pack export

The Production Mapper can export:

- selected exact-size panel PNG;
- mapping JSON;
- evidence-bound manifest JSON;
- one ZIP containing:
  - `master/repeat_4096.png`;
  - `panels/<panel-id>.png` for every panel;
  - `manifest.json`;
  - `mapping.json`;
  - `template.json`.

A generic template produces a `rac-draft-panel-pack-*` ZIP. An imported template that explicitly claims vendor readiness produces `rac-vendor-panel-pack-*`.

## Evidence binding

The production manifest binds the exported artifact set with SHA-256 hashes for:

- the exact 4096×4096 master repeat PNG;
- the imported template JSON;
- the panel mapping configuration;
- every exported panel PNG.

The manifest declares that any artwork, template, or mapping change invalidates stale downstream evidence.

This is the bridge needed for future RAC-D evidence to attach to an exact commercial SKU/artifact rather than to a visual concept alone.

## Batch design factory

The Production Mapper can generate up to 100 deterministic seed candidates for the active design family, rank them with the repository's local entropy/complexity/printability-style proxy, retain the top subset, apply a selected candidate back to the mapper, and export a shortlist JSON.

The batch score is explicitly a local visual/printability proxy. It is **not detector efficacy and not RAC certification evidence**.

## Current export contract

### Product Studio master tile

- PNG
- 4096×4096
- deterministic from family + seed + controls
- master repeat artwork

### Product Studio reference board

- PNG
- 1122×1402
- merchandising / art-direction mockup
- not a vendor cut-panel file

### Production Mapper panel files

- PNG
- exact pixel dimensions from the active template
- independent per-panel transforms
- template-aware bleed/safe-area metadata

### Evidence-bound manifest

- JSON schema version 2.0
- design artifact hash
- template hash
- mapping hash
- per-panel hashes
- explicit vendor/draft status and caveat

## Remaining production work

1. Acquire real provider templates and convert them into the adapter JSON format without guessing dimensions.
2. Add provider-specific template-version libraries only after source material is obtained and recorded.
3. Add vendor-generated mockup comparison for scale/crop/seam validation.
4. Connect selected batch candidates to the measured RAC digital evaluation workflow.
5. Bind RAC-D result records to the manifest's exact design artifact hash.
6. Order the first POD sample and start the physical feedback loop.
7. Add RAC-P physical evidence only after measured garment testing exists.

## Status

The repository now covers **design factory → template adapter → panel mapper → panel-pack export → artifact evidence binding**. The remaining blocker to a true vendor-ready POD upload is not software architecture; it is obtaining and ingesting the actual provider template specifications for the chosen products.

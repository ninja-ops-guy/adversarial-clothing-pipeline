# RAC Product Studio

## Purpose

The repository has two linked apparel surfaces:

- `product-studio.html` — deterministic procedural apparel design and technical mockups.
- `production-studio.html` — vendor-template ingestion, seam-aware panel mapping, artifact hashing, panel-pack export, and batch seed ranking.

The end-to-end flow is:

1. select a deterministic design family and seed;
2. render a repeat tile and technical garment mockup;
3. persist the resolved Product Studio design state;
4. open the Production Mapper;
5. load a normalized preview template or import an exact vendor template JSON;
6. map the design independently across cut panels;
7. validate continuity-group transforms;
8. export exact-size panel PNGs, a ZIP panel pack, mapping JSON, and a hash-bound manifest;
9. optionally generate and rank a batch of candidate seeds for collection development.

## Canonical launch capsule v1

The supplied product-board direction is now the visual target for Product Studio rather than a generic distressed-camouflage look.

| Product | Default family | Art-direction target |
| --- | --- | --- |
| Baseball hat | **Signal Shadow** | black distressed ground, cream/gray fragmentation, blue/yellow signal wedges, fragmented eye/portrait cues |
| Balaclava / mask | **Machine Static** | dense technical interference, micro-blocks, directional grain, sparse signal accents |
| Oversized shirt | **Error Garden** | botanical collage fused with digital artifacts, muted pink/green, eye fragments, signal accents |
| Cargo pants | **Broken Human** | displaced eyes/rib structures, large anatomical fragments, utility-panel composition |
| Beanie | **Ghost Hound** | oversized eye/canine fragments, high-contrast collage, directional noise, sparse signal accents |

The hoodie remains available as a **Machine Static** extension product but is not part of the five-piece canonical launch capsule.

## Implemented design families

- **Signal Shadow** — signal layering, fragmented familiar cues, eyes/portrait fragments, blue/yellow wedges, technical noise.
- **Machine Static** — dark ground, grayscale block interference, micro-grain, vertical channels, restrained signal accents.
- **Ghost Hound** — oversized eye/canine cues layered into the technical grammar.
- **Broken Human** — displaced eye and rib-like anatomy over distressed block structure.
- **Error Garden** — floral/leaf forms, muted greens/pinks, eye fragments, digital artifacts and signal accents.

Changing the seed creates a deterministic variation inside the same family. No external image-generation API is used.

Variation presets are now applied with deterministic pixel transforms rather than browser-dependent canvas filters. This keeps high-contrast, desaturated, alternate-palette, and scale variations reproducible across Chromium and WebKit/iPhone-class browsers.

The obsolete low-resolution showcase image path has been fully removed from Product Studio: no showcase DOM controls, source script, rendering state, compositing path, or showcase-specific CSS remain.

## Implemented Product Studio mockups

The canvas renderer supports:

- hoodie — front/back;
- baseball hat — front/side/back/top;
- beanie — front/side/back/slouch;
- cargo pants — front/back/side;
- balaclava/mask — front/side/back;
- oversized shirt — front/back.

The browser preview uses a 1122×1402 logical board for interactive performance. Export re-renders the board at production-review resolution rather than upscaling the preview bitmap.

## Product Studio export contract

### Master tile

- PNG
- 4096×4096
- deterministic from family + seed + controls
- master repeat artwork

### Reference board

- PNG
- **4096×5119 export**
- 1122×1402 interactive browser preview
- re-rendered from the garment geometry and textile tile at export scale
- merchandising / art-direction mockup
- not a vendor cut-panel file

### Product manifest

- JSON schema version 1.3
- `art_direction_profile: canonical_launch_capsule_v1`
- product and family identity
- seed, scale, density, distress, variation preset, and selected motif features
- `outputs.reference_board_px: [4096, 5119]`
- `outputs.preview_board_px: [1122, 1402]`
- `outputs.production_tile_px: [4096, 4096]`
- explicit digital-design/POD-template status

## Production Mapper

### Vendor-template contract

`templates/vendor-template.schema.json` records:

- provider and product identifiers;
- template version and source;
- DPI and canvas dimensions;
- exact panel rectangles;
- bleed and safe margins;
- required/optional panel status;
- continuity groups;
- optional seam relationships.

The included `templates/generic-aop-hoodie-preview.json` remains deliberately marked `vendor_ready: false`. It is normalized preview geometry only and must not be represented as provider production geometry.

### Seam-aware panel mapper

Every panel has independent X/Y pattern offset, scale and rotation. Panels may share a `continuity_group`; the mapper reports inconsistent transforms and can auto-map a common transform across related panels. Bleed and safe-area guides are drawn when supplied by the template.

### Panel-pack export

The Production Mapper can export:

- selected exact-size panel PNG;
- mapping JSON;
- evidence-bound manifest JSON;
- one ZIP containing `master/repeat_4096.png`, every `panels/<panel-id>.png`, `manifest.json`, `mapping.json`, and `template.json`.

A generic template produces a draft pack. An imported template that explicitly claims vendor readiness produces a vendor-template pack; this is an imported claim, not independent RAC verification of the provider source.

## Evidence binding

The production manifest binds the exact 4096×4096 design artifact, imported template, mapping state and every panel PNG with SHA-256. Artwork, template or mapping changes invalidate stale downstream evidence.

This is the bridge for future RAC-D records to attach to the exact commercial design artifact rather than to a visual concept alone.

Measured detector results remain scoped to their recorded evidence domain. A digital CI convenience fixture is not a physical-garment claim and does not establish broad surveillance resistance.

## Batch design factory

The Production Mapper can generate up to 100 deterministic seed candidates for the active family, rank them with the repository's local entropy/complexity/printability-style proxy, retain a shortlist and load a selected candidate back into mapping.

The local score is **not detector efficacy and not RAC certification evidence**. The reference-inspired candidate-pool exporter now includes Signal Shadow alongside the other Product Studio families.

## Browser regression coverage

Frontend E2E now covers:

- all six garment mockups;
- all five design families;
- live seed / scale / density / distress updates;
- motif selection;
- deterministic variation presets;
- mobile/WebKit usability;
- 4096×4096 tile export;
- 4096×5119 reference-board PNG dimensions;
- manifest output dimensions;
- continued absence of the obsolete low-resolution showcase source.

## Remaining production work

1. Acquire real provider templates and convert them into the adapter format without guessing dimensions.
2. Add provider-specific template-version libraries only after source material is obtained and recorded.
3. Add vendor-generated mockup comparison for scale/crop/seam validation.
4. Connect selected batch candidates to the measured RAC digital evaluation workflow.
5. Bind RAC-D result records to the production manifest's exact design artifact hash.
6. Order the first POD sample and start the physical feedback loop.
7. Add RAC-P physical evidence only after measured garment testing exists.

## Status

The repository now covers **canonical capsule art direction → deterministic design factory → high-resolution reference-board export → template adapter → panel mapper → panel-pack export → artifact evidence binding**. The remaining blocker to a true vendor-ready POD upload remains obtaining and ingesting actual provider template specifications for the chosen products.

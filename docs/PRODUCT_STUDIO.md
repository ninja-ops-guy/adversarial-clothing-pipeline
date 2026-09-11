# RAC Product Studio

## Purpose

The repository has two linked apparel surfaces:

- `product-studio.html` — deterministic procedural apparel design, governed research-candidate preview, and technical mockups.
- `production-studio.html` — vendor-template ingestion, seam-aware panel mapping, artifact hashing, panel-pack export, and batch seed ranking.

The normal canonical-family flow is:

1. select a deterministic design family and seed;
2. render a repeat tile and technical garment mockup;
3. persist the resolved Product Studio design state;
4. open the Production Mapper;
5. load a normalized preview template or import an exact vendor template JSON;
6. map the design independently across cut panels;
7. validate continuity-group transforms;
8. export exact-size panel PNGs, a ZIP panel pack, mapping JSON, and a hash-bound manifest;
9. optionally generate and rank a batch of candidate seeds for collection development.

The P0 research-family flow is deliberately different: the governed Python pattern pipeline remains the source of truth. Product Studio and Production Mapper expose the family inventory and accept an exact PNG candidate artifact for preview/mapping rather than reimplementing the research generators in browser JavaScript.

## Family availability contract

Product Studio now exposes every currently implemented family without promoting deferred work as if it were usable.

### Native Product Studio families — 5

These are deterministic browser-native art-direction families:

- **Signal Shadow** — signal layering, fragmented familiar cues, eyes/portrait fragments, blue/yellow wedges, technical noise.
- **Machine Static** — dark ground, grayscale block interference, micro-grain, vertical channels, restrained signal accents.
- **Ghost Hound** — oversized eye/canine cues layered into the technical grammar.
- **Broken Human** — displaced eye and rib-like anatomy over distressed block structure.
- **Error Garden** — floral/leaf forms, muted greens/pinks, eye fragments, digital artifacts and signal accents.

Changing the seed creates a deterministic variation inside the same family. No external image-generation API is used.

### Implemented P0 research families — 8

The runtime `P0_GENERATORS` inventory is surfaced in both Studio family selectors and as a dedicated Product Studio card set:

- `hyperface_like` — `HyperfaceLikeGenerator`
- `dazzle_surgical_lines` — `DazzleSurgicalLinesGenerator`
- `key_feature_blackout` — `KeyFeatureBlackoutGenerator`
- `saliency_eye_attack` — `SaliencyEyeAttackGenerator`
- `adversarial_patch` — `AdversarialPatchGenerator`
- `swapped_landmarks` — `SwappedLandmarksGenerator`
- `landmark_noise` — `LandmarkNoiseGenerator`
- `feature_collage` — `FeatureCollageGenerator`

For these eight entries, the browser is an **artifact consumer**, not a second scientific generator implementation. Selecting one reveals a governed-candidate import control. The imported PNG is SHA-256 hashed, associated with the selected family/generator, and used as the exact mockup/mapping tile.

The catalog records `PATTERNS_CANONICAL_128_V1` as the corresponding governed local-geometry contract, but browser code does not reproduce that generator logic. Imported research candidates are explicitly labeled `imported_governed_candidate_preview_not_physical_efficacy`.

### Deferred / refused entries

- P1: 5 registered generator stubs remain unavailable in Studio.
- P2: 23 registered generator stubs remain unavailable in Studio.
- P3-refused entries such as `bad_words` and `web_attack_strings` are not surfaced as usable families.

A cross-language contract test compares the browser P0 catalog directly with `ruthless_pipeline.patterns.P0_GENERATORS`, so adding or removing a runtime P0 family now fails tests until Studio exposure is updated too.

## Canonical launch capsule v1

The supplied product-board direction is the visual target for canonical Product Studio generation rather than a generic distressed-camouflage look.

| Product | Default family | Art-direction target |
| --- | --- | --- |
| Baseball hat | **Signal Shadow** | black distressed ground, cream/gray fragmentation, blue/yellow signal wedges, fragmented eye/portrait cues |
| Balaclava / mask | **Machine Static** | dense technical interference, micro-blocks, directional grain, sparse signal accents |
| Oversized shirt | **Error Garden** | botanical collage fused with digital artifacts, muted pink/green, eye fragments, signal accents |
| Cargo pants | **Broken Human** | displaced eyes/rib structures, large anatomical fragments, utility-panel composition |
| Beanie | **Ghost Hound** | oversized eye/canine fragments, high-contrast collage, directional noise, sparse signal accents |

The hoodie remains available as a **Machine Static** extension product but is not part of the five-piece canonical launch capsule.

## Product Studio feature inventory

The visible Product Studio controls now map to real capabilities. The earlier Generate / Refine / Batch / Export mode tabs were removed because they were mostly non-functional chrome; batch ranking and panel-pack export are real Production Mapper capabilities and remain there.

Implemented Product Studio features include:

- 5 native canonical families;
- 8 governed P0 research-family catalog entries;
- governed candidate PNG import with SHA-256 binding;
- six garment mockup types;
- deterministic seed, scale, density, and distress controls;
- selectable feature motifs for canonical families;
- deterministic variation presets;
- reference-image conditioning;
- reference-fidelity scoring and **Find Best Match** for canonical art-direction families only;
- frozen candidate override for exact imported research artifacts;
- 4096×4096 tile export;
- 4096×5119 reference-board export;
- product manifest export;
- handoff to Production Mapper.

Reference-fidelity search is intentionally disabled for P0 research imports because those families do not have canonical art-direction reference profiles. In Production Mapper, a P0 family automatically disables reference-fidelity batch ranking and uses the visual/printability proxy instead.

Variation presets use deterministic pixel transforms rather than browser-dependent canvas filters. This keeps high-contrast, desaturated, alternate-palette, and scale variations reproducible across Chromium and WebKit/iPhone-class browsers.

The obsolete low-resolution showcase image path remains fully removed from Product Studio: no showcase DOM controls, source script, rendering state, compositing path, or showcase-specific CSS remain.

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
- deterministic from family + seed + controls for canonical families
- exact imported frozen artifact for governed P0 research previews
- master repeat artwork

### Reference board

- PNG
- **4096×5119 export**
- 1122×1402 interactive browser preview
- re-rendered from the garment geometry and textile tile at export scale
- merchandising / art-direction mockup
- not a vendor cut-panel file

### Product manifest

- JSON schema version 1.4
- `art_direction_profile: canonical_launch_capsule_v1`
- product and family identity
- seed, scale, density, distress, variation preset, and selected motif features
- `outputs.reference_board_px: [4096, 5119]`
- `outputs.preview_board_px: [1122, 1402]`
- `outputs.production_tile_px: [4096, 4096]`
- explicit digital-design/POD-template status
- imported frozen-tile metadata when a governed research candidate is active

Product Studio itself does **not** create the panel-pack ZIP. Its output list now labels `panel_pack.zip` as a downstream **Production Mapper** output rather than implying that Product Studio creates it directly.

## Production Mapper

Production Mapper exposes the same P0 catalog. Selecting a P0 family requires the governed candidate PNG import; the mapper consumes the imported pixels instead of falling back to one of the five canonical families.

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

Measured detector results remain scoped to their recorded evidence domain. A digital CI convenience fixture or a Studio preview is not a physical-garment claim and does not establish broad surveillance resistance.

## Batch design factory

For canonical families, the Production Mapper can generate up to 100 deterministic seed candidates, rank them with reference fidelity or the local entropy/complexity/printability-style proxy, retain a shortlist and load a selected candidate back into mapping.

For imported P0 research candidates, reference-fidelity ranking is disabled because no canonical art-direction profile exists. The visual/printability proxy remains available, but it is **not detector efficacy and not RAC certification evidence**.

## Browser regression coverage

Frontend E2E now covers:

- all six garment mockups;
- all five native design families;
- exposure of all eight implemented P0 research families;
- exact P0/deferred/refused catalog behavior;
- governed research-candidate PNG import and SHA-256 metadata;
- Product Studio frozen-tile binding;
- Production Mapper P0 selection and ranking-mode guard;
- live seed / scale / density / distress updates;
- motif selection;
- deterministic variation presets;
- mobile/WebKit usability;
- 4096×4096 tile export;
- 4096×5119 reference-board PNG dimensions;
- manifest output dimensions;
- continued absence of the obsolete low-resolution showcase source;
- removal of inert mode tabs and correct downstream panel-pack labeling.

## Remaining production work

1. Acquire real provider templates and convert them into the adapter format without guessing dimensions.
2. Add provider-specific template-version libraries only after source material is obtained and recorded.
3. Add vendor-generated mockup comparison for scale/crop/seam validation.
4. Connect selected governed research candidates to the measured RAC digital evaluation workflow through their exact artifact hashes.
5. Bind RAC-D result records to the production manifest's exact design artifact hash.
6. Order the first POD sample and start the physical feedback loop.
7. Add RAC-P physical evidence only after measured garment testing exists.

## Status

The Studio surfaces now cover **5 canonical native generators + 8 implemented P0 research families via governed artifact import → high-resolution mockup/export → template adapter → panel mapper → panel-pack export → artifact evidence binding**. Deferred generator stubs remain fail-closed rather than appearing as functional Studio options.

The remaining blocker to a true vendor-ready POD upload remains obtaining and ingesting actual provider template specifications for the chosen products.

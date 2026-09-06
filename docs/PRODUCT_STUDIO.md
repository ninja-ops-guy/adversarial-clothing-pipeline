# RAC Product Studio

## Purpose

`product-studio.html` turns the repository's procedural pattern tooling into a product-design surface for print-on-demand apparel.

The current flow is:

1. select a deterministic design family and seed;
2. render a repeat tile;
3. place it on a multi-view technical apparel mockup;
4. export a 4096×4096 production tile;
5. export a reference-board PNG;
6. export a production manifest.

## Implemented design families

- **Machine Static** — dark ground, grayscale block interference, micro-grain, electric-blue and signal-yellow accents.
- **Ghost Hound** — the same technical grammar with fragmented eye/figurative motifs.
- **Broken Human** — displaced eye and rib-like collage cues over distressed block structure.
- **Error Garden** — floral forms, muted greens/pinks, distressed digital artifacts and signal accents.

Changing the seed creates a new deterministic variation inside the same family.

## Implemented mockups

The canvas renderer supports:

- hoodie — front/back;
- beanie — front/side/back/slouch;
- cargo pants — front/back/side;
- balaclava/mask — front/side/back;
- oversized shirt — front/back.

The reference-board renderer uses the supplied visual direction: large industrial product title, off-white technical sheet, multiple garment views, textile-detail crop, pattern-strategy copy, restrained technical typography and signal-color accents.

## Export contract

### Production tile

- PNG
- 4096×4096
- deterministic from family + seed + controls
- intended as master repeat artwork for a print-on-demand template

### Reference board

- PNG
- 1122×1402
- merchandising / art-direction mockup
- not a vendor cut-panel file

### Production manifest

JSON records product, family, seed, pattern controls and required output dimensions.

## Planned tester features

Provider-specific production files cannot be generated correctly until the actual vendor templates are available. The tester should add these features next:

1. **Provider template importer** — load Printful, Printify or Contrado PNG/SVG templates and record template version, safe area, bleed and seams.
2. **Seam-aware panel mapper** — independently position front, back, sleeves, hood and leg panels while preserving continuity across adjoining seams.
3. **Panel-pack exporter** — export every print area at the exact provider dimensions and fail when a required panel is absent or the dimensions are wrong.
4. **Vendor mockup comparison** — import the vendor-generated mockup and compare scale, crop and seam placement against the studio reference board.
5. **Batch design factory** — generate multiple deterministic seeds per design family, score them with existing local visual/printability metrics and queue selected candidates for the repository's digital evaluation flow.
6. **Evidence binding** — bind downstream test evidence to the exact exported design hash so changing the artwork invalidates stale results.

## Status

The visual design + mockup MVP is implemented. Vendor-specific template mapping remains planned rather than inventing provider dimensions.

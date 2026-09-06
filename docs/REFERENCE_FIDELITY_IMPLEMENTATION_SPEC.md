# RAC Reference Fidelity v1 — Patch-Level Implementation Spec

## Objective

Make Product Studio outputs match the supplied canonical product-board references much more closely while preserving deterministic procedural generation and avoiding external image-generation APIs.

This is a coding-agent implementation spec, not a design essay. It defines exact files, data structures, interfaces, tests, and acceptance criteria for `reference-fidelity-v1`.

## Canonical launch capsule

| Product | Default family | Reference intent |
| --- | --- | --- |
| Baseball hat | `signal_shadow` | black technical base; cream/gray fragmentation; sparse electric-blue and signal-yellow accents; large eye/portrait cue; readable cap seams |
| Balaclava / mask | `machine_static` | dense vertical/static interference; micro-blocks; restrained figurative content; full-coverage technical texture |
| Oversized shirt | `error_garden` | botanical first, digital artifacts second; muted pink/olive/cream; hidden eye/animal fragment; softer transitions |
| Cargo pants | `broken_human` | large eye/face/rib fragments distributed across utility panels; strong asymmetry; anatomy survives pockets/knees |
| Beanie | `ghost_hound` | oversized eye/canine fragments; high contrast; wraparound continuity; slouch silhouette remains legible |

The hoodie remains an extension product using `machine_static` but is not part of the five-piece canonical fidelity target.

---

# 1. `studio-style-profiles.js` — NEW

Create a dedicated style-spec module. Do not continue embedding reference intent implicitly across `product-studio.js` and `studio-patterns.js`.

Expose:

```js
window.RACStyleProfiles = {
  profiles,
  productLayouts,
  getProfile,
  getProductLayout,
  resolveProfile
};
```

## 1.1 `profiles`

Use a data-first contract so rendering and scoring consume the same source of truth.

```js
const profiles = {
  signal_shadow: {
    id: 'signal_shadow',
    reference_target: 'SIGNAL SHADOW HAT',
    palette: {
      base: ['#080808', '#151515'],
      neutrals: ['#343434', '#777777', '#d8ccb6'],
      accents: ['#155bd8', '#e7df16']
    },
    target_ratios: {
      dark: [0.58, 0.78],
      cream_gray: [0.16, 0.30],
      blue: [0.015, 0.060],
      yellow: [0.015, 0.060],
      negative_space: [0.12, 0.28]
    },
    hero: {
      type: 'eye_or_portrait_fragment',
      count: [1, 2],
      size_fraction: [0.18, 0.34],
      contrast: 'high',
      priority: 1.0
    },
    structure: {
      block_orientation: 'mixed_vertical_bias',
      large_block_count: [12, 28],
      micro_cluster_count: [35, 95],
      grain_direction: 'vertical'
    },
    variation_limits: {
      scale: [42, 68],
      density: [58, 82],
      distress: [60, 88]
    }
  },
  machine_static: { /* same schema */ },
  ghost_hound: { /* same schema */ },
  broken_human: { /* same schema */ },
  error_garden: { /* same schema */ }
};
```

Implement all five profiles with explicit target ratios and variation limits. Do not use placeholder defaults.

### Suggested targets

#### `machine_static`
- dark: 0.62–0.82
- cream/gray: 0.14–0.28
- blue: 0.01–0.05
- yellow: 0.01–0.05
- hero figurative count: 0–1
- vertical grain bias: strong
- large blocks: 18–38
- micro clusters: 70–150

#### `ghost_hound`
- dark: 0.50–0.70
- cream/gray: 0.22–0.38
- blue: 0.02–0.07
- yellow: 0.02–0.07
- hero eye/canine count: 1–3
- hero size: 0.22–0.40
- silhouette-break priority: high

#### `broken_human`
- dark: 0.46–0.66
- cream/gray: 0.24–0.42
- blue: 0.02–0.07
- yellow: 0.02–0.07
- eye count: 1–3
- rib/anatomy count: 1–2
- hero size: 0.24–0.44
- asymmetry: high

#### `error_garden`
- dark: 0.42–0.62
- cream: 0.10–0.24
- pink: 0.08–0.20
- olive: 0.08–0.20
- blue/yellow combined: 0.02–0.08
- floral count: 8–18
- eye count: 1–2
- transition softness: medium/high

## 1.2 `productLayouts`

Add product-aware normalized zones. Coordinates are 0–1 relative to the master composition canvas.

```js
const productLayouts = {
  hat: {
    family: 'signal_shadow',
    hero_zones: [
      { id: 'crown_front', x: 0.10, y: 0.08, w: 0.55, h: 0.44, weight: 1.0 },
      { id: 'crown_side', x: 0.52, y: 0.16, w: 0.38, h: 0.38, weight: 0.55 }
    ],
    accent_zones: [
      { id: 'brim_left', x: 0.02, y: 0.58, w: 0.36, h: 0.24 },
      { id: 'side_signal', x: 0.62, y: 0.20, w: 0.30, h: 0.32 }
    ],
    suppression_zones: [],
    continuity_hints: ['crown_front_to_side', 'crown_to_brim']
  },
  mask: { /* ... */ },
  beanie: { /* ... */ },
  cargo: { /* ... */ },
  shirt: { /* ... */ },
  hoodie: { /* ... */ }
};
```

Required product-specific rules:

- `hat`: preserve cap-panel readability; hero motif concentrated crown-front/side; accents continue into brim.
- `mask`: protect eye-opening zone from dense hero motifs; favor centerline and neck continuation.
- `beanie`: hero eye above fold/cuff; wraparound continuity; allow slouch drift upward/backward.
- `cargo`: left/right-leg asymmetry; pocket-safe and knee-safe suppression zones; anatomy split across legs intentionally.
- `shirt`: front primary focal zone; back secondary focal zone; collar and side-seam suppression margins.

## 1.3 helpers

Add:

```js
function getProfile(family) { ... }
function getProductLayout(product) { ... }
function resolveProfile({ family, product, mode, controls }) { ... }
```

`resolveProfile()` must clamp user controls to profile ranges when `mode === 'reference'`, while preserving freer ranges in `mode === 'creative'`.

---

# 2. `studio-patterns.js` — REFACTOR

Current family generators should become guided multi-pass composition generators.

## 2.1 Public API

Keep existing `patternGenerators[family]` compatibility, but internally route through:

```js
function buildStyleSpec(family, params, seed, product = null, mode = 'creative')
function renderFamilyFromSpec(ctx, size, spec)
```

Expose for scoring/tests:

```js
window.RACPatternComposition = {
  buildStyleSpec,
  renderFamilyFromSpec,
  analyzeComposition
};
```

## 2.2 Composition passes

Every family must render in this order:

```text
1. base field
2. hero motif layer
3. structural block layer
4. secondary motif layer
5. micro texture / grain layer
6. accent signal layer
7. suppression / cleanup masks
8. final distress pass
```

Do not scatter all motifs from one random loop.

## 2.3 Deterministic sub-seeds

Use named deterministic sub-seeds so small parameter changes do not reshuffle every layer.

Example:

```js
const seeds = {
  base: deriveSeed(seed, 'base'),
  hero: deriveSeed(seed, 'hero'),
  structure: deriveSeed(seed, 'structure'),
  secondary: deriveSeed(seed, 'secondary'),
  grain: deriveSeed(seed, 'grain'),
  accents: deriveSeed(seed, 'accents')
};
```

Add `deriveSeed(baseSeed, label)` with a stable string hash.

## 2.4 Hero placement

Add normalized helper:

```js
function placeHeroInZone(ctx, size, hero, zone, rng)
```

Rules:
- respect `productLayouts[product].hero_zones` in reference mode;
- choose weighted zones deterministically;
- enforce profile hero size limits;
- prevent hero center from landing in suppression zones;
- allow controlled cropping at edges for collage feel.

## 2.5 Family-specific rendering requirements

### Signal Shadow
- 1–2 large eye/portrait fragments;
- sparse angular yellow/blue wedges;
- lower overall density than Ghost Hound;
- visible dark fields between interference regions;
- mixed blocks with vertical bias.

### Machine Static
- no mandatory hero motif;
- dense vertical grain channels;
- micro-block interference should dominate;
- figurative content, if any, must remain low-opacity and secondary;
- signal colors remain sparse.

### Ghost Hound
- hero eye is mandatory in reference mode;
- add abstract canine-ear/face fragments, but avoid literal full dog illustrations;
- large cream fragments around hero motif;
- preserve strong black regions for readability.

### Broken Human
- mandatory anatomy layer in reference mode;
- at least one large eye/face fragment and one rib/anatomy structure;
- strong left/right asymmetry;
- rectangular disruption overlays should partially obscure anatomy.

### Error Garden
- botanical forms dominate area coverage;
- digital artifacts interrupt flowers/leaves rather than sit as a separate wallpaper;
- eye/animal fragment hidden inside foliage;
- pink/olive/cream coverage visibly exceeds blue/yellow coverage.

## 2.6 `analyzeComposition`

Return metrics needed by fidelity scoring:

```js
{
  palette: {
    dark_ratio,
    cream_gray_ratio,
    blue_ratio,
    yellow_ratio,
    pink_ratio,
    olive_ratio
  },
  edges: {
    horizontal_energy,
    vertical_energy,
    directional_bias
  },
  occupancy: {
    high_contrast_ratio,
    negative_space_ratio,
    connected_region_count
  },
  motifs: {
    hero_count,
    hero_area_ratio,
    eye_count,
    anatomy_count,
    floral_count,
    accent_cluster_count
  }
}
```

Motif counts may come directly from the deterministic spec rather than computer vision.

---

# 3. `product-studio.html` — UI PATCH

Add a new control directly below Design Family:

```html
<div class="field">
  <label>Generation Mode</label>
  <select id="generationMode">
    <option value="reference">Reference Match</option>
    <option value="creative">Creative</option>
  </select>
</div>
```

Default: `reference`.

Add a compact readout below controls:

```html
<div id="referenceProfileStatus" class="profile-status"></div>
```

Show:
- active profile
- target product
- whether controls are clamped
- current fidelity score after rendering

Add a button:

```html
<button onclick="RACStudio.findBestMatch()">Find Best Match</button>
```

This should run a small local search (default 24 seeds) using the same fidelity scorer as Production Mapper and load the highest-ranked candidate.

---

# 4. `product-studio.js` — INTEGRATION PATCH

## 4.1 State

Extend state with:

```js
mode: $('generationMode').value
```

Manifest must include:

```js
generation_mode: s.mode,
reference_profile: s.family,
reference_fidelity: {
  score: lastFidelity?.score ?? null,
  subscores: lastFidelity?.subscores ?? null,
  scorer_version: 'reference-fidelity-v1'
}
```

## 4.2 Script dependency

`product-studio.html` must load:

```html
<script src="studio-style-profiles.js"></script>
```

before `studio-patterns.js`.

## 4.3 `makeTile`

Replace direct raw-generator invocation with:

```js
const resolved = RACStyleProfiles.resolveProfile({
  family: s.family,
  product: s.product,
  mode: s.mode,
  controls: {
    scale: s.scale,
    density: s.density,
    distress: s.distress
  }
});

const spec = RACPatternComposition.buildStyleSpec(
  s.family,
  resolved,
  s.seed,
  s.product,
  s.mode
);
RACPatternComposition.renderFamilyFromSpec(ctx, size, spec);
```

Keep a compatibility fallback to `patternGenerators` only for non-capsule families.

## 4.4 Default control behavior

When product or family changes and mode is `reference`:
- set controls to profile midpoint values;
- do not leave stale values from another family;
- update slider ranges visually if practical, otherwise clamp during render and display effective values.

Suggested defaults:

| Family | Scale | Density | Distress |
| --- | ---: | ---: | ---: |
| Signal Shadow | 54 | 67 | 73 |
| Machine Static | 48 | 79 | 82 |
| Ghost Hound | 62 | 69 | 72 |
| Broken Human | 68 | 71 | 70 |
| Error Garden | 64 | 74 | 58 |

## 4.5 Reference board tightening

Create a fixed board-layout schema:

```js
const BOARD_LAYOUT = {
  header: { x: 31, y: 62, maxWidth: 730 },
  descriptor: { x: 797, y: 40, w: 260 },
  detail: { x: 31, y: 930, w: 510, h: 302 },
  strategy: { x: 575, y: 950, w: 480 },
  footerLeft: { x: 32, y: 1334 },
  footerBrand: { x: 885, y: 1330 }
};
```

Use the same layout anchors for every canonical board. Product-specific code should change garment placement only, not the overall technical-sheet grid.

## 4.6 `findBestMatch()`

Implement:

```js
async function findBestMatch({ count = 24 } = {})
```

Behavior:
1. generate deterministic seed candidates around current seed;
2. render 256×256 analysis tiles;
3. call `RACReferenceScorer.score(...)`;
4. select highest score;
5. set `studioSeed` to winner;
6. render full board;
7. show score/subscores.

Do not call RAC-D or detector models here. This is visual-reference fidelity only.

---

# 5. `reference-fidelity.js` — NEW

Expose:

```js
window.RACReferenceScorer = {
  VERSION: 'reference-fidelity-v1',
  score,
  rankCandidates
};
```

## 5.1 Score contract

```js
score({ family, product, analysis, spec, mode }) => {
  score: 0..100,
  subscores: {
    palette,
    accent_balance,
    hero_motif,
    composition,
    directional_texture,
    product_fit,
    macro_detail
  },
  penalties: [],
  warnings: []
}
```

## 5.2 Weights

Use:

```js
const WEIGHTS = {
  palette: 0.18,
  accent_balance: 0.12,
  hero_motif: 0.22,
  composition: 0.18,
  directional_texture: 0.12,
  product_fit: 0.10,
  macro_detail: 0.08
};
```

## 5.3 Scoring rules

### Palette
Score against target ratio ranges from `studio-style-profiles.js`.

For a metric within target range: 100.
Outside range: linearly decay to 0 over a tolerance band equal to 50% of target range width, with a minimum tolerance floor of 0.02.

### Accent balance
- penalize blue/yellow dominance;
- reward sparse but visible accents;
- Error Garden must score pink/olive coverage separately and treat blue/yellow as secondary.

### Hero motif
- mandatory for `signal_shadow`, `ghost_hound`, `broken_human` in reference mode;
- optional/low-weight presence for `machine_static`;
- Error Garden hero score primarily uses floral composition plus hidden eye cue.

### Composition
Use:
- negative-space ratio;
- connected-region count;
- large-vs-small motif balance;
- asymmetry requirements.

### Directional texture
- Machine Static: strong vertical bias preferred;
- Signal Shadow: modest vertical bias;
- Ghost Hound: mixed with directional streaking;
- Broken Human: mixed/asymmetric;
- Error Garden: near-neutral directional bias.

### Product fit
Use zone occupancy from the generated spec:
- hero center should land in allowed hero zones;
- penalize suppression-zone overlap;
- cargo: penalize anatomy centered inside knee/pocket suppression zones;
- mask: penalize hero overlap with eye opening;
- hat: reward crown-to-brim continuity hints.

### Macro detail
Reward enough local variation at 1:1 textile crop without becoming uniformly noisy.

## 5.4 Hard penalties

Apply after weighted score:

- missing mandatory hero motif: −20
- accent total > 16% for non-Error-Garden families: −12
- dark ratio below family minimum by > 0.12: −10
- product suppression-zone overlap > 35% of hero area: −15
- reference mode controls outside allowed profile after clamp bug: −10 and warning

Clamp final score to 0–100.

---

# 6. `production-studio.html` — BATCH UI PATCH

In Batch Design Factory add:

```html
<div class="field">
  <label>Ranking Mode</label>
  <select id="batchRankingMode">
    <option value="reference_fidelity">Reference Fidelity</option>
    <option value="visual_proxy">Legacy Visual / Printability Proxy</option>
  </select>
</div>
```

Add per-card display:
- total score
- palette
- hero
- composition
- product fit

Add a small label:

`REFERENCE STYLE SCORE — NOT RAC CERTIFICATION`

---

# 7. `production-studio.js` — RANKING PATCH

## 7.1 Family mapping bug fix

Update:

```js
const FAMILY_BY_PRODUCT = {
  hoodie:'machine_static',
  hat:'signal_shadow',
  beanie:'ghost_hound',
  cargo:'broken_human',
  mask:'machine_static',
  shirt:'error_garden'
};
```

The current file still lacks `hat`.

## 7.2 Studio state loading

Prefer `resolvedDesignFamily` from `studio-bridge.js` when present.

```js
const family = state.resolvedDesignFamily || state.designFamily || FAMILY_BY_PRODUCT[state.productType];
```

Do not allow literal `auto` to propagate to the Production Mapper.

## 7.3 Batch ranking

Refactor current batch score into:

```js
function scoreLegacyVisualProxy(...)
function scoreReferenceCandidate({ family, product, seed, cfg })
```

When `batchRankingMode === 'reference_fidelity'`:
- build deterministic spec;
- render 192 or 256px tile;
- analyze composition;
- call `RACReferenceScorer.score()`;
- sort descending by fidelity score.

Shortlist JSON schema:

```json
{
  "schema_version": "2.0",
  "ranking_mode": "reference_fidelity",
  "scorer_version": "reference-fidelity-v1",
  "family": "broken_human",
  "product": "cargo",
  "candidates": [
    {
      "seed": 433,
      "score": 87.4,
      "subscores": {
        "palette": 91,
        "accent_balance": 84,
        "hero_motif": 95,
        "composition": 82,
        "directional_texture": 79,
        "product_fit": 88,
        "macro_detail": 81
      }
    }
  ]
}
```

## 7.4 Manifest binding

When a reference-ranked candidate is loaded, include in production manifest:

```js
reference_fidelity: {
  scorer_version: 'reference-fidelity-v1',
  score,
  subscores,
  ranking_mode: 'reference_fidelity'
}
```

Make clear this is style evidence, not detector efficacy or RAC-D evidence.

---

# 8. `studio-bridge.js` — STATE PATCH

Add `generationMode` to `IDS`.

Persist:

```js
state.referenceProfile = state.resolvedDesignFamily;
state.artDirectionProfile = 'canonical_launch_capsule_v1';
```

This ensures Product Studio → Production Mapper carries the exact intended style profile.

---

# 9. `product-studio.css` / `production-studio.css` — UI PATCH

Add only minimal styles required for the new controls and fidelity readouts.

Suggested classes:

```css
.profile-status
.fidelity-score
.fidelity-bars
.fidelity-subscore
.reference-badge
```

Do not redesign the whole UI in this milestone.

---

# 10. `scripts/export_candidate_pool.js` — CANDIDATE PIPELINE PATCH

Add a mode flag:

```bash
node scripts/export_candidate_pool.js --ranking reference_fidelity
```

Default for capsule families: `reference_fidelity`.

Output record additions:

```json
{
  "reference_fidelity_score": 88.2,
  "reference_fidelity_subscores": { ... },
  "reference_profile": "ghost_hound",
  "product_target": "beanie"
}
```

Do not overwrite historical benchmark semantics. Keep this as creative/style selection metadata.

---

# 11. Tests

## 11.1 `tests/e2e/product-studio.spec.js`

Add:

### `reference match mode is default`
- expect `#generationMode` = `reference`.

### `reference profiles clamp controls deterministically`
For each canonical family:
- set intentionally extreme sliders;
- render;
- verify effective profile values fall within profile limits.

### `canonical family/product mapping remains correct`
Retain and extend existing mapping test.

### `reference fidelity score is deterministic`
- fixed product/family/seed;
- render twice;
- exact same score and subscores.

### `find best match does not reduce score`
- record current score;
- click Find Best Match;
- expect final score >= starting score.

### `reference mode families remain visually distinct`
Keep existing distinct-canvas test across all five families.

### `hat four-view board remains functional`
Retain existing Signal Shadow hat test.

## 11.2 `tests/e2e/production-studio.spec.js`

Add:

### `loads resolved Signal Shadow hat state`
- persist Product Studio state with `hat` + `signal_shadow`;
- load current design;
- verify family is `signal_shadow`, never `auto`.

### `reference fidelity ranking sorts descending`
- batch 12 seeds;
- verify score order.

### `selected shortlist candidate round-trips into mapper`
- select candidate;
- verify seed/family update;
- export manifest;
- verify reference fidelity metadata.

### `legacy visual proxy remains available`
Ensure no regression of old ranking mode.

## 11.3 Unit-style browser tests

If no lightweight JS unit harness exists, add a Playwright page-level test that invokes:

```js
RACReferenceScorer.score(...)
RACStyleProfiles.getProfile(...)
RACPatternComposition.buildStyleSpec(...)
```

Validate no NaN/undefined metrics across all canonical families and products.

---

# 12. CI / Pages

Update deployed Pages smoke test to verify:

- `studio-style-profiles.js` and `reference-fidelity.js` load without 404;
- Product Studio Reference Match control exists;
- Signal Shadow Hat renders;
- a fidelity score is shown;
- Production Mapper Reference Fidelity ranking mode exists.

Do not block deployment on historical Python lint/dependency backlog unless those workflows already do so.

---

# 13. Acceptance criteria for `reference-fidelity-v1`

All must pass:

1. Product Studio defaults to `Reference Match` mode.
2. Each canonical product resolves to the intended family.
3. The five families use explicit reference-style profiles, not generic shared thresholds.
4. Hero motifs are zone-guided in reference mode.
5. Generated layers use deterministic sub-seeds.
6. A 0–100 reference-fidelity score is produced with documented subscores.
7. Batch Factory can rank by reference fidelity and still exposes legacy visual proxy.
8. `Find Best Match` improves or preserves the current fidelity score.
9. Product Studio → Production Mapper preserves resolved family and generation mode.
10. Production manifests can contain style-fidelity metadata without presenting it as RAC certification.
11. Existing tile, board, panel-pack, hashing, and vendor-template exports continue to work.
12. Playwright local browser matrix is green.
13. Deployed Product Studio and Production Mapper smoke tests are green.

---

# 14. Non-goals

Do **not** implement these in this milestone:

- external AI/image-generation calls;
- computer-vision comparison against the uploaded reference images;
- real Printful/Printify dimensions without provider source templates;
- claims of adversarial detector efficacy based on reference-fidelity score;
- RAC-P physical certification;
- broad UI redesign unrelated to fidelity.

---

# 15. Recommended implementation order

1. Add `studio-style-profiles.js`.
2. Add `reference-fidelity.js`.
3. Refactor `studio-patterns.js` into deterministic composition passes.
4. Wire Reference Match mode into `product-studio.html/js`.
5. Tighten board-layout constants.
6. Patch `studio-bridge.js` state persistence.
7. Fix `production-studio.js` hat mapping and resolved-family loading.
8. Add reference-fidelity batch ranking to Production Mapper.
9. Patch candidate-pool exporter.
10. Add/extend Playwright tests.
11. Update Pages smoke tests.
12. Update `docs/PRODUCT_STUDIO.md` after implementation reflects ground truth.

---

# 16. Definition of done

The milestone is complete when a user can select any of the five canonical products, leave Product Studio in Reference Match mode, generate multiple seeded candidates, see an explicit reference-fidelity score, automatically select a better-matching candidate, load it into the Production Mapper, and export the same production artifacts as before—without any external image generation and without conflating visual-style similarity with adversarial-performance evidence.

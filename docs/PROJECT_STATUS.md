# Adversarial Clothing Pipeline — Project Status

**Date:** 2026-09-06  
**Repository:** `ninja-ops-guy/adversarial-clothing-pipeline`  
**Status basis:** current `main` plus implemented Product Studio / Production Mapper documentation and the Reference Fidelity v1 implementation spec.

## Executive Summary

The project has advanced beyond a pattern-testing prototype into a multi-layer system with three distinct responsibilities:

1. **Design factory** — deterministic procedural apparel design, technical product boards, and high-resolution master artwork.
2. **Production compiler** — vendor-template ingestion, seam-aware panel mapping, panel-pack export, and artifact hashing.
3. **Evidence / certification system** — ordered RAC digital, physical, and manufacturing evidence states with fail-closed boundaries and provenance requirements.

The five-piece canonical launch capsule is now defined and partially implemented in Product Studio:

- Signal Shadow Hat
- Machine Static Mask
- Error Garden Shirt
- Broken Human Cargo Pants
- Ghost Hound Beanie

A Machine Static hoodie remains an extension product.

The largest remaining visual-development gap is **reference fidelity**. The current generators implement the five families and canonical product mapping, but the more rigorous `reference-fidelity-v1` architecture — style profiles, garment-aware composition zones, explicit visual scoring, Reference Match mode, and fidelity-ranked search — is still a specification and has not yet been implemented as its own modules.

The largest remaining production gap is **real POD provider geometry**. The software can produce artwork, mockups, draft panel packs, and evidence-bound manifests, but true provider-ready uploads still require exact templates from the selected POD provider.

---

## Current Architecture

```text
Research / Pattern Lab
        ↓
Deterministic Pattern Generation
        ↓
Product Studio
        ↓
Canonical Apparel Mockups
        ↓
4096×4096 Master Artwork
        ↓
Production Mapper
        ↓
Vendor Template Adapter
        ↓
Seam-Aware Panel Mapping
        ↓
Panel Pack + Hash Manifest
        ↓
POD Provider
        ↓
Physical Sample
        ↓
RAC-P Evidence
        ↓
Manufacturing Evidence / RAC-M
```

The evidence architecture remains intentionally separate from the creative workflow. Visual quality, reference similarity, local entropy/printability scores, and merchandising mockups do not constitute RAC-D, RAC-P, or RAC-M evidence by themselves.

---

## 1. Design Factory

### Implemented

| Capability | Status | Notes |
| --- | --- | --- |
| Deterministic seeded generation | ✅ | Family + seed + controls reproduce outputs |
| Signal Shadow | ✅ | Canonical hat family |
| Machine Static | ✅ | Canonical mask / hoodie family |
| Ghost Hound | ✅ | Canonical beanie family |
| Broken Human | ✅ | Canonical cargo family |
| Error Garden | ✅ | Canonical shirt family |
| 4096×4096 master tile export | ✅ | POD artwork master |
| Technical reference-board export | ✅ | 1122×1402 merchandising / art-direction board |
| Product manifest | ✅ | Records product, family, seed and controls |
| No external image-generation dependency | ✅ | Procedural canvas generation |

### Canonical Product Mapping

| Product | Family | Status |
| --- | --- | --- |
| Baseball hat | Signal Shadow | ✅ Implemented |
| Balaclava / mask | Machine Static | ✅ Implemented |
| Oversized shirt | Error Garden | ✅ Implemented |
| Cargo pants | Broken Human | ✅ Implemented |
| Beanie | Ghost Hound | ✅ Implemented |
| Hoodie | Machine Static | ✅ Extension product |

### Current Visual Limitation

The existing family renderers are reference-inspired and recognizably differentiated, but they are still primarily procedural pattern generators. They do not yet use a unified, data-driven style-profile system or explicit product-aware hero/suppression zones.

**Assessment:** design-system functionality is mature enough for iteration, but **visual fidelity to the supplied boards is not yet at final-launch quality**.

---

## 2. Reference Fidelity v1

### Planned / Specified

`docs/REFERENCE_FIDELITY_IMPLEMENTATION_SPEC.md` defines the next visual-quality milestone.

| Capability | Status |
| --- | --- |
| `studio-style-profiles.js` | ⏳ Specified, not implemented |
| Explicit per-family palette ratios | ⏳ |
| Product-specific hero zones | ⏳ |
| Product-specific suppression / safe zones | ⏳ |
| Guided multi-pass composition | ⏳ |
| Named deterministic sub-seeds | ⏳ |
| Composition analysis | ⏳ |
| `reference-fidelity.js` scorer | ⏳ |
| 0–100 reference fidelity score | ⏳ |
| Reference Match vs Creative mode | ⏳ |
| `Find Best Match` local seed search | ⏳ |
| Fidelity-ranked batch generation | ⏳ |
| Fidelity metadata in manifests | ⏳ |

### Target Outcome

The next implementation should move generation from:

> seeded visual family

into:

> seeded visual family + explicit style contract + garment-aware composition + measurable reference similarity

This is the highest-priority creative software milestone.

---

## 3. Garment Mockup System

### Implemented

| Garment | Views |
| --- | --- |
| Hoodie | Front / back |
| Baseball hat | Front / side / back / top |
| Beanie | Front / side / back / slouch |
| Cargo pants | Front / back / side |
| Balaclava / mask | Front / side / back |
| Oversized shirt | Front / back |

The technical-board renderer already uses the canonical presentation language: off-white sheet, large industrial heading, multi-view product layout, textile detail, pattern-strategy text, technical typography, and restrained accent usage.

### Remaining Mockup Work

- tighten product silhouette realism;
- standardize the board grid across all products;
- add product-aware motif placement rather than simply applying a repeat across the silhouette;
- compare Studio mockups against vendor-generated mockups after a provider is selected.

---

## 4. Production Mapper / POD Compiler

### Implemented

| Capability | Status |
| --- | --- |
| Vendor-template JSON contract | ✅ |
| Generic AOP preview template | ✅ |
| Exact pixel panel dimensions from template | ✅ |
| Per-panel X/Y offset | ✅ |
| Per-panel scale | ✅ |
| Per-panel rotation | ✅ |
| Continuity groups | ✅ |
| Bleed / safe-area display | ✅ |
| Continuity validation | ✅ |
| Selected panel PNG export | ✅ |
| Mapping JSON export | ✅ |
| Full panel-pack ZIP | ✅ |
| 4096 master included in pack | ✅ |
| SHA-256 artwork/template/mapping/panel binding | ✅ |
| Draft vs imported vendor-ready status distinction | ✅ |

### Important Boundary

The bundled generic template is intentionally not provider-ready. The system must not claim a production pack is vendor-ready simply because it has panel files.

### Remaining Blocker

**Acquire an exact POD template for the first real product.**

Recommended first target: one AOP shirt, hoodie, beanie, or comparable product whose provider supplies sufficiently detailed print geometry.

The quickest validation loop is:

```text
real provider template
→ adapter JSON
→ panel mapping
→ manual upload
→ first sample order
→ compare physical garment to Studio output
```

API integration is secondary to proving the first exact template workflow.

---

## 5. Batch Collection Factory

### Implemented

- deterministic seed batches;
- up to 100 candidates in Production Mapper;
- local entropy / complexity / printability-style proxy ranking;
- shortlist selection;
- candidate loading into mapping;
- Signal Shadow included in the reference-inspired candidate pool.

### Limitation

The existing local score is **not a reference-similarity score and not adversarial efficacy**.

Reference Fidelity v1 should replace generic visual ranking as the primary ranking signal for launch-capsule design selection while retaining the existing proxy as a secondary printability/complexity signal.

---

## 6. RAC Evidence and Certification Architecture

### Current State

The certification system has been substantially hardened. The project now explicitly enforces the ordered evidence chain:

```text
RAC-D0 → RAC-D1 → RAC-D2 → RAC-P1 → RAC-P2 → RAC-M1 → RAC-M2
```

The engineering constitution requires evidence integrity, fail-closed behavior, reproducibility, provenance, artifact hashes, adjacent state transitions, and strict separation between digital, physical, and manufacturing evidence.

Recent hardening work includes:

- rejecting evidence promotion by boolean flags alone;
- requiring bundled physical/manufacturing evidence for P1+ transitions;
- validating measurement domains and rejecting non-finite observations;
- requiring model provenance for measured digital evidence;
- requiring D1/D2 evidence provenance;
- validating pattern-manifest paths and commit provenance;
- containing artifact writes within bundle roots;
- preventing master-copy path traversal.

### Assessment

**Architecture: strong.**  
**Measured real-world certification coverage: incomplete by design.**

RAC-P and RAC-M must remain unavailable until actual physical and manufacturing evidence exists.

---

## 7. CI / Deployment

### Current `main`

`cf5d21c7276acad1e350df7511adec5626c1c700`

Latest change: `fix: prevent master-copy path traversal in CLI`.

### GitHub Pages

The explicit Pages deployment for the current head completed successfully.

### Python CI

Current CI is **red**.

Observed blockers:

- Python 3.10 / 3.11 / 3.12 test jobs stop at the **Lint** step, so downstream test, smoke-test, and certification-contract steps are skipped in those matrix jobs;
- `dependency-audit` fails at `pip-audit`;
- package build succeeds.

This means deployment can be healthy while the repository is **not globally CI-green**.

### CI Priority

Before calling the repo release-ready:

1. clear the lint gate;
2. inspect and resolve or explicitly triage the dependency-audit finding;
3. allow Python test / smoke / certification-contract jobs to execute fully;
4. retain frontend / Pages smoke coverage.

---

## 8. Production Readiness Assessment

| Layer | Status | Assessment |
| --- | --- | --- |
| Core pattern generation | ✅ | Mature |
| Canonical design families | ✅ | Implemented |
| Canonical product mapping | ✅ | Implemented |
| Reference-style boards | ✅ | Implemented, needs fidelity polish |
| Reference Fidelity v1 | ⏳ | Detailed implementation spec only |
| High-res master artwork | ✅ | Implemented |
| Generic panel mapper | ✅ | Implemented |
| Seam-aware mapping | ✅ | Implemented |
| Evidence-bound panel pack | ✅ | Implemented |
| Real POD template library | ❌ | External specs needed |
| Vendor-ready first SKU | ❌ | Blocked on real template + final mapping |
| First physical sample | ❌ | Not yet ordered / validated |
| RAC-D evidence bound to exact commercial SKU | ⚠️ | Architecture exists; final linkage remains |
| RAC-P evidence | ❌ | Requires physical testing |
| RAC-M evidence | ❌ | Requires production evidence |
| GitHub Pages | ✅ | Current explicit deployment succeeded |
| Repository-wide CI | ❌ | Lint + dependency audit blockers |

---

## 9. Revised Critical Path

### Priority 0 — Keep Engineering Ground Truth Green

- fix Python lint failures;
- resolve / triage `pip-audit` failure;
- ensure certification contract tests actually run on all supported Python versions.

### Priority 1 — Implement Reference Fidelity v1

Build the already-specified:

1. style profiles;
2. product composition zones;
3. guided composition renderer;
4. reference fidelity scorer;
5. Reference Match mode;
6. best-seed search and ranked shortlist.

**Success condition:** top-ranked candidates are consistently closer to the five canonical references than arbitrary seeds.

### Priority 2 — Produce One Real POD SKU

- select one provider/product;
- obtain exact template/spec;
- encode template in the adapter;
- map the winning canonical design;
- export exact panel pack;
- upload manually;
- order one sample.

### Priority 3 — Bind Evidence to the Exact SKU

- freeze artwork hash;
- freeze template hash;
- freeze mapping hash;
- attach measured RAC-D evidence only to that exact artifact set;
- preserve explicit `digital-only` scope.

### Priority 4 — Physical Feedback Loop

- inspect print scale, seams, color, crop, material behavior and construction;
- revise Studio/vender mapping assumptions;
- only then begin RAC-P protocol work.

---

## 10. Revised Overall Assessment

The project is **no longer primarily a research prototype**. It is becoming a reproducible apparel-design and evidence infrastructure platform.

The software side is strongest in:

- deterministic generation;
- evidence boundaries;
- reproducibility;
- technical export architecture;
- panel mapping;
- certification guardrails.

The two gaps that now matter most are:

1. **creative fidelity** — getting generated garments to look consistently as strong and deliberate as the supplied reference boards;
2. **physical grounding** — ingesting one real POD template and ordering the first sample.

The correct short-term objective is therefore not to add more garment families or more certification levels. It is:

> **Make the five canonical designs visually excellent, convert one into an exact provider-ready SKU, and close the loop with a real physical sample.**

That is the shortest path from the current repository to a credible commercial proof-of-concept.

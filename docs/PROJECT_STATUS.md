# Adversarial Clothing Pipeline — Project Status

**Date:** 2026-09-08  
**Repository:** `ninja-ops-guy/adversarial-clothing-pipeline`  
**Status basis:** current `main` (head ≥ `b4fe0e5`). For authoritative live completion tracking, use `docs/PROJECT_PROGRESS.md`; this document is the architecture/readiness narrative.

## Current-State Snapshot (2026-09-08)

Machine-readable-ish summary of every experiment, blocker, and user action. Narrative sections below remain the historical record; where they conflict, this table and `docs/PROJECT_PROGRESS.md` win.

### Experiments / generations

| ID | State | Detail |
| --- | --- | --- |
| RAC-PER-D2-0003 | **CLOSED — retained negative** | FAIL / RAC-D0; held-out 1.00 → 1.00 (n=36, PERSON-HO-v2); bundle verified; status archived byte-identical at `manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json` |
| RAC-PER-D2-0004 | **CLOSED — retained negative (log-attested)** | FAIL / RAC-D0; held-out 1.00 → 1.00 mean 0.99473 → 0.89599 (n=36, PERSON-HO-v3); CI run 34175028944 validated the bundle (steps 19–21) but never archived it (packaging step 22 schema-guard failure, infra fix 5cdce1b); closure rests on maintainer-uploaded logs per `docs/D2-0004_CLOSURE_NOTE.md`; sealed release `releases/RAC-EXP-2026-001/`; root `d2-latest-status.json` now carries this outcome |
| RAC-PER-D2-0005 | **PREREGISTERED — frozen, NOT armed, pending design decision** | Skeleton frozen (`lock_status: PREREGISTERED`, triggers not armed); gated on D2-0004 closing; F0 design analysis shows INCONCLUSIVE-dominated at n=72 → user must choose pre-arming design amendment vs exploratory/pilot declaration |
| RAC-PER-D2-0006 | **DRAFT — interpretation policy only** | `docs/PREREGISTRATION_D2-0006_DRAFT.md`; no generation file, no directional hypothesis, not a preregistration |
| P1 physical program | **Tooling READY — awaiting hardware/garments** | Calibration-target generator, rig spec/checklists, session/ingestion templates, frozen stopping rule RAC-P1-STOP-2026-001 (min 93 / max 144 valid trials) on main; synthetic dry-run only (non-evidence) |
| Production Alpha | **IN PROGRESS — externally blocked** | Printful product_id 388 resolved (fallback 257); template archive + v2 mapping auth-gated; `SKU_MANIFEST_DRAFT.json` has UNKNOWN fields; ordering is a user action |

### Open blockers

| Blocker | Blocking | Owner |
| --- | --- | --- |
| D2-0005 power/design decision (F0 finding) | D2-0005 arming | USER |
| Printful API token (`PF_TOKEN`) | template/printfile archive download, v2 catalog mapping | USER |
| Exact vendor template + panel geometry | SKU freeze, panel-pack validation | USER |
| Matched control/candidate garment order | calibration, P1, all physical evidence | USER |
| P1 rig hardware + calibration target print | W0 sessions, measured EOT | USER |
| RAC-P / RAC-M evidence | any physical/manufacturing claim | EXTERNAL |

### USER ACTION REQUIRED

1. Create Printful private API token and export `PF_TOKEN` (`production_alpha/ORDER_CHECKLIST.md` Step 0).
2. Download + SHA-256 the product-388 printfile/template archive; fill `SKU_MANIFEST_DRAFT.json` UNKNOWNs.
3. Place the matched control/candidate garment order (same variant/size for both arms).
4. Decide the D2-0005 pre-arming route: design amendment (§7/§9 of its preregistration) or exploratory/pilot declaration.

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

Reference Fidelity v1 is now implemented in the live Product Studio/Production Mapper path: explicit family style profiles, product-aware composition zones, guided multi-pass rendering, a deterministic 0–100 style scorer, Reference Match mode, Find Best Match, and fidelity-ranked batch generation. The next creative gap is empirical art-direction tuning against the canonical launch references, not missing framework code.

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

### Implemented

`docs/REFERENCE_FIDELITY_IMPLEMENTATION_SPEC.md` defines the next visual-quality milestone.

| Capability | Status |
| --- | --- |
| `studio-style-profiles.js` | ✅ Implemented |
| Explicit per-family palette ratios | ✅ |
| Product-specific hero zones | ✅ |
| Product-specific suppression / safe zones | ✅ |
| Guided multi-pass composition | ✅ |
| Named deterministic sub-seeds | ✅ |
| Composition analysis | ✅ |
| `reference-fidelity.js` scorer | ✅ |
| 0–100 reference fidelity score | ✅ |
| Reference Match vs Creative mode | ✅ |
| `Find Best Match` local seed search | ✅ |
| Fidelity-ranked batch generation | ✅ |
| Fidelity metadata in manifests | ✅ |

### Target Outcome

Reference Fidelity v1 has moved generation from:

> seeded visual family

into:

> seeded visual family + explicit style contract + garment-aware composition + measurable reference similarity

The framework milestone is complete; remaining work is empirical tuning and physical/product validation.

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

Reference Fidelity v1 is now the default creative ranking signal in Production Mapper. The legacy entropy/complexity/printability proxy remains available as a secondary ranking mode and is still explicitly non-certification data.

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

The repository has advanced materially beyond the historical baseline originally recorded in this document. The authoritative current ledger is `docs/PROJECT_PROGRESS.md`.

As of 2026-09-07, Research OS Waves A/B, P1 statistics, calibration ingestion, reporting, failure taxonomy, telemetry contracts and content-addressed releases are on `main`. Wave B was reported green at **168/168 tests** on the pushed tree.

### Active execution

D2-0004 is closed (FAIL / RAC-D0, log-attested; see `docs/D2-0004_CLOSURE_NOTE.md`). The published root `d2-latest-status.json` now carries the D2-0004 outcome; D2-0003's status is archived byte-identical under `manuscript/evidence/RAC-PER-D2-0003/`. The next gated decision is D2-0005 design (amendment vs pilot declaration) — it remains frozen and unarmed.

### CI / deployment rule

CI remains the authoritative software gate. Documentation should record the exact tested commit/run when making a release claim rather than preserving stale historical CI status in this narrative.

---

## 8. Production Readiness Assessment

| Layer | Status | Assessment |
| --- | --- | --- |
| Core pattern generation | ✅ | Mature |
| Canonical design families | ✅ | Implemented |
| Canonical product mapping | ✅ | Implemented |
| Reference-style boards | ✅ | Implemented, needs fidelity polish |
| Reference Fidelity v1 | ✅ | Implemented; empirical tuning remains |
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

### Priority 1 — Tune and Validate Reference Fidelity v1

The framework is implemented. Next: freeze canonical reference metrics, run deterministic seed sweeps across all five capsule families, compare top-ranked vs random seeds, and tune profile ranges/weights only through versioned changes.

**Success condition:** top-ranked candidates are consistently closer to the five canonical references than arbitrary seeds without degrading printability or reproducibility.

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

1. **creative calibration** — tuning the implemented reference-fidelity scorer and style profiles until ranked outputs consistently match the canonical boards;
2. **physical grounding** — ingesting one real POD template and ordering the first sample.

The correct short-term objective is therefore not to add more garment families or more certification levels. It is:

> **Make the five canonical designs visually excellent, convert one into an exact provider-ready SKU, and close the loop with a real physical sample.**

That is the shortest path from the current repository to a credible commercial proof-of-concept.


---

## Current Measured Digital Truth

Historical locked run: **RAC-PER-D2-0003** (`machine_static`) from source commit `65646777151966729ab6c06cdbdfe71671e5266d` (superseded as the published status by D2-0004 on 2026-09-08; its status file is archived byte-identical at `manuscript/evidence/RAC-PER-D2-0003/d2-latest-status.json`).

- Surrogate set: baseline detection rate 1.00 → candidate 0.7222 across 72 valid conditions.
- Held-out set (`PERSON-HO-v2`): baseline detection rate 1.00 → candidate 1.00 across 36 valid conditions.
- Model lock: verified / certification-eligible as a locked digital run.
- D2 certificate decision: **FAIL**; evidence state remains **RAC-D0**.
- Bundle verification: **PASS**.

This is useful negative evidence: the candidate reduced mean held-out confidence but did not cross the preregistered detection-rate criteria. It must not be described as D2-certified or as a physical garment result.

Latest closed run: **RAC-PER-D2-0004** from source commit `b4fe0e5942b56b7fffb8de6f1cb3172744269f59` (CI run 34175028944, 2026-09-08, log-attested per `docs/D2-0004_CLOSURE_NOTE.md`).

- Held-out set (`PERSON-HO-v3`): baseline detection rate 1.00 → candidate 1.00 across 36 valid conditions (mean confidence 0.99473 → 0.89599, mean_delta -0.09874).
- D2 certificate decision: **FAIL**; evidence state remains **RAC-D0**; bundle_verified true in CI.
- Sealed release: `releases/RAC-EXP-2026-001/`; root `d2-latest-status.json` carries this outcome.

This is a second retained negative under the newer PERSON-SUR-v3/HO-v3 contract: detection was not suppressed. It likewise must not be described as D2-certified or as a physical garment result.

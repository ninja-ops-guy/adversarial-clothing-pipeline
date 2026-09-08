# Production Completion Checklist

**Document ID:** PCC-2026-09-07-001
**Version:** 1.0.0
**Date:** September 7, 2026
**Classification:** Internal - Strategic
**Source:** Founder production memo, September 7, 2026
**Repository baseline:** `main` at `3497b4c`
**Companion documents:** `docs/PERPETUAL_IMPROVEMENT_MASTER.md` v1.2.0 (Part V-b), `PRODUCTION_READINESS.md`, `protocols/RAC-PHYSICAL-PRINT-TEST-1.0.md`

---

## Framing

The critical path to a physical product is now short and mostly **not software**. This checklist maps each production step against the repository that exists today, so status labels cannot drift ahead of reality.

**Status legend**

- **Done** — completed and evidenced in-repo
- **In progress** — actively running or partially implemented
- **Open (code)** — requires implementation work
- **Open (external)** — requires physical objects, providers, or lab work; code cannot close it

## Hard gates

| Gate | Definition |
|---|---|
| **Production Alpha** | One frozen design + one exact POD template + provider-accepted panel pack + ordered sample |
| **Production Beta** | Physical sample received + digital/physical calibration + matched control/candidate P1 experiment + revised production mapping |
| **Production v1** | Repeatable SKU + acceptable physical evidence + durability results + golden sample + lot-conformity tolerances + reviewed customer claims |

Current position: **close to Production Alpha; not close to a defensible RAC-P/M production claim** — nearly everything between Beta and v1 depends on real physical objects.

---

## Critical-path checklist

| # | Step | Status | Notes / repo linkage |
|---|---|---|---|
| 1 | **Close D2-0004.** Finish surrogate/adaptive selection, freeze one exact candidate, run the fresh held-out set once, retain the result regardless of PASS/FAIL, verify candidate SHA is identical across candidate → benchmark → Product Studio → print kit | **Done (2026-09-08)** | D2-0004 closed FAIL / RAC-D0, log-attested (authorized re-run 34175028944; candidate sha256 `9c8ae08d…c9e3803`); retained negative per the one-shot rule; `docs/D2-0004_CLOSURE_NOTE.md`; release `releases/RAC-EXP-2026-001/`. Note: the step-22 print-test-kit build failed on the schema guard (infra fix `5cdce1b`), so a D2-0004 print kit was never produced; the operative Production Alpha kit remains the sealed RAC-PER-D2-0003 kit (`production_alpha/SKU_MANIFEST.json`) |
| 2 | **Choose exactly one launch SKU** (oversized shirt or hoodie preferred: all-over-print geometry is simpler than structured caps). Define provider, garment model, fabric, sizes, print technology, SKU | **Open (external)** | Founder decision required; do not productionize six garments simultaneously |
| 3 | **Acquire the actual POD production template** — exact panel geometry, pixel dimensions, DPI, bleed, safe zones, template version | **Open (external)** | Single biggest external production blocker |
| 4 | **Encode the template into Production Mapper** — no guessed dimensions; validate seam continuity; export provider panel pack; hash artwork + template + mapping | **In progress** | Vendor-template import with provenance guard and continuity warnings exist; real provider template not yet imported |
| 5 | **Create the golden digital SKU manifest** binding design SHA, candidate generation, family, seed/spec, adaptation parameters, fidelity result, provider, product ID, template version, panel transforms, panel hashes, fabric/color profile, applicable RAC evidence | **In progress** | Manifest schema 1.4 binds design SHA/candidate/fidelity/frozen-tile metadata; provider/template/panel binding lands with #3–#4 |
| 6 | **Upload the exact pack to the POD provider** (manually first; API automation later). Compare provider preview against Product Studio and investigate discrepancies | **Open (external)** | Blocked on #3–#5 |
| 7 | **Order the first physical control/candidate pair** — matched control on the same garment, material, size, print process | **Open (external)** | Control pairing is mandatory, not optional |
| 8 | **Create the first print calibration target** — color patches, gradients, fine/high-frequency structures, rulers, registration markers, representative pattern fragments | **Open (code)** | Print-test kit produces production artifacts but not a metrology-grade calibration target; replaces the approximate printability proxy with measured digital→fabric error (PIM V-b #18, P0) |
| 9 | **Photograph/measure received garments** — print scale, placement, color shift, seam alignment, crop, registration, deformation, defects; feed back into calibration profile | **Open (external)** | First iteration of the digital-twin calibration loop (PIM V-b #19) |
| 10 | **Establish the P1 capture setup** — fixed camera identities, marked distances/angles/lighting/background/poses, control/candidate pairing, garment size, experimental metadata | **Open (external)** | Software contracts exist (`RAC-PHYSICAL-PRINT-TEST-1.0`); needs actual observations |
| 11 | **Run preregistered physical P1** — no threshold changes after seeing results; invalid conditions (control not reliably detected) marked invalid, never counted as candidate success | **Open (external)** | Invalid-condition rule already enforced in benchmark code (`invalid_condition_fraction`); same discipline applies physically |
| 12 | **Add uncertainty to certification** — confidence intervals, paired effect estimates, minimum sample-count rules | **Open (code)** | Matches PIM V-b #9; production certification must not rest on point thresholds alone |
| 13 | **Repeat across distance/angle/pose/lighting** — first physical response surface, not one ideal-camera result | **Open (external)** | Matches PIM V-b #6 (performance surfaces) |
| 14 | **Laundering/durability testing** — preregistered W0/W1/W5/W10 sequence; measure print/color/geometry degradation; rerun the same frozen physical evaluation | **Open (external)** | Matches PIM V-b #21, RQ-B-004/M-006; G3 gate |
| 15 | **Establish the golden physical sample** — hash/photograph/measure production artifacts of the first garment satisfying tolerances; designate RAC-M1 reference material | **Open (external)** | Blocked on #7–#9 |
| 16 | **Define production-lot tolerances** — color ΔE, scale error, placement error, registration error, seam mismatch, allowable defect rate | **In progress** | Conformity code provides the skeleton; tolerance values require manufacturing measurements |
| 17 | **Test multiple production samples** — establish whether POD variation is small enough that the digital master reliably reproduces the golden sample | **Open (external)** | Blocked on #15–#16 |
| 18 | **Reach RAC-M2 lot conformity** | **Open (external)** | Only after actual manufacturing measurements exist; the code cannot manufacture this evidence |
| 19 | **Freeze customer-facing claims** — three separated categories: aesthetic/design claims, measured digital results, measured physical results | **In progress** | PIM Part II claim ladder + FTC substantiation register (Part XII) provide the governance; claim text frozen only after G2–G4 evidence |
| 20 | **Launch QA** — checkout/order flow, sizing, returns, labeling, privacy/legal copy, accessibility, mobile, artifact backup, incident/revocation procedure, claim-withdrawal mechanism | **Open (code + external)** | Includes the ability to withdraw a product claim if later testing contradicts it |

---

## Next single action

Pick one POD provider and one exact garment SKU, obtain its real production template, map one frozen design, and order the control/candidate pair. **Further software work after that should be driven by what comes back in the mail.**

## Interaction with research governance

- No production claim may advance past the evidence label the underlying data actually carries (PIM Part II).
- "Worked on these two detectors under these conditions" never becomes "defeats surveillance" (PIM Part XII; `RESPONSIBLE_USE.md`).
- Production Alpha artifacts (template, panel pack, SKU manifest) enter the content-addressed artifact discipline (PIM V-b #24) from day one: hash everything, including failures.

---

## Document Control

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-09-07 | Initial checklist; 20-step critical path + Alpha/Beta/v1 gates mapped against repo state at 3497b4c |

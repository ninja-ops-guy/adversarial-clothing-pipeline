# Product Thesis & Public Evidence Standard

**Document ID:** PTS-2026-09-07-001
**Version:** 1.0.0
**Date:** September 7, 2026
**Classification:** Internal - Strategic
**Source:** Founder mission memo, September 7, 2026
**Repository baseline:** `main` at `9e77f24`
**Companion documents:** `docs/PERPETUAL_IMPROVEMENT_MASTER.md` v1.2.0, `docs/PRODUCTION_COMPLETION_CHECKLIST.md` v1.0.0, `RESPONSIBLE_USE.md`

---

## 1. Product thesis (foundational)

**Adversarial privacy apparel for ordinary people, backed by reproducible testing rather than vague "anti-surveillance" marketing.**

The mission is not diluted into generic computational fashion:

- The **fashion system** exists to make the protection wearable.
- The **research system** exists to determine whether it actually works.
- The **certification system** exists to stop the company from claiming more than the evidence supports.

### Foundational principle

> **RAC is willing to sell no efficacy claim rather than sell an unsupported one.**

D2-0003 failing its held-out evaluation is affirmative evidence that the architecture upholds this principle: the pipeline detected a surrogate-only effect that did not transfer, refused certification, and stayed RAC-D0. A system in which every garment miraculously passes would be less trustworthy, not more.

### The loop

```text
design → surrogate research → untouched evaluation → print →
physical validation → public evidence → independent challenge →
newly observed failures → next generation
```

The moat is not a secret pattern. It is the continually refreshed research, physical-validation dataset, manufacturing calibration, model-rotation methodology, and public evidence standard behind the clothing.

---

## 2. Priority directions, mapped to repo state

| # | Direction | Status | Linkage |
|---|---|---|---|
| 1 | **Broad robustness** — transfer across diverse legally obtained vision models, not one detector | In progress | SUR-v3 six-model ensemble; HO-v3 architecture rotation; RQ-A-002, RQ-F-001 |
| 2 | **Real-world robustness** — distance, resolution, compression, pose, body shape, size, stretch, folds, occlusion, day/night, weather, laundering as first-class dimensions | Partial | Protocol 1.2 sweeps; PIM V-b #6; RQ-B series; PCC #13–#14 |
| 3 | **Garment coverage research** — quantify contribution by surface (torso, shoulders, sleeves, legs, headwear, combinations, % visible patterned area) | Open | New RQ candidate (RQ-B-008); feeds protection profiles (#8 below) |
| 4 | **Coordinated outfits** — jointly optimized shirt/pants/hat ensembles vs independently optimized pieces | Open | New RQ candidate (RQ-H-006); more valuable than repeating one texture |
| 5 | **Camera-agnostic testing** — controlled physical camera matrix across resolutions, lenses, heights, distances; never design for a particular surveillance vendor | Open (external) | PCC #10/#13 |
| 6 | **Model-generation testing** — once a model observes a candidate, it is never held out for that lineage again | Implemented | D2-0003 → D2-0004 rotation executed; one-shot generation rule enforced in CI; PIM V-b #8 |
| 7 | **Failure disclosure** — publish where each generation does *not* work ("tested effect at 3–10 m under X; no demonstrated effect under Y") | Open | Extends Part II labels into public language; differentiator vs gimmick products |
| 8 | **Protection profiles** — evidence-backed categories (daylight/medium distance, low-resolution camera, high deformation, …); a garment earns only tested profiles | Open | Depends on #2/#3; natural RAC-P2 vocabulary |
| 9 | **Combination testing** — garments individually and as ensembles; customer-visible measured difference | Open | With #4 |
| 10 | **Accessibility / protection-per-dollar** — public product cannot cost $800; POD first, then manufacturing cost research | Open | PCC #2/#16–#18; manufacturing variance (V-b #22) |
| 11 | **Normal-looking options** — Pareto frontier between ordinary fashion and measured machine-vision robustness | Open | RQ-H-001/002; reference-fidelity system is the design-side instrument |
| 12 | **Durability guarantees** — communicate measured retention after specified wash cycles | Open (external) | RQ-B-004/M-006; PCC #14; G3 gate |
| 13 | **Open verification** — publish enough protocol for independent testing of purchased garments without contaminating future held-out sets | Open | Requires held-out hygiene by design; interacts with #6 |
| 14 | **Reproducible research releases** — freeze candidate SHA, model manifests, protocol, transforms, statistics, software version per generation | Partial | Evidence bundles + hash-bound artifacts exist; release packaging open (V-b #23–#24) |
| 15 | **Independent replication** — frozen garments to an independent university/privacy lab with no optimization involvement | Open (external) | Strongest external evidence tier; post-G2 |
| 16 | **Privacy education** — clothing addresses visual person detection only; gait, phones, plates, access records are different problems; never "universal invisibility" | Partial | `RESPONSIBLE_USE.md` scope language; public education content open |
| 17 | **Public failure bounty** — authorized researchers find conditions where a certified generation fails; failures feed next generations | Open (future) | Post-v1 maturity item |
| 18 | **Longitudinal model resistance** — retest certified garments against later model generations; quantify obsolescence rate | Open | RQ-F-004; uses #6 rotation archive |
| 19 | **Revocation** — superseded/invalidated claims are revoked, not quietly left on the website | Partial | Certificate lifecycle exists for D-states; public revocation mechanism open (PCC #20) |
| 20 | **Public evidence pages** — scan garment code → model/SKU, RAC state, manufacture date, tested conditions, CIs, limitations, wash state, protocol version, independent replications | Open | Depends on #7/#8/#12/#14; requires CIs (V-b #9) first |

---

## 3. Relationship to existing governance

- This document sets **why**; PIM v1.2.0 sets **what evidence counts**; the Production Completion Checklist sets **the order of physical execution**. Conflicts resolve in that order: thesis → evidence governance → execution plan.
- Every public-facing statement derives from the claim ladder (PIM Part II). Failure disclosure (#7) and revocation (#19) are not marketing choices; they are certification-system outputs.
- No protection profile, durability guarantee, or evidence page ships before the underlying measurement exists with uncertainty quantification.

---

## Document Control

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-09-07 | Initial thesis + 20 priority directions mapped against repo state at 9e77f24 |

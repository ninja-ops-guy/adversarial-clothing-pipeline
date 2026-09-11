# Adversarial Clothing Pipeline — Project Status

**Date:** 2026-09-11  
**Repository:** `ninja-ops-guy/adversarial-clothing-pipeline`  
**Status basis:** current `main`; canonical authority is [`CURRENT_PROGRAM_STATE.md`](CURRENT_PROGRAM_STATE.md).

This file is a concise narrative snapshot. It does not replace frozen contracts, preregistrations, closure evidence, or physical execution artifacts.

## Executive snapshot

RAC is now a mature experimental research/production platform rather than a pattern-generation prototype. The major software/integration barriers are closed for their declared scope, the evidence and governance layers are fail-closed, and the program has a controlled route from a frozen digital source into matched physical testing.

The remaining program bottleneck is **physical execution**, not missing core software.

## Current scientific state

| ID / surface | Current state | Meaning |
| --- | --- | --- |
| `RAC-PER-D2-0003` | **CLOSED NEGATIVE / RAC-D0** | Retained digital result; Alpha-001 remains bound here |
| `RAC-PER-D2-0004` | **CLOSED NEGATIVE / RAC-D0** | Retained and immutable |
| `RAC-PER-D2-0005` | **PREREGISTERED / NOT ARMED** | No arming from later work |
| `RAC-PER-D2-0007` | **CLOSED — SCREENED_OUT_H0** | 64/64 Stage-1 compositions evaluated, zero survivors, no downstream promotion |
| `RAC-PRINT-ALPHA-001` | **SOFTWARE-READY FOR LIVE VENDOR BINDING / PHYSICAL PRODUCTION** | Exact source recovered; production release tooling exists; no physical-efficacy result yet |
| P1 physical program | **OPEN — NOT EXECUTED** | Authoritative 144-trial schedule remains to be run with admissible specimens |
| P2 / M1 / M2 | **OPEN — EXTERNAL** | Durability and manufacturing evidence require physical data first |

## D2-0007 result

D2-0007 was deliberately structured as an earned-complexity experiment. Stage 1 screened eight motif families across eight compositions each on the frozen surrogate set.

The preregistered survivor rule required:

- mean absolute detection-rate reduction ≥ `0.15`;
- improvement on at least `4/6` surrogates;
- invalid-condition fraction ≤ `0.10`.

No motif met all criteria. Therefore the generation closed with:

```text
survivors = 0
admitted = 0
held-out access = false
anchor engineering = false
optimization opened = false
candidate freeze = false
Alpha-002 promotion = false
```

The authoritative closure is `evidence/d2-0007/stage1-screening-closure.json`.

## Alpha-001 production state

Alpha-001 remains scientifically bound to D2-0003. The exact historical source was recovered from GitHub Actions run `34078238095` and hash-verified against the frozen pins.

```text
sealed print-test-kit.zip
b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548

pattern_tile_4096.png
b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546
```

Recovery provenance is committed at `evidence/p1/alpha001-source-recovery.json`.

No regeneration, retuning, held-out access, or Alpha-001 rebinding was used to recover the source.

## Current production architecture

```text
Exact frozen Alpha-001 source
        ↓
Live Printful intake
        ↓
Vendor identity / placement / raw-byte verification
        ↓
Exact panel build + matched control
        ↓
Generated UA values
        ↓
Binder dry-run + controlled bind
        ↓
P1 no-spend readiness
        ↓
Human spend authorization
        ↓
Matched candidate/control order
        ↓
Receipt QA + custody
        ↓
Calibration acceptance
        ↓
Frozen 144-trial P1 capture
        ↓
Validated ingestion + sealed evidence
        ↓
Preregistered physical analysis
```

The canonical production software entry point is `tools/p1_production_release.py`.

## Current operator path

Use these documents in order:

1. [`P1_PRODUCTION_RELEASE_GATE.md`](P1_PRODUCTION_RELEASE_GATE.md)
2. [`P1_PRODUCTION_LAUNCH.md`](P1_PRODUCTION_LAUNCH.md)
3. [`USER_ACTION_NEXT_STEPS.md`](USER_ACTION_NEXT_STEPS.md)
4. [`../physical/p1/P1_OPERATOR_RUNBOOK.md`](../physical/p1/P1_OPERATOR_RUNBOOK.md)

The older 108-row Print Alpha planning material is historical. P1 execution is governed by the frozen 144-trial schedule and pairing/randomization contract.

## What is software-complete enough to move forward

- deterministic candidate/artwork generation;
- research/evidence separation;
- frozen contracts and generation isolation;
- surrogate/held-out boundary enforcement;
- negative-result retention;
- provenance and hash validation;
- content-addressed evidence/release infrastructure;
- P1 pairing/randomization/readiness package;
- live Printful intake and exact production-art build path;
- exact Alpha-001 source recovery;
- binder/readiness transition tooling;
- calibration-target generation;
- receipt-QA/custody/runbook infrastructure.

## What is still external

- choose actual garment size;
- use a live Printful token and retrieve current vendor data;
- bind the real vendor geometry/variants;
- authorize and place the matched order;
- physically fabricate the calibration target;
- receive and QA specimens;
- run accepted calibration;
- execute the frozen 144-trial P1 session;
- collect durability and manufacturing evidence later.

## CI / integrity state

The September 11 baseline before this documentation refresh was green across Python 3.10, 3.11, and 3.12, package build, dependency audit, lightweight provenance, and site deployment checks. Documentation changes remain subject to the same repository-wide CI/doclint gates.

## Evidence boundary

The repository is now **production-ready as a research platform**, not product-validated. No claim should imply that Alpha-001 or any other garment defeats arbitrary real-world surveillance or vision systems.

The next meaningful milestone is an admissible P1 physical result under the frozen matched-control protocol.

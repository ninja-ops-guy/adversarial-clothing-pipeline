# Production Completion Checklist

**Document ID:** PCC-2026-09-07-001  
**Version:** 1.1.1  
**Last updated:** 2026-09-11  
**Classification:** Internal — Strategic  
**Current authority:** `docs/CURRENT_PROGRAM_STATE.md` and frozen P1 execution surfaces outrank this checklist.

## Framing

The software path to physical testing is now substantially complete. The remaining critical path is dominated by **live vendor inputs, procurement, physical QA, calibration, and measured testing**.

Status language:

- **Done** — completed and evidenced in-repo.
- **Ready (software)** — implementation is complete enough to execute once real inputs exist.
- **Open (external)** — requires vendor, physical object, operator, or lab action.
- **Open (later evidence)** — cannot start validly until an earlier physical gate closes.

## Current production gates

| Gate | Current meaning | State |
| --- | --- | --- |
| **Production Alpha** | Exact frozen Alpha-001 source + live vendor-bound geometry + matched candidate/control order | **READY FOR LIVE VENDOR BINDING / procurement not yet complete** |
| **Production Beta** | Received QA-admissible specimens + calibration + authoritative P1 execution + sealed physical evidence | **OPEN — EXTERNAL** |
| **Production v1** | Repeatable SKU + physical/durability/manufacturing evidence + reviewed bounded claims | **OPEN — LATER EVIDENCE** |

## Critical-path checklist

| # | Step | Status | Current implementation / action |
| --- | --- | --- | --- |
| 1 | Preserve closed digital generations and scientific boundaries | **Done** | D2-0003 and D2-0004 retained negative; D2-0005 preregistered/unarmed; D2-0007 closed `SCREENED_OUT_H0` with zero survivors |
| 2 | Preserve exact Production Alpha source | **Done** | Original Alpha-001 sealed kit recovered from historical Actions run and hash-verified; `evidence/p1/alpha001-source-recovery.json` |
| 3 | Use one primary physical SKU | **Done (decision)** | Primary = Printful product `388`, All-Over Print Recycled Unisex Hoodie; product `257` retained as fallback/reserve metadata surface |
| 4 | Capture exact live vendor product/variant/placement data | **Ready (software) / Open (external input)** | `tools/p1_production_release.py intake` validates live data and stores untouched bytes + deterministic archives |
| 5 | Build exact provider-sized candidate/control artwork | **Ready (software)** | `tools/p1_production_release.py build` uses the exact recovered Alpha-001 source; no regeneration/retuning |
| 6 | Generate and validate UA values | **Ready (software)** | Production build emits binder-ready values; `tools/p1_bind_ua_values.py --check-only` is required before writing |
| 7 | Bind real production values and re-run no-spend readiness | **Ready (software) / Open (real inputs)** | Atomic binder + `tools/p1_no_spend_readiness_gate.py`; successful software gate does not authorize spend |
| 8 | Human procurement go/no-go | **Open (external)** | Verify hashes, matched pair, live variant/technique/fulfillment facts, then explicitly authorize cost |
| 9 | Order matched control/candidate hoodies | **Open (external)** | Minimum: `PA-HOODIE-CAND-001` + `PA-HOODIE-CTRL-001`; same production variables except artwork |
| 10 | Generate/fabricate calibration target | **Generator Done / Fabrication Open** | `RAC-CALT-P1-0001` deterministic generator exists; print at 100% / 300 DPI and physically verify 100 mm scale bar |
| 11 | Stage P1 rig and storage/custody workflow | **Software/spec Done / Physical setup Open** | Current runbook, camera-lighting setup, custody/QA forms, naming and storage rules exist |
| 12 | Receive and reconcile specimens | **Open (external)** | Receipt QA, pairing, registration, seams, defects, material/fulfillment facts, custody; mismatch blocks testing |
| 13 | Accept calibration under frozen rule | **Open (external)** | Calibrate before efficacy capture; threshold is not changed to make a failed setup pass |
| 14 | Execute matched physical P1 | **Open (external)** | Execute authoritative **144-trial** `physical/p1/P1_CAPTURE_SCHEDULE.json`, not historical 108-row planning sheet |
| 15 | Quantify uncertainty / stopping / invalid conditions | **Done as software; awaits real P1 data** | Paired statistics, uncertainty, stopping and invalid-condition infrastructure already exist |
| 16 | Ingest and seal P1 evidence | **Ready (software) / awaits data** | Preserve raw captures, dispositions, metadata and hashes; seal before preregistered analysis |
| 17 | Run preregistered physical analysis | **Open after P1** | Report PASS / FAIL / negative / inconclusive without post-hoc threshold changes |
| 18 | Run durability sequence | **Open (later evidence)** | W1/W5/W10+ only after a valid W0/P1 baseline |
| 19 | Establish golden physical sample + lot tolerances | **Open (later evidence)** | Requires real specimens and manufacturing measurements |
| 20 | Freeze bounded customer/public claims | **Open (later evidence)** | Claim scope cannot exceed actual digital/physical/manufacturing evidence |

## Exact Alpha-001 pins

```text
print-test-kit.zip
b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548

pattern_tile_4096.png
b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546
```

Any mismatch blocks the Production Alpha build. Do not recreate the pattern to work around a provenance failure.

## Current operator sequence

```text
Choose size + local Printful token
→ strict live intake
→ exact Alpha-001 build
→ operator review
→ binder --check-only
→ atomic bind
→ no-spend readiness PASS
→ separate human spend authorization
→ matched order
→ calibration-target fabrication
→ receipt QA / custody
→ calibration acceptance
→ frozen 144-trial P1
→ ingest + seal
→ preregistered analysis
```

See `docs/P1_PRODUCTION_RELEASE_GATE.md`, `docs/USER_ACTION_NEXT_STEPS.md`, and `physical/p1/P1_OPERATOR_RUNBOOK.md`.

## Next single action

Choose the actual size for the first Printful product-388 hoodie pair, use a local Printful token, and run the strict live vendor intake through `tools/p1_production_release.py intake`; do not authorize spend yet.

## Stop conditions

Stop before procurement or outcome collection if:

- a live vendor value would need to be guessed;
- product/variant/placement data conflicts with the production contract;
- the recovered Alpha-001 source hash fails;
- release gate, binder, or readiness verifier refuses;
- candidate/control matching is broken;
- a frozen scientific surface changes unexpectedly;
- receipt QA or calibration fails.

## Current evidence boundary

RAC is **production-ready as a research system**, not product-validated. Ordering or receiving a garment does not create RAC-P evidence. The next program-defining milestone is admissible matched P1 evidence.

## Document control

| Version | Date | Changes |
| --- | --- | --- |
| 1.0.0 | 2026-09-07 | Initial 20-step production checklist |
| 1.1.0 | 2026-09-11 | Reconciled D2-0007 closure, recovered Alpha-001 source, strict Printful release tooling, implemented calibration/statistics infrastructure, and frozen 144-trial P1 authority |
| 1.1.1 | 2026-09-11 | Restored the machine-readable `Next single action` heading used by the deterministic research-dashboard exporter |

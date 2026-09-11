# RAC Current Program State

**Document ID:** RAC-CURRENT-STATE-001  
**Status:** CANONICAL CURRENT-STATE NAVIGATION LAYER  
**Updated:** 2026-09-11 America/New_York  
**Reviewed head:** `8114e2189a255bed3d4c07708d7380c7ade2aefc`

This document is the fastest authoritative answer to **where the RAC program is now**. It does not replace frozen contracts, preregistrations, closure artifacts, independent audits, or hash-pinned evidence. It states current program-level status and points to those authorities.

> **Core rule:** engineering completion is not efficacy evidence. A software barrier can be closed while physical evidence remains open.

## Authority order

When documentation disagrees, use this order:

1. Frozen experiment / physical contracts and hash-pinned artifacts.
2. Immutable generation closure evidence and barrier-specific audit/handoff records.
3. This current-state navigation layer.
4. `PROJECT_PROGRESS_CURRENT.md` for detailed current workstream context.
5. Architecture / roadmap / operator guidance.
6. Older project-progress and planning documents as historical provenance.

For physical P1 execution, `physical/p1/P1_OPERATOR_RUNBOOK.md`, `physical/p1/P1_CAPTURE_SCHEDULE.json`, `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`, and `physical/p1/P1_READINESS_FREEZE.json` outrank older Print Alpha planning material.

## Program snapshot

| Surface | Current state | Meaning |
| --- | --- | --- |
| Engineering Barriers 0–3 | **CLOSED FOR DECLARED SCOPE** | Inventory, interface freeze, subsystem implementation, and synthetic end-to-end integration have documented exits |
| CTM / governance | **INTEGRATED / PASS FOR CLOSED PASSES** | Later research extensions remain audit-gated and additive |
| Pattern Genome v1 | **FROZEN** | No in-place scientific mutation permitted |
| D2-0003 | **CLOSED NEGATIVE / RAC-D0** | Retained result; Alpha-001 remains bound to this lineage |
| D2-0004 | **CLOSED NEGATIVE / RAC-D0** | Retained and immutable |
| D2-0005 | **PREREGISTERED / NOT ARMED** | No arming from P1 or D2-0007 work |
| D2-0007 | **CLOSED — SCREENED_OUT_H0** | 64/64 Stage-1 compositions evaluated, 0 survivors; downstream stages never opened |
| Alpha-001 frozen source | **EXACT SOURCE RECOVERED + HASH VERIFIED** | Historical sealed kit and 4096×4096 pattern recovered without regeneration |
| P1 production release software | **READY** | Live Printful intake, exact panel build, evidence-integrity verification, and UA-value generation exist |
| P1 no-spend readiness | **SOFTWARE-READY / FAIL-CLOSED** | Readiness/binding paths exist; real vendor values still need to be collected and bound |
| P1 physical capture | **OPEN — NOT EXECUTED** | No RAC-P physical efficacy evidence yet |
| P2 durability | **OPEN — EXTERNAL** | Requires a valid physical baseline first |
| M1/M2 manufacturing evidence | **OPEN — EXTERNAL** | Requires golden-sample and lot-conformity measurements |
| Product physical-efficacy claim | **NOT SUPPORTED** | Physical evidence ladder is not closed |

## Scientific lineage state

### D2-0003 / Alpha-001

`RAC-PER-D2-0003` remains a retained negative digital result. Its physical-production descendant, `RAC-PRINT-ALPHA-001`, remains bound to that lineage; no later generation replaces it.

The exact Alpha-001 source was recovered from successful historical GitHub Actions run `34078238095`. The recovery receipt is `evidence/p1/alpha001-source-recovery.json` and records:

- artifact ID `10003083548`;
- artifact digest `sha256:cfde12ec97ceafcf2d51eef989dee83d774e18be53e3f411c9502ed6a2e0e558`;
- sealed `print-test-kit.zip` SHA-256 `b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548`;
- frozen 4096×4096 pattern SHA-256 `b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546`;
- `source_regenerated=false` and `source_retuned=false`;
- no new held-out access, no Alpha-001 rebinding, and no physical-efficacy claim.

### D2-0007

`RAC-PER-D2-0007` is closed at Stage 1. The authoritative closure is `evidence/d2-0007/stage1-screening-closure.json`.

The preregistered Stage-1 screen evaluated all 64 planned compositions across the frozen eight-family motif pool on `PERSON-SUR-v3`. The survivor rule required at least 0.15 mean absolute detection-rate reduction, improvement on at least 4 of 6 surrogates, and invalid-condition fraction no greater than 0.10. No family met the full rule.

Consequences are therefore frozen and explicit:

- survivor count: **0**;
- admitted count: **0**;
- held-out access: **false**;
- body/garment anchor support built: **false**;
- optimization opened: **false**;
- candidate freeze created: **false**;
- Alpha-002 promoted: **false**;
- D2-0005 touched: **false**;
- Alpha-001 rebound: **false**.

The generation terminates as a useful screened-out null datapoint. Stage 2+ work is not authorized under D2-0007.

## Production Alpha transition

The current manufacturing target remains `RAC-PRINT-ALPHA-001`, using the exact recovered D2-0003 source.

The preferred real-production entry point is `tools/p1_production_release.py`. It wraps the lower-level preparation helper and fail-closes on:

- wrong Printful product identity;
- missing or unexpected production placements;
- malformed/error vendor responses;
- tampered raw-response bytes;
- mismatched deterministic vendor archives;
- mutated vendor-intake receipts;
- incorrect Alpha-001 sealed-kit or pattern hashes.

The current primary garment is Printful product `388` (All-Over Print Recycled Unisex Hoodie). Product `257` remains the fallback/reserve tee metadata surface where required by the production/binder contract.

The release gate does **not** authorize spend or place an order.

## Current P1 execution authority

Older Print Alpha planning material contains a 108-row capture plan. That is superseded for P1 execution.

The authoritative P1 execution package is:

- `physical/p1/P1_CAPTURE_SCHEDULE.json` — **144 frozen trials**;
- `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json` — pairing/randomization authority;
- `physical/p1/P1_OPERATOR_RUNBOOK.md` — specimen-arrival through sealed-evidence procedure;
- `physical/p1/P1_READINESS_FREEZE.json` — hash-pinned readiness surface;
- `tools/p1_no_spend_readiness_gate.py` — readiness verifier;
- `tools/p1_bind_ua_values.py` — fail-closed pending→real-value binder.

Do not execute an older 108-row planning sheet as the P1 protocol.

## CI / repository integrity state

At reviewed head `8114e2189a255bed3d4c07708d7380c7ade2aefc`, the current GitHub Actions checks completed successfully, including:

- Python 3.10 tests / smoke / certification-contract tests — PASS;
- Python 3.11 tests / smoke / certification-contract tests — PASS;
- Python 3.12 tests / smoke / certification-contract tests — PASS;
- package build — PASS;
- dependency audit — PASS;
- lightweight provenance — PASS;
- site build/deployment checks — PASS.

The immediately preceding production-release hardening run reported 2,132 passing tests, 2 skipped, before the documentation-only lint correction; the corrected cross-version run then completed green.

## Immediate critical path

The primary bottleneck is no longer missing software. It is real vendor and physical execution:

```text
Printful token + chosen size
  -> live vendor intake
  -> exact Alpha-001 panel build from recovered sealed source
  -> binder --check-only
  -> controlled UA bind
  -> no-spend readiness PASS
  -> separate human spend authorization
  -> matched candidate/control order
  -> calibration-target fabrication
  -> receipt QA + custody
  -> calibration acceptance
  -> frozen 144-trial P1 execution
  -> validated ingestion + sealed evidence
  -> preregistered analysis
```

Stop before spend or outcome collection if a required vendor value is unknown, the release gate or binder refuses, a hash mismatch appears, the readiness gate fails, candidate/control matching is broken, or a protected scientific surface changes unexpectedly.

## Current operator documentation

Use these in order:

1. `docs/P1_PRODUCTION_RELEASE_GATE.md` — strict production intake/build entry point.
2. `docs/P1_PRODUCTION_LAUNCH.md` — production launch handoff and recovery details.
3. `docs/USER_ACTION_NEXT_STEPS.md` — concise current operator path.
4. `physical/p1/P1_OPERATOR_RUNBOOK.md` — authoritative physical execution procedure after specimens exist.

## Historical-document policy

Historical preregistrations, closure notes, barrier handoffs, older project ledgers, and older Print Alpha plans are intentionally retained. Do not rewrite them to make history look cleaner. Current navigation documents should instead point to the newer authority and explicitly label superseded execution material.

## One-line program status

**RAC is software-ready to move Alpha-001 into controlled physical P1 production; D2-0007 closed as a screened-out null with no Alpha-002; the next program-defining milestone is admissible matched physical evidence, not additional ungated feature work.**

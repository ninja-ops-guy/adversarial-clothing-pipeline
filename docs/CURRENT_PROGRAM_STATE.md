# RAC Current Program State

**Document ID:** RAC-CURRENT-STATE-001  
**Status:** CANONICAL CURRENT-STATE NAVIGATION LAYER  
**Updated:** 2026-09-10 America/New_York (2026-09-11 UTC)  

This document is the fastest authoritative answer to **where the RAC program is now**. It does not replace frozen contracts, experiment records, barrier handoffs, or audit artifacts. Instead, it points to them and states the current program-level status without rewriting historical records.

> **Core rule:** engineering completion is not efficacy evidence. A software barrier may be closed while the corresponding physical evidence level remains open.

## Authority order

When documents appear to disagree, use this order:

1. Frozen experiment / physical contracts and hash-pinned artifacts.
2. Barrier-specific completion handoffs and independent audit reports.
3. This current-state ledger.
4. `PROJECT_PROGRESS_CURRENT.md` for detailed current workstream context.
5. `RAC_TECHNICAL_ROADMAP.md` for implementation history and forward roadmap.
6. Older project-progress, inventory, and planning documents as historical provenance.

For P1 execution specifically, `physical/p1/P1_OPERATOR_RUNBOOK.md`, `physical/p1/P1_CAPTURE_SCHEDULE.json`, `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`, and `physical/p1/P1_READINESS_FREEZE.json` outrank older Print Alpha planning documents.

## Barrier status

| Barrier | Purpose | Status | Exit evidence | Closing / reference state | Remaining blocker |
| --- | --- | --- | --- | --- | --- |
| **Barrier 0 — Inventory** | Establish gap analysis, acceptance matrix, ownership boundaries and dependency order before implementation | **CLOSED / DONE** | `RAC_WORLD_CLASS_GAP_ANALYSIS.md`, `RAC_TECHNICAL_ROADMAP.md`, `RAC_WORLD_CLASS_ACCEPTANCE_MATRIX.md`, `RAC_PARALLEL_SWARM_HANDOFF.md`, `artifacts/rac_deliverable_inventory.json` | Barrier-0 section of `RAC_PARALLEL_SWARM_HANDOFF.md` | None; retained as historical baseline |
| **Barrier 1 — Schema/interface freeze** | Freeze contracts so later lanes can evolve without silently redefining evidence or interfaces | **CLOSED / PASS** | 7 frozen contracts, additive evidence-class registry, 69 contract tests; independent RAC-G negative-case verification 21/21 | `bb3dad5` | None for declared Barrier-1 scope |
| **Barrier 2 — Parallel subsystem implementation** | Build Print Alpha, optimization, EOT, detector-science, Pareto/style and physical-transfer infrastructure | **CLOSED FOR DECLARED SOFTWARE SCOPE / INTEGRATED** | Barrier-2 appendix in `RAC_PARALLEL_SWARM_HANDOFF.md`; later CTM integration/hardening audit PASS | Original Barrier-2 lane series; later CTM hardening recorded in the same handoff | Real vendor/physical inputs still gate measured promotion; research extensions may continue additively |
| **Barrier 3 — End-to-end integration** | Prove the six-stage pipeline composes deterministically, preserves provenance, and fails closed | **CLOSED — PASS_WITH_NONBLOCKING_GAPS** | `BARRIER_3_COMPLETION_HANDOFF.md`, `artifacts/barrier3/`, `audits/RAC_G_BARRIER_3_AUDIT.md` | completion handoff at `b0e9e4a1…`; RAC-G final audit | Finite-difference audit remains conditional/deferred until a gradient-backed generation is actually in scope |

### Barrier 3 integrated path

`Optimization V3 → EOT → Detector Science → Pareto/Style → Printability → Physical Transfer`

Barrier 3 is a **synthetic integration proof**, not physical-efficacy evidence. RAC-G independently verified the package and issued `PASS_WITH_NONBLOCKING_GAPS`; the sole declared deferred check is finite-difference verification for a future gradient-backed path.

## Post-barrier execution state

The numbered engineering barriers are no longer the main bottleneck. The current critical path is the transition from software readiness to real physical evidence.

| Stage | Current status | Authority / evidence | What is still required |
| --- | --- | --- | --- |
| **CTM contracts / governance** | **INTEGRATED** | `PROJECT_PROGRESS_CURRENT.md`, `CTM_BD_INTEGRATION_AUDIT_2026-09-10.md`, CTM handoff appendices | Continue only evidence-justified extensions; do not mutate Pattern Genome v1 |
| **P1 no-spend readiness** | **CLOSED / PASS** | `docs/handoffs/P1_NO_SPEND_HANDOFF.md`, `physical/p1/P1_READINESS_FREEZE.json`, readiness gate | No additional software work required unless a real defect is found |
| **UA binding machinery** | **READY / REAL VALUES UNBOUND** | `tools/p1_bind_ua_values.py`, `physical/p1/UA_VALUES_TEMPLATE.json`, `tests/test_p1_ua_binding.py` | Obtain real UA-1–UA-8 values; `6b36dfe5` is the machinery-complete/unbound checkpoint |
| **Vendor / Production Alpha transition** | **BLOCKED ON EXTERNAL INPUT + HUMAN AUTHORIZATION** | Friday playbook in `docs/handoffs/P1_NO_SPEND_HANDOFF.md`; `docs/USER_ACTION_REQUIRED_PRINT_ALPHA.md` | Resolve vendor/template/SKU/order/calibration/arrival inputs; successful binding does not itself authorize spend |
| **Physical P1 capture** | **OPEN — NOT EXECUTED** | Frozen `P1_OPERATOR_RUNBOOK.md` and 144-trial `P1_CAPTURE_SCHEDULE.json` | QA-admissible physical specimens, accepted calibration, then execute the frozen 144-trial schedule |
| **P2 durability** | **OPEN — EXTERNAL** | durability / physical-program contracts | Requires valid physical baseline evidence first |
| **M1/M2 manufacturing evidence** | **OPEN — EXTERNAL** | manufacturing evidence contracts | Golden-sample and lot-conformity measurements |
| **Product physical-efficacy claim** | **NOT SUPPORTED** | certification/evidence rules | Requires the physical evidence ladder to close under preregistered rules |

## Current scientific state

| Surface | State |
| --- | --- |
| **Pattern Genome v1** | FROZEN; additive/versioned successors only |
| **D2-0004** | CLOSED — NEGATIVE / RAC-D0; retained and immutable |
| **D2-0005** | PREREGISTERED / NOT ARMED |
| **New held-out access** | NONE authorized by barrier, CTM, P1-readiness, or UA-binding work |
| **Scientific thresholds** | UNCHANGED by the barrier/readiness work described here |
| **Physical efficacy** | NOT ESTABLISHED |

## Current P1 execution authority

Older Print Alpha planning material contained a 108-row capture plan. That is **superseded for P1 execution** by the frozen readiness package. The authoritative P1 execution surface is now:

- `physical/p1/P1_CAPTURE_SCHEDULE.json` — **144 frozen trials** derived from the frozen pairing/randomization seed and pinned by `schedule_sha256`.
- `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json` — pairing/randomization authority.
- `physical/p1/P1_OPERATOR_RUNBOOK.md` — specimen-arrival through sealed-evidence procedure.
- `physical/p1/P1_READINESS_FREEZE.json` — hash-pinned readiness surface.
- `tools/p1_no_spend_readiness_gate.py` — fail-closed readiness verifier.
- `tools/p1_bind_ua_values.py` — fail-closed pending→real-value transition; it does not authorize spend.

Do not execute an older 108-row planning sheet as the P1 protocol.

## Immediate critical path

`Verified UA-1–UA-8 values → binder --check-only → atomic bind + receipt → readiness gate PASS → separate human spend authorization → procurement → specimen receipt/QA → calibration acceptance → frozen 144-trial P1 execution → validated ingestion → sealed evidence → preregistered analysis`

Stop if a real UA value is unknown, the binder refuses, the readiness gate fails, provenance cannot be reproduced, or a protected scientific boundary changes unexpectedly.

## Governance and research extensions

Governance Passes 1–2 are formally closed/verified in the current progress ledger. Later governance modules may exist, but their adopted-contract completion remains pass-specific and audit-gated unless a closure record says otherwise.

The noRecognition review is no longer wholly pending: NR-01, NR-02/03, and NR-04/05 implementation/audit work has landed as additive evidence-integrity and observation/reporting controls. NR-06 / predictor-provenance and any further research hypotheses remain prospective until their own evidence and exit criteria are satisfied.

## Reading map

- **Current state:** this file.
- **Detailed current workstreams / CI / governance:** `PROJECT_PROGRESS_CURRENT.md`.
- **Barrier 0–2 history and CTM hardening appendices:** `RAC_PARALLEL_SWARM_HANDOFF.md`.
- **Barrier 3 closure:** `BARRIER_3_COMPLETION_HANDOFF.md`.
- **Independent Barrier 3 audit:** `audits/RAC_G_BARRIER_3_AUDIT.md`.
- **P1 no-spend + Friday transition:** `handoffs/P1_NO_SPEND_HANDOFF.md`.
- **Implementation history / forward roadmap:** `RAC_TECHNICAL_ROADMAP.md`.

## One-line program status

**Engineering Barriers 0–3 are closed for their declared scope; P1 no-spend readiness and UA-binding machinery are ready; the next program-defining milestone is valid measured physical evidence, not more software completion.**

# RAC Documentation Index

**Last updated:** 2026-09-11 America/New_York

This page is the navigation layer for the RAC documentation stack. Frozen contracts, preregistrations, closure evidence, and physical execution artifacts outrank explanatory documentation.

## Start here

For a new technical reviewer, read in this order:

1. **[Current Program State](CURRENT_PROGRAM_STATE.md)** — canonical current status, scientific lineages, P1 state, authority order, and immediate critical path.
2. **[Root README](../README.md)** — executive thesis, current state, system identity, and physical-testing transition.
3. **[Current Project Progress Ledger](PROJECT_PROGRESS_CURRENT.md)** — detailed current workstream and closure ledger.
4. **[System Diagrams](DIAGRAMS.md)** — current topology, D2-0007 closure path, Alpha-001 production path, and P1 evidence flow.
5. **[Architecture](ARCHITECTURE.md)** — implementation planes and evidence boundaries.
6. **[Production Release Gate](P1_PRODUCTION_RELEASE_GATE.md)** — strict software entry point for live Printful intake and Alpha-001 production build.
7. **[User Action — Next Steps](USER_ACTION_NEXT_STEPS.md)** — current human operator path from software readiness to physical P1.
8. **[P1 Operator Runbook](../physical/p1/P1_OPERATOR_RUNBOOK.md)** — authoritative physical P1 execution procedure after specimens exist.
9. **[Certification System](CERTIFICATION_SYSTEM.md)** — fail-closed evidence transitions and promotion/refusal logic.
10. **[Historical Project Progress Ledger](PROJECT_PROGRESS.md)** — September 7–8 milestone history; preserved as provenance, not current authority.

## Authority and conflict rule

When documents disagree, use this order:

1. frozen experiment / physical contracts and hash-pinned artifacts;
2. immutable generation closure evidence and barrier-specific independent audits/handoffs;
3. [Current Program State](CURRENT_PROGRAM_STATE.md);
4. [Current Project Progress Ledger](PROJECT_PROGRESS_CURRENT.md);
5. architecture / operator / roadmap documentation;
6. older historical ledgers, preregistration-time status descriptions, and planning documents.

For physical P1 execution specifically, these are authoritative:

```text
physical/p1/P1_OPERATOR_RUNBOOK.md
physical/p1/P1_CAPTURE_SCHEDULE.json        # 144 frozen trials
physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json
physical/p1/P1_READINESS_FREEZE.json
tools/p1_no_spend_readiness_gate.py
tools/p1_bind_ua_values.py
```

The older 108-row Print Alpha planning sheet is historical only.

## Current status

- **Engineering Barriers 0–3:** closed for declared scope.
- **D2-0003:** retained negative / RAC-D0; Alpha-001 remains bound to this lineage.
- **D2-0004:** retained negative / RAC-D0.
- **D2-0005:** preregistered / not armed.
- **D2-0007:** closed at Stage 1 as `SCREENED_OUT_H0`; 64/64 compositions evaluated, 0 survivors, no anchors, optimization, candidate freeze, held-out access, or Alpha-002.
- **Alpha-001 source:** exact historical sealed source recovered and hash-verified; provenance at `evidence/p1/alpha001-source-recovery.json`.
- **P1 production software:** strict live Printful intake/build path implemented via `tools/p1_production_release.py`.
- **P1 physical evidence:** open; no efficacy claim is supported yet.

## Production / physical documentation

- **[P1 Production Release Gate](P1_PRODUCTION_RELEASE_GATE.md)** — canonical strict release wrapper for real vendor intake/build. **Status: current.**
- **[P1 Production Launch](P1_PRODUCTION_LAUNCH.md)** — detailed production handoff, exact Alpha-001 source pins, binding/readiness sequence. **Status: current.**
- **[User Action — Next Steps](USER_ACTION_NEXT_STEPS.md)** — current operator checklist. **Status: current.**
- **[P1 Operator Runbook](../physical/p1/P1_OPERATOR_RUNBOOK.md)** — specimen receipt → calibration → frozen 144-trial capture → ingestion/sealing. **Status: frozen / authoritative for execution.**
- **[P1 No-Spend Handoff](handoffs/P1_NO_SPEND_HANDOFF.md)** — earlier readiness/binder transition handoff. **Status: valid historical handoff; current operator flow is the documents above.**
- **[User Action Required — Print Alpha](USER_ACTION_REQUIRED_PRINT_ALPHA.md)** — earlier planning-era operator document containing superseded execution assumptions. **Status: historical provenance; do not use as P1 execution authority.**
- **[Production Readiness](../PRODUCTION_READINESS.md)** — current readiness gates and evidence boundary. **Status: current.**

## Scientific lineage documentation

- **[D2-0007 Preregistration](PREREGISTRATION_D2-0007.md)** — frozen prospective declaration. Its `NOT_ARMED` wording describes the state at freeze time and must not be rewritten post hoc.
- **[D2-0007 Amendment A1](PREREGISTRATION_D2-0007_AMENDMENT_A1.md)** — frozen pre-execution clarification.
- `evidence/d2-0007/stage0-landmark-free-smoke-closure.json` — Stage-0 PASS closure.
- `evidence/d2-0007/stage1-screening-closure.json` — authoritative Stage-1 screened-out closure and downstream prohibition state.
- **[D2-0005 Preregistration](PREREGISTRATION_D2-0005.md)** — frozen, not armed.
- **[D2-0004 Closure Note](D2-0004_CLOSURE_NOTE.md)** — retained negative D2-0004 closure.

A frozen preregistration may contain a historical status such as `NOT_ARMED` even after later execution/closure records exist. That is intentional provenance. Current status belongs in the closure evidence and current-state navigation files, not by rewriting the preregistration.

## Architecture and research system

- **[System Diagrams](DIAGRAMS.md)** — visual topology and current evidence/production paths. **Status: current.**
- **[Architecture](ARCHITECTURE.md)** — four-plane architecture, earned-complexity gating, production release, P1 authority. **Status: current.**
- **[Certification System](CERTIFICATION_SYSTEM.md)** — evidence ladder and fail-closed transitions. **Status: current unless a frozen contract says otherwise.**
- **[Engineering Constitution](ENGINEERING_CONSTITUTION.md)** — evidence integrity and reproducibility rules.
- **[Research Release Format](RESEARCH_RELEASE_FORMAT.md)** — content-addressed research-release contract.
- **[End-to-End Research SOP](END_TO_END_RESEARCH_SOP.md)** — broader research workflow; frozen/current P1 documents win if older production details conflict.

## Governance

- **[Experimental Governance v1](experimental_governance/RAC_EXPERIMENTAL_GOVERNANCE_V1.md)** — adopted prospective governance contract.
- **[Governance Roadmap](experimental_governance/ROADMAP.md)** — implementation/audit ordering.
- **[Pass 1 Closure](experimental_governance/PASS1_CLOSURE_2026-09-10.md)** — closed/verified.
- **[Pass 2 Closure](experimental_governance/PASS2_CLOSURE_2026-09-10.md)** — closed/verified.
- Later passes remain pass-specific and audit-gated unless their own closure evidence says otherwise.

## Historical / generated state notes

- **[Historical Project Progress Ledger](PROJECT_PROGRESS.md)** is a September 8 snapshot. Its old “single source of truth” language is superseded by this index and `CURRENT_PROGRAM_STATE.md`; the file itself is retained unchanged as historical provenance.
- `program_state/SUMMARY.md` is generated from its compiler's declared canonical inputs. Generation records are intentionally not rewritten after preregistration, so a lifecycle cell may reflect the frozen record while separate closure evidence carries a later scientific outcome. For D2-0007, the authoritative post-execution result is `evidence/d2-0007/stage1-screening-closure.json` and the current-state docs above.
- `PROJECT_STATUS.md` is now a concise current narrative and no longer serves as a competing authority.

## Important evidence boundary

Documentation describing implemented software does not imply a physical product has been validated. RAC-P/RAC-M remain unavailable until real physical/manufacturing evidence closes those gates. The next program-defining milestone is admissible matched P1 evidence.

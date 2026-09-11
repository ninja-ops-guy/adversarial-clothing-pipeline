# RAC Documentation Index

**Last updated:** 2026-09-10 America/New_York (2026-09-11 UTC)

This page is the navigation layer for the RAC documentation stack. Use the documents below according to their authority and purpose.

## Start here

For a new technical reviewer, read in this order:

1. **[Current Program State](CURRENT_PROGRAM_STATE.md)** — canonical Barrier 0–3 status, P1/UA state, physical-evidence critical path, and authority order.
2. **[Root README](../README.md)** — executive thesis, system identity and end-to-end flow.
3. **[System Diagrams](DIAGRAMS.md)** — topology, architecture, trust boundaries, evidence flow, production flow and research lifecycle.
4. **[Architecture](ARCHITECTURE.md)** — implementation planes, component responsibilities and evidence boundaries.
5. **[Certification System](CERTIFICATION_SYSTEM.md)** — fail-closed evidence transitions and promotion/refusal logic.
6. **[End-to-End Research SOP](END_TO_END_RESEARCH_SOP.md)** — operational design → benchmark → print → physical-validation workflow.
7. **[Current Project Progress Ledger](PROJECT_PROGRESS_CURRENT.md)** — detailed current completion state, governance/CI baseline and workstream status.
8. **[Historical Project Progress Ledger](PROJECT_PROGRESS.md)** — detailed Sep. 7–8 milestone and D2 closure history.
9. **[Manuscript Workspace](papers/README.md)** — pre-results papers explaining RAC research questions and methods.

## Authority and conflict rule

When documents disagree, use this order:

1. frozen experiment / physical contracts and hash-pinned artifacts;
2. barrier-specific completion handoffs and independent audit reports;
3. [Current Program State](CURRENT_PROGRAM_STATE.md);
4. [Current Project Progress Ledger](PROJECT_PROGRESS_CURRENT.md);
5. roadmap/planning documents;
6. older historical ledgers and inventory documents.

For physical P1 execution specifically, `physical/p1/P1_OPERATOR_RUNBOOK.md`,
`physical/p1/P1_CAPTURE_SCHEDULE.json`, `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`
and `physical/p1/P1_READINESS_FREEZE.json` outrank older Print Alpha planning material.
The current P1 execution schedule is **144 frozen trials**; the older 108-row planning
sheet is not the execution authority.

## Governance order

1. **[Product Thesis](PRODUCT_THESIS.md)** — why RAC exists, public-interest mission, evidence/claim philosophy.
2. **[Perpetual Improvement Master](PERPETUAL_IMPROVEMENT_MASTER.md)** — research governance, evidence labels, open questions and R&D roadmap.
3. **[Experimental Governance v1](experimental_governance/RAC_EXPERIMENTAL_GOVERNANCE_V1.md)** — prospective constraint-lineage, cohort-sealing, sampling, sentinel/bridge and adaptive-governance specification. **Status: prospective adopted contract; Passes 1–2 are closed/verified, later passes remain audit-gated unless a pass-specific closure says otherwise; frozen experiments are not retroactively mutated.**
4. **[Experimental Governance Roadmap](experimental_governance/ROADMAP.md)** — critical-first implementation sequence and authoritative pass-completion checklist; keeps current physical/POD work ahead of lower-priority infrastructure.
5. **[Seven Implementation Passes](experimental_governance/IMPLEMENTATION_PASSES.md)** — pass-by-pass deliverables, tests and exit gates for Governance v1.
6. **[Pass 1 Closure](experimental_governance/PASS1_CLOSURE_2026-09-10.md)** — adopted Governance Core closure, verified by CI #821.
7. **[Pass 2 Closure](experimental_governance/PASS2_CLOSURE_2026-09-10.md)** — adopted Constraint Lineage closure, verified by CI #836.
8. **[Production Completion Checklist](PRODUCTION_COMPLETION_CHECKLIST.md)** — execution order and Production Alpha/Beta/v1 gates.
9. **[Current Project Progress Ledger](PROJECT_PROGRESS_CURRENT.md)** — detailed current completion status, verified baseline and active gates.

## Current status

- **[Current Program State](CURRENT_PROGRAM_STATE.md)** — recommended first source for current RAC status; Engineering Barriers 0–3 are closed for their declared scope, P1 no-spend readiness is PASS, and UA binding is ready but real values remain unbound.
- **[P1 No-Spend Handoff / Friday Playbook](handoffs/P1_NO_SPEND_HANDOFF.md)** — frozen-readiness handoff plus UA binding/vendor transition procedure.
- **[Current Project Progress Ledger](PROJECT_PROGRESS_CURRENT.md)** — detailed RAC/CTM state and physical critical path.
- **[Barrier 0–2 / CTM Swarm Handoff](RAC_PARALLEL_SWARM_HANDOFF.md)** — historical Barrier 0–2 implementation record plus CTM hardening appendices.
- **[Barrier 3 Completion Handoff](BARRIER_3_COMPLETION_HANDOFF.md)** — closed deterministic six-stage integration package.
- **[Independent Barrier 3 Audit](audits/RAC_G_BARRIER_3_AUDIT.md)** — `PASS_WITH_NONBLOCKING_GAPS`; finite-difference verification remains conditional on a future gradient-backed path.
- **[Experimental Governance Roadmap](experimental_governance/ROADMAP.md)** — Passes 1–2 closed; later passes audit-gated unless independently closed.
- **[Historical Project Progress Ledger](PROJECT_PROGRESS.md)** — detailed Sep. 7–8 milestone history; preserved rather than rewritten retroactively.
- **[CTM B–D Integration Audit](CTM_BD_INTEGRATION_AUDIT_2026-09-10.md)** — closed PASS audit for the September 10 integration/hardening cycle.
- **[Project Status](PROJECT_STATUS.md)** — architecture/readiness narrative; historical sections may lag the current-state files above.
- **[Production Readiness](../PRODUCTION_READINESS.md)** — fail-closed technical/product readiness gates.
- **[Research Evidence Register](RESEARCH_EVIDENCE_REGISTER.md)** — evidence/source register.

## Architecture and research system

- [System Diagrams](DIAGRAMS.md) — visual topology of the four-plane system, candidate-generation path, held-out trust boundary, evidence lifecycle, fail-closed certification, digital-to-physical translation, provenance graph and feedback loop. **Status: current.**
- [Architecture](ARCHITECTURE.md) — four-plane system architecture and component responsibilities. **Status: current.**
- [Certification System](CERTIFICATION_SYSTEM.md) — RAC evidence ladder and fail-closed transitions. **Status: current.**
- [Engineering Constitution](ENGINEERING_CONSTITUTION.md) — evidence-integrity, reproducibility and provenance rules. **Status: current.**
- [Research Release Format](RESEARCH_RELEASE_FORMAT.md) — content-addressed RAC-EXP release contract. **Status: current.**
- [Paper Series Plan](PAPER_SERIES.md) — research manuscript plan. **Status: current.**
- [Manuscript Workspace](papers/README.md) — active pre-results paper drafts, including system-architecture and evidence-certification papers. **Status: draft (pre-results).**
- [CAPGen Integration](CAPGEN_INTEGRATION.md) — environment-adaptive generation inspired by CAPGen (no vendored AGPL code). **Status: current.**

## Preregistrations, amendments and analyses

- [Preregistration D2-0005](PREREGISTRATION_D2-0005.md) — frozen mean-vs-CVaR two-arm ablation preregistration with amendments A1–A4 (§9 log); frozen, NOT armed; its D2-0004 gate is satisfied but arming still requires its own authorized governance decision. **Status: current (preregistered, unarmed).**
- [Design Analysis D2-0005](DESIGN_ANALYSIS_D2-0005.md) — pre-arming operating-characteristics simulation. **Status: analysis only; no outcome data.**
- [Preregistration D2-0006 DRAFT](PREREGISTRATION_D2-0006_DRAFT.md) — predeclared interpretation-policy decision tree for the prospective replication generation. **Status: draft — not a preregistration; arms nothing.**
- [Amendment D2-0004-INFRA-001](AMENDMENT_D2-0004_INFRA-001.md) — infrastructure-only amendment consumed by the D2-0004 closure. **Status: consumed.**
- [D2-0004 Closure Note](D2-0004_CLOSURE_NOTE.md) — canonical narrative of the retained FAIL / RAC-D0 closure. **Status: current.**
- [Ingest Notes](INGEST_NOTES.md) — `ingest_closed_generation.py` field-mapping notes for converting a closed D2 generation into a RAC-EXP release. **Status: current.**

## Design / production

- [Product Studio](PRODUCT_STUDIO.md) — design factory / studio feature documentation. **Status: current.**
- [Reference Fidelity Implementation Spec](REFERENCE_FIDELITY_IMPLEMENTATION_SPEC.md) — Reference Fidelity v1 style profiles and scorer spec. **Status: current (framework implemented; empirical tuning open).**
- [Production Alpha SKU](PRODUCTION_ALPHA_SKU.md) — first-SKU decision/spec and provider-specific production path. **Status: current.**
- [User Action Required — Print Alpha](USER_ACTION_REQUIRED_PRINT_ALPHA.md) — current human/vendor sequence; binder-owned fields are resolved through `RAC-P1-UA-BINDER-001`, and P1 capture follows the frozen 144-trial schedule. **Status: current.**

## Operating procedures

- [End-to-End Research SOP](END_TO_END_RESEARCH_SOP.md) — full design → D2 → production → calibration → P1 → durability → manufacturing → paper workflow. **Status: current.**
- [Printful Production Alpha SOP](PRINTFUL_PRODUCTION_SOP.md) — matched control/candidate ordering and provenance procedure; frozen P1 execution surfaces win if any older capture-planning detail conflicts. **Status: production procedure.**
- [Experiment Pickup Guide](EXPERIMENT_PICKUP_GUIDE.md) — short resume-from-here checklist for each project state. **Status: current.**

## Physical program

- [P1 No-Spend Handoff / Friday Playbook](handoffs/P1_NO_SPEND_HANDOFF.md) — no-spend readiness PASS, UA binder transition and stop rules. **Status: current.**
- [P1 Operator Runbook](../physical/p1/P1_OPERATOR_RUNBOOK.md) — frozen specimen-arrival → calibration → 144-trial capture → ingestion → sealed-evidence procedure. **Status: frozen / authoritative for P1 execution.**
- [Capture Lab](CAPTURE_LAB.md) — sequential camera capture, matched control/candidate workflow, analysis contract and session sealing. **Status: current UI/workflow documentation; frozen P1 runbook controls the scientific execution sequence.**
- [Physical Test Infrastructure](PHYSICAL_TEST_INFRASTRUCTURE.md) — calibration target + P1 capture rig protocol specification. **Status: draft / partially superseded by frozen P1 assets.**
- [Calibration Target Spec](CALIBRATION_TARGET_SPEC.md) — calibration target specification. **Status: current.**
- [P1 Capture Rig Spec](P1_CAPTURE_RIG_SPEC.md) — capture rig hardware/geometry specification. **Status: current.**

## Important evidence boundary

Documentation describing implemented software does not imply a physical product has been validated. Engineering Barriers 0–3 and P1 no-spend readiness can be closed while physical efficacy remains unproven. The authoritative current program map is [CURRENT_PROGRAM_STATE.md](CURRENT_PROGRAM_STATE.md), with details in [PROJECT_PROGRESS_CURRENT.md](PROJECT_PROGRESS_CURRENT.md). RAC-P/RAC-M remain unavailable until real evidence closes those gates; older ledgers are retained as historical provenance.

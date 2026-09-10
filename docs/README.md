# RAC Documentation Index

**Last updated:** 2026-09-09

This page is the navigation layer for the RAC documentation stack. Use the documents below according to their authority and purpose.

## Start here

For a new technical reviewer, read in this order:

1. **[Root README](../README.md)** — executive thesis, system identity and end-to-end flow.
2. **[System Diagrams](DIAGRAMS.md)** — topology, architecture, trust boundaries, evidence flow, production flow and research lifecycle.
3. **[Architecture](ARCHITECTURE.md)** — implementation planes, component responsibilities and evidence boundaries.
4. **[Certification System](CERTIFICATION_SYSTEM.md)** — fail-closed evidence transitions and promotion/refusal logic.
5. **[End-to-End Research SOP](END_TO_END_RESEARCH_SOP.md)** — operational design → benchmark → print → physical-validation workflow.
6. **[Project Progress Ledger](PROJECT_PROGRESS.md)** — authoritative current completion state.
7. **[Manuscript Workspace](papers/README.md)** — pre-results papers explaining RAC research questions and methods.

## Governance order

1. **[Product Thesis](PRODUCT_THESIS.md)** — why RAC exists, public-interest mission, evidence/claim philosophy.
2. **[Perpetual Improvement Master](PERPETUAL_IMPROVEMENT_MASTER.md)** — research governance, evidence labels, open questions and R&D roadmap.
3. **[Production Completion Checklist](PRODUCTION_COMPLETION_CHECKLIST.md)** — execution order and Production Alpha/Beta/v1 gates.
4. **[Project Progress Ledger](PROJECT_PROGRESS.md)** — current completion status, completed work and active tasks.

## Current status

- **[Project Progress Ledger](PROJECT_PROGRESS.md)** — recommended source for current state.
- **[Project Status](PROJECT_STATUS.md)** — architecture/readiness narrative; historical sections may lag the ledger.
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

- [Preregistration D2-0005](PREREGISTRATION_D2-0005.md) — frozen mean-vs-CVaR two-arm ablation preregistration with amendments A1–A4 (§9 log); frozen, NOT armed; its D2-0004 gate is satisfied but arming still awaits the pending F0 design decision. **Status: current (preregistered, unarmed).**
- [Design Analysis D2-0005](DESIGN_ANALYSIS_D2-0005.md) — pre-arming operating-characteristics simulation; F0 finding: INCONCLUSIVE-dominated at n=72; pending design decision. **Status: current (analysis; no outcome data).**
- [Preregistration D2-0006 DRAFT](PREREGISTRATION_D2-0006_DRAFT.md) — predeclared interpretation-policy decision tree for the prospective replication generation. **Status: draft — not a preregistration; arms nothing.**
- [Amendment D2-0004-INFRA-001](AMENDMENT_D2-0004_INFRA-001.md) — infrastructure-only amendment consumed by the D2-0004 closure. **Status: consumed.**
- [D2-0004 Closure Note](D2-0004_CLOSURE_NOTE.md) — canonical narrative of the retained FAIL / RAC-D0 closure. **Status: current.**
- [Ingest Notes](INGEST_NOTES.md) — `ingest_closed_generation.py` field-mapping notes for converting a closed D2 generation into a RAC-EXP release. **Status: current.**

## Design / production

- [Product Studio](PRODUCT_STUDIO.md) — design factory / studio feature documentation. **Status: current.**
- [Reference Fidelity Implementation Spec](REFERENCE_FIDELITY_IMPLEMENTATION_SPEC.md) — Reference Fidelity v1 style profiles and scorer spec. **Status: current (framework implemented; empirical tuning open).**
- [Production Alpha SKU](PRODUCTION_ALPHA_SKU.md) — first-SKU decision/spec and provider-specific production path. **Status: current.**

## Operating procedures

- [End-to-End Research SOP](END_TO_END_RESEARCH_SOP.md) — full design → D2 → production → calibration → P1 → durability → manufacturing → paper workflow. **Status: current.**
- [Printful Production Alpha SOP](PRINTFUL_PRODUCTION_SOP.md) — exact matched control/candidate ordering and provenance procedure. **Status: current.**
- [Experiment Pickup Guide](EXPERIMENT_PICKUP_GUIDE.md) — short resume-from-here checklist for each project state. **Status: current.**

## Physical program

- [Capture Lab](CAPTURE_LAB.md) — sequential camera capture, matched control/candidate workflow, analysis contract and session sealing. **Status: current.**
- [Physical Test Infrastructure](PHYSICAL_TEST_INFRASTRUCTURE.md) — calibration target + P1 capture rig protocol specification. **Status: draft / partially superseded by frozen P1 assets.**
- [Calibration Target Spec](CALIBRATION_TARGET_SPEC.md) — calibration target specification. **Status: current.**
- [P1 Capture Rig Spec](P1_CAPTURE_RIG_SPEC.md) — capture rig hardware/geometry specification. **Status: current.**

## Important evidence boundary

Documentation describing implemented software does not imply a physical product has been validated. The authoritative physical/product state is tracked in [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md), and RAC-P/RAC-M remain unavailable until real evidence closes those gates.

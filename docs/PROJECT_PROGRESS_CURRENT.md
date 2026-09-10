# RAC Current Project Progress Ledger

**Version:** 1.1.0  
**Last updated:** 2026-09-10  
**Verified code baseline:** `main` at `d7eed338e404dc287cce416147523dd37828112e` — CI run #821 (`34515747476`) PASS.  
**Authority:** This file is the current-state overlay for RAC/CTM. `PROJECT_PROGRESS.md` remains the historical Sep. 8 ledger and is not rewritten retroactively.

> Engineering completion is not efficacy evidence. Software, schemas, simulations, governance, and CI can be complete while RAC-P physical evidence, RAC-M manufacturing evidence, or a product-efficacy claim remain unavailable.

## Executive state

RAC is now best described as a research and experimental-governance platform spanning design generation, controlled evaluation, provenance, claim certification, production preparation, and a gated physical program.

The September 10 CTM integration/hardening cycle is **software-integrated and CI-green**. Governance Pass 1 is now **CLOSED / PASS** against the adopted Governance v1 contract. That does **not** advance the physical-evidence ladder. The next high-value work should remain evidence-driven rather than feature-count-driven.

## Current completion snapshot

| Workstream | Current state | Meaning |
| --- | --- | --- |
| Core research software | **ADVANCED / INTEGRATED** | Design, optimization, evaluation, reporting, provenance and certification primitives are present |
| CTM contracts / governance | **INTEGRATED** | CTM contract surfaces, matched-null logic, anti-optimization controls, channel/claim semantics and research-integrity layers are implemented and reconciled |
| CTM B–D integration audit | **PASS** | Semantic mismatches found during audit were corrected; the historical Barrier-3 blocker is resolved and retained only as provenance |
| Governance Pass 1 | **CLOSED / PASS** | Adopted IDs, append-only ledger, ledger-backed state transitions, structured HALT, schemas and semantic validation are CI-verified |
| Governance Passes 2–7 | **AUDIT-GATED** | Later-pass modules may already exist, but code presence is not pass certification until each adopted-contract exit gate is independently closed |
| Provenance graph | **CURRENT / VERIFIED** | Deterministic graph is committed and independently verifiable; regeneration no longer requires the ML runtime |
| Repository CI | **GREEN** | Run #821 passed Python 3.10/3.11/3.12, package build, dependency audit and lightweight provenance |
| Pattern Genome v1 | **FROZEN** | v1 remains unchanged; later Genome work must be additive/versioned |
| D2-0004 | **CLOSED — NEGATIVE / RAC-D0** | Historical retained result remains immutable and log-attested |
| D2-0005 | **PREREGISTERED / NOT ARMED** | No arming occurred during CTM/governance hardening or CI work |
| Production Alpha | **IN PROGRESS / EXTERNAL DEPENDENCIES REMAIN** | Provider/template/order steps remain outside software completion |
| P1 physical evidence | **OPEN — EXTERNAL** | No software or CI change substitutes for matched physical testing |
| P2 durability evidence | **OPEN — EXTERNAL** | Requires real durability/wash evidence |
| M1/M2 manufacturing evidence | **OPEN — EXTERNAL** | Requires golden-sample and lot-conformity measurements |
| Product efficacy claim | **NOT SUPPORTED** | Claims must remain scoped to evidence actually obtained |

## September 10 CTM hardening closure

### Completed and mechanically enforced

- [x] CTM matched-property null contracts remain fail-closed.
- [x] Anti-optimization / held-out provenance firewall remains enforced.
- [x] Factor-swap validity semantics are represented explicitly.
- [x] Scalar values have typed epistemic/analysis semantics rather than implicit coercion.
- [x] Optimizer-imposed structure is kept in generation provenance rather than mutating Pattern Genome v1.
- [x] Camera / ISP / channel identity is a first-class validity dimension.
- [x] Target/mechanism semantics distinguish architecture accidents from broader mechanism classes.
- [x] Evaluation-surface / Goodhart-relevant configuration is part of experiment semantics.
- [x] Claim scope is structurally tied to pipeline stage rather than relying only on prose linting.
- [x] Citation/corpus/positioning infrastructure supports bounded literature claims and verification status.
- [x] Retrospective mining decisions are metadata/provenance-aware and sealed decisions are re-derived during verification.
- [x] External physical cohorts remain secondary evidence and cannot silently promote into controlled CTM physical efficacy.
- [x] CTM B–D integration audit is closed as PASS in `CTM_BD_INTEGRATION_AUDIT_2026-09-10.md`.

### Explicitly deferred

- [ ] Pattern Genome v2 candidate expansion — **deferred until its evidence gate justifies promotion**.
- [ ] `defense_dual` heuristic lifecycle — **deferred until the CTM-F heuristic-promotion lifecycle is active**.

These deferred items are not current integration blockers.

## Governance Pass 1 closure

Governance Pass 1 is formally closed in `experimental_governance/PASS1_CLOSURE_2026-09-10.md`.

The closure corrected prototype/adopted-contract drift without rewriting historical prototype records:

- [x] new IDs emit canonical Governance v1 forms such as `RAC-GOV-EVT-*`, `RAC-COHORT-*`, `RAC-SAMP-*`, `RAC-CS-*`, `RAC-OVERLAP-*` and `RAC-DIAG-*`;
- [x] legacy abbreviated IDs remain read-compatible aliases but map to the same semantic identity;
- [x] event payloads and event metadata are separately SHA-256 bound and previous-event chained;
- [x] reversal/supersession semantics are append-only;
- [x] lifecycle state is read-only outside the governance state machine;
- [x] every legal transition writes a governance event before changing state;
- [x] generic HALT bypass is unavailable; HALT requires a structured invariant-conflict event;
- [x] canonical identifiers are accepted consistently by Python semantic validation and JSON Schema;
- [x] adopted-contract tests cover happy-path completion, structured HALT, tamper detection, alias collision, invalid references and anti-bypass behavior.

A Pass-6 sampling/diagnostics merge landed during this hardening cycle and was preserved. CI #821 therefore verifies the Pass-1 closure together with that merged sampling layer. Pass 6 itself remains roadmap-open until a pass-specific audit verifies all of its adopted exit criteria.

## CI / reproducibility state

### Authoritative verification

GitHub Actions CI run #821 at `d7eed338e404dc287cce416147523dd37828112e` completed successfully across all six jobs:

- Python 3.10 — PASS
- Python 3.11 — PASS
- Python 3.12 — PASS
- package build — PASS
- dependency audit — PASS
- lightweight provenance — PASS

The Python 3.11 repository-wide run reported **1,638 passed, 2 skipped, 16 warnings**, followed by **12/12 certification-contract tests passed** and a passing smoke test. Ruff passed.

### Infrastructure hardening completed

- [x] Top-level `ruthless_pipeline` convenience exports are lazy-loaded while preserving the existing public API.
- [x] Provenance generation/verification can run from the repository source tree without installing Torch, torchvision, NumPy, SciPy or Pillow.
- [x] CI has a zero-install provenance/import-boundary gate.
- [x] Regression tests prevent accidental eager reintroduction of the ML dependency stack at package import time.
- [x] Hosted CPU CI installs CPU-only PyTorch wheels and asserts `torch.version.cuda is None` rather than downloading the CUDA runtime stack.
- [x] Full package requirements remain unchanged by the CI optimization.

## Scientific invariants preserved during hardening

The September 10 integration/governance/CI work did **not**:

- modify Pattern Genome v1;
- arm D2-0005;
- introduce new held-out access;
- alter scientific thresholds or decision-rule values;
- convert exploratory evidence into controlled evidence;
- execute P1 physical work;
- create RAC-P or RAC-M evidence;
- make a physical-efficacy or broad surveillance-evasion claim.

## Immediate next work

### Software / research work that can proceed without physical evidence

- [ ] Audit Governance Pass 2 against its adopted contract and close only the requirements actually demonstrated by code/tests.
- [ ] Continue the same pass-by-pass audit for Passes 3–6; do not infer completion from namespace presence.
- [ ] Keep Pass 7 adaptive/chaos lifecycle deferred until multiple sealed waves or an actual experimental need justify it.
- [ ] Keep manuscript/corpus exports synchronized with integrated CTM schemas and bounded-claim rules.
- [ ] Continue prospective evidence collection through preregistered research questions rather than generic optimization.
- [ ] Keep Genome v2 and heuristic-promotion work behind their declared gates rather than expanding representation prematurely.

### External / physical critical path

These remain the project’s primary evidence bottleneck:

- [ ] Resolve exact POD provider/product/variant/template inputs.
- [ ] Freeze the exact first-SKU production template and provenance.
- [ ] Produce/order matched control and candidate garments.
- [ ] Produce the calibration target through the same physical process.
- [ ] Complete the real capture-rig rehearsal/preregistration requirements.
- [ ] Execute matched P1 physical sessions.
- [ ] Ingest measured calibration/channel evidence.
- [ ] Begin durability/wash cohorts only after a valid W0 physical artifact exists.
- [ ] Establish M1 golden-sample and M2 lot-conformity evidence before manufacturing claims.

## Operating rule

**Prioritize closed evidence loops over new feature count.**

The software platform is sufficiently elaborate that additional infrastructure should now be justified by a concrete validity, reproducibility, measurement, or publication need. Physical efficacy remains unproven until the physical evidence ladder is actually executed.

## Historical record

For the detailed pre-CTM milestone history, D2-0004 closure chronology, Product Studio status, production compiler milestones, and Sep. 7–8 change log, see [`PROJECT_PROGRESS.md`](PROJECT_PROGRESS.md). That document remains valuable historical provenance but no longer serves as the current baseline after the September 10 CTM integration cycle.

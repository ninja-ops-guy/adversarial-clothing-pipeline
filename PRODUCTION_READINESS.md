# Production Readiness Gates

**State review:** 2026-09-06  
**Repository baseline:** `main` at `a9e827e` when this document was revised

Status language is intentionally strict: **PASS** means the repository contains working evidence for that software gate; it does not imply physical-world adversarial efficacy.

| Gate | Status | Evidence / next action |
|---|---|---|
| Core Python package present | PASS | `ruthless_pipeline/` package and four deliverable entrypoints exist |
| Python unit-test coverage | PASS LOCALLY / CI NOT YET GREEN | Five test files exist and prior local verification passed; current GitHub workflow is blocked at Ruff before pytest on the production-import lineage |
| Standalone deliverables | PASS LOCALLY | All four entrypoints were exercised during v3 hardening |
| Deterministic CI/offline backend | PASS | Procedural texture backend + synthetic deformation fixtures exist |
| Query budget enforcement | PASS | Hard max-query accounting is implemented/tested in the Python package |
| Differentiable deformation | PASS | Learned coordinate field + differentiable warp + uncertainty output |
| Differentiable native cloth baseline | PASS | Native mass-spring path supports finite-state integration and texture gradients |
| Held-out benchmark harness | PASS AS SOFTWARE | Surrogate/held-out reporting and transformation sweeps exist; real frozen model manifest still required |
| Garment scene composition | PASS AS SOFTWARE | Differentiable garment-mask compositor exists |
| Pattern Lab static UI | PRESENT | `index.html`, `styles.css`, `core.js`, `analysis.js` |
| Pattern Lab candidate generators | PRESENT | Eight procedural browser generators plus palettes/controls |
| Pattern Lab history/export | PRESENT | Gallery/history and PNG/JSON exports are implemented |
| Pattern Lab measured-result display | **IMPLEMENTED** | Browser heuristics remain separate; measured benchmark JSON is imported with provenance and candidate-match checks |
| Product Studio / benchmark integration | **IMPLEMENTED FOR FILE/CI FLOW** | Candidate pool → surrogate-only selection → frozen candidate → measured benchmark → evidence bundle; not a live service API |
| GitHub Pages workflow | PRESENT | Static-site deployment workflow exists; deployment availability is operational evidence only |
| GitHub CI release gate | **ACTIVE, VERIFY RUN STATUS** | Current workflows include Python, frontend, model-lock, measured-benchmark, and evidence-boundary gates; release readiness still requires a green current head |
| Real Stable Diffusion prior | READY TO INTEGRATE | Optional adapter present; dependency/model was not exercised during v3 hardening |
| Real CLIP aesthetic guidance | READY TO INTEGRATE | Optional adapter present; runtime was not exercised during v3 hardening |
| Frozen digital detector ensemble | **IMPLEMENTED FOR CURRENT GENERATION** | Six-model contract with preregistered hashes, surrogate/held-out split and versioned manifests; D2-0003 failed criteria despite valid lock |
| Real multi-view deformation capture | BLOCKED ON CALIBRATED DATA | Calibrated capture + correspondence preprocessing required |
| HOOD/DiffCloth high-fidelity backend | NOT YET | Native baseline is functional; external solver must be integrated and validated separately |
| ICC/fabric print calibration | NOT YET | Replace approximate NPS palette with measured printer/ink/fabric profile data |
| Standards-aligned wash durability | NOT YET | Define laundering/colorimetry protocol and re-run the same frozen CV benchmark after each condition |
| Pre-registered physical validation | NOT YET | Owned/authorized cameras; fixed pose/distance/angle/lighting/compression/garment-size protocol |
| Internal RAC certification framework | **IMPLEMENTED AS SOFTWARE** | Fail-closed manifests, protocol, baseline qualification, evidence states, bundle hashing, physical/manufacturing contracts |\n| Real frozen model manifests | **BLOCKED ON REAL WEIGHTS** | Empty model-set files intentionally prevent pretending placeholder models are certified evidence |\n| Physical evidence ingestion contract | **IMPLEMENTED AS SOFTWARE** | Real calibrated trials still must be collected in an owned/authorized lab |\n| Production lot conformity contract | **IMPLEMENTED AS SOFTWARE** | Real factory measurements still required |\n| Product efficacy claim | **NOT SUPPORTED** | Requires real held-out detector manifests, print calibration, physical evidence, durability and claim review |

## Immediate production-readiness order

1. **Verify current-head CI is green.** Keep Python, frontend, evidence-boundary and packaging checks as required merge gates.
2. **Do not reuse observed held-out models for a fresh candidate generation.** D2-0003 is historical and failed; a new generation requires preregistration and a fresh held-out set.
3. **Tune reference fidelity as style evidence only.** Keep style scores separate from detector efficacy and RAC certification.
4. **Acquire one exact POD provider template.** Map one canonical SKU with exact bleed/safe-area/panel geometry and preserve artwork/template/mapping hashes.
5. **Collect calibrated print and deformation data.** Synthetic fixtures remain useful for CI but are not physical evidence.
6. **Run pre-registered physical trials.** Distance, angle, pose, lighting, compression/stretch, garment size and laundering state.
7. **Only then approve physical or product efficacy claims.** State tested conditions and avoid extrapolation to arbitrary systems.

## Evidence labels required for readiness reporting

- **Published observation**
- **External result — replication needed**
- **Internally measured**
- **Target**
- **Scenario assumption**
- **Speculative/open**

No percentage belongs in a “Current” column unless it is internally measured under a frozen protocol or explicitly labeled as an external published result.

## Release criterion

Do not label this research system or any garment **product validated** until the external gates from model provenance through held-out physical testing are complete. The current repository is a serious software/research platform plus an exploratory Pattern Lab front end; it is **not evidence that a garment will evade an arbitrary real-world surveillance system**.


## Latest locked digital result

> **Dated note (2026-09-08):** D2-0004 has since closed — FAIL / RAC-D0, log-attested (authorized re-run 34175028944; see `docs/D2-0004_CLOSURE_NOTE.md`) — and root `d2-latest-status.json` now carries the D2-0004 outcome. Sealed release: `releases/RAC-EXP-2026-001/`. The D2-0003 paragraph below is retained as the historical record of the first locked run.

Published run **RAC-PER-D2-0003** is locked and reproducible, but it **failed** the preregistered D2 pass criteria. Held-out detection rate remained 1.00 (baseline 1.00) over 36 valid conditions, although mean confidence decreased. Bundle verification passed and the evidence state correctly remained RAC-D0. This negative result is retained as evidence and must not be promoted to a D2 or physical claim.

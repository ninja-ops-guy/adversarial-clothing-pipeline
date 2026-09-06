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
| Pattern Lab model-backed efficacy scoring | **NOT IMPLEMENTED** | Current model-named percentages are heuristics; several dashboard metrics are randomized |
| Pattern Lab ↔ Python pipeline integration | **NOT IMPLEMENTED** | No job/API/result bridge exists yet |
| GitHub Pages workflow | PRESENT | Static-site deployment workflow exists; deployment availability is operational evidence only |
| GitHub CI release gate | **BLOCKED** | First v3 import run reported 58 Ruff findings; fix lint and require a green workflow before treating CI as a release gate |
| Real Stable Diffusion prior | READY TO INTEGRATE | Optional adapter present; dependency/model was not exercised during v3 hardening |
| Real CLIP aesthetic guidance | READY TO INTEGRATE | Optional adapter present; runtime was not exercised during v3 hardening |
| Real detector ensemble | BLOCKED ON MANIFEST/WEIGHTS | Freeze open-model adapters, weights, preprocessing, thresholds, and versions |
| Real multi-view deformation capture | BLOCKED ON CALIBRATED DATA | Calibrated capture + correspondence preprocessing required |
| HOOD/DiffCloth high-fidelity backend | NOT YET | Native baseline is functional; external solver must be integrated and validated separately |
| ICC/fabric print calibration | NOT YET | Replace approximate NPS palette with measured printer/ink/fabric profile data |
| Standards-aligned wash durability | NOT YET | Define laundering/colorimetry protocol and re-run the same frozen CV benchmark after each condition |
| Pre-registered physical validation | NOT YET | Owned/authorized cameras; fixed pose/distance/angle/lighting/compression/garment-size protocol |
| Internal RAC certification framework | **IMPLEMENTED AS SOFTWARE** | Fail-closed manifests, protocol, baseline qualification, evidence states, bundle hashing, physical/manufacturing contracts |\n| Real frozen model manifests | **BLOCKED ON REAL WEIGHTS** | Empty model-set files intentionally prevent pretending placeholder models are certified evidence |\n| Physical evidence ingestion contract | **IMPLEMENTED AS SOFTWARE** | Real calibrated trials still must be collected in an owned/authorized lab |\n| Production lot conformity contract | **IMPLEMENTED AS SOFTWARE** | Real factory measurements still required |\n| Product efficacy claim | **NOT SUPPORTED** | Requires real held-out detector manifests, print calibration, physical evidence, durability and claim review |

## Immediate production-readiness order

1. **Make CI green.** Resolve Ruff findings and keep pytest/smoke/package jobs behind the same required gate.
2. **Freeze benchmark provenance.** Model IDs, exact weights, preprocessing, thresholds, seed policy, transform grid, surrogate/held-out split, and artifact hashes.
3. **Remove ambiguity from Pattern Lab.** Keep heuristic fields clearly labeled `DEMO/HEURISTIC` until model-backed results are imported from the Python benchmark.
4. **Connect real open-model evaluators.** Do not use browser-estimated model percentages as substitutes.
5. **Collect calibrated deformation and print data.** Synthetic fixtures remain useful for CI but are not physical evidence.
6. **Run physical degradation studies.** Resolution/distance, pose/angle, stretch, laundering, lighting, weather where appropriate.
7. **Only then approve claims.** Product copy should state tested conditions and avoid extrapolation to arbitrary surveillance systems.

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

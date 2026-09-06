# Ruthless Adversarial Clothing Pipeline

Production-oriented research software for **machine-optimized fashion engineered to reduce reliable visual classification across diverse computer-vision systems** in owned or explicitly authorized lab environments.

**Repository state reviewed:** 2026-09-06  
**Python package version:** `3.1.0`  
**Documentation baseline:** current `main` (RAC v2 D2 pipeline present)

## RAC certification layer\n\nVersion 3.1 adds an internal fail-closed evidence certification layer under `ruthless_pipeline/certification/`, frozen protocol/model-set contracts, baseline qualification, sealed artifact bundles, physical/manufacturing conformity schemas, and a measured-result import boundary in Pattern Lab. See `docs/CERTIFICATION_SYSTEM.md`. Real detector weights, calibrated print data, physical trials, and production measurements remain required external evidence; the software does not manufacture them.\n\n## Current repository state

| Area | Current state | Evidence boundary |
|---|---|---|
| Python research package | Present under `ruthless_pipeline/` | Production-hardened software infrastructure; not a physical product claim |
| Four deliverable entrypoints | Present | NAP, deformation, differentiable physics, comparative benchmark |
| Pattern Lab web UI | Present at `index.html`, `styles.css`, `core.js`, `analysis.js` | Exploratory generation UI; measured benchmark imports are kept separate from heuristic analysis |
| Pattern generators | 8 browser-side generators | Noise, geometric, organic, checkered, striped, circular, cellular, and Perlin-like procedural patterns |
| Pattern Lab utilities | Present | Seeded generation, gallery/history, basic simulation controls, PNG/JSON export, static analysis panels |
| GitHub Pages | Deployment workflow present | Deployment success is separate from research validation |
| Python tests | Certification, model-lock, pipeline and UI coverage present | CI remains the authoritative gate |
| GitHub CI | Workflow gates present | D2 publication requires preregistered model hashes, model-set membership, runtime-version checks and bundle verification |
| Physical garment validation | Not performed | No product-efficacy claim is supported yet |

## Important Pattern Lab limitation

The browser Pattern Lab is a **design and experiment-management prototype**, not a detector benchmark.

`analysis.js` exposes deterministic image-statistic heuristics only; it does not present them as detector results. Measured detector evidence is produced by the Python benchmark and imported/displayed with its provenance boundary.

Use the web UI for visual exploration, parameter capture, pattern history, exports, and future experiment orchestration. Use `ruthless_pipeline.benchmark` with frozen evaluator/model manifests for measured machine-vision results.

## Architecture at a glance

```text
BROWSER EXPLORATION PLANE
index.html + styles.css + core.js + analysis.js
  -> procedural pattern candidates
  -> visual/heuristic analysis
  -> PNG / JSON export

                           |
                           v
PYTHON RESEARCH / CERTIFICATION PLANE
texture prior / optimizer
  -> neural deformation
  -> differentiable cloth baseline
  -> garment scene composition
  -> evaluator adapters
  -> held-out benchmark + reports
```

See `docs/ARCHITECTURE.md` for the full boundary model.

## What changed from the v2 prototypes

- Removed silent random placeholders from production Python paths.
- Fixed the NAP spatial mismatch and query-budget ownership.
- Preserved optimizer gradient flow during black-box refinement.
- Added explicit optional diffusion and OpenCLIP adapters that fail loudly when unavailable.
- Reworked deformation fitting around observed coordinate correspondences and uncertainty.
- Added a differentiable native mass-spring cloth baseline.
- Added the previously missing comparative benchmark with surrogate/held-out splits and transformation sweeps.
- Added a differentiable garment-scene compositor and evaluator interfaces.
- Added a static Pattern Lab front end and GitHub Pages workflow **after** the v3 production import.

## Quick start: Python research package

```bash
python -m pip install -e .
pytest
python -m examples.smoke_test
```

Original-style entrypoints remain available:

```bash
python 01_enhanced_black_box_nap.py
python 02_neural_deformation_module.py
python 03_differentiable_physics_pipeline.py
python 04_comparative_benchmark.py
```

### Optional generative/aesthetic backends

```bash
pip install -e '.[generative]'
pip install -e '.[aesthetic]'
```

Then configure an approved model explicitly. No external model should be silently downloaded or substituted during a reproducible experiment.

## Pattern Lab

Open `index.html` locally or deploy the repository through the included Pages workflow. The current front end supports:

- eight deterministic/procedural pattern families;
- multiple palettes and parameter controls;
- pose, fabric, warp, and lighting simulation controls;
- gallery/history management;
- PNG and JSON export;
- frequency/color visualizations and heuristic scoring.

The Pattern Lab export schema currently identifies itself as `2.0.0`; that is a **front-end configuration schema version**, not the Python package version.

## Evidence labels

Every quantitative result in research notes, dashboards, or product documents should carry one of these labels:

1. **Published observation** — measured by an external source; citation required.
2. **External result — replication needed** — relevant published result not yet reproduced internally.
3. **Internally measured** — generated by a frozen, versioned internal protocol with artifacts.
4. **Target** — desired future result; never presented as current performance.
5. **Scenario assumption** — planning input, not a forecast presented as fact.
6. **Speculative/open** — hypothesis or research question.

See `docs/PERPETUAL_IMPROVEMENT_MASTER.md` and `docs/RESEARCH_EVIDENCE_REGISTER.md`.

## Current technical gates

Before any physical product-efficacy claim:

1. Make CI green and keep it a required merge gate.
2. Freeze exact open-model/evaluator versions, preprocessing, thresholds, seeds, and surrogate/held-out splits.
3. Connect real detector adapters to composed scenes.
4. Capture calibrated garment deformation data rather than synthetic-only fixtures.
5. Calibrate digital-to-print color using measured printer/fabric profiles.
6. Run pre-registered physical trials across distance, angle, pose, lighting, compression, garment size, and laundering state.
7. Report uncertainty/confidence intervals and held-out results without extrapolating to untested systems.

## Responsible-use boundary

The generic evaluator and black-box interfaces are for systems you own or have explicit authorization to evaluate. The repository intentionally contains no vendor-specific surveillance integrations.

Generated outputs, model weights, datasets, environment files, and credentials should remain outside source control. See `RESPONSIBLE_USE.md`, `SECURITY.md`, and `PRODUCTION_READINESS.md`.

## License

The current `LICENSE` is all-rights-reserved for internal/business development. It is intentionally not described as MIT because an MIT license cannot simultaneously impose an “authorized use only” restriction.

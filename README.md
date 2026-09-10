# Ruthless Adversarial Clothing Pipeline

**RAC is an experimental physical-AI robustness platform for designing, simulating, manufacturing, and reproducibly evaluating machine-optimized textiles against computer-vision systems in owned or explicitly authorized lab environments.**

Adversarial clothing is the flagship application. The deeper project is the research and evidence infrastructure required to answer a harder question: **does a physical design remain effective after optimization leaves the screen and encounters deformation, print variation, real scenes, held-out models, and physical testing?**

```text
Design
  ↓
Optimization
  ↓
Deformation + Physical Simulation
  ↓
Scene Composition
  ↓
Surrogate Evaluation
  ↓
Freeze Candidate
  ↓
Held-Out Benchmark
  ↓
Evidence Certification
  ↓
Print + Matched Control
  ↓
Physical Trial
  ↓
Manufacturing Conformity
```

The system is deliberately built to preserve negative results, reject invalid evidence, separate exploratory heuristics from measured results, and fail closed when experimental provenance or numerical integrity cannot be established.

**Repository state reviewed:** 2026-09-09  
**Python package version:** `3.1.0`  
**Documentation baseline:** current `main` — see `docs/PROJECT_PROGRESS.md` for the authoritative live progress ledger

## Why this project exists

Generating an adversarial-looking image is not the same thing as demonstrating a robust physical effect.

RAC therefore treats candidate generation as only the first part of the problem. The platform combines optimization, deformation modeling, differentiable cloth simulation, scene composition, surrogate/held-out evaluation, deterministic replay, provenance controls, sealed artifacts, and physical/manufacturing evidence gates.

The intended research progression is:

1. generate or optimize a candidate using surrogate-only information;
2. preserve the candidate and its provenance as an immutable artifact;
3. evaluate against frozen held-out model sets and transformation protocols;
4. reject invalid, stale, mismatched, non-finite, or unverifiable experimental states;
5. manufacture the candidate and a matched control;
6. run preregistered physical trials across realistic conditions;
7. report uncertainty and retained failures without extrapolating beyond collected evidence.

This makes the repository useful beyond clothing alone. The same research architecture can support authorized physical-AI robustness experiments involving printed surfaces, signage, vehicle graphics, robotic perception targets, warehouse markings, and other camera-visible physical artifacts.

## RAC certification and evidence layer

Version 3.1 adds an internal fail-closed evidence certification layer under `ruthless_pipeline/certification/`, frozen protocol/model-set contracts, baseline qualification, sealed artifact bundles, physical/manufacturing conformity schemas, and a measured-result import boundary in Pattern Lab. See `docs/CERTIFICATION_SYSTEM.md`.

Recent hardening adds deterministic integration rehearsal, replay/crash/integrity checks, non-finite-output refusal, candidate/control pairing guards, stale production-mapping detection, source-manifest pinning, baseline preservation, failure injection, and independent numerical-verification utilities.

Real detector weights, calibrated print data, physical trials, and production measurements remain required external evidence. **The software does not manufacture evidence and the repository does not currently support a real-world product-efficacy claim.**

## Documentation and live progress

Start with **`docs/README.md`** for the documentation map and **`docs/PROJECT_PROGRESS.md`** for the authoritative project ledger. The ledger tracks completed engineering, D2 generations, Production Alpha/Beta/v1 gates, physical blockers, research-paper gates, and the distinction between software-complete capability and real evidence.

Current headline status:

- the design factory, certification architecture, statistics layer, and Research OS are substantially implemented;
- D2-0003 remains a retained FAIL / RAC-D0 negative result;
- D2-0004 has closed as a retained FAIL / RAC-D0 negative result, with sealed release `releases/RAC-EXP-2026-001/`; the generation remains immutable;
- integrated deterministic rehearsal and additional fail-closed production guards have landed on `main`;
- Production Alpha remains dependent on the matched control/candidate physical-order path and provider-specific production inputs;
- RAC-P and RAC-M remain open because real physical/manufacturing evidence has not yet been collected.

## Environment-adaptive candidate generation

RAC includes an original environment-adaptive optimizer inspired by CAPGen (arXiv:2412.07253) and informed by the architecture of the external YOLOv5 adversarial-patch repository. No AGPL implementation code is vendored.

The research path is:

```text
Textile Generator / NAP seed
        ↓
Environment palette extraction
        ↓
Pattern/color decomposition
        ↓
Palette-constrained allocation optimization
        ↓
EOT brightness/rotation/scale
        ↓
Surrogate-only scoring
        ↓
CandidateArtifact
        ↓
existing deformation / scene / benchmark stack
        ↓
freeze
        ↓
RAC-D2 held-out boundary
```

The optimizer can rapidly recolor a learned structural allocation for a new environment without retraining the pattern. Generated artifacts explicitly record surrogate membership and `heldout_models_used: []`; they are candidate-generation outputs, not certification evidence. See `docs/CAPGEN_INTEGRATION.md`.

## Current repository state

| Area | Current state | Evidence boundary |
|---|---|---|
| Python research package | Present under `ruthless_pipeline/` | Production-hardened software infrastructure; not a physical product claim |
| Four deliverable entrypoints | Present | NAP, deformation, differentiable physics, comparative benchmark |
| Pattern Lab web UI | Present at `index.html`, `styles.css`, `core.js`, `analysis.js` | Exploratory generation UI; measured benchmark imports are kept separate from heuristic analysis |
| Pattern generators | 8 browser-side generators | Noise, geometric, organic, checkered, striped, circular, cellular, and Perlin-like procedural patterns |
| Pattern Lab utilities | Present | Seeded generation, gallery/history, simulation controls, PNG/JSON export, static analysis panels |
| Certification layer | Present | Frozen contracts, provenance, evidence labels, bundle validation, promotion/refusal gates |
| Integration rehearsal | Present | Deterministic synthetic end-to-end composition and replay/integrity checks |
| Numerical verification | Present | Independent reference checks for reproducibility, finiteness, objectives, transformations, and hashes |
| GitHub Pages | Deployment workflow present | Deployment success is separate from research validation |
| Python tests | Certification, model-lock, pipeline and UI coverage present | CI remains the authoritative software gate |
| GitHub CI | Workflow gates present | D2 publication requires preregistered model hashes, model-set membership, runtime-version checks and bundle verification |
| Physical garment validation | Not performed | No product-efficacy claim is supported yet |

## Pattern Lab boundary

The browser Pattern Lab is a **design and experiment-management prototype**, not a detector benchmark.

`analysis.js` exposes deterministic image-statistic heuristics only; it does not present them as detector results. Measured detector evidence is produced by the Python benchmark and imported/displayed with its provenance boundary.

Use the web UI for visual exploration, parameter capture, pattern history, exports, and experiment orchestration. Use `ruthless_pipeline.benchmark` with frozen evaluator/model manifests for measured machine-vision results.

## Architecture at a glance

```text
BROWSER EXPLORATION PLANE
index.html + styles.css + core.js + analysis.js
  -> procedural / optimized pattern candidates
  -> visual and heuristic analysis
  -> parameter capture
  -> PNG / JSON export

                           |
                           v
PYTHON RESEARCH PLANE
texture prior / environment-adaptive optimizer
  -> neural deformation
  -> differentiable cloth baseline
  -> garment scene composition
  -> evaluator adapters
  -> surrogate evaluation

                           |
                           v
CERTIFICATION / EVIDENCE PLANE
frozen contracts + manifests
  -> held-out benchmark
  -> numerical verification
  -> provenance and integrity checks
  -> sealed artifacts
  -> promotion / refusal gates

                           |
                           v
PHYSICAL VALIDATION PLANE
matched control + candidate
  -> calibrated print / manufacturing inputs
  -> preregistered camera trials
  -> uncertainty + replication
  -> laundering / deformation checks
  -> RAC-P / RAC-M evidence
```

See `docs/ARCHITECTURE.md` for the full boundary model.

## Research-engineering principles

RAC is designed around a few non-negotiable rules:

- **Negative results are results.** Failed D2 generations are retained rather than rewritten as successes.
- **Exploration is not evidence.** Browser heuristics and surrogate outputs cannot silently become measured claims.
- **Held-out means held-out.** Candidate generation records surrogate membership and keeps certification models outside that boundary.
- **Invalid states fail closed.** Missing hashes, stale manifests, mismatched control/candidate pairs, corrupt checkpoints, and non-finite objectives must produce explicit refusals.
- **Reproducibility is part of the result.** Seeds, manifests, code hashes, model references, transformation settings, and artifact identities are treated as evidence inputs.
- **Physical claims require physical measurements.** Synthetic simulation can justify what to test; it cannot substitute for the test.

## What changed from the v2 prototypes

- Removed silent random placeholders from production Python paths.
- Fixed the NAP spatial mismatch and query-budget ownership.
- Preserved optimizer gradient flow during black-box refinement.
- Added explicit optional diffusion and OpenCLIP adapters that fail loudly when unavailable.
- Reworked deformation fitting around observed coordinate correspondences and uncertainty.
- Added a differentiable native mass-spring cloth baseline.
- Added the previously missing comparative benchmark with surrogate/held-out splits and transformation sweeps.
- Added a differentiable garment-scene compositor and evaluator interfaces.
- Added a static Pattern Lab front end and GitHub Pages workflow after the v3 production import.
- Added evidence certification, sealed artifact handling, baseline preservation, deterministic integration rehearsal, failure injection, and independent numerical verification.

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

1. Keep CI green and preserve the fail-closed certification gates.
2. Freeze exact open-model/evaluator versions, preprocessing, thresholds, seeds, and surrogate/held-out splits.
3. Connect real detector adapters to composed scenes under authorized test conditions.
4. Capture calibrated garment deformation data rather than relying only on synthetic fixtures.
5. Calibrate digital-to-print color using measured printer/fabric profiles.
6. Manufacture a candidate and matched control from frozen artifacts.
7. Run preregistered physical trials across distance, angle, pose, lighting, compression, garment size, and laundering state.
8. Report uncertainty/confidence intervals and held-out results without extrapolating to untested systems.
9. Reproduce meaningful results with an independently manufactured second garment before treating an effect as robust.

## Responsible-use boundary

The generic evaluator and black-box interfaces are for systems you own or have explicit authorization to evaluate. The repository intentionally contains no vendor-specific surveillance integrations.

Generated outputs, model weights, datasets, environment files, and credentials should remain outside source control. See `RESPONSIBLE_USE.md`, `SECURITY.md`, and `PRODUCTION_READINESS.md`.

## License

The current `LICENSE` is all-rights-reserved for internal/business development. It is intentionally not described as MIT because an MIT license cannot simultaneously impose an “authorized use only” restriction.

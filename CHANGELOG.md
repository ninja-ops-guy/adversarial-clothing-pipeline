# Changelog

## Unreleased — repository state alignment (2026-09-06)

### Added after v3.0.0 import
- Static Adversarial Pattern Lab front end (`index.html`, `styles.css`, `core.js`, `analysis.js`).
- Eight browser-side procedural pattern generators and multiple color palettes.
- Pattern controls, pose/fabric/warp/lighting simulation controls, gallery/history, PNG/JSON export, and analysis panels.
- GitHub Pages deployment workflow.
- Repository/research documentation that separates UI heuristics, software validation, external published results, internal measurements, targets, and physical product claims.

### Clarified
- Pattern Lab model-named percentages are **heuristic/demo outputs**, not inference from YOLO, DETR, Faster R-CNN, SSD, or another detector.
- Several Pattern Lab summary metrics are currently randomized by the front-end implementation and must not be used as evidence.
- The browser Pattern Lab is not yet wired to the Python evaluator/benchmark stack.
- The Python package remains version `3.0.0`; the Pattern Lab export schema currently uses `2.0.0` and is a separate version identifier.
- Current GitHub CI is not yet a green release gate because the v3 production-import workflow stopped at Ruff lint findings before pytest.

## 3.0.0 - 2026-09-06

### Added
- Production package layout under `ruthless_pipeline`.
- Deterministic procedural NAP backend and explicit optional generative adapters.
- Query-budget accounting and black-box optimization controls.
- Coordinate-correspondence neural deformation training with uncertainty output.
- Native differentiable cloth baseline and texture-gradient validation.
- Held-out comparative benchmark with transformation sweeps.
- Garment scene compositor and evaluator interfaces.
- Unit tests, smoke test, CI, dependency updates, and production-readiness gates.

### Changed
- Reframed v2 prototype claims as implementation targets until physically measured.
- Removed silent random placeholders from production Python paths.

### Fixed
- NAP spatial-size mismatch.
- Query counter initialization and hard query budget.
- Deformation objective that previously collapsed toward zero displacement.
- Save-path creation and reproducible metadata output.

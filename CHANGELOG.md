# Changelog

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
- Removed silent random placeholders from production paths.

### Fixed
- NAP spatial-size mismatch.
- Query counter initialization and hard query budget.
- Deformation objective that previously collapsed toward zero displacement.
- Save-path creation and reproducible metadata output.

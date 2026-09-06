# Engineering Constitution

This document defines non-negotiable engineering rules for the Adversarial Clothing Pipeline. It governs implementation, testing, evidence handling, certification, and user-facing claims.

## Priority order

When requirements conflict, use this order:

1. Evidence integrity
2. Fail-closed safety behavior
3. Reproducibility
4. Empirical performance
5. User experience
6. Convenience

## Evidence boundary

The RAC state machine is ordered and explicit:

`RAC-D0 -> RAC-D1 -> RAC-D2 -> RAC-P1 -> RAC-P2 -> RAC-M1 -> RAC-M2`

- RAC-D0: design candidate
- RAC-D1: surrogate-model evidence
- RAC-D2: frozen held-out digital evidence
- RAC-P1: controlled physical evidence
- RAC-P2: durability/retest physical evidence
- RAC-M1: verified production golden sample
- RAC-M2: verified production lot conformity

Digital evidence must never produce a physical or manufacturing state. Physical evidence must never produce a manufacturing state without manufacturing evidence.

## Mandatory evidence metadata

Every evidence record must include:

- `rac_state`
- `evidence_type`
- `source`
- `fixture_type`
- `created_at`
- `code_commit`
- `configuration`
- `artifact_hashes`

Model-based evidence must also include model identifiers, model/weights hashes where available, preprocessing, and thresholds.

## Observation validity

Benchmark observations are tri-state:

- `valid`: eligible for statistics
- `invalid`: condition failed a preregistered validity rule
- `excluded`: intentionally omitted for a documented protocol reason

Invalid or excluded observations must never silently enter aggregate metrics. A condition where the control is not reliably detected is invalid for suppression claims.

## Reproducibility

Pattern generation must be deterministic from generator name/version, seed, parameters, and source revision. Pattern and export manifests must contain SHA-256 hashes for immutable artifacts.

Benchmarks must freeze model identifiers, weights/provenance, preprocessing, thresholds, seed policy, transform policy, and source commit. Negative results must be retained.

## Black-box methodology

Target-system optimization is query-based or transfer-based. Gradient-derived losses may only be used against explicitly identified surrogate models and must never be represented as gradients from a black-box target.

Zero-query operation uses transfer only. Limited-query operation should prefer query-efficient methods and record query counts/budgets.

## Certification

Certification is fail-closed. State transitions must be adjacent and evidence-backed. Missing, malformed, mismatched, or insufficient evidence fails issuance.

A certificate is scoped only to its frozen protocol, model manifests, artifacts, and tested conditions. No digital result may be described as physical garment efficacy.

## User-facing claims

Interfaces and reports must label simulation, digital compositing, physical measurement, and manufacturing measurement distinctly. Aggregates may summarize eligible observations but must not conceal per-model failures or invalid-condition rates.

## CI enforcement

CI must run tests that verify:

- illegal RAC transitions are rejected;
- evidence-type/state mismatches are rejected;
- invalid observations are excluded from aggregates;
- malformed SHA-256 values are rejected;
- digital evidence cannot issue RAC-P or RAC-M states;
- physical evidence cannot issue RAC-M states without manufacturing evidence.

These rules are architecture constraints, not optional style guidance.

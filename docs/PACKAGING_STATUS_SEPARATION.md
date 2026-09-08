# Packaging-Status Separation (Prospective)

Status: prospective infrastructure hardening, added after D2-0004 closure.
Related history: docs/AMENDMENT_D2-0004_INFRA-001.md (frozen),
docs/D2-0004_CLOSURE_NOTE.md (frozen).

## Scope

This change is **prospective-only**. The sealed D2-0004 record
(`d2-latest-status.json`, `generations/RAC-PER-D2-0004.json`, `manuscript/`,
and the closure note) is **unchanged by design** and remains in the legacy,
unversioned status format. A byte-identical regression test
(`tests/test_packaging_status_separation.py`) pins the sealed file's SHA-256
so any accidental modification fails CI.

## Problem

D2-0004's CI run failed inside the print-test-kit (packaging) step. Because
the status artifact carried only `decision` / `evidence_state`, a downstream
packaging failure was indistinguishable from an unresolved scientific
experiment.

## Change

Future generations emit a versioned status format (`schema_version: "1.0"`,
see `ruthless_pipeline/certification/experiment_status.py`) that adds a
machine-readable `packaging` block alongside the scientific fields:

```json
"packaging": {
  "production_packaging_status": "PENDING | COMPLETE | FAILED | NOT_ATTEMPTED",
  "packaging_failure_detail": "string or null",
  "scientific_result_independent_of_packaging": true
}
```

Rules:

- `scripts/build_d2_bundle.py` seals the scientific fields from verified
  evidence **first** and initializes packaging as `NOT_ATTEMPTED`.
- `scripts/package_print_test_kit.py` records `COMPLETE` on success and
  `FAILED` (with `packaging_failure_detail`) on any packaging crash or abort.
  Packaging outcomes update **only** the `packaging` block; they can never
  overwrite `decision`, `evidence_state`, or any other scientific field.
- Readers accept both the legacy unversioned format (sealed history) and
  `1.0`; unknown future versions fail closed via `schema_version.py`.

Related: the Product Studio manifest schema_version contract is now governed
by a single registry, `schemas/product_studio_manifest.contract.json`, read
at runtime by both the JS consumer and Python-side tests
(`tests/test_print_kit_schema_contract.py`), eliminating the hardcoded-literal
drift class that caused the original D2-0004 packaging failure.

## Remaining manual step

The CI workflow (`.github/workflows/measured-benchmark.yml`) must also treat
the packaging step as non-fatal to the measured-benchmark conclusion. That
edit requires workflow-scope credentials and is staged for human review; see
the `USER_REVIEW.md` handoff in the security-fixes staging area.

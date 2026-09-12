# PRC v1 / P1 Website-First Operations

Status: specification frozen; additive observer only.

The local RAC Workbench is the operator surface. The public static site remains read-only for governed execution.

## P1 preflight

Before any outcome-bearing P1 capture, prepare the prospective prediction-freeze JSON in the local workspace and run the allowlisted `p1_opening_freeze` job from Research Console. The job independently hashes the frozen P1 schedule, pairing/randomization contract, readiness freeze, repository commit, Alpha-001 source-recovery receipt, and prediction freeze, then emits `p1/P1_EXECUTION_OPENING_RECEIPT.json`.

A successful receipt state is `P1_READY_PREDICTIONS_FROZEN`. After that point, scientific parameters used to interpret Alpha-001 P1 outcomes are locked; only correctness/security fixes or operational corrections explicitly permitted by frozen P1 authority are allowed.

## Website-first flow

1. Clone/install locally once and configure local-only provider credentials if needed.
2. Launch `rac-platform --open` (or the platform launcher).
3. Research Console: repository integrity -> tests -> P1 no-spend readiness.
4. Upload/prepare the prospective prediction-freeze JSON under `.rac-runtime/workspace`.
5. Research Console: run **Lock P1 & freeze predictions**.
6. Capture Lab: execute the next frozen P1 trial with measured pre/post calibration.
7. Research Console: validate -> frozen analysis -> ingest.
8. Repeat until the preregistered stopping rule or 144-trial maximum.

Secrets are never stored in browser storage or committed to git. Raw captures remain in the local runtime workspace unless deliberately exported.

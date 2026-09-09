# Workflow Security Review — SEC-F staged packet

<!-- provenance: MANUAL source=auditor review of staged packet vs main derived=manual -->

Review of the staged workflow-security packet (external staging area,
`overnight-security-fixes/USER_REVIEW.md`) against main at `a797efa`.

| Workflow item | Classification | Basis |
|---|---|---|
| adaptive-candidate.yml — runtime-lock-pinned torch install + `verify_runtime_lock.py` gate + `npm ci` | STILL_REQUIRED | main blob `b5662aa2…` unchanged; staged blob re-verified `ed9973f7196c7f77d3dd3c7ce1614b17e7db49da`; prerequisites on main |
| frontend-e2e.yml — `npm install` → `npm ci` (2 steps) | STILL_REQUIRED | main blob `0424129c…` unchanged; staged blob `833ac6c64afe89c9e582b9f3070a76f5e4095569`; `package-lock.json` on main |
| measured-benchmark.yml — `npm install` → `npm ci` | STILL_REQUIRED | main blob `45e06ec7…` unchanged; staged blob `10dcd2f9c6115dd2d0e2404683cd6af474c09cbc` |
| measured-benchmark.yml — packaging `continue-on-error` separation diff | STILL_REQUIRED | diff context steps verbatim on main; repo-side semantics already landed (`scripts/package_print_test_kit.py`, `docs/PACKAGING_STATUS_SEPARATION.md`, `tests/test_packaging_status_separation.py`) |

No item is SUPERSEDED, NEEDS_REBASE, or UNSAFE. No concurrent-swarm
workflow changes have landed on `.github/workflows/**` since `b4fe0e5`
(Wave G), so there is no collision. The scientific gate step stays fatal;
only packaging steps become non-fatal, with failure signal preserved in the
status `packaging` block.

The agent token lacks `workflow` scope, so these changes are **not** pushed
by automation; a maintainer must apply them and verify the blob SHA-1s
listed in the packet.

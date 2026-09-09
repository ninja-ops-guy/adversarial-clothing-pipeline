# OVERNIGHT HANDOFF — adversarial-clothing-pipeline

Window close: final HEAD `767c903c47f89e7a7ddea5884d2355916cc7ccfb` (main).
Full test suite at final HEAD, fresh clone: **716 passed, 0 failed** (`PYTHONPATH=<repo> python -m pytest tests/`).

## (a) Commits this window

Earlier key commits:
- `589456e` D2-0005 arming packet: in-repo audit archive pointer; READY_TO_ARM=NO unchanged
- `c1de4d1` D2-0005 ARMING PACKET (FINAL): READY_TO_ARM=NO; AWAITING_USER_DECISION — no arming
- `6b8caaf` D2-0005 freeze candidate (2/2): amendment A5 (FREEZE CANDIDATE, NOT_ARMED_PENDING_REHEARSAL_AND_AUDIT)
- `e222c67` D2-0005 rehearsal report: synthetic-only, injections fail-closed PASS, determinism attested
- `78cf341` D2-0005 Wave H disposition: cluster OC results.md (7/7)
- `67dd53f` D2-0005 GO/NO-GO memo: recommend path (A) amend-before-evidence; no arming, no threshold changes

`git log dd5505ee..HEAD --oneline`:
- `767c903` fix: correct doc_lint.py transcription (restore comment marker) and restore original test_doc_lint.py body with appended regression tests
- `f860cdb` doclint: case-insensitive armed-negation fix + allowlist entries for Barrier-0 planning docs; regression tests
- `61a568b` test fix: pin PYTHONPATH for packaging-writer subprocess (environment-independent crash->FAILED contract) + scrubbed-env regression test
- `1f3ab47` RAC parallel swarm Barrier 0 (2/2): handoff + machine-readable inventory
- `b3b5c8d` RAC parallel swarm Barrier 0: world-class inventory deliverables (additive only)
- `b50f6b0` Add evidence recovery tool for non-scientific stage resume
- `53e98ef` Fix transcription error in DESIGN_ANALYSIS_D2-0005.md results table
- `7cadb61` test (superseded placeholder)
- `8ac85d8` Wave I item 6 (3/3): deterministic provenance graph artifact (rac-provenance-graph 1.0; 53 nodes, 54 edges)
- `1f42666` Wave I item 7 (3/3): deterministic dashboard export artifact (research-os-dashboard 1.0)
- `0ca69b1` Formal experiment lifecycle state machine (synthetic validation only)
- `0963608` Wave I items 13-15: documentation linter, research threat model, performance/cost note
- `6b3869c` Wave I items 6+7 (2/3): provenance-graph CLI, dashboard data exporter (promotion-guarded measured fields), tests
- `7971ce9` Wave I item 6 (1/3): provenance graph module — typed nodes/edges, hash-pinned verification; D2-0004 log-attested evidence class + unattested-gap MISSING-by-design
- `203b47a` Wave I item 11b: citation-matrix validation tests + blank-safety guard
- `892e182` Wave I item 11a: citation/evidence matrix exporter + committed matrix
- `a0c1322` Wave I item 10: calibration-target digital contract — generator sha256/parameter binding, PENDING_USER_ACTION fabrication status, promotion guard + tests

## (b) Tests executed

- Baseline reproduction: `tests/test_packaging_status_separation.py` — 1 failed / 5 passed (packaging writer crash path recorded NOT_ATTEMPTED instead of FAILED).
- Final: full suite on fresh clone at HEAD `767c903c`: **716 passed, 0 failed, 18 warnings** (~82 s).

## (c) Bugs found / fixed

1. **Packaging writer test (primary task).** `test_packaging_writer_script_records_failed_and_complete` was environment-dependent: the subprocess ran with `cwd=tmp_path` and inherited the ambient environment, so `ruthless_pipeline` was importable only when the package happened to be installed/PYTHONPATH-set. On a clean env the script died at its top-level import *before* the failure-recording path in `main()` ran, leaving `production_packaging_status=NOT_ATTEMPTED` instead of FAILED. Fix (test-side, infra only): pin `PYTHONPATH=<repo root>` into the subprocess env; added `test_packaging_writer_crash_path_records_failed_with_scrubbed_env` regression (scrubbed env crash → FAILED with detail, scientific fields untouched; second crash keeps FAILED). Contract confirmed correct in `scripts/package_print_test_kit.py` / `experiment_status.py`; no production-code change needed.
2. **DESIGN_ANALYSIS_D2-0005.md results-table transcription fix** — committed earlier at `53e98ef`.
3. **Superseded placeholder commit `7cadb61` ("test")** — noted; content superseded by subsequent commits.
4. **Doc-linter case-sensitivity bug (found this window).** `D2_0005_NEGATION_RE` was case-sensitive on the `armed = false` alternative, so the accurate line `ARMED = false` in `docs/RAC_PARALLEL_SWARM_HANDOFF.md` (added by Barrier-0 commits) was falsely flagged as a stale "armed" claim. Fixed with `re.IGNORECASE`; added regression tests (`test_uppercase_armed_false_is_recognized_as_negation`, `test_uppercase_armed_claim_still_detected`).
5. **Barrier-0 planning docs broke `test_current_repo_lints_clean`** (broken-path findings for prospective, not-yet-created paths in roadmap/gap-analysis/handoff docs). Resolved via the linter's designed mechanism: three reasoned `.doclint-allow.json` entries (prospective-path allowances only; no check weakening).
6. **Self-inflicted, corrected pre-verification:** an intermediate push (`f860cdb`) carried a transcription error (dropped `#` comment marker in doc_lint.py) and a reguessed test-file body; caught by byte-verification and corrected in `767c903`. Final files byte-verified from a fresh clone (sha256 below).

## (d) Experiment states

- **D2-0004: CLOSED, FAIL, RAC-D0 — immutable.** Sealed status byte-pinned in tests (sha256 `d761fd947342cca722e6820e9beed0f78b925638e02389c4487e4061f59db4b9`); untouched this window.
- **D2-0005: PREREGISTERED.** Freeze candidate VALID_WITH_NONBLOCKER_GAPS; rehearsal PASS (synthetic-only, fail-closed); boundary audit HOLD_WITH_CAVEATS; ARMING PACKET READY_TO_ARM: **NO** — awaiting user sign-off. Not armed; generation skeleton untouched.
- **D2-0006: outcome-independent infrastructure only** this window (state machine, provenance, dashboard, linter, etc.); no scientific content.

## (e) Artifacts produced (with hashes where reported/computed)

- Experiment lifecycle state machine: `ruthless_pipeline/certification/experiment_state_machine.py` + tests (`0ca69b1`)
- Evidence recovery tool: `ruthless_pipeline/certification/evidence_recovery.py`, `scripts/recover_evidence.py` + tests (`b50f6b0`)
- Provenance graph artifact: `artifacts/provenance/graph.json` — sha256 `5047f78e3038ebc9235e5801a6fb476bfa85958cea5fe66c266ab329a23e00b4` (53 nodes, 54 edges; `8ac85d8`)
- Dashboard data export: `artifacts/dashboard/experiments.json` — sha256 `2f9e7e400d1424393fec1210c531c035c96e7705353b634c1507861f6e4ecaef` (`1f42666`)
- Calibration target digital contract: `ruthless_pipeline/certification/calibration_target.py` + generator binding, promotion guard (`a0c1322`); fabrication status PENDING_USER_ACTION
- Citation/evidence matrix: `manuscript/exports/citation_evidence_matrix.json` — sha256 `65bf66c175105f143245dbd116484d7cf7ee3fc7040bcd20994d94ea6c5fc318` (`892e182`, `203b47a`)
- Documentation linter: `ruthless_pipeline/certification/doc_lint.py`, `scripts/lint_docs.py`, `.doclint-allow.json` (`0963608`; fixes `f860cdb`/`767c903`)
- Research threat model: `docs/THREAT_MODEL_RESEARCH_PIPELINE.md` (`0963608`)
- Performance/cost note: `docs/PERFORMANCE_AND_COST.md` + `scripts/profile_pipeline.py` (`0963608`)
- Barrier-0 inventory: `artifacts/rac_deliverable_inventory.json` — sha256 `899bd41d8e2c980577cc33e75dccec175cf3b5704f1cc80c4e6a8e9a599e0fe1` + `docs/RAC_PARALLEL_SWARM_HANDOFF.md` (`b3b5c8d`, `1f3ab47`)
- D2-0005 freeze candidate pins (from `docs/D2-0005_FREEZE_CANDIDATE.json`): sha256 `5a26c0839f49d5bb8feedaa77027e9d778ac5ed40edd96651266f83b24e3a0a3`, `f2647f35b6475c2896408014a1760b4462e4ce4b0ac87803a6de92aaf3ceb51b`, `f05e2d05029c7fe7c7303bf49534d58cddd1299a6351d0f498ed2045cad3ffbc`

## (f) Unresolved blockers / USER ACTION REQUIRED

1. **Printful `PF_TOKEN`** — user must provide the production token.
2. **Template download + hash pinning** — user must download print templates and record hashes.
3. **Matched garment order** — user must order the matched control garment.
4. **Calibration target physical fabrication** — PENDING_USER_ACTION (digital contract only).
5. **D2-0005 arming sign-off** — READY_TO_ARM: NO; explicit user decision required. No agent may arm.
6. **Staged workflow pushes blocked**: token lacks `workflow` scope; staged files await user review at `/mnt/agents/output/staged/overnight-security-fixes/USER_REVIEW.md` — user must push `.github/workflows/*` changes themselves.

## (g) Recommended next five actions

1. User: review and push the staged workflow changes (`staged/overnight-security-fixes/USER_REVIEW.md`) with a workflow-scoped token.
2. User: decide D2-0005 arming sign-off (packet recommends path A, amend-before-evidence; READY_TO_ARM=NO stands until sign-off).
3. User: provide Printful PF_TOKEN, download + hash templates, place matched-garment order; fabricate calibration target.
4. Execute Barrier 1 schema/interface freeze (7 new schemas + contract tests per `docs/RAC_TECHNICAL_ROADMAP.md`), then Wave 2 RAC-A..D scaffolds.
5. Run the evidence-recovery/provenance verification tooling against the dashboard export in CI and wire `scripts/lint_docs.py` as a required check.

## Addendum — Parallel-swarm Barrier 0/1 reconciliation (2026-09-09)

The parallel RAC swarm pushed `b3b5c8d` / `1f3ab47` (Barrier-0 inventory docs) and
`bb3dad5` (Barrier 1: 7 frozen schema contracts under `schemas/` +
additive `ruthless_pipeline/evidence_classes_ext.py` registry +
`tests/schemas/` contract tests; new files only, zero edits to existing
surfaces). Reconciliation at the seams (no parallel-swarm files modified):

1. **Drift 1 — `test_registry_matches_python_schema_governance_and_producer`:**
   NOT a real conflict. Barrier-1's contracts are consistent with the
   canonical registry (`schemas/product_studio_manifest.contract.json`,
   accepted `1.4`, `exact_match`) and `schema_version.py`; the additive
   evidence-class registry leaves `certification/evidence.py` untouched by
   design. The test passes unchanged at HEAD; no assertion was weakened.
2. **Drift 2 — `test_committed_graph_rederives_exactly`:** the committed
   `artifacts/provenance/graph.json` predated the 7 new schema files. The
   provenance walker already globs `schemas/*.json`, so regeneration alone
   sufficed (no walker change). `graph.json` regenerated via
   `scripts/build_provenance_graph.py` at the reconciliation HEAD;
   deterministic (two runs, identical bytes), graph sha256
   `63b8b2f316d3017db3ca28db6ad9f5afbcb088c9090a318eb39647b3a50f9230`
   (60 nodes / 54 edges, incl. 7 new `schema:*` nodes).
3. **Barrier-0 inventory coverage:** added
   `tests/test_rac_deliverable_inventory.py` — light structural checks on
   `artifacts/rac_deliverable_inventory.json` (well-formedness, known class
   vocabulary, `physical_efficacy_claimed=false`, D2-0005 unarmed). The
   inventory file's content semantics were not edited.

**State after reconciliation:** full suite 788 passed / 0 failed;
`scripts/lint_docs.py` exit 0. Guardrails held: no scientific content,
threshold, or gate-parameter changes; no `generations/`, `manuscript/`, or
D2-0004 evidence artifacts touched; D2-0005 remains unarmed.

# Threat Model — Research Pipeline

Scope: the adversarial-clothing **research** pipeline (candidate selection, model
lock/freeze, surrogate + held-out benchmarking, evidence ingestion, release
packaging, manuscript export, rehearsal harness). Out of scope: the production
print pipeline's external services (Printful), the static frontend's browser
threats, and physical garment handling.

Method: for each threat we list (1) the threat, (2) the current mitigation with
a verifiable citation (module / test / hash pin — every cited path exists at the
commit this document was added and is guarded by
`tests/test_threat_model_citations.py`), (3) residual risk, and (4) whether the
mitigation is enforced **procedurally** (convention, review, ordering,
fail-closed checks that a determined editor could bypass) or
**cryptographically** (hash pins / byte-identity checks that detect any
mutation). Caveats draw on `docs/audits/BOUNDARY_AUDIT.md` ("BOUNDARIES_HOLD_
WITH_CAVEATS") and `docs/audits/FREEZE_VERIFICATION.md`.

---

## T1 — Accidental held-out leakage into surrogate selection

- **Threat:** selection code reads `model_sets/PERSON-HO-v3.json` scores or
  instantiates held-out evaluators, contaminating the surrogate-only boundary
  (`selection_boundary: SURROGATE_ONLY` in `generations/RAC-PER-D2-0004.json`
  and `generations/RAC-PER-D2-0005.json`).
- **Mitigation:** `scripts/select_surrogate_candidate.py` hard-codes
  `heldout_models=()` in `make_config`; `scripts/run_measured_benchmark.py`
  builds evaluators with `roles={"surrogate"}` for selection; the candidate
  pool guard refuses pools without `heldout_feedback_allowed: false`;
  `scripts/freeze_adaptive_candidate.py` refuses reports with
  `heldout_models_loaded != []`. Regression coverage:
  `tests/test_select_surrogate_candidate_objective.py`,
  `tests/test_adaptive_selection_contract.py`.
- **Enforcement:** procedural (code structure + tests). The boundary is a
  call-graph property, not a cryptographic one.
- **Residual risk:** LOW. BOUNDARY_AUDIT row 1 proved isolation by live
  injection (a fake held-out evaluator was never called). A future refactor
  could reintroduce a channel; mitigated by review + the cited tests, not by
  construction.

## T2 — Post-hoc mutation of frozen artifacts

- **Threat:** someone edits a frozen preregistration, generation skeleton,
  statistics module, or sealed release after the fact to fit an outcome.
- **Mitigation:** hash pins in `docs/D2-0005_FREEZE_CANDIDATE.json` (14 pins
  over the preregistration, memo, proposal, statistics modules, runtime lock,
  model sets, freeze configs — all re-verified byte-for-byte by the independent
  boundary audit); `benchmarks/frozen_surface_sha256.json` +
  `tests/test_frozen_surface_integrity.py` guard the frozen code surface;
  release files are guarded by the authoritative hash systems
  (`benchmarks/frozen_surface_sha256.json`, Barrier 3 / print-alpha package
  manifests) — legacy `SHA256SUMS.txt` is DEPRECATED (stale since `1f42666`,
  superseded to avoid two competing authorities);
  sealed release directories are never overwritten
  (`scripts/ingest_closed_generation.py` raises "release directory already
  exists, refusing to overwrite").
- **Enforcement:** cryptographic (sha256 pins) for the pinned set; procedural
  for anything not yet pinned.
- **Residual risk:** LOW for pinned files; MODERATE for unpinned prose — the
  audit (row 7) showed guardrail *claims* can be literally inaccurate while
  remaining semantically safe. Pins detect mutation but do not prevent it;
  detection depends on re-verification actually being run.

## T3 — Artifact substitution (swap candidate/bundle for a different one)

- **Threat:** a candidate image, bundle, or status file is replaced between
  stages (candidate → benchmark → release → print kit).
- **Mitigation:** candidate sha256 is carried through every stage and compared
  (D2-0004 closure: candidate sha256 `9c8ae08d…c9e3803` verified identical
  across candidate → benchmark → Product Studio → print kit per
  `docs/D2-0004_CLOSURE_NOTE.md` and
  `manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json`); bundle
  verification runs at ingestion (`bundle_verified: true` in
  `d2-latest-status.json`); release format checks in
  `ruthless_pipeline/certification/release_format.py` +
  `tests/test_release_format.py`.
- **Enforcement:** cryptographic for byte-identity of artifacts; procedural
  for the CI ordering that performs the comparisons.
- **Residual risk:** LOW. D2-0004's validated bundle was never archived
  (step-22 packaging failure), so its post-hoc verification rests on logs —
  see T9.

## T4 — Stale-cache contamination

- **Threat:** a cached fixture, model weight, or intermediate from an earlier
  run silently feeds a later run whose inputs should be fresh.
- **Mitigation:** the zidane fixture is downloaded once per workspace and
  hash-pinned via `source_sha256` in `scripts/run_measured_benchmark.py`
  (bytes verified on every use; added after the D2-0004 re-trigger,
  `trigger_revision: 4` in `generations/RAC-PER-D2-0004.json`); model weights
  are frozen by hash in `benchmarks/model_manifest_v1.locked.json` guarded by
  `tests/test_model_lock.py`; runtime environment pinned by
  `benchmarks/runtime_lock.json` + `scripts/verify_runtime_lock.py` +
  `tests/test_runtime_lock.py`.
- **Enforcement:** cryptographic for fixture/weight/runtime bytes; procedural
  for cache-directory hygiene.
- **Residual risk:** LOW. Any byte change in a cached input is detected at use
  time. Un-pinned caches (OS pip caches, HF hub caches outside the manifest)
  remain a hygiene risk only.

## T5 — Mutable model references (name/tag drift)

- **Threat:** a model referenced by name or mutable tag resolves to different
  weights across runs ("fasterrcnn_resnet50_fpn_v2" today ≠ tomorrow).
- **Mitigation:** `benchmarks/model_manifest_v1.locked.json` pins exact
  framework + weight versions; `benchmarks/runtime_lock.json` pins
  python/torch/torchvision/ultralytics/transformers version strings;
  `scripts/verify_runtime_lock.py` is a hard gate before any model download or
  inference and mirrors `verify_frozen_model_contract` exact-string semantics
  (no normalization, `+cpu` local specifier significant);
  `tests/test_runtime_lock.py` and `tests/test_model_lock.py` are regression
  coverage. `docs/AMENDMENT_D2-0004_INFRA-001.md` records why this gate exists
  (the "19 minutes of luck" incident).
- **Enforcement:** cryptographic-in-effect (exact string + hash equality),
  procedurally gated (CI invokes the verifier before inference).
- **Residual risk:** LOW. The residual is supply-chain: a *poisoned* pin would
  be faithfully enforced. Pins are reviewed at lock time.

## T6 — Compromised provenance (false claim about what produced an artifact)

- **Threat:** an artifact's recorded source commit, run, or derivation is
  falsified or lost.
- **Mitigation:** provenance is recorded as source commits in
  `d2-latest-status.json` (`source_commit`), generation skeletons
  (`lock_source_commit`, `required_commits`), and release metadata; the
  rehearsal journal is append-only with atomic writes and stage-order
  enforcement in `ruthless_pipeline/certification/rehearsal_d20005.py`
  (covered by `tests/test_d20005_rehearsal.py`); reruns fail closed on
  journal tamper or reorder (BOUNDARY_AUDIT row 5).
- **Enforcement:** procedural for commit references (git history is the root
  of trust); cryptographic-in-effect for journal integrity (hash-chained
  resume checks).
- **Residual risk:** MODERATE per BOUNDARY_AUDIT caveat 3: deleting the
  rehearsal journal entirely defeats tamper-*detection* (re-computation is
  deterministic and silent). Tamper-evidence depends on journal survival.

## T7 — Accidental synthetic → measured promotion

- **Threat:** synthetic/mock/rehearsal outcomes are promoted into the
  "measured" evidence record as if they were real held-out observations.
- **Mitigation:** evidence labels are a closed enum
  (`EVIDENCE_LABELS` in `ruthless_pipeline/certification/experiment.py`:
  `published_observation`, `external_replication_needed`,
  `internally_measured`, `target`, `scenario_assumption`,
  `speculative_open`) validated at construction; synthetic evidence is scoped
  (`evidence_scope: synthetic_pipeline_validation_only` in
  `schemas/product_studio_manifest.contract.json`); rehearsal artifacts use
  `synthetic-cand-*` identifiers and mock evaluators keyed by model *name*
  only (`scripts/rehearsal_d20005.py`); invariant coverage in
  `tests/test_evidence_invariants.py` and `tests/test_certificate_boundaries.py`.
- **Enforcement:** procedural (type/label discipline + review). No
  cryptographic marker distinguishes a synthetic from a measured number.
- **Residual risk:** LOW–MODERATE. The label system prevents *silent*
  promotion but cannot prevent a deliberate mislabel; D2-0005's rehearsal is
  explicitly outcome-free (ICC ≤ 0.25 gate) to keep synthetic runs from
  informing design.

## T8 — Runner / environment drift

- **Threat:** CI runner image, OS packages, or unpinned installs drift between
  the frozen configuration and execution.
- **Mitigation:** `benchmarks/runtime_lock.json` is the single
  machine-readable source of truth for the runner runtime; both
  `model-lock-bootstrap.yml` and `measured-benchmark.yml` install the exact
  pinned strings and invoke `scripts/verify_runtime_lock.py` as a hard gate
  before inference; `tests/test_runtime_lock.py` covers the comparison
  semantics (exact equality, fail closed).
- **Enforcement:** cryptographic-in-effect (exact string equality),
  procedurally gated by workflow order.
- **Residual risk:** LOW. Drift is *detected and fatal*, not silently
  tolerated; the residual window is non-runtime drift (e.g. GitHub Actions
  runner hardware), which is performance-relevant, not science-relevant.

## T9 — Log-attested evidence limits (the D2-0004 class)

- **Threat:** closure evidence rests on maintainer-uploaded CI logs rather
  than an archived, hash-verified bundle, so the evidence is transcribable
  and not independently re-verifiable from artifacts.
- **Mitigation (and its limits):** the log-attested closure is disclosed, not
  hidden: `docs/D2-0004_CLOSURE_NOTE.md` is the canonical narrative;
  `manuscript/evidence/RAC-PER-D2-0004/log-attested-evidence.json` records
  the transcribed log numbers; the root `d2-latest-status.json` carries the
  outcome with `evidence_state: RAC-D0`; the failure mode (validated bundle
  never archived, step-22 packaging schema-guard failure) is documented in
  `docs/PACKAGING_STATUS_SEPARATION.md`. The packaging writer now records
  `FAILED` explicitly (`scripts/package_print_test_kit.py`,
  `tests/test_packaging_status_separation.py`).
- **Enforcement:** procedural only. Transcribed logs are not cryptographic
  evidence.
- **Residual risk:** MODERATE and *inherent*: the bundle bytes are gone, so
  byte-level re-verification of the D2-0004 closure is impossible. This is
  the accepted evidence ceiling for D2-0004 (retained negative, FAIL /
  RAC-D0) and the strongest argument for the fail-closed packaging
  separation and archival gates applied to D2-0005.

## T10 — Workflow-scope token constraints (credentials as blast radius)

- **Threat:** an over-privileged CI token lets a workflow (or a compromised
  step) rewrite history, protections, or other workflows.
- **Mitigation:** workflows declare least `permissions:` blocks
  (`.github/workflows/measured-benchmark.yml` uses `contents: write` only —
  sufficient to publish status/releases, insufficient to modify workflow
  files, which require the `workflows` scope); agent-side pushes in this
  program are constrained to tokens *without* workflow scope, so
  `.github/workflows/*` cannot be modified by automation (a known constraint:
  the packaging non-fatality edit in
  `docs/PACKAGING_STATUS_SEPARATION.md` is staged for human review precisely
  because it needs workflow-scope credentials).
- **Enforcement:** cryptographic (platform-enforced token scopes), plus
  procedural review for any workflow change.
- **Residual risk:** LOW for automation-driven workflow tampering; MODERATE
  in the other direction — the constraint blocks *legitimate* automation too
  and pushes workflow edits into manual, less-auditable channels.

---

## Summary table

| # | Threat | Enforcement | Residual |
|---|--------|-------------|----------|
| T1 | Held-out leakage | procedural | LOW |
| T2 | Post-hoc frozen-artifact mutation | cryptographic (pins) | LOW (pinned set) |
| T3 | Artifact substitution | cryptographic (sha carry-through) | LOW |
| T4 | Stale-cache contamination | cryptographic (hash-verified inputs) | LOW |
| T5 | Mutable model references | exact-pin (crypto-effect) | LOW |
| T6 | Compromised provenance | procedural + journal hashes | MODERATE (journal deletion) |
| T7 | Synthetic→measured promotion | procedural (labels) | LOW–MODERATE |
| T8 | Runner/environment drift | exact-pin hard gate | LOW |
| T9 | Log-attested evidence limits | procedural (disclosure) | MODERATE (inherent to D2-0004) |
| T10 | Workflow-scope token constraints | cryptographic (platform scopes) | LOW / workflow-edit friction |

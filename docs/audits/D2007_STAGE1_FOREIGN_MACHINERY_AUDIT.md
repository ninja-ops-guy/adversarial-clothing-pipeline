# D2-0007 — Independent Audit of Foreign-Landed Stage-1 Screening Machinery

**Audit date:** 2026-09-11T05:09Z · **Auditor:** independent audit lane (fresh clone, no science modified)
**Repo HEAD at audit:** `ea103f04c721eb404aee2fe0061076f2116a099a` (main)
**Scope:** foreign-lane Stage-0 gate, Amendment A1, frozen Stage-1 config, screening core, scripts, self-arming overlay, Stage-1 CI workflow. This audit re-derived no scientific conclusions and accessed no held-out surface.

## Hash pins (audit-time working tree @ ea103f0)

| Surface | SHA-256 |
|---|---|
| `docs/PREREGISTRATION_D2-0007.md` | `38b955d5b60e3428cce84a8c6b849fbcb61b153a4b3fb3a3040aa730d6e1564f` (matches config/arming pins) |
| `generations/RAC-PER-D2-0007.json` | `3efd0ddd6ca00c9a9f4ee15ef233eac2d8733cf235ef669927dc8665d072efef` (matches pins; still `PREREGISTERED`, `armed:false`) |
| `configs/d2007_stage1_screening_v1.json` | `94526c4d0a90485d95b193e20bea139595a0d0892431b83dcfae60cef2611237` |
| `docs/PREREGISTRATION_D2-0007_AMENDMENT_A1.md` | `2e5a1fa2bec871f5c8ceaf77510c733bbbfa8f69ba7d8eae34c7310b8f56f715` |
| `ruthless_pipeline/patterns/d2007_screening.py` | `25df27197940e1d87ac2fbdd9da7f08c77212e937b6b8ed6e869e15c3a36dc8b` |
| `scripts/d2007_motif_screen.py` | `96d8a72c02d12f87d7368923817f57599cd49c60a0055efd579e25f57df42727` |
| `scripts/d2007_aggregate_screening.py` | `eab49d4ec9912c3da289cd4705b37ada0684c551b174c8e7430562d7e1dcf6c6` |
| `evidence/d2-0007/stage0-landmark-free-smoke-closure.json` | `065b17040ee1b76893e770779ab204f59430bf1883881ab69c409c437299d187` |
| `evidence/d2-0007/stage1-arming.json` | `67f47587b9defdb94a0c82485ec0c5f29c6a12161e7f471d600159619e439f97` |
| `.github/workflows/d2007-stage0-smoke.yml` | `ef48941cb9d247300d71ad0b6aba2beb7e87827c8c02cf78a056278938e4b514` |
| `.github/workflows/d2007-stage1-screening.yml` | `cedebcf9c01884b093fdd429158ccbf7f0ea0705ae9e7adf60336df5114f7a0e` |

## 1. CONFIG FIDELITY — **PASS** (seed derivation reconciliation: amendment-governed, defensible)

`configs/d2007_stage1_screening_v1.json` implements the preregistered stopping rule in `generations/RAC-PER-D2-0007.json` (`motif_screening.stopping_rule` / `decision_rule`):

- **8 P0 generators, frozen order** — config `generator_order` equals `generations/RAC-PER-D2-0007.json::motif_screening.generator_set` in the same order, and `d2007_screening.py:128-133` hard-fails if runtime `P0_GENERATORS` order drifts from the freeze.
- **8 compositions/generator, 64 total** — `budget.compositions_per_generator=8`, `total_compositions=64`; enforced at `d2007_screening.py:139-142` and in `close_screening` (`:277-280`, requires exactly the 64 unique (generator, composition) pairs).
- **Root seeds `[20270110, 20270111, 20270112]`** — enforced byte-exact at `d2007_screening.py:136-138`.
- **max 4 candidates admitted** — `max_candidates_admitted_to_optimization=4`, enforced `:143-144` and applied as `survivors[:cap]` at `:337-338`. Workflow aggregate assert `admitted_count <= 4` (`d2007-stage1-screening.yml:178`).
- **optional stopping / budget extension** — both `false`, enforced `:145-146`.

**3 seeds vs 8 compositions reconciliation.** The preregistration froze three root seeds *and* 8 compositions/generator but did not serialize the expansion. Amendment A1 (committed **before** any Stage-1 run, with declared Stage-0 telemetry exposure) froze the expansion: composition `i` uses `root_seeds[i mod 3]`, then a deterministic hash — first 8 bytes of SHA-256 over `RAC-PER-D2-0007|stage1|generator_index={g}|composition_index={i}|root_seed={root}`, big-endian, masked to 63 bits — yielding 64 distinct derived seeds, all serialized in the config (`derived_seeds_by_generator`). **This audit independently recomputed all 64 derived seeds from the A1 rule: exact match with the serialized schedule.** `d2007_screening.py:148-162` re-derives and hard-fails on any drift. Verdict: a genuine under-specification in the parent preregistration, but it was closed by a pre-execution amendment (A1) rather than silently post-hoc — a defensible, amendment-governed reading, not an unamended discrepancy.

**Survivor decision rule vs prereg.** `close_screening` (`d2007_screening.py:296-336`) applies exactly: mean per-surrogate absolute detection-rate reduction ≥ 0.15, strictly positive improvement on ≥ 4 of 6 surrogates (enforced: exactly 6 models required, `:289-290`), `invalid_condition_fraction ≤ 0.10`, best-of-8 per family with preregistered tie-breaks, cap of 4 admitted. `"No surviving motif ⇒ no adapter, screened-out null"` is implemented as `preregistered_h0_screened_out: not bool(survivors)` (`:359`) with `body_garment_anchor_support_built/optimization_opened/candidate_freeze_created/alpha_002_promoted` all pinned `False` (`:355-358`).

## 2. BOUNDARY INTEGRITY — **PASS**

Traced every code path the Stage-1 workflow executes (arming assert → `verify_runtime_lock.py` → `d2007_motif_screen.py` → boundary assert → `git diff --exit-code` → artifact upload; then `d2007_aggregate_screening.py` → aggregate assert):

- **No held-out loading/reference-by-value.** `d2007_motif_screen.py:96` builds evaluators with `roles={"surrogate"}` only; `:38-45` requires model set id `PERSON-SUR-v3`, `role=surrogate`, exactly 6 unique models; `:106-107` hard-exits if the benchmark config contains held-out models; surrogate weight state hashes are verified against the manifest (`:100-103`). `PERSON-HO-v3` appears in the executed code only as a string constant used to *reject* wrong boundary identity (`d2007_screening.py:28,123-126`). The aggregator loads no models at all. Held-out is hash-referenced only (per `benchmarks/frozen_surface_sha256.json`).
- **No anchor/provider construction.** Config geometry `PATTERNS_CANONICAL_128_V1` is generator-local 128×128 motif canvas geometry (A1 §2: not person keypoints/garment anchors); no anchor provider schema is instantiated; candidates are stamped `body_garment_anchor_used: False` (`d2007_screening.py:244`) and `build_observation` rejects any candidate claiming otherwise (`:257-258`).
- **No optimization, no candidate freeze, no Alpha-002 promotion** anywhere in the executed paths; both workflow jobs assert these flags are `False` in every partial and in the aggregate (`d2007-stage1-screening.yml:109-116, 176-182`), and both jobs end with `git diff --exit-code` against tracked frozen surfaces.
- **EXPLORATORY / hypothesis-screening labeling throughout:** `evidence_scope: "surrogate-only hypothesis screening; not transfer/efficacy evidence"`, `evidence_class: "internally_measured"` in every emitted record.
- **Fail-closed assertions verified by adversarial exercise** (this audit ran them, not just read them): clean spec validates against repo root; each of root-seed drift, screening-set substitution to `PERSON-HO-v3`, seed-schedule tamper, weakened guard, threshold drift, and status drift raises `D2007ScreeningError` with the correct message; `close_screening` with 0 observations raises (requires exactly 64). Module's own tests pass: `tests/patterns/test_d2007_screening.py`, `test_d2007_smoke.py`, `test_d2007_stage0_closure.py` (15 passed).
- **`scripts/select_surrogate_candidate.py`** is a pre-existing D2-0004-era script (last touched `d123efe`, `21ca0a6`, `db3be44` — all pre-Stage-1); the Stage-1 machinery imports only its `make_config` helper (`d2007_motif_screen.py:34`). Its `main()` gates a schema-3.0 candidate pool with `heldout_feedback_allowed=false` and `design_profile_sha256`, and is invoked only by the pre-existing `adaptive-candidate.yml` / `measured-benchmark.yml` workflows — **never** by `d2007-stage1-screening.yml`. It therefore cannot be triggered by, or ahead of, Stage-1 aggregation.

## 3. EXECUTION EVIDENCE — **Stage-0 PASS; Stage-1 IN FLIGHT at audit time**

From the GitHub Actions API (public, queried 2026-09-11T05:0xZ) and repo receipts:

- **Stage-0:** run `34561027145`, head `59143b12`, **completed success** — matches the persisted PASS closure `evidence/d2-0007/stage0-landmark-free-smoke-closure.json` (`workflow_run_id: 34561027145`, telemetry sha `93bebada…34bc`).
- **Pre-execution verification CI** on `c7fa80b` (run `34561631754`): **success** — matches the arming record's six PASS rows.
- **Stage-1 attempt 1:** run `34561891542` on `5efd79a`, **completed failure** — matches the arming record (`ABORTED_PRE_INFERENCE`, 0 observations; workflow guard read `stage0_telemetry_sha256` at the wrong JSON path). Fixed by `c2f2282` (1-line workflow fix binding the guard to the nested `stage0_gate` field) and re-triggered from identical frozen scientific inputs by `09dc60d` (arming `execution_attempts` + `trigger_revision: 2` — consistent with the declared infrastructure-retry policy).
- **Stage-1 attempt 2:** run `34561945925` on `09dc60d` — **in_progress at audit time**: `screen-g1` completed success; `screen-g0, g2–g7` in progress; `aggregate` job not yet started. **No Stage-1 results are committed anywhere in the repo** (`git log --all -- benchmarks/runtime/d2-0007` empty; no screening-result artifact on any branch). Results, when produced, will exist only as CI artifacts with `retention-days: 90` (`d2007-stage1-screening.yml:134, 203`). The audit therefore records: 8×8 = 64 observations not yet complete; no aggregate `screening-result.json` hash exists to pin; results-at-risk-of-expiry if not persisted within 90 days of the run.

## 4. GOVERNANCE DISPOSITION — **REQUIRES_USER_RATIFICATION**

<!-- doclint:allow check="broken-path" reason="backticked references in this section carry :line,col source-location suffixes (e.g. docs/D2-0005_ARMING_PACKET.md:7,271-283, docs/PREREGISTRATION_D2-0005_AMENDMENT_A5.md:12,348); the target files exist in the repo — only the citation suffixes make the literal tokens unresolvable" -->
<!-- doclint:allow check="stale-d2-0005-armed" reason="this section describes the D2-0007 Stage-1 arming overlay (evidence/d2-0007/stage1-arming.json) and cites D2-0005 arming-governance precedent; it does not describe D2-0005 itself as armed" -->

Facts: `evidence/d2-0007/stage1-arming.json` (`armed:true`, additive, parent untouched) armed Stage 1 and the workflow ran real surrogate inference, with **no recorded user sign-off**. Precedent: `docs/D2-0005_ARMING_PACKET.md:7,271-283` and `docs/PREREGISTRATION_D2-0005_AMENDMENT_A5.md:12,348` establish that arming "requires explicit user sign-off regardless of all other gates" — the READY_TO_ARM packet is a *request*, the user decision is the gate. The foreign lane broke that discipline.

Balancing factors: (a) the user's D2-0007 plan explicitly endorses cheap surrogate screening as hypothesis screening and allows surrogate/development results to influence selection (held-out may not); (b) the armed scope is exactly the frozen 64-composition PERSON-SUR-v3 screen — inside the endorsed plan; (c) the arming was executed as an additive overlay preserving the frozen parent (armed:false), with pre-execution CI verification and declared Stage-0 telemetry exposure; (d) everything executed is **reversible/repeatable** (surrogate inference on public fixtures; no held-out access — the irreversible boundary — occurred; no anchor/optimization/freeze/promotion state advanced).

Verdict: **REQUIRES_USER_RATIFICATION** — within the endorsed scientific plan and not a boundary violation, but the self-arming deviates from repo arming governance and must be ratified (or the Stage-1 observations discarded and re-run) by explicit user decision before any downstream stage consumes the results. Nothing irreversible happened; ratification can legitimately be retrospective because all scientific inputs were frozen before any Stage-1 observation and the retry policy was honored.

## 5. SUITE STATE @ ea103f0

`pytest tests --ignore=tests/e2e -p no:cacheprovider`: **2050 passed, 3 failed, 1 skipped** (225 s). Failures, all pre-existing and unrelated to Stage-1 machinery:
- `tests/test_provenance_graph.py::test_committed_graph_rederives_exactly` — committed provenance graph sha (`ae66bbad…`) ≠ re-derived (`0541e186…`); stale Lane-A1/E artifact after newer module commits.
- `tests/test_stale_artifacts.py::test_report_is_machine_readable_and_deterministic` and `::test_current_repo_artifact_surfaces_fresh_via_cli` — the new program-state/stale-artifact checker reports non-FRESH surfaces (same root cause: artifacts not regenerated at HEAD).

No D2-0007 test fails; the Stage-1 screening/smoke/stage0-closure tests all pass.

## Audit boundaries

NO_SCIENCE_MODIFIED=true (audit added only this document). HELDOUT_ACCESSED=false (no held-out model, weight, or value-surface was loaded or queried; verification was by code trace, negative tests, and public CI API). WORKFLOWS_PUSHED=false. The Stage-1 attempt-2 aggregate outcome post-dates this audit and is explicitly unverified.

# RAC Studio UX Specification — Unified Design / Research / Capture / Evidence

**Status:** SPECIFICATION ONLY. This document defines work to be performed **after the current experiment wave** (D2-0004 re-run, D2-0005 arming). Nothing here is implemented; nothing here changes any frozen contract, protocol, model manifest, generation, benchmark, or workflow.
**Grounded at:** commit `b4fe0e5` ("ci: land Wave G runtime lock workflow fixes").
**Audience:** the single operator of this pipeline, and any future collaborator.

---

## 0. Why this spec exists

The program currently operates through three disconnected surfaces:

- **`product-studio.html` / `product-studio.js`** — client-side Design surface (tile generation, frozen-candidate loading, fidelity scoring, 4096×5119 export).
- **`capture-lab.html` / `capture-lab.js`** — physical Capture surface (7-step SOP strip: Experiment → Calibration → Control → Candidate → Motion → Review → Seal; freeze hash, blinded outcomes, sealed immutable sessions).
- **Scripts + docs + CI** — the Research/Evidence layer: `scripts/build_d2_bundle.py`, `scripts/verify_runtime_lock.py`, `scripts/freeze_adaptive_candidate.py`, `ruthless_pipeline/certification/*`, preregistrations, amendments, runtime locks.

Every operator mistake this program has recorded (§1) happened at a **seam between these surfaces** — a loader that didn't know its own protocol schema, a runtime pinned by luck instead of by a control the operator could see, an experiment whose outcome status ("never observed") existed only in prose. The unified **RAC Studio** exists to make the governance state of every artifact *visible before an action is taken*, so the next mistake is caught by the UI rather than by a postmortem.

**Non-negotiable framing:** the UI is a *display and gating layer* over the existing fail-closed machinery (`ruthless_pipeline/certification/evidence.py`, `verify_frozen_model_contract`, CI gates). The UI must never become the enforcement mechanism of record; it makes enforcement legible. Where this spec says "the UI blocks X", it means the UI surfaces the block that the underlying tooling already enforces (or must be extended to enforce) — fail-closed semantics remain in code and CI.

---

## 1. Operator-mistake postmortems → UI guardrails

Each entry cites the real incident/mechanism (with source) and derives the concrete guardrail. Guardrail IDs (G1–G10) are referenced throughout §2–§4.

### PM-1 — The step-18 loader failure (D2-0004)

**Incident (source: `docs/AMENDMENT_D2-0004_INFRA-001.md` §1–2):** CI run 34147902820 completed held-out inference (step 17) and then died in ~1 second at step 18, `scripts/build_d2_bundle.py`, because `load_protocol()` constructed a frozen dataclass `CertificationProtocol` lacking the `generation_id` field that protocol `RAC-PERSON-DETECT-1.2` (added in `581ba5e`) was the first to carry. `TypeError: CertificationProtocol.__init__() got an unexpected keyword argument 'generation_id'`. The protocol was correct; the **loader was stale**. Fixed by `7148202d`. No evidence bundle was built; the step-17 output was never inspected.

**What the operator lacked:** any way to see, *before triggering a run*, that the checked-out tooling could not parse the preregistered protocol. The schema incompatibility was invisible until it killed a one-shot experiment mid-flight.

**Guardrails:**
- **G1 — Loader/schema compatibility banner (P0).** Every experiment card in the Research view shows the result of a dry "can the current tooling load this protocol/generation?" check (the equivalent of importing `ruthless_pipeline.certification.protocol.load_protocol` against `protocols/RAC-PERSON-DETECT-1.2.json` and the generation file). States: `COMPATIBLE` (green), `LOADER STALE — <exception summary>` (red, run buttons disabled). Derives directly from PM-1: the exact exception class and field name are displayed, because that is what the operator had to reconstruct by hand from CI logs.
- **G2 — Run-step provenance rail (P1).** For a running experiment, a step strip (like Capture Lab's SOP strip, but for the benchmark workflow) showing each step's status, so a failure at "step 18 of N, died in ~1s, before verification logic ran" is visible as a distinct failure class ("infrastructure crash, no scientific output produced") rather than "run failed".

### PM-2 — The version-drift near-miss (19 minutes of luck)

**Incident (source: `docs/AMENDMENT_D2-0004_INFRA-001.md` §1, §6):** the runner resolved torchvision `0.29.0+cpu`, ultralytics `8.4.142`, transformers `4.57.6` — exactly the frozen manifest versions — but ultralytics 8.4.143 hit PyPI **19 minutes after** the unpinned install finished. The match was luck, not a control. Permanent fix: `benchmarks/runtime_lock.json` (python 3.11, torch 2.14.0+cpu, torchvision 0.29.0+cpu, ultralytics 8.4.142, transformers 4.57.6) is now the machine-readable source of truth, installed exactly and hard-gated by `scripts/verify_runtime_lock.py` before any model download or inference, with exact-string comparison semantics (`+cpu` significant, no normalization).

**What the operator lacked:** a visible, pre-run statement of "the runtime you are about to execute on vs. the runtime the frozen contract requires." The drift window was invisible.

**Guardrails:**
- **G3 — Frozen-runtime lock status banner (P0).** A persistent banner in Research and Capture views showing the runtime lock: the five pinned strings from `benchmarks/runtime_lock.json`, the live environment's resolved versions, and `MATCH` / `MISMATCH` per package with exact-string semantics (including `+cpu`). MISMATCH state hard-disables every "run / arm / analyze" control in the UI. This is the UI face of `scripts/verify_runtime_lock.py`.
- **G4 — "Pinned vs. floating" indicator on every install/trigger action (P1).** Any action that installs dependencies shows whether versions come from the lock file or from a floating resolver, so "unpinned install" can never again be a silent default.

### PM-3 — The one-shot boundary risk

**Incident (source: `docs/AMENDMENT_D2-0004_INFRA-001.md` §5):** the single authorized re-run of D2-0004 was legitimate *only because* "the experiment's outcome was **never observed**: step 18 crashed in the loader before building or verifying any evidence, nothing was published, and no held-out result was seen by any person or consumed by any selection process." The workflow itself blocks a run "if published held-out evidence for this generation already exists" (`measured-benchmark.yml` guard, cited in §7 of the amendment). The re-run count is governance: exactly ONE re-run authorized; any further re-run needs a new amendment.

**What the operator lacked:** the "outcome never observed" fact existed only as prose in an amendment. Whether a generation still has its one shot — and how many re-runs remain under amendments — was not queryable at a glance.

**Guardrails:**
- **G5 — "Outcome never observed" state chip (P0).** Every generation carries a chip: `OUTCOME: NEVER OBSERVED` (green — one-shot intact), `OUTCOME: OBSERVED <timestamp> <bundle hash>` (blue — sealed), or `OUTCOME: PARTIALLY PRODUCED / NOT OBSERVED` (amber — the PM-1 state: step-17 output existed but was never inspected). The chip is derived from evidence-bundle existence and observation records, not from prose. Run/arm controls are disabled unless the chip is `NEVER OBSERVED` or a valid amendment explicitly authorizes the attempt (see G6).
- **G6 — Re-run allowance counter (P0).** Where an amendment authorizes re-runs (D2-0004-INFRA-001: exactly 1), the UI shows `RE-RUNS AUTHORIZED: 1 · CONSUMED: 0` with a link to the amendment document and its hash. Attempting a trigger when CONSUMED = AUTHORIZED requires a new amendment artifact, mirroring amendment §3.

### PM-4 — Pre-arming tuning temptation (D2-0005 design analysis)

**Incident (source: `docs/DESIGN_ANALYSIS_D2-0005.md`):** a deterministic simulation computed the operating characteristics of the frozen D2-0005 design (power curves over Δ_true × discordance × n). The document explicitly forbids using those curves to change the preregistered thresholds (0.20 `INCONCLUSIVE_WIDTH_MAX`, CVaR α = 0.5, decision regions) after seeing them — "post-hoc tuning wearing pre-arming clothes." Legitimate outputs are only (a) capability characterization or (b) pre-arming design amendment / exploratory declaration via the §7/§9 amendment route of `docs/PREREGISTRATION_D2-0005.md`.

**What the operator lacked:** the boundary between "looking at operating characteristics" (allowed) and "editing a frozen threshold" (forbidden) is currently enforced only by discipline.

**Guardrails:**
- **G7 — Frozen-field lockout with amendment-only edit path (P0).** In the Research view, every preregistered field (thresholds, model sets, candidate policy, seeds, decision regions) renders read-only with a lock icon and the preregistration hash. Editing is impossible inline; the only affordance is "Propose Amendment", which creates a new amendment document linked in the target's amendment log — mirroring the §9 amendment log of `PREREGISTRATION_D2-0005.md` and the A1–A4 history.
- **G8 — Evidence-label chips on all displayed numbers (P1).** The six-label governance used in `DESIGN_ANALYSIS_D2-0005.md` (`scenario_assumption`, `target`, `speculative_open`, etc.) becomes a mandatory chip on every numeric display, so synthetic/scenario numbers can never be visually confused with observed evidence.

### PM-5 — Dependency ordering between generations

**Incident (source: `docs/PREREGISTRATION_D2-0005.md` header):** "D2-0004 … must close first; D2-0005 MUST NOT be opened, executed, or trigger-wired while D2-0004 is open." At commit `b4fe0e5`, D2-0005 is a frozen skeleton (`lock_status: PREREGISTERED`, `lock_inference_performed: false`, triggers NOT armed) while D2-0004 remains open. This ordering constraint lives in prose.

**Guardrails:**
- **G9 — Dependency gate display (P0).** Generation cards show declared dependencies (`depends_on: RAC-PER-D2-0004 → status OPEN`) and the UI disables open/arm/trigger controls while any dependency is not `CLOSED`. The blocked control shows *why* ("D2-0004 status: READY_FOR_FRESH_HELDOUT_RUN — close required by preregistration").

### PM-6 — Evidence-class and promotion boundaries

**Mechanism (source: `docs/CERTIFICATION_SYSTEM.md`):** evidence states RAC-D0→D1→D2→P1→P2→M1→M2; "Digital evidence may never satisfy a physical or manufacturing state. Physical evidence may never satisfy a manufacturing state without manufacturing evidence." Certificate issuance is fail-closed (preregistered protocol, distinct surrogate/held-out sets, pattern/master hash, source commit, baseline-qualified held-out results, sealed bundle; physical/manufacturing states require their corresponding evidence). Observations are `valid` / `invalid` / `excluded`; invalid conditions never enter aggregates; "control not detectable" is invalid and cannot count as adversarial success. Golden-sample certificates do not transfer to production lots.

**Guardrails:**
- **G10 — Evidence-class color coding + promotion gate checklist (P0).** Every artifact, bundle, and certificate carries a class badge (`SYNTHETIC` / `DIGITAL-HELDOUT` / `PHYSICAL` / `MANUFACTURING`) with a fixed color, and every state transition shows the fail-closed checklist from `docs/CERTIFICATION_SYSTEM.md` with per-item status. A transition whose requirements are unmet renders the target state chip as `INELIGIBLE — <missing items>`; there is no override affordance in the UI (overrides are amendments, per G7).

---

## 2. View-by-view specification

Global chrome: view switcher (Design / Research / Capture / Evidence), the G3 runtime-lock banner, and a "current open generation" indicator (today: `RAC-PER-D2-0004 · OPEN`).

### 2.1 Design view (evolution of `product-studio.html`)

- **Purpose:** generate, score, and freeze pattern candidates; prepare print assets. Unchanged core: family/style-spec tile generation (`RACPatternComposition.buildStyleSpec`), reference-fidelity scoring (`RACReferenceScorer.score`), variation presets, 4096×5119 export, frozen-tile loading (`loadFrozenTile`).
- **Primary entities:** product type (hoodie/hat/beanie/cargo/mask/shirt), design family (signal_shadow / machine_static / ghost_hound / broken_human / error_garden), candidate tile, fidelity score, master-art hash, candidate pool (exactly 100 Product Studio candidates for D2-0004 per amendment §4), print-test kit (`scripts/build_print_test_kit.js`, `scripts/package_print_test_kit.py`, `print-test-kit-status.json`, protocol `protocols/RAC-PHYSICAL-PRINT-TEST-1.0.md`).
- **Key states:** `draft` → `scored (fidelity N/100)` → `frozen (hash)` → `in candidate pool` → `winner (frozen before held-out inference)` → `promoted to print-test kit`. Chips: G8 evidence label (`scenario_assumption`/`design`), master-art SHA-256.
- **Error-prevention controls:**
  - Frozen-candidate mode (the existing `frozenTileOverride` mechanism) is a distinct visual mode: border, banner "FROZEN CANDIDATE — parameters locked", all seed/scale/density/distress controls disabled. Today a frozen tile can be loaded while parameter controls remain live, inviting accidental divergence between displayed parameters and the frozen art (PM-4 class of mistake: silent parameter drift).
  - Export button displays the hash of exactly what will be exported *before* download; the hash is recomputed from the canvas, not from cached metadata.
  - Candidate-pool membership is displayed with pool-hash; adding/removing a candidate after pool freeze is blocked (G7 amendment-only path).
- **Provenance affordances:** per-candidate lineage card (seed, family, variation preset, fidelity score + subscores, source commit of `product-studio.js`), link from candidate to the generation(s) that consumed it, print-test-kit manifest with per-file hashes.

### 2.2 Research view (new surface over scripts + certification modules + preregistrations)

- **Purpose:** the operator's control room for generations, protocols, model sets, runtime locks, preregistrations, and amendments — today spread across `generations/*.json`, `protocols/`, `model_sets/`, `model_manifests/`, `benchmarks/`, `docs/PREREGISTRATION_*`, `docs/AMENDMENT_*`, and CI workflows.
- **Primary entities:** generation (`RAC-PER-D2-0004`, `RAC-PER-D2-0005`), protocol (`RAC-PERSON-DETECT-1.2`), model sets (`PERSON-SUR-v3` 6 models; `PERSON-HO-v3` 2 models), runtime lock (`benchmarks/runtime_lock.json`), preregistration, amendment, design analysis (`scripts/design_analysis_d20005.py`).
- **Key states (generation lifecycle):** `draft` → `preregistered (hash displayed)` → `frozen` → `armed` → `running` → `closed (outcome observed)` / `closed (never observed — infrastructure abort)` → `sealed`. Plus G5 outcome chip and G9 dependency gate. D2-0005 today: `PREREGISTERED · NOT ARMED · depends on D2-0004`.
- **Error-prevention controls:** G1 loader-compatibility banner, G3 runtime banner, G5/G6 one-shot chips and re-run counters, G7 frozen-field lockout, G9 dependency gates. The "Trigger run" button is a multi-confirm dialog that restates: protocol hash, runtime lock MATCH status, re-run allowance, and the sentence "this consumes the one shot for generation X" (or "this consumes re-run 1 of 1 under amendment D2-0004-INFRA-001").
- **Provenance affordances:** preregistration hash displayed verbatim (truncated with copy, never silently shortened in exports); amendment log per generation (timeline rendering of the §9-style log: A1–A4 for D2-0005, INFRA-001 for D2-0004) with document hashes; model-set lineage showing surrogate vs held-out set membership and the distinctness check; runtime-lock diff view (lock vs live, per G3); design-analysis operating-characteristics viewer that displays G8 labels on every cell and shows the forbidden-action notice from `DESIGN_ANALYSIS_D2-0005.md` next to any threshold it references.

### 2.3 Capture view (evolution of `capture-lab.html`)

- **Purpose:** physical evidence capture sessions — already the strongest surface (freeze hash, blinded outcomes, matched control/candidate pairs, calibration gate, sealed immutable session, per-capture SHA-256 ledger). Preserve the 7-step SOP strip verbatim.
- **Primary entities:** capture session (`RAC-CAP-*`), arms (control/candidate), stills/videos, condition tuple (distance, yaw, pose, lighting), frozen session manifest, analysis contract (models + thresholds + preprocessing + motion sampling), physical evidence bundle.
- **Key states:** `unfrozen` → `frozen (freeze_sha256)` → `capturing (arm)` → `pair valid` → `analysis contract frozen` → `sealed · immutable`. Class badge: `PHYSICAL` (G10).
- **Error-prevention controls (additions to existing):**
  - Analysis-contract ensemble presets (`surrogate` / `heldout`) must display the model-set ID they correspond to (`PERSON-SUR-v3` / `PERSON-HO-v3`) and warn loudly if a *held-out* set is attached to a session whose linked generation is still in surrogate phase (held-out boundary leak — the most expensive possible capture mistake; see §3-I2).
  - Seal is blocked unless calibration passed and matched pair complete (existing); the UI additionally requires the linked generation's state to be capture-eligible (e.g., winner frozen) before freeze, preventing orphaned physical sessions.
  - Hash fields validate 64-hex (existing) and additionally show a "hash seen before?" check against the local ledger to catch copy-paste of a stale generation hash (PM-1 class: silent schema/identity mismatch).
- **Provenance affordances:** the existing ledger becomes an append-only hash chain display (each capture row shows prev-hash → hash), the exported session JSON links to `scripts/analyze_capture_session.py` output, and sealed sessions link forward into Evidence view.

### 2.4 Evidence view (new surface over `ruthless_pipeline/certification/*`)

- **Purpose:** the read-mostly ledger of everything the program has *established*: evidence records, bundles, certificates, and their RAC states. Wraps `evidence.py` (state/type boundaries), `artifact_bundle.py`, `certificate.py` (fail-closed issuance), `registry.py`, `report_compiler.py`, `verification.py`, and `docs/RESEARCH_EVIDENCE_REGISTER.md`.
- **Primary entities:** evidence record (RAC state, evidence type, source/fixture, ISO-8601 timestamp, source commit, exact config, SHA-256 artifact hashes, model/preprocessing/threshold metadata), evidence bundle (`hashes.sha256`, `certificate.json`), certificate, observation (valid/invalid/excluded), production artifacts (`production_alpha/ORDER_CHECKLIST.md`, `PRINTFUL_PRODUCT_RESOLUTION.md`, `SKU_MANIFEST_DRAFT.json`, `docs/PRODUCTION_ALPHA_SKU.md`).
- **Key states:** per-record `valid` / `invalid (reason)` / `excluded`; per-state eligibility: `eligible` / `ineligible — <missing requirements>`; certificates `issued` / `refused (fail-closed)`. States RAC-D0 through RAC-M2 rendered as a ladder with the current artifact's position and the G10 checklist for the next rung.
- **Error-prevention controls:** no edit affordances at all for sealed bundles; verification action (`tools/certify_bundle.py verify`) surfaced as a one-click "verify hashes" with byte-level result; invalid/excluded observations rendered but visually quarantined so they can never be misread as aggregates ("control not detectable" rows explicitly labeled "INVALID — cannot count as adversarial success" per `CERTIFICATION_SYSTEM.md`).
- **Provenance affordances:** lineage graph from master-art hash → surrogate evidence (D1) → held-out evidence (D2) → physical trials (P1/P2) → golden sample (M1) → lot conformity (M2); bundle hash-chain browser; certificate panel showing every fail-closed requirement and the artifact hash satisfying it; amendment cross-links wherever a bundle exists because of an amendment (D2-0004 bundle → INFRA-001).

---

## 3. Cross-view invariants the UI must enforce visually

- **I1 — One-shot rule (PM-3, G5/G6).** No view may present an executable "run held-out inference" affordance for a generation whose outcome has been observed, or whose re-run allowance is exhausted, unless a new amendment artifact exists and is linked. The invariant is visible as the outcome chip everywhere the generation appears (Research cards, Capture linking dropdown, Evidence lineage).
- **I2 — Held-out boundary (PM-4, PM-6; `heldout_feedback_allowed: false`, distinct `PERSON-SUR-v3`/`PERSON-HO-v3` sets).** Surrogate artifacts and held-out artifacts carry different class badges; no surrogate-phase screen may display held-out model names as selectable; the candidate-selection flow shows "surrogate-only" as a banner. Any screen that would mix sets (e.g., Capture analysis contract preset) warns per §2.3.
- **I3 — Synthetic vs physical evidence classes (PM-6, G8/G10).** The class badge is global and unremovable: `SYNTHETIC`/`scenario_assumption` numbers (design analysis, simulations) never share visual treatment with `DIGITAL-HELDOUT` observations or `PHYSICAL` captures. "Digital evidence may never satisfy a physical or manufacturing state" renders as a hard stop on the Evidence ladder, not a tooltip.
- **I4 — Promotion gates (PM-6, G10).** Every RAC state transition displays its fail-closed checklist inline; `INELIGIBLE` is a first-class visible state with named missing items; no UI path bypasses the checklist (bypass = amendment document, G7).
- **I5 — Frozen means frozen (PM-1, PM-4, G1/G7).** Anything displaying a preregistration/freeze hash renders the underlying fields read-only everywhere; the loader-compatibility banner (G1) appears on every view when the tooling cannot parse a frozen artifact the view would touch.
- **I6 — Dependency ordering (PM-5, G9).** Declared cross-generation dependencies gate controls in all views (e.g., Capture cannot freeze a session linked to D2-0005 while D2-0004 is open).

---

## 4. Prioritized backlog

Effort in ideal engineer-days (d), assuming the unified shell is a thin local web app over the existing files and modules (read-only by default). Dependencies reference existing tooling.

| # | Item | View | Pri | Effort | Depends on | Derives from |
|---|------|------|-----|--------|-----------|--------------|
| B1 | Unified shell + view switcher + global chrome (runtime banner slot, open-generation indicator) | all | P0 | 3d | existing HTML/JS surfaces | — |
| B2 | G3 runtime-lock banner reading `benchmarks/runtime_lock.json` + `verify_runtime_lock.py` semantics (exact-string, `+cpu` significant) | Research, Capture | P0 | 2d | `scripts/verify_runtime_lock.py` | PM-2 |
| B3 | G5/G6 outcome chips + re-run allowance counters (data: generation JSON, evidence-bundle presence, amendment docs) | Research, Capture, Evidence | P0 | 3d | `generations/*.json`, `ruthless_pipeline/certification/artifact_bundle.py` | PM-3 |
| B4 | G1 loader-compatibility check (headless `load_protocol()`/generation parse probe) + banner + control lockout | Research | P0 | 2d | `ruthless_pipeline/certification/protocol.py` | PM-1 |
| B5 | G7 frozen-field lockout rendering (preregistered fields read-only, "Propose Amendment" affordance) | Research, Design | P0 | 2d | preregistration/amendment doc conventions | PM-4 |
| B6 | G9 dependency gate parsing + control disable with reason text | Research, Capture | P0 | 1d | `generations/*.json`, prereg headers | PM-5 |
| B7 | G10 evidence-class badges + Evidence ladder with fail-closed checklists | Evidence, all | P0 | 4d | `ruthless_pipeline/certification/evidence.py`, `certificate.py` | PM-6 |
| B8 | Design view: frozen-candidate lockdown mode + pre-export hash display | Design | P0 | 2d | `product-studio.js` frozen-tile path | PM-4 class |
| B9 | Capture view: model-set ID on presets + held-out-leak warning + stale-hash check | Capture | P0 | 2d | `capture-lab.js`, `model_sets/*.json` | I2, PM-1 class |
| B10 | Evidence view v1: record/bundle/certificate browser + one-click verify | Evidence | P0 | 4d | `tools/certify_bundle.py verify`, `hashes.sha256` | PM-6 |
| B11 | G2 run-step provenance rail for benchmark workflows | Research | P1 | 3d | workflow log access | PM-1 |
| B12 | G4 pinned-vs-floating indicator on install/trigger actions | Research | P1 | 1d | `benchmarks/runtime_lock.json` | PM-2 |
| B13 | Amendment timeline component (per-generation amendment log with doc hashes) | Research, Evidence | P1 | 2d | `docs/AMENDMENT_*`, §9-style logs | PM-3, PM-4 |
| B14 | G8 evidence-label chips on all numeric displays | all | P1 | 2d | six-label convention in `DESIGN_ANALYSIS_D2-0005.md` | PM-4 |
| B15 | Lineage graph (master art → D1 → D2 → P1/P2 → M1/M2) | Evidence | P1 | 4d | `registry.py`, bundle manifests | PM-6 |
| B16 | Capture ledger as visible append-only hash chain | Capture | P1 | 1d | existing per-capture SHA-256 ledger | PM-3 |
| B17 | Design-analysis OC viewer with forbidden-action notice | Research | P1 | 2d | `scripts/design_analysis_d20005.py` artifact | PM-4 |
| B18 | Candidate-pool freeze display (pool hash, membership locked) | Design, Research | P2 | 2d | candidate-pool export scripts | PM-4 |
| B19 | Production/lot conformity panels (`production_alpha/` order docs, golden-sample vs lot) | Evidence | P2 | 3d | `production_alpha/`, manufacturing.py | PM-6 |
| B20 | Print-test-kit builder UI (wraps `build_print_test_kit.js` / `package_print_test_kit.py`, status from `print-test-kit-status.json`) | Design | P2 | 3d | print-test-kit scripts | PM-6 |

**P0 list (execution order):** B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8 → B9 → B10. Total ≈ 25d.

---

## 5. NON-GOALS for the current wave

1. **No implementation at all during the current wave.** This spec is docs-only. D2-0004 re-run, D2-0005 arming, and all frozen contracts proceed exactly as preregistered; nothing here may be used to justify touching `generations/`, `protocols/`, `model_manifests/`, `model_sets/`, `design_profiles/`, `benchmarks/`, or `.github/workflows/` now.
2. **No new enforcement logic.** The Studio is a display/gating layer. Fail-closed enforcement stays in `ruthless_pipeline/certification/*`, `scripts/verify_runtime_lock.py`, and CI. The UI must never become the only place a rule is checked.
3. **No replacement of the document-based governance trail.** Preregistrations and amendments remain hashed markdown documents; the UI links to and renders them, it does not absorb them.
4. **No collaboration/multi-user features, no cloud backend, no accounts.** Single-operator local tool for this wave.
5. **No real-time inference in the browser.** As Capture Lab already states: "Browser does not fabricate inference" — analysis remains the job of `scripts/analyze_capture_session.py` and authorized runners.
6. **No redesign of the Design surface's generative core.** Pattern composition, fidelity scoring, and export formats are frozen inputs to this spec, not targets.
7. **No retrospective modification of any existing evidence, bundle, amendment, or amendment log** — including rendering layers that would rewrite history rather than link to it.

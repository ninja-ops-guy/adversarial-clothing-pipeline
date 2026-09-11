# RAC Current Project Progress Ledger

**Version:** 1.4.0  
**Last updated:** 2026-09-11 America/New_York  
**Reviewed head:** `8114e2189a255bed3d4c07708d7380c7ade2aefc`  
**Authority:** detailed current-state overlay. For the fastest program-level status, start with [`CURRENT_PROGRAM_STATE.md`](CURRENT_PROGRAM_STATE.md). [`PROJECT_PROGRESS.md`](PROJECT_PROGRESS.md) remains the historical September 8 ledger.

> Engineering completion is not efficacy evidence. Software, schemas, simulation, governance, CI, and production-readiness machinery can be complete while physical and manufacturing evidence remain open.

## Executive state

RAC has crossed the main software/integration barriers and is now primarily constrained by real vendor inputs and physical execution.

The two most important changes since the previous current ledger are:

1. **D2-0007 is scientifically closed at Stage 1 as `SCREENED_OUT_H0`.** All 64 planned compositions were evaluated on `PERSON-SUR-v3`; zero motifs met the preregistered survivor rule. No anchors, optimization, candidate freeze, held-out evaluation, or Alpha-002 promotion were authorized.
2. **Alpha-001 is production-prepared without regenerating its source.** The exact historical sealed kit and 4096×4096 pattern were recovered from the original successful benchmark artifact, hash-verified against frozen pins, and bound to a recovery receipt. A fail-closed Printful intake/build release path now exists.

## Current completion snapshot

| Workstream | Current state | Meaning |
| --- | --- | --- |
| Core research software | **ADVANCED / INTEGRATED** | Design, optimization, simulation, evaluation, provenance, reporting, and certification primitives exist |
| Engineering Barriers 0–3 | **CLOSED FOR DECLARED SCOPE** | Synthetic integration and fail-closed composition have documented exits |
| CTM / governance | **INTEGRATED** | Closed governance passes remain valid; later passes/extensions are audit-gated |
| Pattern Genome v1 | **FROZEN** | Later representation work must be additive/versioned |
| D2-0003 | **CLOSED NEGATIVE / RAC-D0** | Retained; Alpha-001 remains bound to this lineage |
| D2-0004 | **CLOSED NEGATIVE / RAC-D0** | Retained and immutable |
| D2-0005 | **PREREGISTERED / NOT ARMED** | No change from D2-0007 or P1 production work |
| D2-0007 | **CLOSED — SCREENED_OUT_H0** | 64/64 Stage-1 compositions, 0 survivors, 0 downstream admissions |
| Alpha-001 source recovery | **COMPLETE / HASH VERIFIED** | Exact sealed source recovered; no regeneration, retuning, or lineage rebinding |
| P1 production intake/build | **IMPLEMENTED / FAIL-CLOSED** | Live Printful intake, exact geometry derivation, deterministic archives, candidate/control panel build, and generated UA values |
| P1 release integrity wrapper | **IMPLEMENTED** | Verifies vendor-intake receipt/raw/archive integrity before and after render |
| P1 no-spend readiness | **SOFTWARE-READY** | Existing binder/readiness machinery remains the controlled pending→real-value transition |
| Calibration target generator | **IMPLEMENTED** | Physical fabrication remains user action |
| Authoritative P1 schedule | **FROZEN — 144 TRIALS** | Supersedes the older 108-row planning artifact for execution |
| P1 physical evidence | **OPEN — NOT EXECUTED** | No physical-efficacy result exists yet |
| P2 durability | **OPEN — EXTERNAL** | Requires valid P1 baseline first |
| M1/M2 manufacturing evidence | **OPEN — EXTERNAL** | Requires golden-sample and lot measurements |
| Product efficacy claim | **NOT SUPPORTED** | Must remain bounded to future measured evidence |

## D2-0007 closure

Authoritative closure: `evidence/d2-0007/stage1-screening-closure.json`.

### What executed

- Stage 0 landmark-free wiring smoke: **PASS**.
- Stage 1 motif screen: **executed under frozen rules**.
- Eight preregistered generator families × eight compositions each = **64 observed compositions**.
- Surrogate model set: `PERSON-SUR-v3`.
- Invalid-condition fraction for all family-best observations: `0.0`.

### Survivor rule

A motif needed all of:

- mean absolute detection-rate reduction ≥ `0.15`;
- improvement on at least `4/6` surrogate models;
- invalid-condition fraction ≤ `0.10`.

Several family-best candidates cleared the mean-reduction threshold, but none improved at least four surrogates. Final state:

- `survivor_count = 0`;
- `admitted_count = 0`;
- `generation_status = CLOSED_SCREENED_OUT_H0`.

### Frozen consequences

Because Stage 1 produced zero survivors:

- [x] no body/garment anchor provider was built;
- [x] no Stage-3 optimization/EOT search opened;
- [x] no candidate freeze was created;
- [x] no `PERSON-HO-v3` held-out evaluation occurred;
- [x] no Alpha-002/P1B promotion occurred;
- [x] D2-0005 remained untouched;
- [x] Alpha-001 remained bound to D2-0003.

The closure is a valid negative/screened-out research result, not an unfinished feature branch.

## Alpha-001 source recovery

The exact original Alpha-001 bytes were recovered from GitHub Actions run `34078238095`, artifact `rac-print-test-kit-34078238095`.

Committed receipt: `evidence/p1/alpha001-source-recovery.json`.

Verified pins:

- artifact digest: `sha256:cfde12ec97ceafcf2d51eef989dee83d774e18be53e3f411c9502ed6a2e0e558`;
- sealed kit SHA-256: `b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548`;
- pattern SHA-256: `b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546`;
- pattern dimensions: `4096×4096`.

This closes the prior provenance gap where the repo held hashes but not an immediately available exact source artifact. The binary remains an external/recovered artifact; the repository commits the recovery receipt and frozen hashes rather than silently regenerating the source.

## Production Alpha software state

New production tooling now turns live Printful metadata plus the exact Alpha-001 source into binder-ready production artifacts.

### Canonical operator entry point

`tools/p1_production_release.py`

This wraps `tools/prepare_print_alpha_production.py` and adds fail-closed evidence-integrity checks.

### Intake responsibilities

- fetch or ingest untouched Printful responses;
- validate primary product `388` and fallback/reserve product `257`;
- select an exact White variant for the chosen size;
- require preregistered production placements;
- reject unexpected non-mockup placements pending review;
- join variant print-file mappings to exact printfile dimensions;
- derive millimetre geometry from px/DPI;
- store untouched response bytes;
- create deterministic vendor-source archives;
- emit a self-hashed vendor-intake receipt;
- place no order and authorize no spend.

### Build responsibilities

- verify the vendor-intake receipt and every raw/archive byte;
- require the exact frozen Alpha-001 kit or exact frozen pattern hash;
- tile/fill the frozen candidate without retuning;
- generate exact-size hoodie candidate/control panel files;
- prepare reserve tee panel artifacts where required;
- emit deterministic role/product artwork archives;
- generate binder-ready UA values;
- validate the generated values against the P1 binder contract;
- re-verify vendor evidence after rendering to catch concurrent mutation.

## P1 authority and 108 → 144 reconciliation

The older Print Alpha 108-row sheet is historical planning only.

Current execution authority:

- `physical/p1/P1_CAPTURE_SCHEDULE.json` — **144 trials**;
- `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`;
- `physical/p1/P1_OPERATOR_RUNBOOK.md`;
- `physical/p1/P1_READINESS_FREEZE.json`;
- `tools/p1_no_spend_readiness_gate.py`;
- `tools/p1_bind_ua_values.py`.

Any current operator or README documentation should point to these surfaces.

## CI / verification state

Reviewed head `8114e2189a255bed3d4c07708d7380c7ade2aefc` is green across the active checks observed for this documentation baseline.

The current CI matrix includes successful:

- Python 3.10 full tests, smoke test, and certification-contract tests;
- Python 3.11 full tests, smoke test, and certification-contract tests;
- Python 3.12 full tests, smoke test, and certification-contract tests;
- package build;
- dependency audit;
- lightweight provenance verification;
- site build/deployment checks.

The production-release implementation initially exposed one documentation-lint failure caused by intentionally runtime-generated paths. That was corrected using the repository's existing doclint exception mechanism; the corrected cross-version run completed green.

## Immediate physical critical path

The shortest valid path is now:

```text
1. Choose garment size.
2. Create/use a local Printful token.
3. Run p1_production_release.py intake against live vendor data.
4. Build from the recovered exact print-test-kit.zip.
5. Review generated geometry, variants, hashes, and panel files.
6. Run p1_bind_ua_values.py --check-only.
7. Bind only after the dry check is clean.
8. Re-run p1_no_spend_readiness_gate.py and require PASS.
9. Make a separate human spend decision.
10. Order matched candidate/control hoodies.
11. Fabricate RAC-CALT-P1-0001 at exact scale.
12. Perform receipt QA and custody checks.
13. Accept calibration under the frozen rule.
14. Execute the frozen 144-trial P1 schedule.
15. Ingest, validate, seal, then run preregistered analysis.
```

## Software/research work that can still proceed

Software work should now be evidence-driven rather than feature-count driven. Useful work includes:

- publication/report automation that consumes verified evidence rather than mutable status flags;
- pass-specific governance audits where adopted exit criteria exist;
- research hypotheses that create new preregistered generations rather than modifying closed ones;
- physical-data ingestion and analysis hardening that does not invent physical measurements;
- manufacturing/durability tooling needed after P1 yields admissible evidence.

Avoid reopening D2-0007 simply because its screen was negative. A new motif hypothesis should receive a new generation identity and preregistration.

## Explicitly open external work

- [ ] live Printful token / vendor snapshot;
- [ ] actual size selection;
- [x] exact Alpha-001 source recovery;
- [ ] live vendor geometry/variant binding;
- [ ] matched garment procurement;
- [ ] physical calibration-target fabrication;
- [ ] receipt QA and custody;
- [ ] P1 capture;
- [ ] P2 durability;
- [ ] M1/M2 manufacturing conformity.

## Scientific invariants preserved

The September 11 D2-0007 closure and P1 productionization work did **not**:

- mutate D2-0005;
- access D2-0007 held-out data;
- build unearned anchor support;
- open D2-0007 optimization after a failed screen;
- create or promote Alpha-002;
- replace or rebind Alpha-001;
- claim physical efficacy;
- place an order or authorize spend.

## Documentation authority map

- `CURRENT_PROGRAM_STATE.md` — canonical current program status.
- `PROJECT_PROGRESS_CURRENT.md` — this detailed current ledger.
- `P1_PRODUCTION_RELEASE_GATE.md` — canonical real-production software entry point.
- `P1_PRODUCTION_LAUNCH.md` — production handoff and source-recovery context.
- `USER_ACTION_NEXT_STEPS.md` — current operator checklist.
- `ARCHITECTURE.md` / `DIAGRAMS.md` — explanatory topology.
- `PROJECT_PROGRESS.md` — historical Sep. 8 milestone ledger.

Historical records remain immutable provenance and should not be rewritten simply to match current wording.

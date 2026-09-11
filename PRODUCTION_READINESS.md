# Production Readiness Gates

**State review:** 2026-09-11  
**Reviewed baseline:** `main` at `8114e2189a255bed3d4c07708d7380c7ade2aefc`

Status language is intentionally strict. **PASS** means the repository contains working software/evidence for that gate. It does not imply physical-world efficacy.

## Current readiness snapshot

| Gate | Status | Evidence / remaining action |
| --- | --- | --- |
| Core Python package | **PASS** | `ruthless_pipeline/` package is active and packaged |
| Cross-version CI | **PASS** | Current head completed Python 3.10/3.11/3.12 tests plus package, dependency, provenance, and deployment checks successfully |
| Research / certification framework | **PASS AS SOFTWARE** | Frozen contracts, evidence states, provenance, numerical checks, sealing, and fail-closed transitions exist |
| Engineering Barriers 0–3 | **CLOSED FOR DECLARED SCOPE** | Inventory, schema freeze, subsystem integration, and end-to-end synthetic integration are closed |
| Pattern Genome v1 | **FROZEN** | Additive/versioned successors only |
| D2-0003 | **CLOSED NEGATIVE / RAC-D0** | Retained; Alpha-001 remains bound to this lineage |
| D2-0004 | **CLOSED NEGATIVE / RAC-D0** | Retained and immutable |
| D2-0005 | **PREREGISTERED / NOT ARMED** | No change from production work |
| D2-0007 | **CLOSED — SCREENED_OUT_H0** | 64/64 Stage-1 compositions evaluated; zero survivors; no held-out access or Alpha-002 |
| Exact Alpha-001 source | **RECOVERED / HASH VERIFIED** | Sealed kit and 4096×4096 pattern match frozen pins; recovery receipt committed |
| Printful live intake | **READY AS SOFTWARE** | `tools/p1_production_release.py intake`; still needs operator token + size + live vendor responses |
| Exact production-art build | **READY AS SOFTWARE** | `tools/p1_production_release.py build`; requires recovered exact kit and live intake receipt |
| Vendor evidence integrity | **PASS AS SOFTWARE** | Raw response, archive, intake self-hash, product identity, and placement validation fail closed |
| P1 UA binding | **READY AS SOFTWARE** | Generated/verified vendor values still need controlled binding before procurement |
| P1 no-spend readiness | **READY / FAIL-CLOSED** | Existing readiness freeze and verifier protect the transition to procurement |
| Authoritative P1 schedule | **FROZEN — 144 TRIALS** | Older 108-row planning sheet is superseded for execution |
| Calibration target generator | **PASS AS SOFTWARE** | Physical target still needs fabrication and measurement |
| Receipt QA / custody procedure | **SPECIFIED** | Requires real manufactured garments |
| P1 physical evidence | **OPEN — NOT EXECUTED** | Requires matched candidate/control specimens and accepted calibration |
| P2 durability | **OPEN — EXTERNAL** | Requires valid P1 baseline first |
| M1/M2 manufacturing evidence | **OPEN — EXTERNAL** | Requires golden-sample and lot-conformity measurements |
| Product physical-efficacy claim | **NOT SUPPORTED** | Cannot be promoted before physical evidence closes |

## Canonical production path

For real Alpha-001 manufacturing, use the strict release wrapper:

```bash
export PF_TOKEN='<secret>'

python tools/p1_production_release.py intake \
  --fetch \
  --size M \
  --output-dir production_alpha/vendor_intake

python tools/p1_production_release.py build \
  --intake production_alpha/vendor_intake/vendor-intake.json \
  --print-test-kit /secure/path/print-test-kit.zip \
  --recorded-by '<operator>'
```

The wrapper does not place an order or authorize spend.

After operator review:

```bash
python tools/p1_bind_ua_values.py \
  --values production_alpha/vendor_intake/ua-values.generated.json \
  --check-only

python tools/p1_bind_ua_values.py \
  --values production_alpha/vendor_intake/ua-values.generated.json

python tools/p1_no_spend_readiness_gate.py
```

Proceed to procurement only after the controlled binding and readiness checks pass and a human explicitly authorizes the spend.

## Alpha-001 source integrity

The original sealed source was recovered from successful historical workflow run `34078238095` and is recorded at `evidence/p1/alpha001-source-recovery.json`.

Frozen pins:

```text
sealed print-test-kit.zip
b22b022fd98bc8587251099464010dbc3288f8da70756e183f8e366be06f0548

pattern_tile_4096.png
b07b617fe6dbe178330fff2d9f65c2b720948b641e2bd4865e43ebd62c261546
```

Any mismatch blocks production. Do not regenerate Alpha-001 to make a mismatch disappear.

## P1 execution authority

The current physical execution authority is:

- `physical/p1/P1_CAPTURE_SCHEDULE.json` — 144 frozen trials;
- `physical/p1/PAIRING_RANDOMIZATION_CONTRACT.json`;
- `physical/p1/P1_OPERATOR_RUNBOOK.md`;
- `physical/p1/P1_READINESS_FREEZE.json`;
- `tools/p1_no_spend_readiness_gate.py`.

Older 108-row Print Alpha planning material is retained as historical provenance but is not executable authority.

## Immediate readiness order

1. Verify current-head CI and readiness state.
2. Verify the recovered Alpha-001 kit hash.
3. Choose the real garment size and use a local Printful token.
4. Run the strict live vendor intake.
5. Build exact panel artwork from the recovered kit.
6. Review variant/geometry/artwork/archive hashes.
7. Run binder `--check-only`, then controlled binding.
8. Re-run no-spend readiness and require PASS.
9. Make a separate human procurement decision.
10. Order a matched candidate/control hoodie pair.
11. Fabricate and physically verify `RAC-CALT-P1-0001`.
12. Perform receipt QA and chain of custody.
13. Accept calibration under the frozen runbook.
14. Execute the frozen 144-trial P1 schedule.
15. Ingest and seal evidence before analysis or claims.

## Scientific stop conditions

Do not proceed if:

- a vendor field would need to be guessed;
- the live vendor response conflicts with the declared product/placement contract;
- the recovered source hash does not match;
- the release gate, binder, or readiness gate refuses;
- candidate/control are not materially matched except for artwork;
- a protected scientific surface changes unexpectedly;
- receipt QA or calibration fails.

## Evidence boundary

The repository is now **production-ready as a research system**, meaning it has a controlled path from exact frozen source + live vendor data to matched physical specimens and a frozen physical trial. It is **not product-validated** and is not evidence that a garment will evade arbitrary real-world vision systems.

Physical efficacy remains `false` until admissible P1 measurements exist and the preregistered analysis is complete.

## Current documentation

- `docs/CURRENT_PROGRAM_STATE.md` — canonical program state.
- `docs/P1_PRODUCTION_RELEASE_GATE.md` — strict production release entry point.
- `docs/P1_PRODUCTION_LAUNCH.md` — detailed production handoff.
- `docs/USER_ACTION_NEXT_STEPS.md` — human operator checklist.
- `physical/p1/P1_OPERATOR_RUNBOOK.md` — authoritative physical execution procedure.

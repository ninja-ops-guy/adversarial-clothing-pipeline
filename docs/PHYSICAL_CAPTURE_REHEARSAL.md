# Physical Capture Rehearsal (synthetic, non-measured)

**Status:** `physical_test_executed=false` · `physical_efficacy_claimed=false` ·
`evidence_label=synthetic_pipeline_validation_only` on every artifact.

This document records the end-to-end rehearsal of the full physical chain with
**synthetic fixtures only**. No garment was printed, no capture rig ran, no
detector model executed, and no held-out data was touched. The rehearsal proves
the artifact chain and its failure-handling protocol are wired correctly before
any physical session.

Machinery:

- `ruthless_pipeline/certification/physical_capture_rehearsal.py` — chain driver
- `scripts/rehearse_physical_capture.py` — CLI (`--twice` proves determinism)
- `tests/test_physical_capture_rehearsal.py` — 12 tests

## Chain stages rehearsed

1. **Print Alpha package** — synthetic control + candidate garment specimens
   (hash-seeded artwork/garment digests; `physical_item_exists=false`).
2. **Receipt representation** — binds specimen hashes into a synthetic receipt.
3. **Calibration ingestion** — synthetic `PrintCameraProfile` through the real
   `certification.calibration_ingest` acceptance (ΔE ≤ 6, scale ≤ 2%,
   registration ≤ 3 mm).
4. **Capture Lab** — capture registration enforcing unique capture identity and
   mandatory calibration-profile association.
5. **Trial store** — hash-chained JSONL store over the 108-row Print Alpha
   trial geometry (`print-alpha/CAPTURE/trial-sheet.csv`: 3 distances
   {2, 5, 8 m} × 3 yaws {−30, 0, +30°} × 1 pitch × 2 poses × 2 lightings × 3
   repeats = 108 matched pairs).
6. **Detector-response ingestion** — hash-seeded mock detector
   (`MOCK-DETECTOR-SYNTHETIC-NOT-A-MODEL`); never a real model, never held-out.
7. **Statistics** — real `paired_trial_statistics`, `invalid_condition_report`,
   preregistered stopping rule (`physical/p1/STOPPING_RULE.json`, read-only).
8. **Research OS registration** — real `ExperimentRegistry` /
   `ExperimentArtifact` (`RAC-EXP-2026-901`,
   `evidence_label=scenario_assumption` + `evidence_class=synthetic_pipeline_validation_only`
   validity flag, `rac_evidence_eligible=false`).
9. **Report** — real `certification.report_compiler.compile_report`.
10. **Release + verification** — sealed rehearsal release with
    `ReleaseManifest`; `verify_release` must pass.

## Run table (reference run at author HEAD a797efa)

| Metric | Value |
|---|---|
| Total trials (synthetic) | 108 |
| Valid trials | 106 |
| Invalid trials | 2 (synthetic injected, control-undetected) |
| Calibration acceptance | pass |
| Stopping decision | `may_stop=true` — "preregistered stopping criteria satisfied" |
| Stopping-rule replay | deterministic (two evaluations identical) |
| Release verification | `ok=true` |
| Release content hash | `292f80b93a85206d3445fbaec82b7059ce4c70e4fd2497788f378730c1cccf17` |

## Failure-injection results

| Injection | Expected protocol behaviour | Result |
|---|---|---|
| Duplicate capture identity | `DuplicateCaptureError` | rejected ✔ |
| Calibration association missing | `CalibrationAssociationError` | rejected ✔ |
| Invalid-condition over threshold (condition `D02_Y+00_P0_STANDING_INDOOR_EVEN` forced fully invalid; fraction 1.0 > 0.10 flag) | excluded from valid trials, flagged, **never** counted as candidate success | handled ✔ (`counted_as_candidate_success=false`) |
| Stopping-rule replay | two evaluations byte-identical | deterministic ✔ |
| Tampered trial store (bit-flip in line 3) | hash-chain break detected | `TrialStoreTamperedError` at line 4 ✔ |
| Promotion attempt to `physical_garment_p1` | refused | `PromotionRefusedError` ✔ |

Promotion is **impossible** by construction: `promote_rehearsal_release`
raises `PromotionRefusedError` for any release carrying
`evidence_label=synthetic_pipeline_validation_only` (and refuses anything else
too). Synthetic NEVER promotes to measured.

## Artifact hashes (run 1)

| Artifact | SHA-256 |
|---|---|
| print-alpha-package.json | `982ebabf697b0747e8dd4487b7671ff749e0d630b989beb1212f91f64d355407` |
| receipt.json | `da8e9429f9ffbef566f99eb35128cc9e98025564122ede354973c77f0de718d1` |
| calibration-profile.json | `ed7eb549414fd5b541bdb8282273d5cf6dc082f06bf964fe23836a4e1ffbc8fa` |
| capture-lab.json | `6a01fb59f8372e6b8c802433eb958d2698307f4702a59b1d9f283d26894f257c` |
| trial-store.jsonl | `01261500eaaae594715755a2d79f6c938217b4d1b58a589590540743cea9d81b` |
| statistics.json | `8059fbfae17a08b92ce724847b6e09aa0f25ad1fd3e6623769148b7fdbd884ad` |
| research-os-registry.json | `d55012f9d42e58573ba1c6c56dcc4eb45a3f6000e3575336cbbb24b2e3fc1caf` |
| REPORT.md | `ebd36f542364a8633cad2ac21a947ce1e3ab75fc25999dc83a1b857607b5a902` |
| report.json | `e600c762acc334f2a7ed73b180b3e9fae8c8a8e275c2465857d93980506135a4` |
| release/RELEASE.json | `b221cbcfd81955b28e19d6888ad1e2b7b757fbbc7ea435fa539847c975f3d72b` |
| release/MANIFEST.json | `b126787a24327c123411f85caef4fb9894a7ecfe3b917de7d116d1fcc48e72c2` |

## Determinism

Two full independent runs produce byte-identical artifacts:

| Run | summary.json SHA-256 |
|---|---|
| run 1 | `a8b8466b0a1ded4140c57e5e4fcd1901bd68e194f9a5c1c2e905ddf44423df36` |
| run 2 (replay) | `a8b8466b0a1ded4140c57e5e4fcd1901bd68e194f9a5c1c2e905ddf44423df36` |

Identical: **true**. All synthetic values derive from SHA-256 of stable
identifiers; no wall-clock reads, no ambient RNG.

## Boundaries

- `physical_test_executed=false`, `physical_efficacy_claimed=false` on every
  artifact and on this document.
- No D2-0004/D2-0005 surfaces were modified or executed; no held-out sets were
  accessed; no bootstrap/threshold parameters of the preregistrations were
  touched (stopping rule is loaded read-only).
- Reproduce with:
  `PYTHONPATH=. python scripts/rehearse_physical_capture.py --twice`
